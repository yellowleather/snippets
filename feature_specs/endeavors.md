# Endeavors Feature Specification

## Overview
Add support for multiple "endeavors" (contexts/categories) to organize different tracking areas (e.g., "pet project", "fitness", "marathon"). This allows users to maintain separate tracking contexts within the same application.

## Requirements

### 1. Data Model
- Add `endeavor` field to all Firestore collections:
  - `snippets` - Weekly work snippets
  - `goals` - Weekly goals
  - `reflections` - Weekly reflections
  - `daily_scores` - Daily movement tracking
- **Default value**: `"pet project"`
- **Type**: `string`
- **Backward compatibility**: Use `.get('endeavor', 'pet project')` pattern when reading data to handle existing records without this field

### 2. Backend API Changes

#### New Endpoints

**GET /api/endeavors**
- Returns list of unique endeavor names from all collections
- Requires authentication
- Response: `["pet project", "fitness", "marathon"]`
- Implementation:
  ```python
  # Query all 4 collections
  # Extract endeavor field with default 'pet project'
  # Return unique sorted list
  ```

**POST /api/endeavors/rename**
- Renames an endeavor across all 4 collections
- Requires authentication
- Request body: `{"old_name": "fitness", "new_name": "marathon"}`
- Response: `{"success": true, "updated_counts": {...}}`
- Validation: Empty names not allowed, old_name must exist
- Implementation:
  ```python
  # For each collection (snippets, goals, reflections, daily_scores):
  #   Query documents where endeavor == old_name
  #   Update each document with new_name
  #   Return count of updated documents
  ```

#### Updated Endpoints
All existing GET endpoints accept optional `endeavor` query parameter:
- `GET /api/snippets?start_date=X&end_date=Y&endeavor=Z`
- `GET /api/goals?start_date=X&end_date=Y&endeavor=Z`
- `GET /api/reflections?start_date=X&end_date=Y&endeavor=Z`
- `GET /api/daily_scores?start_date=X&end_date=Y&endeavor=Z`

All POST/PUT endpoints accept `endeavor` in request body (defaults to "pet project" if not provided).

**Filter Implementation Pattern**:
```python
# Client-side filtering for backward compatibility
for doc in query.stream():
    data = doc.to_dict()
    if data.get('endeavor', 'pet project') == endeavor:
        # Include this document
```

### 3. Frontend Changes

#### Tab Bar UI (HTML Structure)
Located in `templates/index.html` above date controls:
```html
<div class="endeavor-tabs">
    <div id="tabsContainer" class="tabs-container">
        <!-- Tabs dynamically inserted here -->
    </div>
    <button class="add-endeavor-btn" onclick="createNewEndeavor()">+ New Endeavor</button>
</div>
```

#### Tab Styling (CSS)
Location: `static/css/style.css`

**Container styles**:
- `.endeavor-tabs`: Flex container with gap, border-bottom
- `.tabs-container`: Flex with wrap support for multiple tabs

**Tab styles**:
- `.endeavor-tab`: Light grey background (#f1f3f4), rounded top corners
- `.endeavor-tab.active`: Blue background (#1a73e8), white text, bottom border accent
- `.endeavor-tab.editable`: Input field style with blue border
- `.endeavor-tab:hover`: Darker grey (#e8eaed) for hover state

**Button styles**:
- `.add-endeavor-btn`: White background, blue text, border

#### Tab Actions & JavaScript Logic

**Global State** (in `static/js/app.js`):
```javascript
let currentEndeavor = 'pet project'; // Active endeavor
let endeavorsCache = []; // List of all endeavors
```

**Key Functions**:

1. `loadEndeavors()` - Fetch and cache all endeavors from API
2. `renderTabs(endeavors)` - Render tab buttons with double-click handlers
3. `switchEndeavor(name)` - Change active endeavor, update URL, reload data
4. `createNewEndeavor()` - Prompt for name, create new endeavor
5. `startRenameEndeavor(name)` - Convert tab to input field for inline editing
6. `renameEndeavor(oldName, newName)` - Call API to rename across all collections

**Double-click to Rename Flow**:
```javascript
// On double-click, replace tab button with input field
// User types new name and presses Enter
// Call POST /api/endeavors/rename
// Update local cache and re-render tabs
// Reload all data for current view
```

**Data Loading Pattern**:
```javascript
// All API calls include endeavor parameter
fetch(`/api/snippets?start_date=${start}&end_date=${end}&endeavor=${currentEndeavor}`)
```

#### URL Integration
- URL format: `/?endeavor=fitness`
- Uses `URLSearchParams` and `history.pushState`
- On page load: Read endeavor from URL, default to "pet project"
- On endeavor switch: Update URL without page reload
- Enables bookmarking and sharing specific endeavors

### 4. Data Migration Strategy
**No explicit migration required** - handled via defensive coding:
- Backend: Use `.get('endeavor', 'pet project')` when reading documents
- Frontend: Pass endeavor parameter in all requests
- New documents: Always include endeavor field
- Existing documents: Treated as "pet project" when endeavor field missing

### 5. Business Rules
- **No limit** on number of endeavors users can create
- **Not deletable** - endeavors persist once created (no delete UI/API)
- **Mutable names** - can be renamed at any time via double-click
- **Empty names not allowed** - validation in both frontend and backend
- **Case-sensitive** - "Fitness" and "fitness" are different endeavors
- **URL safe** - endeavor names URL-encoded in query parameters

### 6. User Experience Flow

**Initial Load**:
1. App loads, reads `endeavor` from URL query param (default: "pet project")
2. Fetches all endeavors via `GET /api/endeavors`
3. Renders tabs with current endeavor highlighted
4. Loads data filtered by current endeavor

**Switching Endeavors**:
1. User clicks different tab
2. Tab becomes active (blue highlight)
3. URL updates with new endeavor
4. All data reloads filtered by new endeavor
5. Snippets, goals, reflections, daily scores all update

**Creating New Endeavor**:
1. User clicks "+ New Endeavor" button
2. Prompt asks for endeavor name
3. If name provided, creates first snippet/goal with that endeavor
4. New tab appears, becomes active
5. View switches to empty new endeavor

**Renaming Endeavor**:
1. User double-clicks any tab
2. Tab converts to inline input field with current name
3. User types new name and presses Enter (or Esc to cancel)
4. API call renames across all collections
5. Tab updates with new name
6. If renamed tab was active, URL updates

**Bookmarking**:
1. User can copy URL like `https://app.com/?endeavor=fitness`
2. Opening this URL directly loads fitness endeavor
3. Works for sharing specific endeavor views

### 7. Implementation Files

#### Backend: `app.py`
**New Functions**:
- `get_endeavors()` - Lines 559-602
- `rename_endeavor()` - Lines 605-675

**Modified Functions** (added endeavor parameter):
- `get_snippets()` - Added endeavor query param and filtering
- `create_snippet()` - Added endeavor field to document
- `get_goals()` - Added endeavor query param and filtering
- `create_goal()` - Added endeavor field to document
- `get_reflections()` - Added endeavor query param and filtering
- `create_reflection()` - Added endeavor field to document
- `get_daily_scores()` - Added endeavor query param and filtering
- `toggle_daily_score()` - Added endeavor field to document

#### Frontend: `static/js/app.js`
**New Functions**:
- `loadEndeavors()` - Lines 973-988
- `renderTabs()` - Lines 991-1033
- `switchEndeavor()` - Lines 1126-1135
- `createNewEndeavor()` - Lines 1138-1155
- `startRenameEndeavor()` - Lines 1036-1078
- `renameEndeavor()` - Lines 1080-1124

**Modified Functions**:
- `loadSnippets()` - Added endeavor parameter to API calls
- `saveSnippet()` - Added endeavor field to request body
- `loadGoals()` - Added endeavor parameter to API calls
- `saveGoal()` - Added endeavor field to request body
- `loadDailyScores()` - Added endeavor parameter to API calls
- `toggleDailyScore()` - Added endeavor field to request body
- `initApp()` - Added endeavor loading from URL

#### Templates: `templates/index.html`
**New Elements**:
- Endeavor tabs container (lines 37-42)
- Tab rendering target: `<div id="tabsContainer">`
- Add endeavor button: `<button class="add-endeavor-btn">`

#### Styles: `static/css/style.css`
**New Styles** (lines 94-160):
- `.endeavor-tabs` - Container layout
- `.tabs-container` - Tabs flexbox
- `.endeavor-tab` - Base tab styling
- `.endeavor-tab.active` - Active state (blue)
- `.endeavor-tab.editable` - Input field state
- `.endeavor-tab:hover` - Hover effects
- `.add-endeavor-btn` - New button styling

### 8. Testing

#### Test Coverage
- 12 new tests in `TestEndeavors` class
- 13 existing tests modified to include endeavor parameter
- Total: 64 tests, 92% code coverage

#### New Test Cases
- `test_get_endeavors_empty()` - Empty list scenario
- `test_get_endeavors_multiple()` - Multiple endeavors from all collections
- `test_get_endeavors_with_default()` - Default "pet project" handling
- `test_rename_endeavor()` - Successful rename across collections
- `test_rename_endeavor_missing_old_name()` - Validation error
- `test_rename_endeavor_missing_new_name()` - Validation error
- `test_rename_endeavor_empty_new_name()` - Empty name validation
- `test_get_snippets_with_endeavor_filter()` - Filtering works
- `test_get_snippets_multiple_endeavors()` - Multiple endeavors separated
- `test_get_goals_with_endeavor_filter()` - Goals filtering
- `test_get_reflections_with_endeavor_filter()` - Reflections filtering
- `test_get_daily_scores_with_endeavor_filter()` - Daily scores filtering

### 9. Performance Considerations
- **Frontend caching**: Endeavors list cached in `endeavorsCache` array
- **Lazy loading**: Only load data for current endeavor
- **Client-side filtering**: Backend returns all matching dates, client filters by endeavor
- **No N+1 queries**: Single query per collection per date range

### 10. Implementation Notes
- Store endeavor as string directly in each Firestore document
- To rename: Batch update all 4 collections with old→new name mapping
- Use Firestore queries with `.get('endeavor', 'pet project')` for backward compatibility
- Cache endeavors list in frontend to minimize API calls
- URL encoding ensures special characters in endeavor names work correctly
- Double-click pattern familiar from file systems provides intuitive rename UX

### 11. Edge Cases Handled
- Empty endeavor name → Validation error
- Renaming to same name → No-op, re-render tabs
- Non-existent old name in rename → Returns zero updates
- URL with invalid endeavor → Falls back to "pet project"
- No endeavors exist → Initialize with ["pet project"]
- Endeavor with special characters → URL encoded properly
- Multiple browser tabs → URL state kept in sync via URLSearchParams
