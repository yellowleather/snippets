import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-to-a-random-secret-key')

# Configuration
DATABASE = 'snippets.db'
USERNAME = os.environ.get('SNIPPET_USERNAME', 'admin')
PASSWORD_HASH = generate_password_hash(os.environ.get('SNIPPET_PASSWORD', 'changeme'), method='pbkdf2:sha256')

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS snippets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT NOT NULL,
            week_end TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.commit()

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
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    db = get_db()
    
    if start_date and end_date:
        snippets = db.execute(
            'SELECT * FROM snippets WHERE week_start >= ? AND week_end <= ? ORDER BY week_start DESC',
            (start_date, end_date)
        ).fetchall()
    else:
        snippets = db.execute(
            'SELECT * FROM snippets ORDER BY week_start DESC LIMIT 10'
        ).fetchall()
    
    return jsonify([dict(snippet) for snippet in snippets])

@app.route('/api/snippets/<int:snippet_id>', methods=['GET'])
@login_required
def get_snippet(snippet_id):
    db = get_db()
    snippet = db.execute('SELECT * FROM snippets WHERE id = ?', (snippet_id,)).fetchone()
    
    if snippet:
        return jsonify(dict(snippet))
    return jsonify({'error': 'Snippet not found'}), 404

@app.route('/api/snippets', methods=['POST'])
@login_required
def create_snippet():
    data = request.get_json()
    week_start = data.get('week_start')
    week_end = data.get('week_end')
    content = data.get('content')
    
    if not all([week_start, week_end, content]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    db = get_db()
    cursor = db.execute(
        'INSERT INTO snippets (week_start, week_end, content) VALUES (?, ?, ?)',
        (week_start, week_end, content)
    )
    db.commit()
    
    return jsonify({'id': cursor.lastrowid, 'success': True})

@app.route('/api/snippets/<int:snippet_id>', methods=['PUT'])
@login_required
def update_snippet(snippet_id):
    data = request.get_json()
    content = data.get('content')
    
    if not content:
        return jsonify({'error': 'Content is required'}), 400
    
    db = get_db()
    db.execute(
        'UPDATE snippets SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (content, snippet_id)
    )
    db.commit()
    
    return jsonify({'success': True})

@app.route('/api/snippets/<int:snippet_id>', methods=['DELETE'])
@login_required
def delete_snippet(snippet_id):
    db = get_db()
    db.execute('DELETE FROM snippets WHERE id = ?', (snippet_id,))
    db.commit()
    
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

@app.route('/api/snippets/search', methods=['GET'])
@login_required
def search_snippets():
    """Search snippets by content with improved matching"""
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify([])
    
    # Split the search query into words
    search_terms = query.split()
    if not search_terms:
        return jsonify([])
    
    db = get_db()
    
    # Build the WHERE clause for multiple terms (AND condition)
    where_clause = ' AND '.join(['LOWER(content) LIKE ?' for _ in search_terms])
    # Prepare the parameters for each term
    params = [f'%{term}%' for term in search_terms]
    
    snippets = db.execute(
        f'''SELECT *, 
            (LENGTH(content) - LENGTH(REPLACE(LOWER(content), ?, ''))) / LENGTH(?) as match_score
            FROM snippets 
            WHERE {where_clause}
            ORDER BY match_score DESC, week_start DESC''',
        params + [query, query]  # Add params for match_score calculation
    ).fetchall()
    
    return jsonify([dict(snippet) for snippet in snippets])

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5001)
