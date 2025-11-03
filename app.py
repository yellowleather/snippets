import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

# Firestore import
try:
    from google.cloud import firestore
    db = firestore.Client()
    FIRESTORE_AVAILABLE = True
except Exception:
    # For local development without credentials
    db = None
    FIRESTORE_AVAILABLE = False

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-to-a-random-secret-key')

# Configuration
USERNAME = os.environ.get('SNIPPET_USERNAME', 'admin')
PASSWORD_HASH = generate_password_hash(os.environ.get('SNIPPET_PASSWORD', 'changeme'), method='pbkdf2:sha256')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_week_dates(date):
    """Get Monday and Sunday of the week containing the given date"""
    # Get the weekday (0 = Monday, 6 = Sunday)
    weekday = date.weekday()
    # Calculate Monday of this week
    monday = date - timedelta(days=weekday)
    # Calculate Sunday of this week
    sunday = monday + timedelta(days=6)
    return monday, sunday

def get_week_number(date):
    """Get ISO week number"""
    return date.isocalendar()[1]

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if username == USERNAME and check_password_hash(PASSWORD_HASH, password):
            session['logged_in'] = True
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/api/snippets', methods=['GET'])
@login_required
def get_snippets():
    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    snippets_ref = db.collection('snippets')

    if start_date and end_date:
        # Query all snippets ordered by week_start
        # Filter client-side for overlapping weeks
        # week overlaps with range if week_start <= end_date AND week_end >= start_date
        query = snippets_ref.order_by('week_start', direction=firestore.Query.DESCENDING)

        snippets = []
        for doc in query.stream():
            snippet = doc.to_dict()
            snippet['id'] = doc.id
            # Filter: week overlaps if week_start <= end_date AND week_end >= start_date
            if snippet['week_start'] <= end_date and snippet['week_end'] >= start_date:
                snippets.append(snippet)
    else:
        query = snippets_ref.order_by('week_start', direction=firestore.Query.DESCENDING).limit(10)
        snippets = []
        for doc in query.stream():
            snippet = doc.to_dict()
            snippet['id'] = doc.id
            snippets.append(snippet)

    return jsonify(snippets)

@app.route('/api/snippets/<snippet_id>', methods=['GET'])
@login_required
def get_snippet(snippet_id):
    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    doc_ref = db.collection('snippets').document(snippet_id)
    doc = doc_ref.get()

    if doc.exists:
        snippet = doc.to_dict()
        snippet['id'] = doc.id
        return jsonify(snippet)
    return jsonify({'error': 'Snippet not found'}), 404

@app.route('/api/snippets', methods=['POST'])
@login_required
def create_snippet():
    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    data = request.get_json()
    week_start = data.get('week_start')
    week_end = data.get('week_end')
    content = data.get('content')

    if not all([week_start, week_end, content]):
        return jsonify({'error': 'Missing required fields'}), 400

    doc_ref = db.collection('snippets').document()
    doc_ref.set({
        'week_start': week_start,
        'week_end': week_end,
        'content': content,
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    })

    return jsonify({'id': doc_ref.id, 'success': True})

@app.route('/api/snippets/<snippet_id>', methods=['PUT'])
@login_required
def update_snippet(snippet_id):
    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    data = request.get_json()
    content = data.get('content')

    if not content:
        return jsonify({'error': 'Content is required'}), 400

    doc_ref = db.collection('snippets').document(snippet_id)
    doc_ref.update({
        'content': content,
        'updated_at': firestore.SERVER_TIMESTAMP
    })

    return jsonify({'success': True})

@app.route('/api/snippets/<snippet_id>', methods=['DELETE'])
@login_required
def delete_snippet(snippet_id):
    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    db.collection('snippets').document(snippet_id).delete()

    return jsonify({'success': True})

@app.route('/api/week/<date_str>', methods=['GET'])
@login_required
def get_week_info(date_str):
    """Get week information for a specific date"""
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        monday, sunday = get_week_dates(date)
        week_num = get_week_number(date)

        return jsonify({
            'week_number': week_num,
            'week_start': monday.strftime('%Y-%m-%d'),
            'week_end': sunday.strftime('%Y-%m-%d'),
            'week_start_formatted': monday.strftime('%b %d, %Y'),
            'week_end_formatted': sunday.strftime('%b %d, %Y')
        })
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
