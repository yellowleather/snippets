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

# Feature Flags
GOALS_ENABLED = os.environ.get('GOALS_ENABLED', 'true').lower() == 'true'
REFLECTIONS_ENABLED = os.environ.get('REFLECTIONS_ENABLED', 'true').lower() == 'true'
DAILY_SCORES_ENABLED = os.environ.get('DAILY_SCORES_ENABLED', 'true').lower() == 'true'

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

@app.route('/api/config', methods=['GET'])
@login_required
def get_config():
    """Return feature flags and configuration"""
    return jsonify({
        'goals_enabled': GOALS_ENABLED,
        'reflections_enabled': REFLECTIONS_ENABLED,
        'daily_scores_enabled': DAILY_SCORES_ENABLED
    })

@app.route('/api/snippets', methods=['GET'])
@login_required
def get_snippets():
    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    endeavor = request.args.get('endeavor', 'pet project')

    snippets_ref = db.collection('snippets')

    if start_date and end_date:
        # Query all snippets ordered by week_start
        # Filter client-side for overlapping weeks and endeavor
        # week overlaps with range if week_start <= end_date AND week_end >= start_date
        query = snippets_ref.order_by('week_start', direction=firestore.Query.DESCENDING)

        snippets = []
        for doc in query.stream():
            snippet = doc.to_dict()
            snippet['id'] = doc.id
            # Filter: week overlaps if week_start <= end_date AND week_end >= start_date
            # Also filter by endeavor, defaulting to 'pet project' for old records
            snippet_endeavor = snippet.get('endeavor', 'pet project')
            if snippet['week_start'] <= end_date and snippet['week_end'] >= start_date and snippet_endeavor == endeavor:
                snippets.append(snippet)
    else:
        query = snippets_ref.order_by('week_start', direction=firestore.Query.DESCENDING).limit(10)
        snippets = []
        for doc in query.stream():
            snippet = doc.to_dict()
            snippet['id'] = doc.id
            # Filter by endeavor, defaulting to 'pet project' for old records
            snippet_endeavor = snippet.get('endeavor', 'pet project')
            if snippet_endeavor == endeavor:
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
    endeavor = data.get('endeavor', 'pet project')

    if not all([week_start, week_end, content]):
        return jsonify({'error': 'Missing required fields'}), 400

    doc_ref = db.collection('snippets').document()
    doc_ref.set({
        'week_start': week_start,
        'week_end': week_end,
        'content': content,
        'endeavor': endeavor,
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


# Goals API endpoints
@app.route('/api/goals', methods=['GET'])
@login_required
def get_goals():
    if not GOALS_ENABLED:
        return jsonify({'error': 'Goals feature is disabled'}), 404

    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    endeavor = request.args.get('endeavor', 'pet project')

    goals_ref = db.collection('goals')

    if start_date and end_date:
        query = goals_ref.order_by('week_start', direction=firestore.Query.DESCENDING)

        goals = []
        for doc in query.stream():
            goal = doc.to_dict()
            goal['id'] = doc.id
            # Filter by endeavor, defaulting to 'pet project' for old records
            goal_endeavor = goal.get('endeavor', 'pet project')
            if goal['week_start'] <= end_date and goal['week_end'] >= start_date and goal_endeavor == endeavor:
                goals.append(goal)
    else:
        query = goals_ref.order_by('week_start', direction=firestore.Query.DESCENDING).limit(10)
        goals = []
        for doc in query.stream():
            goal = doc.to_dict()
            goal['id'] = doc.id
            # Filter by endeavor, defaulting to 'pet project' for old records
            goal_endeavor = goal.get('endeavor', 'pet project')
            if goal_endeavor == endeavor:
                goals.append(goal)

    return jsonify(goals)


@app.route('/api/goals/<goal_id>', methods=['GET'])
@login_required
def get_goal(goal_id):
    if not GOALS_ENABLED:
        return jsonify({'error': 'Goals feature is disabled'}), 404

    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    doc_ref = db.collection('goals').document(goal_id)
    doc = doc_ref.get()

    if doc.exists:
        goal = doc.to_dict()
        goal['id'] = doc.id
        return jsonify(goal)
    return jsonify({'error': 'Goal not found'}), 404


@app.route('/api/goals', methods=['POST'])
@login_required
def create_goal():
    if not GOALS_ENABLED:
        return jsonify({'error': 'Goals feature is disabled'}), 404

    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    data = request.get_json()
    week_start = data.get('week_start')
    week_end = data.get('week_end')
    content = data.get('content')
    endeavor = data.get('endeavor', 'pet project')

    if not all([week_start, week_end, content]):
        return jsonify({'error': 'Missing required fields'}), 400

    doc_ref = db.collection('goals').document()
    doc_ref.set({
        'week_start': week_start,
        'week_end': week_end,
        'content': content,
        'endeavor': endeavor,
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    })

    return jsonify({'id': doc_ref.id, 'success': True})


@app.route('/api/goals/<goal_id>', methods=['PUT'])
@login_required
def update_goal(goal_id):
    if not GOALS_ENABLED:
        return jsonify({'error': 'Goals feature is disabled'}), 404

    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    data = request.get_json()
    content = data.get('content')

    if not content:
        return jsonify({'error': 'Content is required'}), 400

    doc_ref = db.collection('goals').document(goal_id)
    doc_ref.update({
        'content': content,
        'updated_at': firestore.SERVER_TIMESTAMP
    })

    return jsonify({'success': True})


@app.route('/api/goals/<goal_id>', methods=['DELETE'])
@login_required
def delete_goal(goal_id):
    if not GOALS_ENABLED:
        return jsonify({'error': 'Goals feature is disabled'}), 404

    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    db.collection('goals').document(goal_id).delete()

    return jsonify({'success': True})


# Reflections API endpoints
@app.route('/api/reflections', methods=['GET'])
@login_required
def get_reflections():
    if not REFLECTIONS_ENABLED:
        return jsonify({'error': 'Reflections feature is disabled'}), 404

    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    endeavor = request.args.get('endeavor', 'pet project')

    reflections_ref = db.collection('reflections')

    if start_date and end_date:
        query = reflections_ref.order_by('week_start', direction=firestore.Query.DESCENDING)

        reflections = []
        for doc in query.stream():
            reflection = doc.to_dict()
            reflection['id'] = doc.id
            # Filter by endeavor, defaulting to 'pet project' for old records
            reflection_endeavor = reflection.get('endeavor', 'pet project')
            if reflection['week_start'] <= end_date and reflection['week_end'] >= start_date and reflection_endeavor == endeavor:
                reflections.append(reflection)
    else:
        query = reflections_ref.order_by('week_start', direction=firestore.Query.DESCENDING).limit(10)
        reflections = []
        for doc in query.stream():
            reflection = doc.to_dict()
            reflection['id'] = doc.id
            # Filter by endeavor, defaulting to 'pet project' for old records
            reflection_endeavor = reflection.get('endeavor', 'pet project')
            if reflection_endeavor == endeavor:
                reflections.append(reflection)

    return jsonify(reflections)


@app.route('/api/reflections/<reflection_id>', methods=['GET'])
@login_required
def get_reflection(reflection_id):
    if not REFLECTIONS_ENABLED:
        return jsonify({'error': 'Reflections feature is disabled'}), 404

    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    doc_ref = db.collection('reflections').document(reflection_id)
    doc = doc_ref.get()

    if doc.exists:
        reflection = doc.to_dict()
        reflection['id'] = doc.id
        return jsonify(reflection)
    return jsonify({'error': 'Reflection not found'}), 404


@app.route('/api/reflections', methods=['POST'])
@login_required
def create_reflection():
    if not REFLECTIONS_ENABLED:
        return jsonify({'error': 'Reflections feature is disabled'}), 404

    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    data = request.get_json()
    week_start = data.get('week_start')
    week_end = data.get('week_end')
    content = data.get('content')
    endeavor = data.get('endeavor', 'pet project')

    if not all([week_start, week_end, content]):
        return jsonify({'error': 'Missing required fields'}), 400

    doc_ref = db.collection('reflections').document()
    doc_ref.set({
        'week_start': week_start,
        'week_end': week_end,
        'content': content,
        'endeavor': endeavor,
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    })

    return jsonify({'id': doc_ref.id, 'success': True})


@app.route('/api/reflections/<reflection_id>', methods=['PUT'])
@login_required
def update_reflection(reflection_id):
    if not REFLECTIONS_ENABLED:
        return jsonify({'error': 'Reflections feature is disabled'}), 404

    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    data = request.get_json()
    content = data.get('content')

    if not content:
        return jsonify({'error': 'Content is required'}), 400

    doc_ref = db.collection('reflections').document(reflection_id)
    doc_ref.update({
        'content': content,
        'updated_at': firestore.SERVER_TIMESTAMP
    })

    return jsonify({'success': True})


@app.route('/api/reflections/<reflection_id>', methods=['DELETE'])
@login_required
def delete_reflection(reflection_id):
    if not REFLECTIONS_ENABLED:
        return jsonify({'error': 'Reflections feature is disabled'}), 404

    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    db.collection('reflections').document(reflection_id).delete()

    return jsonify({'success': True})


# Daily Movement Scores API endpoints
@app.route('/api/daily_scores', methods=['GET'])
@login_required
def get_daily_scores():
    if not DAILY_SCORES_ENABLED:
        return jsonify({'error': 'Daily scores feature is disabled'}), 404

    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    endeavor = request.args.get('endeavor', 'pet project')

    scores_ref = db.collection('daily_scores')

    if start_date and end_date:
        # Query all scores and filter by date range and endeavor
        query = scores_ref.order_by('date')

        scores = []
        for doc in query.stream():
            score = doc.to_dict()
            score['id'] = doc.id
            # Filter by endeavor, defaulting to 'pet project' for old records
            score_endeavor = score.get('endeavor', 'pet project')
            if score['date'] >= start_date and score['date'] <= end_date and score_endeavor == endeavor:
                scores.append(score)
    else:
        # Get recent scores
        query = scores_ref.order_by('date', direction=firestore.Query.DESCENDING).limit(30)
        scores = []
        for doc in query.stream():
            score = doc.to_dict()
            score['id'] = doc.id
            # Filter by endeavor, defaulting to 'pet project' for old records
            score_endeavor = score.get('endeavor', 'pet project')
            if score_endeavor == endeavor:
                scores.append(score)

    return jsonify(scores)


@app.route('/api/daily_scores/toggle', methods=['POST'])
@login_required
def toggle_daily_score():
    if not DAILY_SCORES_ENABLED:
        return jsonify({'error': 'Daily scores feature is disabled'}), 404

    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    data = request.get_json()
    date = data.get('date')
    endeavor = data.get('endeavor', 'pet project')

    if not date:
        return jsonify({'error': 'Date is required'}), 400

    # Check if score already exists for this date and endeavor
    scores_ref = db.collection('daily_scores')
    query = scores_ref.where('date', '==', date).where('endeavor', '==', endeavor).limit(1)

    existing_docs = list(query.stream())

    if existing_docs:
        # Score exists (is 1), delete it to set to 0
        existing_docs[0].reference.delete()
        return jsonify({'success': True, 'score': 0})
    else:
        # Score doesn't exist (is 0), create it to set to 1
        doc_ref = scores_ref.document()
        doc_ref.set({
            'date': date,
            'score': 1,
            'endeavor': endeavor,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        return jsonify({'success': True, 'score': 1, 'id': doc_ref.id})


# Endeavors API endpoints
@app.route('/api/endeavors', methods=['GET'])
@login_required
def get_endeavors():
    """Get list of all unique endeavors across all collections"""
    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    endeavors = set()

    # Get endeavors from snippets
    snippets_ref = db.collection('snippets')
    for doc in snippets_ref.stream():
        snippet = doc.to_dict()
        endeavor = snippet.get('endeavor', 'pet project')
        endeavors.add(endeavor)

    # Get endeavors from goals (if enabled)
    if GOALS_ENABLED:
        goals_ref = db.collection('goals')
        for doc in goals_ref.stream():
            goal = doc.to_dict()
            endeavor = goal.get('endeavor', 'pet project')
            endeavors.add(endeavor)

    # Get endeavors from reflections (if enabled)
    if REFLECTIONS_ENABLED:
        reflections_ref = db.collection('reflections')
        for doc in reflections_ref.stream():
            reflection = doc.to_dict()
            endeavor = reflection.get('endeavor', 'pet project')
            endeavors.add(endeavor)

    # Get endeavors from daily_scores (if enabled)
    if DAILY_SCORES_ENABLED:
        scores_ref = db.collection('daily_scores')
        for doc in scores_ref.stream():
            score = doc.to_dict()
            endeavor = score.get('endeavor', 'pet project')
            endeavors.add(endeavor)

    # Convert set to sorted list
    endeavors_list = sorted(list(endeavors))

    return jsonify(endeavors_list)


@app.route('/api/endeavors/rename', methods=['POST'])
@login_required
def rename_endeavor():
    """Rename an endeavor across all collections"""
    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    data = request.get_json()
    old_name = data.get('old_name')
    new_name = data.get('new_name')

    if not old_name or not new_name:
        return jsonify({'error': 'Both old_name and new_name are required'}), 400

    if not new_name.strip():
        return jsonify({'error': 'New endeavor name cannot be empty'}), 400

    updated_count = 0

    # Update snippets
    snippets_ref = db.collection('snippets')
    for doc in snippets_ref.stream():
        snippet = doc.to_dict()
        endeavor = snippet.get('endeavor', 'pet project')
        if endeavor == old_name:
            doc.reference.update({
                'endeavor': new_name,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            updated_count += 1

    # Update goals (if enabled)
    if GOALS_ENABLED:
        goals_ref = db.collection('goals')
        for doc in goals_ref.stream():
            goal = doc.to_dict()
            endeavor = goal.get('endeavor', 'pet project')
            if endeavor == old_name:
                doc.reference.update({
                    'endeavor': new_name,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                updated_count += 1

    # Update reflections (if enabled)
    if REFLECTIONS_ENABLED:
        reflections_ref = db.collection('reflections')
        for doc in reflections_ref.stream():
            reflection = doc.to_dict()
            endeavor = reflection.get('endeavor', 'pet project')
            if endeavor == old_name:
                doc.reference.update({
                    'endeavor': new_name,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                updated_count += 1

    # Update daily_scores (if enabled)
    if DAILY_SCORES_ENABLED:
        scores_ref = db.collection('daily_scores')
        for doc in scores_ref.stream():
            score = doc.to_dict()
            endeavor = score.get('endeavor', 'pet project')
            if endeavor == old_name:
                doc.reference.update({
                    'endeavor': new_name,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                updated_count += 1

    return jsonify({'success': True, 'updated_count': updated_count})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
