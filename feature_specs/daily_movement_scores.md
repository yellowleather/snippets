# Daily Movement Scores Feature Specification

## Overview

The Daily Movement Scores feature allows users to track their daily "movement" or progress with a simple binary scoring system (win/loss) for each day of the week. Each week displays a visual meter with 7 squares representing Monday through Sunday, where users can click past day squares to toggle between a "win" (green) and "loss" (white/default) state.

## Use Cases

1. **Habit Tracking**: Track whether you completed a daily habit (exercise, meditation, etc.)
2. **Goal Progress**: Binary success/fail tracking for daily goals
3. **Visual Motivation**: See weekly patterns at a glance with color-coded squares
4. **Retrospective Analysis**: Review past weeks to identify patterns in consistency

## Core Principles

1. **Binary Simplicity**: Only two states - win (1) or default (0)
2. **Visual Clarity**: Instantly see which days were wins via green squares
3. **Past-Only Editing**: Can only toggle scores for days before today (not today or future)
4. **Instant Feedback**: Immediate UI updates without page reload
5. **Storage Efficiency**: Only store wins (1s), not defaults (0s)

## Database Schema

### Firestore Collection: `daily_scores`

Each document represents a single day with a win (score=1). Days without documents default to 0.

```python
{
    'date': '2025-11-04',          # ISO date string (YYYY-MM-DD)
    'score': 1,                    # Always 1 (only wins are stored)
    'created_at': Timestamp,       # Server timestamp
    'updated_at': Timestamp        # Server timestamp
}
```

**Key Fields:**
- `date` (string, required): ISO format YYYY-MM-DD
- `score` (int, required): Always 1 for stored documents
- `created_at` (timestamp): When the win was first recorded
- `updated_at` (timestamp): Last modification time

**Index Requirements:**
- `date` (ascending) - for date range queries
- No composite indexes needed

## Backend Implementation

### Feature Flag

```python
# app.py
DAILY_SCORES_ENABLED = os.environ.get('DAILY_SCORES_ENABLED', 'true').lower() == 'true'
```

### API Endpoints

#### 1. GET /api/daily_scores

Fetch daily scores within a date range.

```python
@app.route('/api/daily_scores', methods=['GET'])
@login_required
def get_daily_scores():
    if not DAILY_SCORES_ENABLED:
        return jsonify({'error': 'Daily scores feature is disabled'}), 404

    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    scores_ref = db.collection('daily_scores')

    if start_date and end_date:
        # Query all scores and filter by date range
        query = scores_ref.order_by('date')

        scores = []
        for doc in query.stream():
            score = doc.to_dict()
            score['id'] = doc.id
            if score['date'] >= start_date and score['date'] <= end_date:
                scores.append(score)
    else:
        # Get recent scores
        query = scores_ref.order_by('date', direction=firestore.Query.DESCENDING).limit(30)
        scores = []
        for doc in query.stream():
            score = doc.to_dict()
            score['id'] = doc.id
            scores.append(score)

    return jsonify(scores)
```

**Query Parameters:**
- `start_date` (optional): ISO date string for range start
- `end_date` (optional): ISO date string for range end

**Returns:** Array of score objects with `id`, `date`, `score`, `created_at`, `updated_at`

#### 2. POST /api/daily_scores/toggle

Toggle a daily score between 0 and 1.

```python
@app.route('/api/daily_scores/toggle', methods=['POST'])
@login_required
def toggle_daily_score():
    if not DAILY_SCORES_ENABLED:
        return jsonify({'error': 'Daily scores feature is disabled'}), 404

    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    data = request.get_json()
    date = data.get('date')

    if not date:
        return jsonify({'error': 'Date is required'}), 400

    # Check if score already exists for this date
    scores_ref = db.collection('daily_scores')
    query = scores_ref.where('date', '==', date).limit(1)

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
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        return jsonify({'success': True, 'score': 1, 'id': doc_ref.id})
```

**Request Body:**
```json
{
    "date": "2025-11-04"
}
```

**Returns:**
```json
{
    "success": true,
    "score": 1,  // 0 or 1
    "id": "doc_id"  // only when creating (score=1)
}
```

#### 3. GET /api/config

Updated to include daily scores feature flag.

```python
@app.route('/api/config', methods=['GET'])
@login_required
def get_config():
    """Return feature flags and configuration"""
    return jsonify({
        'goals_enabled': GOALS_ENABLED,
        'reflections_enabled': REFLECTIONS_ENABLED,
        'daily_scores_enabled': DAILY_SCORES_ENABLED
    })
```

## Frontend Implementation

### Global State

```javascript
let dailyScoresEnabled = true; // Default to true, will be updated from server
```

### Configuration Loading

```javascript
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        goalsEnabled = config.goals_enabled;
        reflectionsEnabled = config.reflections_enabled;
        dailyScoresEnabled = config.daily_scores_enabled;
    } catch (error) {
        console.error('Error loading config:', error);
        goalsEnabled = true;
        reflectionsEnabled = true;
        dailyScoresEnabled = true;
    }
}
```

### Data Loading

```javascript
async function loadSnippets() {
    // ... date range setup ...

    try {
        // Load snippets, conditionally load daily scores, goals and reflections
        const promises = [
            fetch(`/api/snippets?start_date=${queryStart}&end_date=${queryEnd}`)
        ];

        if (dailyScoresEnabled) {
            promises.push(fetch(`/api/daily_scores?start_date=${queryStart}&end_date=${queryEnd}`));
        }

        if (reflectionsEnabled) {
            promises.push(fetch(`/api/reflections?start_date=${queryStart}&end_date=${queryEnd}`));
        }

        if (goalsEnabled) {
            promises.push(fetch(`/api/goals?start_date=${queryStart}&end_date=${queryEnd}`));
        }

        const responses = await Promise.all(promises);
        const snippets = await responses[0].json();

        let dailyScores = [];
        let reflections = [];
        let goals = [];
        let responseIndex = 1;

        if (dailyScoresEnabled) {
            dailyScores = await responses[responseIndex].json();
            responseIndex++;
        }

        if (reflectionsEnabled) {
            reflections = await responses[responseIndex].json();
            responseIndex++;
        }

        if (goalsEnabled) {
            goals = await responses[responseIndex].json();
        }

        // Map daily scores by date for easy lookup
        const scoresMap = {};
        dailyScores.forEach(s => { scoresMap[s.date] = s.score; });

        displayWeeks(universe, snippetsMap, goalsMap, reflectionsMap, scoresMap);
    } catch (error) {
        console.error('Error loading data:', error);
    }
}
```

### Render Score Meter

```javascript
function renderScoreMeter(week, scoresMap) {
    let html = '<div class="score-meter">';
    html += '<span class="score-label">Daily Score</span>';

    // Get today's date for comparison (as ISO string YYYY-MM-DD)
    const today = new Date();
    const todayStr = formatDate(today);

    // Day names for tooltips
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

    // Generate 7 squares for Mon-Sun
    const weekStartDate = new Date(week.weekStartObj);

    for (let i = 0; i < 7; i++) {
        const currentDate = new Date(weekStartDate);
        currentDate.setDate(currentDate.getDate() + i);
        const dateStr = formatDate(currentDate);
        const dayName = dayNames[currentDate.getDay()];

        // Check if this date has a score (1 = win/green, 0/undefined = default/no color)
        const hasScore = scoresMap[dateStr] === 1;

        // Determine if this date is in the past (can be toggled)
        // Past weeks: all 7 days will be < today, so all clickable
        // Current week: only days before today are clickable
        // Today and future: NOT clickable
        const isPast = dateStr < todayStr;
        const isClickable = isPast ? 'clickable' : '';
        const winClass = hasScore ? 'win' : '';

        // Build the square HTML
        if (isPast) {
            html += `<div class="score-square ${winClass} ${isClickable}" onclick="toggleDailyScore('${dateStr}', event)" title="${dayName}"></div>`;
        } else {
            html += `<div class="score-square ${winClass}" title="${dayName}"></div>`;
        }
    }

    html += '</div>';
    return html;
}
```

### Display Weeks (Integration)

```javascript
function displayWeeks(weeks, snippetsMap, goalsMap, reflectionsMap, scoresMap) {
    // ... loop through weeks ...

    for (let i = weeks.length - 1; i >= 0; i--) {
        const week = weeks[i];

        html += `<div class="week-section">`;
        html += `  <div class="week-header">`;
        html += `    <span class="week-badge">Week ${weekNum}</span>`;
        html += `    <h2 class="week-title">${startFormatted} – ${endFormatted}</h2>`;
        if (dailyScoresEnabled) {
            html += renderScoreMeter(week, scoresMap);
        }
        html += `  </div>`;

        // ... rest of week rendering ...
    }
}
```

### Toggle Score Function

```javascript
async function toggleDailyScore(date, event) {
    // Immediate UI update - toggle the square
    const clickedSquare = event ? event.currentTarget : null;
    if (clickedSquare) {
        clickedSquare.classList.toggle('win');
    }

    try {
        // Save to server in background
        const response = await fetch('/api/daily_scores/toggle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ date })
        });

        if (!response.ok) {
            // Revert the UI update on failure
            if (clickedSquare) {
                clickedSquare.classList.toggle('win');
            }
            alert('Failed to update score');
        }
        // No reload needed - the UI is already updated!
    } catch (error) {
        console.error('Error toggling score:', error);
        // Revert the UI update on error
        if (clickedSquare) {
            clickedSquare.classList.toggle('win');
        }
        alert('Failed to update score');
    }
}
```

## CSS Styling

```css
/* Daily Movement Score Meter */
.score-meter {
    display: flex;
    gap: 6px;
    padding: 4px 0;
    margin-left: auto;
    align-items: center;
}

.score-label {
    font-size: 13px;
    color: #5f6368;
    font-weight: 500;
    margin-right: 4px;
}

.score-square {
    width: 28px;
    height: 28px;
    border: 2px solid #dadce0;
    border-radius: 4px;
    background: white;
    transition: all 0.2s ease;
}

.score-square.clickable {
    cursor: pointer;
}

.score-square.clickable:hover {
    border-color: #5f6368;
    transform: scale(1.05);
}

.score-square.win {
    background: #34a853;
    border-color: #34a853;
}

.score-square.win.clickable:hover {
    background: #2d9148;
    border-color: #2d9148;
}
```

## Unit Tests

### Test Class

```python
class TestDailyScores:
    """Test daily movement scores"""

    def test_get_daily_scores_requires_auth(self, client):
        """Test that getting daily scores requires authentication"""
        response = client.get('/api/daily_scores')
        assert response.status_code == 302  # Redirect to login

    def test_toggle_daily_score_create(self, authenticated_client, mock_firestore):
        """Test toggling a daily score from 0 to 1 (create)"""
        # Mock Firestore query that returns no existing score
        mock_query = Mock()
        mock_query.stream.return_value = []
        mock_query.limit.return_value = mock_query

        mock_collection = Mock()
        mock_collection.where.return_value = mock_query

        mock_doc_ref = Mock()
        mock_doc_ref.id = 'test-score-id'
        mock_collection.document.return_value = mock_doc_ref

        mock_firestore.collection.return_value = mock_collection

        score_data = {
            'date': '2025-11-01'
        }

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.post('/api/daily_scores/toggle',
                                                data=json.dumps(score_data),
                                                content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['score'] == 1
        assert 'id' in data
        mock_doc_ref.set.assert_called_once()

    def test_toggle_daily_score_delete(self, authenticated_client, mock_firestore):
        """Test toggling a daily score from 1 to 0 (delete)"""
        # Mock Firestore query that returns an existing score
        mock_doc = Mock()
        mock_doc.reference = Mock()

        mock_query = Mock()
        mock_query.stream.return_value = [mock_doc]
        mock_query.limit.return_value = mock_query

        mock_collection = Mock()
        mock_collection.where.return_value = mock_query
        mock_firestore.collection.return_value = mock_collection

        score_data = {
            'date': '2025-11-01'
        }

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.post('/api/daily_scores/toggle',
                                                data=json.dumps(score_data),
                                                content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['score'] == 0
        mock_doc.reference.delete.assert_called_once()

    def test_toggle_daily_score_missing_date(self, authenticated_client, mock_firestore):
        """Test toggling without providing date"""
        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.post('/api/daily_scores/toggle',
                                                data=json.dumps({}),
                                                content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_daily_scores_with_date_filter(self, authenticated_client, mock_firestore):
        """Test getting daily scores with date range filter"""
        mock_doc1 = Mock()
        mock_doc1.id = 'score-1'
        mock_doc1.to_dict.return_value = {
            'date': '2025-11-01',
            'score': 1
        }

        mock_doc2 = Mock()
        mock_doc2.id = 'score-2'
        mock_doc2.to_dict.return_value = {
            'date': '2025-11-02',
            'score': 1
        }

        mock_query = Mock()
        mock_query.stream.return_value = [mock_doc1, mock_doc2]
        mock_query.order_by.return_value = mock_query

        mock_collection = Mock()
        mock_collection.order_by.return_value = mock_query
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/daily_scores?start_date=2025-11-01&end_date=2025-11-03')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_get_daily_scores_without_filter(self, authenticated_client, mock_firestore):
        """Test getting recent daily scores without date filter"""
        mock_doc = Mock()
        mock_doc.id = 'score-1'
        mock_doc.to_dict.return_value = {
            'date': '2025-11-01',
            'score': 1
        }

        mock_query = Mock()
        mock_query.stream.return_value = [mock_doc]
        mock_query.limit.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        mock_collection = Mock()
        mock_collection.order_by.return_value = mock_query
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/daily_scores')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
```

**Test Coverage**: 6 comprehensive tests covering authentication, create, delete, validation, and querying.

## Configuration

### Environment Variables

**app.yaml.template:**
```yaml
env_variables:
  SNIPPET_USERNAME: __SNIPPET_USERNAME__
  SNIPPET_PASSWORD: __SNIPPET_PASSWORD__
  SECRET_KEY: __SECRET_KEY__
  GOALS_ENABLED: __GOALS_ENABLED__
  REFLECTIONS_ENABLED: __REFLECTIONS_ENABLED__
  DAILY_SCORES_ENABLED: __DAILY_SCORES_ENABLED__
```

**deploy.sh:**
```bash
# Set default for DAILY_SCORES_ENABLED if not provided
if [ -z "$DAILY_SCORES_ENABLED" ]; then
    DAILY_SCORES_ENABLED="true"
fi

# Create app.yaml from template with secrets
sed -e "s|__SNIPPET_USERNAME__|$SNIPPET_USERNAME|g" \
    -e "s|__SNIPPET_PASSWORD__|$SNIPPET_PASSWORD|g" \
    -e "s|__SECRET_KEY__|$SECRET_KEY|g" \
    -e "s|__GOALS_ENABLED__|$GOALS_ENABLED|g" \
    -e "s|__REFLECTIONS_ENABLED__|$REFLECTIONS_ENABLED|g" \
    -e "s|__DAILY_SCORES_ENABLED__|$DAILY_SCORES_ENABLED|g" \
    app.yaml.template > app.yaml
```

**run_local.sh:**
```bash
# Set default for DAILY_SCORES_ENABLED if not in .env.production
if [ -z "$DAILY_SCORES_ENABLED" ]; then
    DAILY_SCORES_ENABLED="true"
fi

# Export environment variables for Flask
export DAILY_SCORES_ENABLED="$DAILY_SCORES_ENABLED"
```

### Disabling the Feature

To disable daily scores:

1. Add to `.env.production`:
   ```bash
   DAILY_SCORES_ENABLED=false
   ```

2. Redeploy:
   ```bash
   ./deploy.sh
   ```

The UI will hide all score meters and the API will return 404 for score endpoints.

## UI/UX Specifications

### Visual Layout

```
[Week 44] [Oct 28, 2024 – Nov 3, 2024]    Daily Score [□][□][■][■][□][□][□]
                                                       Mon Tue Wed Thu Fri Sat Sun
```

### States and Interactions

1. **Default State (Score = 0)**:
   - White background
   - Gray border (#dadce0)
   - No special styling

2. **Win State (Score = 1)**:
   - Green background (#34a853)
   - Green border (#34a853)

3. **Clickable (Past Days)**:
   - Pointer cursor on hover
   - Border darkens on hover (#5f6368)
   - Scales up slightly (1.05x) on hover
   - Click toggles between win/default

4. **Non-Clickable (Today/Future)**:
   - Default cursor
   - No hover effects
   - No click handler

### Tooltips

- Hover shows day name: "Monday", "Tuesday", etc.
- No additional information needed (simple is better)

### Label

- "Daily Score" text label to left of squares
- Gray color (#5f6368)
- 13px font size
- Medium weight (500)

## Error Handling

### Backend Errors

1. **Feature Disabled**: Returns 404 with error message
2. **Firestore Unavailable**: Returns 500 with error message
3. **Missing Date**: Returns 400 with validation error

### Frontend Errors

1. **Toggle Failure**: Reverts UI change and shows alert
2. **Network Error**: Reverts UI change and shows alert
3. **Config Load Failure**: Defaults to enabled, logs error

## Performance Optimizations

1. **Optimistic UI Updates**: Toggle happens instantly, server sync in background
2. **No Page Reload**: Only updates the clicked square, not entire page
3. **Efficient Storage**: Only stores wins (1s), not defaults (0s)
4. **Conditional Loading**: Only fetches scores if feature is enabled
5. **Indexed Queries**: Firestore date index for fast range queries

## Maintenance and Debugging

### Common Issues

1. **Scores not appearing**: Check DAILY_SCORES_ENABLED flag
2. **Can't click squares**: Verify date is before today
3. **Slow toggles**: Check network tab for API latency
4. **Wrong day highlighted**: Verify timezone handling in formatDate()

### Logging

```javascript
// Frontend
console.error('Error loading daily scores:', error);
console.error('Error toggling score:', error);

// Backend
# Flask automatically logs errors
```

### Firestore Console

Query for scores:
```
Collection: daily_scores
Order by: date (descending)
Limit: 30
```

## Rebuild Checklist

If this feature is accidentally deleted, rebuild using these steps:

### Backend (app.py)

- [ ] Add `DAILY_SCORES_ENABLED` feature flag
- [ ] Update `/api/config` endpoint to return `daily_scores_enabled`
- [ ] Add `GET /api/daily_scores` endpoint with flag check
- [ ] Add `POST /api/daily_scores/toggle` endpoint with flag check
- [ ] Ensure Firestore collection is `daily_scores`

### Frontend (static/js/app.js)

- [ ] Add `dailyScoresEnabled` global variable
- [ ] Update `loadConfig()` to load `daily_scores_enabled`
- [ ] Update `loadSnippets()` to conditionally fetch scores
- [ ] Create `scoresMap` from scores array
- [ ] Create `renderScoreMeter()` function
- [ ] Update `displayWeeks()` to conditionally call `renderScoreMeter()`
- [ ] Create `toggleDailyScore()` function with optimistic updates

### CSS (static/css/style.css)

- [ ] Add `.score-meter` styles
- [ ] Add `.score-label` styles
- [ ] Add `.score-square` base styles
- [ ] Add `.score-square.clickable` hover styles
- [ ] Add `.score-square.win` green styles

### Tests (test_app.py)

- [ ] Create `TestDailyScores` class
- [ ] Add authentication test
- [ ] Add toggle create test (0→1)
- [ ] Add toggle delete test (1→0)
- [ ] Add missing date validation test
- [ ] Add date filter query test
- [ ] Add no-filter query test

### Configuration

- [ ] Add `DAILY_SCORES_ENABLED` to `app.yaml.template`
- [ ] Add default setting to `deploy.sh`
- [ ] Add sed replacement to `deploy.sh`
- [ ] Add default setting to `run_local.sh`
- [ ] Add export statement to `run_local.sh`

### Verification

- [ ] Run `./run_tests.sh` - all 51 tests should pass
- [ ] Run `./run_local.sh` - verify squares appear
- [ ] Click past day square - should toggle instantly
- [ ] Try clicking today/future - should not be clickable
- [ ] Set `DAILY_SCORES_ENABLED=false` - squares should disappear
- [ ] Deploy with `./deploy.sh` - verify in production

## Version History

- **v1.0** (2025-11-05): Initial implementation
  - Binary win/loss scoring system
  - Visual 7-square meter for each week
  - Instant toggle with optimistic UI updates
  - Only stores wins (efficient)
  - Complete test coverage (6 tests)
  - Feature flag support
  - Tooltips show day names
  - "Daily Score" label for clarity
