# Feature Specification: Weekly Goals

## Overview

The Weekly Goals feature adds a second data model and UI column to complement the existing work snippets functionality. It enables users to track not only what they accomplished (Work Done) but also what they planned or are planning to do (Weekly Goals) for each week.

**Feature Status**: Enabled by default via `GOALS_ENABLED` feature flag

**Version**: 1.0

**Last Updated**: November 3, 2025

---

## Purpose and Use Cases

### Primary Use Case
Allow users to:
1. Record weekly goals/plans at the start or during a week
2. Compare goals vs actual work done at the end of the week
3. Review planning accuracy over time
4. Maintain a historical record of both intentions and outcomes

### User Workflow
1. User navigates to a specific week
2. Left column shows "Work Done" (traditional snippets)
3. Right column shows "Weekly Goals" (new feature)
4. Each column has independent Add/Edit/Delete functionality
5. Both columns apply to the same date range filters

---

## Architecture

### Data Model Separation
- **Snippets**: Existing collection for work done
- **Goals**: New parallel collection for weekly goals
- Both share identical schema structure
- Both follow the same week constraints (Monday-Sunday)

### Feature Flag Design
- `GOALS_ENABLED` environment variable controls feature visibility
- Default: `true` (enabled)
- When disabled: Single-column layout, goals API returns 404
- When enabled: Two-column layout with full CRUD for both

---

## Database Schema

### Firestore Collection: `goals`

Identical structure to the existing `snippets` collection:

```javascript
{
  week_start: "2025-10-27",     // String, YYYY-MM-DD format, Monday
  week_end: "2025-11-02",       // String, YYYY-MM-DD format, Sunday
  content: "# Weekly Goals...", // String, Markdown content
  created_at: Timestamp,        // Firestore SERVER_TIMESTAMP
  updated_at: Timestamp         // Firestore SERVER_TIMESTAMP
}
```

**Constraints**:
- `week_start` must be a Monday
- `week_end` must be a Sunday
- `week_end` must be exactly 6 days after `week_start`
- One goal per week maximum (enforced by UI logic, not database)

**Indexes Required**:
- Composite index on `week_start` (DESCENDING) for efficient date-range queries

---

## Backend Implementation

### File: `app.py`

#### 1. Feature Flag Configuration

Add after existing configuration:

```python
# Feature Flags
GOALS_ENABLED = os.environ.get('GOALS_ENABLED', 'true').lower() == 'true'
```

#### 2. Config API Endpoint

```python
@app.route('/api/config', methods=['GET'])
@login_required
def get_config():
    """Return feature flags and configuration"""
    return jsonify({
        'goals_enabled': GOALS_ENABLED
    })
```

#### 3. Goals API Endpoints

All endpoints follow the same pattern as snippets with added feature flag check:

**GET /api/goals**
- List goals with optional date filtering
- Query parameters: `start_date`, `end_date` (YYYY-MM-DD)
- Returns: Array of goal objects

```python
@app.route('/api/goals', methods=['GET'])
@login_required
def get_goals():
    if not GOALS_ENABLED:
        return jsonify({'error': 'Goals feature is disabled'}), 404

    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    goals_ref = db.collection('goals')

    if start_date and end_date:
        query = goals_ref.order_by('week_start', direction=firestore.Query.DESCENDING)

        goals = []
        for doc in query.stream():
            goal = doc.to_dict()
            goal['id'] = doc.id
            # Client-side filtering for overlapping weeks
            if goal['week_start'] <= end_date and goal['week_end'] >= start_date:
                goals.append(goal)
    else:
        query = goals_ref.order_by('week_start', direction=firestore.Query.DESCENDING).limit(10)
        goals = []
        for doc in query.stream():
            goal = doc.to_dict()
            goal['id'] = doc.id
            goals.append(goal)

    return jsonify(goals)
```

**GET /api/goals/<goal_id>**
- Retrieve specific goal by ID
- Returns: Goal object or 404

```python
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
```

**POST /api/goals**
- Create new goal
- Request body: `{ week_start, week_end, content }`
- Returns: `{ id, success: true }`

```python
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

    if not all([week_start, week_end, content]):
        return jsonify({'error': 'Missing required fields'}), 400

    doc_ref = db.collection('goals').document()
    doc_ref.set({
        'week_start': week_start,
        'week_end': week_end,
        'content': content,
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    })

    return jsonify({'id': doc_ref.id, 'success': True})
```

**PUT /api/goals/<goal_id>**
- Update existing goal content
- Request body: `{ content }`
- Returns: `{ success: true }`

```python
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
```

**DELETE /api/goals/<goal_id>**
- Delete goal
- Returns: `{ success: true }`

```python
@app.route('/api/goals/<goal_id>', methods=['DELETE'])
@login_required
def delete_goal(goal_id):
    if not GOALS_ENABLED:
        return jsonify({'error': 'Goals feature is disabled'}), 404

    if not FIRESTORE_AVAILABLE:
        return jsonify({'error': 'Firestore not available'}), 500

    db.collection('goals').document(goal_id).delete()

    return jsonify({'success': True})
```

---

## Frontend Implementation

### File: `static/js/app.js`

#### 1. Global State Variables

Add to existing global state:

```javascript
// Global state
let currentSnippetId = null;
let currentGoalId = null;        // NEW
let currentWeekStart = null;
let currentWeekEnd = null;
let currentModalType = null;      // NEW: 'snippet' or 'goal'
let goalsEnabled = true;          // NEW: Feature flag
```

#### 2. Configuration Loading

```javascript
// Initialize the app
document.addEventListener('DOMContentLoaded', async () => {
    await loadConfig();           // NEW: Load config first
    initializeDefaultView();
    setupDateInputs();
});

async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        goalsEnabled = config.goals_enabled;
    } catch (error) {
        console.error('Error loading config:', error);
        goalsEnabled = true;      // Default to enabled if fetch fails
    }
}
```

#### 3. Data Loading with Feature Flag Check

Modify `loadSnippets()` function:

```javascript
async function loadSnippets() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    if (!startDate || !endDate) return;

    // ... date validation ...

    const universe = computeUniverseWeeks(startDate, endDate);
    const queryStart = universe[0].week_start;
    const queryEnd = universe[universe.length - 1].week_end;

    try {
        // Conditionally load goals based on feature flag
        const promises = [
            fetch(`/api/snippets?start_date=${queryStart}&end_date=${queryEnd}`)
        ];

        if (goalsEnabled) {
            promises.push(fetch(`/api/goals?start_date=${queryStart}&end_date=${queryEnd}`));
        }

        const responses = await Promise.all(promises);
        const snippets = await responses[0].json();
        const goals = goalsEnabled && responses[1] ? await responses[1].json() : [];

        // Map data by week_start
        const snippetsMap = {};
        snippets.forEach(s => { snippetsMap[s.week_start] = s; });

        const goalsMap = {};
        if (goalsEnabled) {
            goals.forEach(g => { goalsMap[g.week_start] = g; });
        }

        displayWeeks(universe, snippetsMap, goalsMap);
    } catch (error) {
        console.error('Error loading data:', error);
    }
}
```

#### 4. Two-Column Display

Modify `displayWeeks()` function signature and logic:

```javascript
function displayWeeks(weeks, snippetsMap, goalsMap) {
    const container = document.getElementById('snippetsContainer');

    if (!weeks || weeks.length === 0) {
        container.innerHTML = '<p>No weeks to display</p>';
        return;
    }

    let html = '';

    // Render weeks in reverse chronological order
    for (let i = weeks.length - 1; i >= 0; i--) {
        const week = weeks[i];
        const weekNum = getWeekNumber(week.week_start);
        const startFormatted = formatDateDisplay(week.week_start);
        const endFormatted = formatDateDisplay(week.week_end);

        html += `<div class="week-section">`;
        html += `  <div class="week-header">`;
        html += `    <span class="week-badge">Week ${weekNum}</span>`;
        html += `    <h2 class="week-title">${startFormatted} – ${endFormatted}</h2>`;
        html += `  </div>`;

        // Add single-column class when goals disabled
        html += `  <div class="week-columns${goalsEnabled ? '' : ' single-column'}">`;

        // LEFT COLUMN: Snippets (Work Done)
        html += `    <div class="week-column">`;

        // Only show column title when in two-column mode
        if (goalsEnabled) {
            html += `      <h3 class="column-title">Work Done</h3>`;
        }

        html += `      <div class="snippet-content">`;

        const snippet = snippetsMap[week.week_start];
        if (snippet) {
            const contentHtml = marked.parse(snippet.content);
            html += contentHtml;
            html += `      </div>`;
            html += `      <div class="snippet-actions">`;
            html += `        <button class="edit-btn" onclick="openEditSnippetModal('${snippet.id}')">Edit</button>`;
            html += `        <button class="delete-btn" onclick="deleteSnippet('${snippet.id}')" title="Delete snippet">`;
            html += `          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">`;
            html += `            <polyline points="3 6 5 6 21 6"></polyline>`;
            html += `            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>`;
            html += `            <line x1="10" y1="11" x2="10" y2="17"></line>`;
            html += `            <line x1="14" y1="11" x2="14" y2="17"></line>`;
            html += `          </svg>`;
            html += `        </button>`;
            html += `      </div>`;
        } else {
            html += `      </div>`;
            html += `      <button class="add-snippet-btn" onclick="openNewSnippetModalForWeek('${week.week_start}','${week.week_end}')">Add Snippets</button>`;
        }
        html += `    </div>`;

        // RIGHT COLUMN: Goals - Only render if feature enabled
        if (goalsEnabled) {
            html += `    <div class="week-column">`;
            html += `      <h3 class="column-title">Weekly Goals</h3>`;
            html += `      <div class="snippet-content">`;

            const goal = goalsMap[week.week_start];
            if (goal) {
                const contentHtml = marked.parse(goal.content);
                html += contentHtml;
                html += `      </div>`;
                html += `      <div class="snippet-actions">`;
                html += `        <button class="edit-btn" onclick="openEditGoalModal('${goal.id}')">Edit</button>`;
                html += `        <button class="delete-btn" onclick="deleteGoal('${goal.id}')" title="Delete goal">`;
                html += `          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">`;
                html += `            <polyline points="3 6 5 6 21 6"></polyline>`;
                html += `            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>`;
                html += `            <line x1="10" y1="11" x2="10" y2="17"></line>`;
                html += `            <line x1="14" y1="11" x2="14" y2="17"></line>`;
                html += `          </svg>`;
                html += `        </button>`;
                html += `      </div>`;
            } else {
                html += `      </div>`;
                html += `      <button class="add-snippet-btn" onclick="openNewGoalModalForWeek('${week.week_start}','${week.week_end}')">Add Goals</button>`;
            }
            html += `    </div>`;
        }

        html += `  </div>`;
        html += `</div>`;
    }

    container.innerHTML = html;
}
```

#### 5. Modal Functions for Goals

Add new functions for goal modals:

```javascript
// Open new goal modal
function openNewGoalModalForWeek(weekStart, weekEnd) {
    currentSnippetId = null;
    currentGoalId = null;
    currentModalType = 'goal';
    currentWeekStart = weekStart;
    currentWeekEnd = weekEnd;

    const weekNum = getWeekNumber(weekStart);
    const startFormatted = formatDateDisplay(weekStart);
    const endFormatted = formatDateDisplay(weekEnd);

    document.getElementById('modalTitle').textContent = `New Weekly Goals - Week ${weekNum} (${startFormatted}–${endFormatted.split(',')[0]}, ${endFormatted.split(',')[1]})`;
    document.getElementById('snippetContent').value = '';

    showModal();
}

// Open edit goal modal
async function openEditGoalModal(goalId) {
    try {
        const response = await fetch(`/api/goals/${goalId}`);
        const goal = await response.json();

        currentSnippetId = null;
        currentGoalId = goalId;
        currentModalType = 'goal';
        currentWeekStart = goal.week_start;
        currentWeekEnd = goal.week_end;

        const weekNum = getWeekNumber(goal.week_start);
        const startFormatted = formatDateDisplay(goal.week_start);
        const endFormatted = formatDateDisplay(goal.week_end);

        document.getElementById('modalTitle').textContent = `Edit Weekly Goals - Week ${weekNum} (${startFormatted}–${endFormatted.split(',')[0]}, ${endFormatted.split(',')[1]})`;
        document.getElementById('snippetContent').value = goal.content;

        showModal();
    } catch (error) {
        console.error('Error loading goal:', error);
        alert('Failed to load goal');
    }
}
```

Update existing snippet modal functions to set `currentModalType`:

```javascript
function openNewSnippetModalForWeek(weekStart, weekEnd) {
    currentSnippetId = null;
    currentGoalId = null;
    currentModalType = 'snippet';  // NEW
    // ... rest of function
}

async function openEditSnippetModal(snippetId) {
    // ... fetch snippet ...
    currentSnippetId = snippetId;
    currentGoalId = null;
    currentModalType = 'snippet';  // NEW
    // ... rest of function
}
```

#### 6. Unified Save Function

Modify `saveSnippet()` to handle both snippets and goals:

```javascript
async function saveSnippet() {
    const content = document.getElementById('snippetContent').value.trim();

    // Determine type based on currentModalType
    const isGoal = currentModalType === 'goal';
    const currentId = isGoal ? currentGoalId : currentSnippetId;
    const apiPath = isGoal ? '/api/goals' : '/api/snippets';
    const itemType = isGoal ? 'goal' : 'snippet';

    // Empty content handling
    if (!content && currentId) {
        if (confirm(`Empty content will delete this ${itemType}. Continue?`)) {
            if (isGoal) {
                await deleteGoal(currentId, true);
            } else {
                await deleteSnippet(currentId, true);
            }
        }
        return;
    }

    if (!content) {
        alert('Please enter some content');
        return;
    }

    try {
        let response;

        if (currentId) {
            // Update existing
            response = await fetch(`${apiPath}/${currentId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
        } else {
            // Create new
            response = await fetch(apiPath, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    week_start: currentWeekStart,
                    week_end: currentWeekEnd,
                    content
                })
            });
        }

        if (response.ok) {
            closeModal();
            await loadSnippets();
        } else {
            alert(`Failed to save ${itemType}`);
        }
    } catch (error) {
        console.error(`Error saving ${itemType}:`, error);
        alert(`Failed to save ${itemType}`);
    }
}
```

#### 7. Delete Goal Function

```javascript
async function deleteGoal(goalId, skipConfirm = false) {
    if (!skipConfirm && !confirm('Are you sure you want to delete this goal?')) {
        return;
    }

    try {
        const response = await fetch(`/api/goals/${goalId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            closeModal();
            await loadSnippets();
        } else {
            alert('Failed to delete goal');
        }
    } catch (error) {
        console.error('Error deleting goal:', error);
        alert('Failed to delete goal');
    }
}
```

#### 8. Close Modal Updates

```javascript
function closeModal() {
    document.getElementById('editModal').classList.remove('show');
    currentSnippetId = null;
    currentGoalId = null;      // NEW
    currentModalType = null;   // NEW
}
```

---

## CSS Styling

### File: `static/css/style.css`

Add these styles after existing week-related styles:

```css
/* Two-column layout for snippets and goals */
.week-columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 30px;
}

/* Single column when goals disabled */
.week-columns.single-column {
    grid-template-columns: 1fr;
}

.week-column {
    min-width: 0;  /* Allow grid items to shrink below content size */
}

/* Column headers */
.column-title {
    font-size: 16px;
    font-weight: 500;
    color: #5f6368;
    margin-bottom: 15px;
    padding-bottom: 10px;
    border-bottom: 2px solid #e8eaed;
}

/* Responsive: stack columns on mobile */
@media (max-width: 900px) {
    .week-columns {
        grid-template-columns: 1fr;
    }
}
```

---

## Testing

### File: `test_app.py`

Add comprehensive test class for goals:

```python
class TestGoalsCRUD:
    """Test goals CRUD operations"""

    def test_get_goals_requires_auth(self, client):
        """Test that getting goals requires authentication"""
        response = client.get('/api/goals')
        assert response.status_code == 302  # Redirect to login

    def test_create_goal(self, authenticated_client, mock_firestore):
        """Test creating a new goal"""
        mock_doc_ref = Mock()
        mock_doc_ref.id = 'test-goal-id'
        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore.collection.return_value = mock_collection

        goal_data = {
            'week_start': '2025-10-27',
            'week_end': '2025-11-02',
            'content': '# Weekly Goals\n\n- Complete feature X\n- Review PRs'
        }

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.post('/api/goals',
                                                data=json.dumps(goal_data),
                                                content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'id' in data

    def test_create_goal_missing_fields(self, authenticated_client, mock_firestore):
        """Test creating goal with missing required fields"""
        incomplete_data = {
            'week_start': '2025-10-27',
            # Missing week_end and content
        }

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.post('/api/goals',
                                                data=json.dumps(incomplete_data),
                                                content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_goal_by_id(self, authenticated_client, mock_firestore):
        """Test retrieving a specific goal by ID"""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.id = 'test-goal-id'
        mock_doc.to_dict.return_value = {
            'week_start': '2025-10-27',
            'week_end': '2025-11-02',
            'content': 'Complete feature X'
        }

        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc

        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/goals/test-goal-id')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['week_start'] == '2025-10-27'
        assert data['content'] == 'Complete feature X'

    def test_get_nonexistent_goal(self, authenticated_client, mock_firestore):
        """Test retrieving a goal that doesn't exist"""
        mock_doc = Mock()
        mock_doc.exists = False

        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc

        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/goals/nonexistent-id')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_update_goal(self, authenticated_client, mock_firestore):
        """Test updating an existing goal"""
        mock_doc_ref = Mock()
        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore.collection.return_value = mock_collection

        update_data = {
            'content': '# Updated Goals\n\nNew priorities'
        }

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.put('/api/goals/test-goal-id',
                                               data=json.dumps(update_data),
                                               content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        mock_doc_ref.update.assert_called_once()

    def test_update_goal_missing_content(self, authenticated_client, mock_firestore):
        """Test updating goal without content"""
        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.put('/api/goals/test-goal-id',
                                               data=json.dumps({}),
                                               content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_delete_goal(self, authenticated_client, mock_firestore):
        """Test deleting a goal"""
        mock_doc_ref = Mock()
        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.delete('/api/goals/test-goal-id')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        mock_doc_ref.delete.assert_called_once()

    def test_get_goals_with_date_filter(self, authenticated_client, mock_firestore):
        """Test getting goals with date range filter"""
        mock_doc1 = Mock()
        mock_doc1.id = 'goal-1'
        mock_doc1.to_dict.return_value = {
            'week_start': '2025-10-27',
            'week_end': '2025-11-02',
            'content': 'Week 1 goals'
        }

        mock_doc2 = Mock()
        mock_doc2.id = 'goal-2'
        mock_doc2.to_dict.return_value = {
            'week_start': '2025-10-20',
            'week_end': '2025-10-26',
            'content': 'Week 2 goals'
        }

        mock_query = Mock()
        mock_query.stream.return_value = [mock_doc1, mock_doc2]
        mock_query.order_by.return_value = mock_query

        mock_collection = Mock()
        mock_collection.order_by.return_value = mock_query
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/goals?start_date=2025-10-20&end_date=2025-11-02')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
```

**Expected Test Coverage**:
- Total tests: 36 (27 existing + 9 new)
- Coverage: ~85-87%

---

## Configuration and Deployment

### Environment Variable: `GOALS_ENABLED`

**Location**: `.env.production`

**Format**:
```bash
GOALS_ENABLED=true   # Enable goals feature (default)
GOALS_ENABLED=false  # Disable goals feature
```

**Default**: `true` if not specified

### File: `app.yaml.template`

Add environment variable:

```yaml
env_variables:
  SNIPPET_USERNAME: __SNIPPET_USERNAME__
  SNIPPET_PASSWORD: __SNIPPET_PASSWORD__
  SECRET_KEY: __SECRET_KEY__
  GOALS_ENABLED: __GOALS_ENABLED__
```

### File: `deploy.sh`

Add default handling and substitution:

```bash
# Set default for GOALS_ENABLED if not provided
if [ -z "$GOALS_ENABLED" ]; then
    GOALS_ENABLED="true"
fi

# Create app.yaml from template with secrets
sed -e "s|__SNIPPET_USERNAME__|$SNIPPET_USERNAME|g" \
    -e "s|__SNIPPET_PASSWORD__|$SNIPPET_PASSWORD|g" \
    -e "s|__SECRET_KEY__|$SECRET_KEY|g" \
    -e "s|__GOALS_ENABLED__|$GOALS_ENABLED|g" \
    app.yaml.template > app.yaml
```

### File: `run_local.sh`

Add default handling and export:

```bash
# Set default for GOALS_ENABLED if not in .env.production
if [ -z "$GOALS_ENABLED" ]; then
    GOALS_ENABLED="true"
fi

# Export environment variables for Flask
export SECRET_KEY="$SECRET_KEY"
export SNIPPET_USERNAME="$SNIPPET_USERNAME"
export SNIPPET_PASSWORD="$SNIPPET_PASSWORD"
export GOALS_ENABLED="$GOALS_ENABLED"
export FLASK_ENV=development
export FLASK_DEBUG=1
```

---

## UI/UX Specifications

### Two-Column Layout (Goals Enabled)

```
┌─────────────────────────────────────────────────────┐
│ Week Header: Week 44 • Oct 28 - Nov 3, 2025        │
├─────────────────────────┬───────────────────────────┤
│ Work Done               │ Weekly Goals              │
├─────────────────────────┼───────────────────────────┤
│ - Completed feature X   │ - Complete feature X      │
│ - Fixed 3 bugs          │ - Write unit tests        │
│ - Code review           │ - Deploy to staging       │
│                         │                           │
│ [Edit] [🗑]             │ [Edit] [🗑]               │
└─────────────────────────┴───────────────────────────┘
```

### Single-Column Layout (Goals Disabled)

```
┌─────────────────────────────────────────────────────┐
│ Week Header: Week 44 • Oct 28 - Nov 3, 2025        │
├─────────────────────────────────────────────────────┤
│ - Completed feature X                               │
│ - Fixed 3 bugs                                      │
│ - Code review                                       │
│                                                     │
│ [Edit] [🗑]                                         │
└─────────────────────────────────────────────────────┘
```

### Mobile Responsive (< 900px)

Both columns stack vertically:
1. Work Done (top)
2. Weekly Goals (bottom)

### Empty States

**No Work Done**:
```
[Add Snippets] button only (left column)
```

**No Goals**:
```
[Add Goals] button only (right column)
```

### Button Styling

**Add Buttons**:
- Blue background (#1a73e8)
- White text
- Rounded corners (4px)

**Edit Button**:
- Text link style
- Blue color (#1a73e8)
- No background

**Delete Button**:
- Trash can icon (SVG)
- Red color (#d93025)
- Border with hover effect
- 32x32px size

---

## Modal Behavior

### Modal Title Updates

**Snippets**:
- New: "New Work Done - Week X (dates)"
- Edit: "Edit Work Done - Week X (dates)"

**Goals**:
- New: "New Weekly Goals - Week X (dates)"
- Edit: "Edit Weekly Goals - Week X (dates)"

### Save Button Behavior

- Single "Save" button handles both snippets and goals
- Determines type from `currentModalType` variable
- Routes to appropriate API endpoint

### Empty Content Handling

When user saves empty content for existing item:
1. Show confirmation: "Empty content will delete this [snippet/goal]. Continue?"
2. If confirmed: Call delete function with `skipConfirm=true`
3. Close modal and refresh UI

---

## Feature Flag Behavior Matrix

| Feature Flag | Backend | Frontend | UI Display |
|--------------|---------|----------|------------|
| `true` | Goals API active | Loads goals data | Two-column layout |
| `false` | Goals API returns 404 | Skips goals fetch | Single-column layout |
| Missing | Defaults to `true` | Defaults to `true` | Two-column layout |

---

## Migration Path

### From No Goals to Goals

1. Deploy with `GOALS_ENABLED=true`
2. Firestore automatically creates `goals` collection on first write
3. No data migration needed
4. Existing snippets unaffected

### Disabling Goals

1. Set `GOALS_ENABLED=false` in `.env.production`
2. Redeploy
3. Goals data remains in Firestore but is not accessible via API
4. UI reverts to single-column layout

### Re-enabling Goals

1. Set `GOALS_ENABLED=true`
2. Redeploy
3. All historical goals become accessible again
4. No data loss

---

## Error Handling

### Backend Errors

**Goals Disabled**:
```json
{
  "error": "Goals feature is disabled"
}
```
Status: 404

**Firestore Unavailable**:
```json
{
  "error": "Firestore not available"
}
```
Status: 500

**Missing Fields**:
```json
{
  "error": "Missing required fields"
}
```
Status: 400

**Goal Not Found**:
```json
{
  "error": "Goal not found"
}
```
Status: 404

### Frontend Error Handling

**Config Load Failure**:
- Logs error to console
- Defaults to `goalsEnabled = true`
- Continues normal operation

**Goals Fetch Failure**:
- Logs error to console
- Sets `goals = []`
- Displays snippets without goals column

**Goal Save/Delete Failure**:
- Shows alert to user
- Modal remains open
- User can retry

---

## Performance Considerations

### Database Queries

1. **Parallel Loading**: Goals and snippets fetched in parallel using `Promise.all()`
2. **Client-Side Filtering**: Both use same pattern of server ordering + client filtering
3. **No Additional Indexes**: Goals use same index pattern as snippets

### Frontend Optimization

1. **Conditional Loading**: Goals only fetched when feature enabled
2. **Single Render**: Both columns rendered in single pass
3. **No Extra Requests**: Config loaded once at app initialization

---

## Security Considerations

1. **Authentication**: All goals endpoints require `@login_required` decorator
2. **Authorization**: Single-user app, no multi-tenant concerns
3. **Input Validation**: Content validated for presence, week dates validated
4. **SQL Injection**: N/A - using Firestore (NoSQL)
5. **XSS Protection**: Markdown rendered via marked.js with default sanitization

---

## Maintenance

### Adding New Features to Goals

To add features to goals that mirror snippets:
1. Implement in snippets first
2. Copy pattern to goals with goal-specific naming
3. Wrap in `if goalsEnabled` checks
4. Add corresponding tests

### Debugging Feature Flag Issues

**Check flag value**:
```bash
# In App Engine logs
gcloud app logs tail -s default | grep GOALS_ENABLED
```

**Verify frontend config**:
```javascript
// In browser console
console.log(goalsEnabled);
```

**Test API**:
```bash
# Should return feature flag status
curl https://your-app.appspot.com/api/config
```

---

## Rollback Procedure

If goals feature needs to be quickly disabled:

1. **Quick Disable** (no redeployment):
   - Not possible - requires redeployment

2. **Disable via Redeploy** (5 minutes):
   ```bash
   # Edit .env.production
   echo "GOALS_ENABLED=false" >> .env.production

   # Redeploy
   ./deploy.sh
   ```

3. **Complete Removal** (if needed):
   - Revert commits that added goals
   - Remove goals-related code
   - Redeploy
   - Goals data remains in Firestore for potential restore

---

## Future Enhancements

Potential improvements to consider:

1. **Goal Templates**: Pre-defined goal templates for common scenarios
2. **Goal Completion Tracking**: Checkboxes for goal items
3. **Goals vs Actuals**: Side-by-side comparison view
4. **Goal Carry-Over**: Automatically copy incomplete goals to next week
5. **Analytics**: Goal completion rates, planning accuracy metrics
6. **Export**: Compare goals and snippets in export functionality

---

## Checklist for Rebuilding

If this feature is deleted and needs to be rebuilt, follow this checklist:

### Backend
- [ ] Add `GOALS_ENABLED` feature flag to app.py
- [ ] Add `/api/config` endpoint
- [ ] Add all 5 goals API endpoints (GET list, GET single, POST, PUT, DELETE)
- [ ] Add feature flag checks to all goals endpoints
- [ ] Add 9 test cases to test_app.py

### Frontend
- [ ] Add global state variables (currentGoalId, currentModalType, goalsEnabled)
- [ ] Add loadConfig() function
- [ ] Update DOMContentLoaded to call loadConfig()
- [ ] Update loadSnippets() to conditionally load goals
- [ ] Update displayWeeks() signature and add two-column rendering
- [ ] Add openNewGoalModalForWeek() function
- [ ] Add openEditGoalModal() function
- [ ] Update openNewSnippetModalForWeek() to set currentModalType
- [ ] Update openEditSnippetModal() to set currentModalType
- [ ] Update saveSnippet() to handle both types
- [ ] Add deleteGoal() function
- [ ] Update closeModal() to clear goal state

### CSS
- [ ] Add .week-columns styling
- [ ] Add .single-column class
- [ ] Add .column-title styling
- [ ] Add mobile responsive breakpoint

### Configuration
- [ ] Add GOALS_ENABLED to app.yaml.template
- [ ] Update deploy.sh to handle GOALS_ENABLED
- [ ] Update run_local.sh to handle GOALS_ENABLED
- [ ] Update README with feature flag documentation

### Testing
- [ ] Run all tests (should be 36 total)
- [ ] Test with GOALS_ENABLED=true
- [ ] Test with GOALS_ENABLED=false
- [ ] Test goal creation, editing, deletion
- [ ] Test empty content deletion

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-03 | Initial implementation with feature flag |

---

## Contact

For questions about this feature:
- Review git history for implementation details
- Check test_app.py for behavior examples
- Consult README.md for user-facing documentation
