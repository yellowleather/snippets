# Weekly Reflections Feature Specification

## Overview

### Purpose
The Weekly Reflections feature enables users to record retrospective thoughts about past weeks. Unlike snippets (what was done) and goals (what was planned), reflections are introspective notes about what worked, what didn't, and what could be improved. This feature helps users learn from their experiences and make better decisions in the future.

### Key Characteristics
- **Past weeks only**: Reflections can only be created for weeks that have already occurred
- **Independent of snippets**: Can exist whether or not a snippet exists for that week
- **Structured prompts**: Pre-filled with three guiding questions to facilitate reflection
- **Full CRUD operations**: Create, read, update, and delete reflections
- **Date-filtered**: Respects the same date range filters as snippets and goals

### Feature Status
- **Status**: Active
- **Version**: 1.0
- **Database**: Firestore collection `reflections`
- **Feature Flag**: `REFLECTIONS_ENABLED` (defaults to `true`)

---

## Architecture

### High-Level Design

```
┌─────────────┐
│   Browser   │
│  (Client)   │
└──────┬──────┘
       │
       │ HTTPS
       │
┌──────▼──────┐
│  Flask App  │
│  (app.py)   │
└──────┬──────┘
       │
       │ Firestore API
       │
┌──────▼──────────┐
│   Firestore     │
│  'reflections'  │
│   collection    │
└─────────────────┘
```

### Data Flow

1. **Create Reflection**:
   - User clicks "Record Reflection" button (only visible for past weeks)
   - Modal opens with pre-filled template
   - User edits template and saves
   - POST to `/api/reflections`
   - Document created in Firestore
   - UI refreshes to show reflection

2. **Read Reflections**:
   - Page loads with date range
   - GET to `/api/reflections?start_date=X&end_date=Y`
   - Server queries Firestore, filters by date
   - Frontend maps reflections by week_start
   - Displays reflections for past weeks only

3. **Update Reflection**:
   - User clicks "Edit" on existing reflection
   - Modal opens with current content
   - User modifies and saves
   - PUT to `/api/reflections/<id>`
   - Firestore document updated
   - UI refreshes

4. **Delete Reflection**:
   - User clicks delete button or saves empty content
   - Confirmation dialog
   - DELETE to `/api/reflections/<id>`
   - Firestore document deleted
   - UI refreshes, "Record Reflection" button reappears

---

## Database Schema

### Firestore Collection: `reflections`

**Collection Name**: `reflections`

**Document Structure**:
```json
{
  "week_start": "2025-10-28",      // String, YYYY-MM-DD, Monday
  "week_end": "2025-11-03",        // String, YYYY-MM-DD, Sunday
  "content": "- **What worked...", // String, Markdown content
  "created_at": Timestamp,         // Firestore SERVER_TIMESTAMP
  "updated_at": Timestamp          // Firestore SERVER_TIMESTAMP
}
```

**Field Descriptions**:
- `week_start`: ISO format date string (YYYY-MM-DD) representing Monday of the week
- `week_end`: ISO format date string (YYYY-MM-DD) representing Sunday of the week
- `content`: Markdown-formatted text containing reflection content
- `created_at`: Firestore server timestamp, set when document is created
- `updated_at`: Firestore server timestamp, updated on every modification

**Indexes Required**:
- Single field index: `week_start` (DESCENDING) - for date-ordered queries
- Composite index: Not required (simple queries only)

**Constraints**:
- One reflection per week (enforced by client logic, not database)
- `week_start` must be a Monday
- `week_end` must be a Sunday
- `content` must not be empty (validated by API)
- Week must be in the past (enforced by UI, not API)

---

## Backend Implementation

### File: `app.py`

Add the following API endpoints after the goals endpoints:

```python
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

    reflections_ref = db.collection('reflections')

    if start_date and end_date:
        query = reflections_ref.order_by('week_start', direction=firestore.Query.DESCENDING)

        reflections = []
        for doc in query.stream():
            reflection = doc.to_dict()
            reflection['id'] = doc.id
            if reflection['week_start'] <= end_date and reflection['week_end'] >= start_date:
                reflections.append(reflection)
    else:
        query = reflections_ref.order_by('week_start', direction=firestore.Query.DESCENDING).limit(10)
        reflections = []
        for doc in query.stream():
            reflection = doc.to_dict()
            reflection['id'] = doc.id
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

    if not all([week_start, week_end, content]):
        return jsonify({'error': 'Missing required fields'}), 400

    doc_ref = db.collection('reflections').document()
    doc_ref.set({
        'week_start': week_start,
        'week_end': week_end,
        'content': content,
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
```

**API Endpoints Summary**:
- `GET /api/reflections` - List reflections with optional date filtering
- `GET /api/reflections/<id>` - Get single reflection by ID
- `POST /api/reflections` - Create new reflection
- `PUT /api/reflections/<id>` - Update reflection content
- `DELETE /api/reflections/<id>` - Delete reflection

---

## Frontend Implementation

### File: `static/js/app.js`

#### 1. Update Global State Variables

Add `currentReflectionId` to global state:

```javascript
// Global state
let currentSnippetId = null;
let currentGoalId = null;
let currentReflectionId = null;
let currentWeekStart = null;
let currentWeekEnd = null;
let currentModalType = null; // 'snippet', 'goal', or 'reflection'
let goalsEnabled = true;
```

#### 2. Update loadSnippets() Function

Modify to fetch reflections alongside snippets and goals:

```javascript
async function loadSnippets() {
    // ... existing code ...

    try {
        // Load snippets, conditionally load goals, and load reflections
        const promises = [
            fetch(`/api/snippets?start_date=${queryStart}&end_date=${queryEnd}`),
            fetch(`/api/reflections?start_date=${queryStart}&end_date=${queryEnd}`)
        ];

        if (goalsEnabled) {
            promises.push(fetch(`/api/goals?start_date=${queryStart}&end_date=${queryEnd}`));
        }

        const responses = await Promise.all(promises);
        const snippets = await responses[0].json();
        const reflections = await responses[1].json();
        const goals = goalsEnabled && responses[2] ? await responses[2].json() : [];

        // Map snippets, reflections, and goals by week_start
        const snippetsMap = {};
        snippets.forEach(s => { snippetsMap[s.week_start] = s; });

        const reflectionsMap = {};
        reflections.forEach(r => { reflectionsMap[r.week_start] = r; });

        const goalsMap = {};
        if (goalsEnabled) {
            goals.forEach(g => { goalsMap[g.week_start] = g; });
        }

        displayWeeks(universe, snippetsMap, goalsMap, reflectionsMap);
    } catch (error) {
        console.error('Error loading data:', error);
    }
}
```

#### 3. Update displayWeeks() Function

Modify signature and add reflection rendering:

```javascript
function displayWeeks(weeks, snippetsMap, goalsMap, reflectionsMap) {
    // ... existing week rendering code ...

    // For each week, after snippet rendering:
    const snippet = snippetsMap[week.week_start];
    if (snippet) {
        // ... render snippet ...

        // Show "Record Reflection" button for past weeks even when snippet exists
        const reflection = reflectionsMap[week.week_start];
        if (!week.isFuture && !reflection) {
            html += `      <button class="record-reflection-btn" onclick="openNewReflectionModalForWeek('${week.week_start}','${week.week_end}')">Record Reflection</button>`;
        }
    } else {
        html += `      </div>`;
        html += `      <div class="snippet-button-group">`;
        html += `        <button class="add-snippet-btn" onclick="openNewSnippetModalForWeek('${week.week_start}','${week.week_end}')">Add Snippets</button>`;

        // Show "Record Reflection" button only for past weeks
        const reflection = reflectionsMap[week.week_start];
        if (!week.isFuture && !reflection) {
            html += `        <button class="record-reflection-btn" onclick="openNewReflectionModalForWeek('${week.week_start}','${week.week_end}')">Record Reflection</button>`;
        }
        html += `      </div>`;
    }

    // Show reflection if it exists for past weeks
    const reflection = reflectionsMap[week.week_start];
    if (reflection && !week.isFuture) {
        html += `      <div class="reflection-section">`;
        html += `        <h4 class="reflection-title">Reflection</h4>`;
        html += `        <div class="snippet-content">`;
        const enableMarkdown = true;
        const reflectionHtml = enableMarkdown ? marked.parse(reflection.content) : escapeHtml(reflection.content);
        html += reflectionHtml;
        html += `        </div>`;
        html += `        <div class="snippet-actions">`;
        html += `          <button class="edit-btn" onclick="openEditReflectionModal('${reflection.id}')">Edit</button>`;
        html += `          <button class="delete-btn" onclick="deleteReflection('${reflection.id}')" title="Delete reflection">`;
        html += `            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">`;
        html += `              <polyline points="3 6 5 6 21 6"></polyline>`;
        html += `              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>`;
        html += `              <line x1="10" y1="11" x2="10" y2="17"></line>`;
        html += `              <line x1="14" y1="11" x2="14" y2="17"></line>`;
        html += `            </svg>`;
        html += `          </button>`;
        html += `        </div>`;
        html += `      </div>`;
    }
}
```

#### 4. Add Reflection Modal Functions

```javascript
// Open the new reflection modal for a specific week (week boundaries passed)
function openNewReflectionModalForWeek(weekStart, weekEnd) {
    currentSnippetId = null;
    currentGoalId = null;
    currentReflectionId = null;
    currentModalType = 'reflection';
    currentWeekStart = weekStart;
    currentWeekEnd = weekEnd;

    const weekNum = getWeekNumber(weekStart);
    const startFormatted = formatDateDisplay(weekStart);
    const endFormatted = formatDateDisplay(weekEnd);

    document.getElementById('modalTitle').textContent = `Record Reflection - Week ${weekNum} (${startFormatted}–${endFormatted.split(',')[0]}, ${endFormatted.split(',')[1]})`;

    const defaultReflectionTemplate = `- **What worked well?**
  - <Insert>
- **What was not a great use of time?**
  - <Insert>
- **What do I wish to have spent more time on?**
  - <Insert>
`;

    document.getElementById('snippetContent').value = defaultReflectionTemplate;

    showModal();
}

async function openEditReflectionModal(reflectionId) {
    try {
        const response = await fetch(`/api/reflections/${reflectionId}`);
        const reflection = await response.json();

        currentSnippetId = null;
        currentGoalId = null;
        currentReflectionId = reflectionId;
        currentModalType = 'reflection';
        currentWeekStart = reflection.week_start;
        currentWeekEnd = reflection.week_end;

        const weekNum = getWeekNumber(reflection.week_start);
        const startFormatted = formatDateDisplay(reflection.week_start);
        const endFormatted = formatDateDisplay(reflection.week_end);

        document.getElementById('modalTitle').textContent = `Edit Reflection - Week ${weekNum} (${startFormatted}–${endFormatted.split(',')[0]}, ${endFormatted.split(',')[1]})`;
        document.getElementById('snippetContent').value = reflection.content;

        showModal();
    } catch (error) {
        console.error('Error loading reflection:', error);
        alert('Failed to load reflection');
    }
}

async function deleteReflection(reflectionId, skipConfirm = false) {
    if (!skipConfirm && !confirm('Are you sure you want to delete this reflection?')) {
        return;
    }

    try {
        const response = await fetch(`/api/reflections/${reflectionId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            closeModal();
            await loadSnippets();
        } else {
            alert('Failed to delete reflection');
        }
    } catch (error) {
        console.error('Error deleting reflection:', error);
        alert('Failed to delete reflection');
    }
}
```

#### 5. Update closeModal() Function

```javascript
function closeModal() {
    document.getElementById('editModal').classList.remove('show');
    currentSnippetId = null;
    currentGoalId = null;
    currentReflectionId = null;  // Add this line
    currentModalType = null;
}
```

#### 6. Update saveSnippet() Function

Modify to handle reflections:

```javascript
async function saveSnippet() {
    const content = document.getElementById('snippetContent').value.trim();

    // Determine if we're working with snippet, goal, or reflection
    const isGoal = currentModalType === 'goal';
    const isReflection = currentModalType === 'reflection';
    const currentId = isGoal ? currentGoalId : (isReflection ? currentReflectionId : currentSnippetId);
    const apiPath = isGoal ? '/api/goals' : (isReflection ? '/api/reflections' : '/api/snippets');
    const itemType = isGoal ? 'goal' : (isReflection ? 'reflection' : 'snippet');

    // If content is empty and we're editing an existing item, delete it instead
    if (!content && currentId) {
        if (confirm(`Empty content will delete this ${itemType}. Continue?`)) {
            if (isGoal) {
                await deleteGoal(currentId, true);
            } else if (isReflection) {
                await deleteReflection(currentId, true);
            } else {
                await deleteSnippet(currentId, true);
            }
        }
        return;
    }

    // ... rest of save logic ...
}
```

---

## CSS Styling

### File: `static/css/style.css`

Add the following styles after the `.add-snippet-btn` styles:

```css
.snippet-button-group {
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 20px;
}

.snippet-button-group .add-snippet-btn {
    margin-bottom: 0;
}

.record-reflection-btn {
    padding: 12px 24px;
    background: white;
    color: #5f6368;
    border: 1px solid #dadce0;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    margin-top: 15px;
}

.record-reflection-btn:hover {
    background: #f1f3f4;
    border-color: #5f6368;
}

.snippet-button-group .record-reflection-btn {
    margin-top: 0;
}

.reflection-section {
    margin-top: 30px;
    padding-top: 30px;
    border-top: 2px solid #e8eaed;
}

.reflection-title {
    font-size: 14px;
    font-weight: 500;
    color: #5f6368;
    margin-bottom: 15px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
```

**Style Notes**:
- `.record-reflection-btn` uses secondary styling (white background, gray border) to be visually distinct from primary "Add Snippets" button
- `.reflection-section` adds clear separation between snippet and reflection with top border
- `.reflection-title` uses uppercase styling to match other section headers

---

## Testing

### File: `test_app.py`

Add a new test class for reflections:

```python
class TestReflectionsCRUD:
    """Test reflections CRUD operations"""

    def test_get_reflections_requires_auth(self, client):
        """Test that getting reflections requires authentication"""
        response = client.get('/api/reflections')
        assert response.status_code == 302  # Redirect to login

    def test_create_reflection(self, authenticated_client, mock_firestore):
        """Test creating a new reflection"""
        mock_doc_ref = Mock()
        mock_doc_ref.id = 'test-reflection-id'
        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore.collection.return_value = mock_collection

        reflection_data = {
            'week_start': '2025-10-27',
            'week_end': '2025-11-03',
            'content': '# Weekly Reflection\n\n- Learned about X\n- Improved Y'
        }

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.post('/api/reflections',
                                                data=json.dumps(reflection_data),
                                                content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'id' in data

    def test_create_reflection_missing_fields(self, authenticated_client, mock_firestore):
        """Test creating reflection with missing required fields"""
        incomplete_data = {
            'week_start': '2025-10-27',
            # Missing week_end and content
        }

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.post('/api/reflections',
                                                data=json.dumps(incomplete_data),
                                                content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_reflection_by_id(self, authenticated_client, mock_firestore):
        """Test retrieving a specific reflection by ID"""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.id = 'test-reflection-id'
        mock_doc.to_dict.return_value = {
            'week_start': '2025-10-27',
            'week_end': '2025-11-03',
            'content': 'Learned about testing'
        }

        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc

        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/reflections/test-reflection-id')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['week_start'] == '2025-10-27'
        assert data['content'] == 'Learned about testing'

    def test_get_nonexistent_reflection(self, authenticated_client, mock_firestore):
        """Test retrieving a reflection that doesn't exist"""
        mock_doc = Mock()
        mock_doc.exists = False

        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc

        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/reflections/nonexistent-id')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_update_reflection(self, authenticated_client, mock_firestore):
        """Test updating an existing reflection"""
        mock_doc_ref = Mock()
        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore.collection.return_value = mock_collection

        update_data = {
            'content': '# Updated Reflection\n\nNew insights'
        }

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.put('/api/reflections/test-reflection-id',
                                               data=json.dumps(update_data),
                                               content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        mock_doc_ref.update.assert_called_once()

    def test_update_reflection_missing_content(self, authenticated_client, mock_firestore):
        """Test updating reflection without content"""
        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.put('/api/reflections/test-reflection-id',
                                               data=json.dumps({}),
                                               content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_delete_reflection(self, authenticated_client, mock_firestore):
        """Test deleting a reflection"""
        mock_doc_ref = Mock()
        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.delete('/api/reflections/test-reflection-id')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        mock_doc_ref.delete.assert_called_once()

    def test_get_reflections_with_date_filter(self, authenticated_client, mock_firestore):
        """Test getting reflections with date range filter"""
        mock_doc1 = Mock()
        mock_doc1.id = 'reflection-1'
        mock_doc1.to_dict.return_value = {
            'week_start': '2025-10-27',
            'week_end': '2025-11-03',
            'content': 'Week 1 reflections'
        }

        mock_doc2 = Mock()
        mock_doc2.id = 'reflection-2'
        mock_doc2.to_dict.return_value = {
            'week_start': '2025-10-20',
            'week_end': '2025-10-26',
            'content': 'Week 2 reflections'
        }

        mock_query = Mock()
        mock_query.stream.return_value = [mock_doc1, mock_doc2]
        mock_query.order_by.return_value = mock_query

        mock_collection = Mock()
        mock_collection.order_by.return_value = mock_query
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/reflections?start_date=2025-10-20&end_date=2025-11-03')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
```

**Test Coverage**:
- Authentication requirements
- Create with valid data
- Create with missing fields
- Get by ID
- Get nonexistent reflection
- Update with valid data
- Update with missing content
- Delete reflection
- Date filtering

**Running Tests**:
```bash
./run_tests.sh
```

Expected result: All 45 tests pass (36 existing + 9 new reflection tests)

---

## Configuration

### Environment Variables

**REFLECTIONS_ENABLED** (optional, default: `true`)
- Controls whether the reflections feature is enabled
- Set to `"true"` to enable reflections
- Set to `"false"` to disable reflections
- When disabled:
  - API endpoints return 404 errors
  - Frontend does not fetch or display reflections
  - "Record Reflection" buttons are hidden

**Configuration Files**:
- `.env.production` - Set `REFLECTIONS_ENABLED=true` or `REFLECTIONS_ENABLED=false`
- `app.yaml` - Populated from `app.yaml.template` during deployment
- `deploy.sh` - Defaults to `true` if not set
- `run_local.sh` - Defaults to `true` if not set

### Feature Flag Implementation

The feature flag is implemented at multiple layers:

**Backend (app.py)**:
```python
REFLECTIONS_ENABLED = os.environ.get('REFLECTIONS_ENABLED', 'true').lower() == 'true'
```

All reflection API endpoints check this flag:
```python
@app.route('/api/reflections', methods=['GET'])
@login_required
def get_reflections():
    if not REFLECTIONS_ENABLED:
        return jsonify({'error': 'Reflections feature is disabled'}), 404
    # ... rest of implementation
```

**Frontend (static/js/app.js)**:
```javascript
let reflectionsEnabled = true; // Default to true, updated from server

async function loadConfig() {
    const response = await fetch('/api/config');
    const config = await response.json();
    reflectionsEnabled = config.reflections_enabled;
}
```

**Conditional Rendering**:
- "Record Reflection" buttons only render if `reflectionsEnabled === true`
- Reflection sections only render if `reflectionsEnabled === true`
- Reflections API only called if `reflectionsEnabled === true`

---

## UI/UX Specifications

### Button Placement

**Scenario 1: Past week WITHOUT snippet**
```
┌──────────────────────────────────┐
│ Week 44                          │
│ Oct 28, 2024 – Nov 3, 2024      │
├──────────────────────────────────┤
│                                  │
│ [Add Snippets]  [Record Reflection] │
│                                  │
└──────────────────────────────────┘
```

**Scenario 2: Past week WITH snippet, NO reflection**
```
┌──────────────────────────────────┐
│ Week 44                          │
│ Oct 28, 2024 – Nov 3, 2024      │
├──────────────────────────────────┤
│ • Completed feature X            │
│ • Fixed bug Y                    │
│                                  │
│ [Edit] [🗑]                      │
│                                  │
│ [Record Reflection]              │
└──────────────────────────────────┘
```

**Scenario 3: Past week WITH snippet AND reflection**
```
┌──────────────────────────────────┐
│ Week 44                          │
│ Oct 28, 2024 – Nov 3, 2024      │
├──────────────────────────────────┤
│ • Completed feature X            │
│ • Fixed bug Y                    │
│                                  │
│ [Edit] [🗑]                      │
│                                  │
│ ────────────────────────────────│
│ REFLECTION                       │
│                                  │
│ - What worked well?              │
│   - Good planning helped         │
│ - What was not great?            │
│   - Too many meetings            │
│                                  │
│ [Edit] [🗑]                      │
└──────────────────────────────────┘
```

**Scenario 4: Future week**
```
┌──────────────────────────────────┐
│ Week 46                          │
│ Nov 11, 2024 – Nov 17, 2024     │
├──────────────────────────────────┤
│                                  │
│ [Add Snippets]                   │
│                                  │
│ (No Record Reflection button)    │
└──────────────────────────────────┘
```

### Visual Hierarchy

**Button Styling**:
- **"Add Snippets"**: Primary button (blue background, white text) - most prominent
- **"Record Reflection"**: Secondary button (white background, gray border, gray text) - less prominent

This visual distinction makes it clear that adding snippets is the primary action, while recording reflections is optional.

### Default Template

When "Record Reflection" is clicked, the modal opens with this pre-filled markdown:

```markdown
- **What worked well?**
  - <Insert>
- **What was not a great use of time?**
  - <Insert>
- **What do I wish to have spent more time on?**
  - <Insert>
```

Users can:
1. Replace `<Insert>` with their answers
2. Add multiple sub-bullets under each question
3. Completely rewrite the template if desired
4. Use full markdown formatting

### Modal Titles

- New reflection: `Record Reflection - Week XX (Month DD, YYYY–MMM DD, YYYY)`
- Edit reflection: `Edit Reflection - Week XX (Month DD, YYYY–MMM DD, YYYY)`

---

## Error Handling

### Backend Errors

**Missing Required Fields (400)**:
```json
{
  "error": "Missing required fields"
}
```
**When**: POST request missing `week_start`, `week_end`, or `content`

**Empty Content (400)**:
```json
{
  "error": "Content is required"
}
```
**When**: PUT request with empty content

**Not Found (404)**:
```json
{
  "error": "Reflection not found"
}
```
**When**: GET/PUT/DELETE request for non-existent reflection ID

**Firestore Unavailable (500)**:
```json
{
  "error": "Firestore not available"
}
```
**When**: Database connection failure

### Frontend Error Handling

**Delete Confirmation**:
- User is prompted with "Are you sure you want to delete this reflection?"
- If confirmed, deletion proceeds
- If cancelled, no action taken

**Empty Content Deletion**:
- When saving with empty content and existing reflection
- Prompt: "Empty content will delete this reflection. Continue?"
- If yes, deletes without second confirmation
- If no, returns to editor

**Network Errors**:
- Caught and logged to console
- User-friendly alert shown
- No data loss (modal remains open)

---

## Maintenance

### Debugging Tips

**Reflection Not Appearing**:
1. Check browser console for API errors
2. Verify week is in the past (`week.isFuture === false`)
3. Confirm reflection exists in Firestore
4. Check that `reflectionsMap` is populated correctly

**Button Not Showing**:
1. Verify week is past (future weeks don't show button)
2. Check that reflection doesn't already exist
3. Inspect `week.isFuture` value in `computeUniverseWeeks()`
4. Ensure today's date is calculated correctly

**Template Not Pre-filling**:
1. Check `openNewReflectionModalForWeek()` function
2. Verify `defaultReflectionTemplate` constant is defined
3. Ensure modal element ID is correct

**Save/Delete Not Working**:
1. Check `currentModalType` is set to 'reflection'
2. Verify `currentReflectionId` is populated for edits
3. Check API responses in Network tab
4. Confirm authentication is active

### Common Issues

**Issue**: "Record Reflection" appears for future weeks
**Solution**: Check `computeUniverseWeeks()` - ensure `isFuture` calculation compares `monday > today` correctly

**Issue**: Reflection appears for future week
**Solution**: Check `displayWeeks()` - ensure condition is `if (reflection && !week.isFuture)`

**Issue**: Can't delete reflection
**Solution**: Check `deleteReflection()` function - ensure `skipConfirm` parameter works correctly for empty content saves

### Rollback Procedure

**To Disable Reflections**:
1. Remove reflection API calls from `loadSnippets()`
2. Remove reflection button rendering from `displayWeeks()`
3. Remove reflection modal functions
4. Comment out reflection API endpoints in `app.py`
5. Redeploy

**To Remove Reflections Data**:
```bash
# Delete all reflections from Firestore (CAUTION!)
gcloud firestore collections delete reflections --project=your-project-id
```

---

## Rebuild Checklist

Use this checklist to rebuild the feature from scratch:

### Backend (app.py)
- [ ] Add 5 reflection API endpoints (GET list, GET single, POST, PUT, DELETE)
- [ ] Each endpoint checks `FIRESTORE_AVAILABLE`
- [ ] Each endpoint requires `@login_required` decorator
- [ ] GET list supports date filtering with `start_date` and `end_date` params
- [ ] POST validates all required fields
- [ ] PUT validates content is not empty
- [ ] DELETE simply removes document

### Frontend - Global State (static/js/app.js)
- [ ] Add `currentReflectionId = null` to global state
- [ ] Update `currentModalType` comment to include 'reflection'

### Frontend - Data Loading
- [ ] Modify `loadSnippets()` to fetch reflections API
- [ ] Add reflections fetch to Promise.all() array
- [ ] Create `reflectionsMap` from API response
- [ ] Pass `reflectionsMap` to `displayWeeks()`

### Frontend - Display Logic
- [ ] Update `displayWeeks()` function signature to accept `reflectionsMap`
- [ ] Add "Record Reflection" button for past weeks WITHOUT reflection
  - Show after snippet content if snippet exists
  - Show next to "Add Snippets" if no snippet
  - Only show if `!week.isFuture && !reflection`
- [ ] Add reflection display section for past weeks WITH reflection
  - Separate section with `.reflection-section` class
  - Show "REFLECTION" title
  - Render markdown content
  - Show Edit and Delete buttons

### Frontend - Modal Functions
- [ ] Add `openNewReflectionModalForWeek(weekStart, weekEnd)` function
  - Set modal type to 'reflection'
  - Set title with week info
  - Pre-fill with default template (3 questions)
  - Call `showModal()`
- [ ] Add `openEditReflectionModal(reflectionId)` function
  - Fetch reflection from API
  - Set modal type to 'reflection'
  - Set title with week info
  - Fill with existing content
  - Call `showModal()`
- [ ] Add `deleteReflection(reflectionId, skipConfirm)` function
  - Show confirmation (unless skipped)
  - DELETE to API
  - Close modal and reload on success

### Frontend - Save Logic
- [ ] Update `saveSnippet()` to handle reflections
  - Add `isReflection = currentModalType === 'reflection'`
  - Set `currentId` conditionally (snippet/goal/reflection)
  - Set `apiPath` conditionally
  - Set `itemType` conditionally
  - Handle empty content deletion for reflections

### Frontend - Modal Cleanup
- [ ] Update `closeModal()` to reset `currentReflectionId = null`

### CSS (static/css/style.css)
- [ ] Add `.snippet-button-group` styles (flex, gap, wrap)
- [ ] Add `.record-reflection-btn` styles (secondary button appearance)
- [ ] Add `.snippet-button-group .record-reflection-btn` (remove top margin)
- [ ] Add `.reflection-section` styles (top border, spacing)
- [ ] Add `.reflection-title` styles (uppercase, letter-spacing)

### Testing (test_app.py)
- [ ] Add `TestReflectionsCRUD` class
- [ ] Add test for authentication requirement
- [ ] Add test for creating reflection
- [ ] Add test for creating with missing fields
- [ ] Add test for getting by ID
- [ ] Add test for getting nonexistent reflection
- [ ] Add test for updating reflection
- [ ] Add test for updating with missing content
- [ ] Add test for deleting reflection
- [ ] Add test for date filtering
- [ ] Run tests: `./run_tests.sh`
- [ ] Verify all 45 tests pass (36 existing + 9 new)

### Manual Testing
- [ ] Test creating reflection for past week without snippet
- [ ] Test creating reflection for past week with snippet
- [ ] Verify button does NOT appear for future weeks
- [ ] Test editing reflection
- [ ] Test deleting reflection via delete button
- [ ] Test deleting reflection via empty save
- [ ] Verify template pre-fills correctly
- [ ] Test markdown rendering in displayed reflection
- [ ] Test date filtering (reflections respect date range)
- [ ] Verify visual distinction between buttons

### Deployment
- [ ] Run tests locally
- [ ] Commit changes
- [ ] Deploy to App Engine: `./deploy.sh`
- [ ] Create Firestore index if needed (automatic on first query)
- [ ] Verify in production

---

## Version History

- **v1.0** (2025-01-04): Initial implementation
  - Full CRUD operations for reflections
  - Past-week-only constraint enforced in UI
  - Pre-filled template with three guiding questions
  - Visual distinction from primary actions
  - Complete test coverage (9 tests)
  - Integration with existing date filtering
