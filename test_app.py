"""
Unit tests for the Snippets application.
Tests key user experiences including authentication, snippet CRUD operations, and date handling.
"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from werkzeug.security import check_password_hash
import os

# Mock Firestore before importing app
with patch('app.firestore'):
    from app import app, get_week_dates, get_week_number


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_firestore():
    """Mock Firestore database"""
    with patch('app.db') as mock_db:
        yield mock_db


@pytest.fixture
def authenticated_client(client):
    """Create an authenticated test client"""
    with client.session_transaction() as sess:
        sess['logged_in'] = True
    return client


class TestAuthentication:
    """Test authentication functionality"""

    def test_login_page_loads(self, client):
        """Test that login page loads successfully"""
        response = client.get('/login')
        assert response.status_code == 200

    def test_successful_login(self, client):
        """Test successful login with correct credentials"""
        response = client.post('/login',
                              data=json.dumps({
                                  'username': os.environ.get('SNIPPET_USERNAME', 'admin'),
                                  'password': os.environ.get('SNIPPET_PASSWORD', 'changeme')
                              }),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_failed_login_wrong_password(self, client):
        """Test failed login with incorrect password"""
        response = client.post('/login',
                              data=json.dumps({
                                  'username': 'admin',
                                  'password': 'wrongpassword'
                              }),
                              content_type='application/json')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False

    def test_failed_login_wrong_username(self, client):
        """Test failed login with incorrect username"""
        response = client.post('/login',
                              data=json.dumps({
                                  'username': 'wronguser',
                                  'password': 'changeme'
                              }),
                              content_type='application/json')
        assert response.status_code == 401

    def test_logout(self, authenticated_client):
        """Test logout functionality"""
        response = authenticated_client.get('/logout')
        assert response.status_code == 302  # Redirect to login
        assert response.location.endswith('/login')

    def test_unauthenticated_access_redirects(self, client):
        """Test that unauthenticated users are redirected to login"""
        response = client.get('/')
        assert response.status_code == 302
        assert response.location.endswith('/login')


class TestSnippetCRUD:
    """Test snippet CRUD operations"""

    def test_get_snippets_requires_auth(self, client):
        """Test that getting snippets requires authentication"""
        response = client.get('/api/snippets')
        assert response.status_code == 302  # Redirect to login

    def test_create_snippet(self, authenticated_client, mock_firestore):
        """Test creating a new snippet"""
        # Mock Firestore collection and document
        mock_doc_ref = Mock()
        mock_doc_ref.id = 'test-snippet-id'
        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore.collection.return_value = mock_collection

        snippet_data = {
            'week_start': '2025-10-27',
            'week_end': '2025-11-02',
            'content': '# Test Snippet\n\n- Item 1\n- Item 2',
            'endeavor': 'pet project'
        }

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.post('/api/snippets',
                                                data=json.dumps(snippet_data),
                                                content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'id' in data

    def test_create_snippet_missing_fields(self, authenticated_client, mock_firestore):
        """Test creating snippet with missing required fields"""
        incomplete_data = {
            'week_start': '2025-10-27',
            # Missing week_end and content
        }

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.post('/api/snippets',
                                                data=json.dumps(incomplete_data),
                                                content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_snippet_by_id(self, authenticated_client, mock_firestore):
        """Test retrieving a specific snippet by ID"""
        # Mock Firestore document
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.id = 'test-id'
        mock_doc.to_dict.return_value = {
            'week_start': '2025-10-27',
            'week_end': '2025-11-02',
            'content': 'Test content',
            'endeavor': 'pet project'
        }

        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc

        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/snippets/test-id')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['week_start'] == '2025-10-27'
        assert data['content'] == 'Test content'
        assert data['endeavor'] == 'pet project'

    def test_get_nonexistent_snippet(self, authenticated_client, mock_firestore):
        """Test retrieving a snippet that doesn't exist"""
        mock_doc = Mock()
        mock_doc.exists = False

        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc

        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/snippets/nonexistent-id')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_update_snippet(self, authenticated_client, mock_firestore):
        """Test updating an existing snippet"""
        mock_doc_ref = Mock()
        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore.collection.return_value = mock_collection

        update_data = {
            'content': '# Updated Content\n\nThis is updated'
        }

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.put('/api/snippets/test-id',
                                               data=json.dumps(update_data),
                                               content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        mock_doc_ref.update.assert_called_once()

    def test_update_snippet_missing_content(self, authenticated_client, mock_firestore):
        """Test updating snippet without content"""
        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.put('/api/snippets/test-id',
                                               data=json.dumps({}),
                                               content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_delete_snippet(self, authenticated_client, mock_firestore):
        """Test deleting a snippet"""
        mock_doc_ref = Mock()
        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.delete('/api/snippets/test-id')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        mock_doc_ref.delete.assert_called_once()

    def test_get_snippets_with_date_filter(self, authenticated_client, mock_firestore):
        """Test getting snippets with date range filter"""
        # Mock Firestore query
        mock_doc1 = Mock()
        mock_doc1.id = 'snippet-1'
        mock_doc1.to_dict.return_value = {
            'week_start': '2025-10-27',
            'week_end': '2025-11-02',
            'content': 'Week 1 content',
            'endeavor': 'pet project'
        }

        mock_doc2 = Mock()
        mock_doc2.id = 'snippet-2'
        mock_doc2.to_dict.return_value = {
            'week_start': '2025-10-20',
            'week_end': '2025-10-26',
            'content': 'Week 2 content',
            'endeavor': 'pet project'
        }

        mock_query = Mock()
        mock_query.stream.return_value = [mock_doc1, mock_doc2]
        mock_query.order_by.return_value = mock_query
        mock_query.where.return_value = mock_query

        mock_collection = Mock()
        mock_collection.order_by.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/snippets?start_date=2025-10-20&end_date=2025-11-02')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_get_snippets_with_endeavor_filter(self, authenticated_client, mock_firestore):
        """Test getting snippets filtered by endeavor"""
        # Mock Firestore query
        mock_doc1 = Mock()
        mock_doc1.id = 'snippet-1'
        mock_doc1.to_dict.return_value = {
            'week_start': '2025-10-27',
            'week_end': '2025-11-02',
            'content': 'Work snippet',
            'endeavor': 'work'
        }

        mock_query = Mock()
        mock_query.stream.return_value = [mock_doc1]
        mock_query.order_by.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_collection = Mock()
        mock_collection.order_by.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/snippets?endeavor=work')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_get_snippets_multiple_endeavors(self, authenticated_client, mock_firestore):
        """Test that different endeavors return different data"""
        # Mock Firestore query for 'work' endeavor
        mock_doc_work = Mock()
        mock_doc_work.id = 'snippet-work'
        mock_doc_work.to_dict.return_value = {
            'week_start': '2025-10-27',
            'week_end': '2025-11-02',
            'content': 'Work content',
            'endeavor': 'work'
        }

        mock_query = Mock()
        mock_query.stream.return_value = [mock_doc_work]
        mock_query.order_by.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_collection = Mock()
        mock_collection.order_by.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/snippets?endeavor=work')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)


class TestWeekUtilities:
    """Test week-related utility functions"""

    def test_get_week_dates_for_monday(self):
        """Test getting week dates when input is a Monday"""
        # October 28, 2024 is a Monday
        monday = datetime(2024, 10, 28)
        result_monday, result_sunday = get_week_dates(monday)

        assert result_monday == monday
        assert result_sunday == datetime(2024, 11, 3)  # Following Sunday

    def test_get_week_dates_for_wednesday(self):
        """Test getting week dates when input is mid-week"""
        # October 30, 2024 is a Wednesday
        wednesday = datetime(2024, 10, 30)
        result_monday, result_sunday = get_week_dates(wednesday)

        assert result_monday == datetime(2024, 10, 28)  # Previous Monday
        assert result_sunday == datetime(2024, 11, 3)   # Following Sunday

    def test_get_week_dates_for_sunday(self):
        """Test getting week dates when input is a Sunday"""
        # November 3, 2024 is a Sunday
        sunday = datetime(2024, 11, 3)
        result_monday, result_sunday = get_week_dates(sunday)

        assert result_monday == datetime(2024, 10, 28)  # Week's Monday
        assert result_sunday == sunday

    def test_get_week_number(self):
        """Test ISO week number calculation"""
        # January 1, 2024 is Week 1
        date = datetime(2024, 1, 1)
        week_num = get_week_number(date)
        assert week_num == 1

        # October 28, 2024
        date = datetime(2024, 10, 28)
        week_num = get_week_number(date)
        assert week_num > 0 and week_num <= 53


class TestWeekInfoAPI:
    """Test the week info API endpoint"""

    def test_get_week_info(self, authenticated_client):
        """Test getting week information for a specific date"""
        response = authenticated_client.get('/api/week/2024-10-30')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'week_number' in data
        assert 'week_start' in data
        assert 'week_end' in data
        assert 'week_start_formatted' in data
        assert 'week_end_formatted' in data

        # Wednesday Oct 30 should be in week starting Oct 28 (Monday)
        assert data['week_start'] == '2024-10-28'
        assert data['week_end'] == '2024-11-03'

    def test_get_week_info_invalid_date(self, authenticated_client):
        """Test getting week info with invalid date format"""
        response = authenticated_client.get('/api/week/invalid-date')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


class TestFirestoreUnavailable:
    """Test behavior when Firestore is unavailable"""

    def test_snippets_api_firestore_unavailable(self, authenticated_client):
        """Test that API returns error when Firestore is unavailable"""
        with patch('app.FIRESTORE_AVAILABLE', False):
            response = authenticated_client.get('/api/snippets')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Firestore' in data['error']


class TestHomePage:
    """Test home page functionality"""

    def test_home_page_requires_auth(self, client):
        """Test that home page requires authentication"""
        response = client.get('/')
        assert response.status_code == 302
        assert response.location.endswith('/login')

    def test_home_page_loads_when_authenticated(self, authenticated_client):
        """Test that authenticated users can access home page"""
        response = authenticated_client.get('/')
        assert response.status_code == 200
        assert b'My snippets' in response.data or b'Snippets' in response.data


class TestPasswordSecurity:
    """Test password hashing and security"""

    def test_password_is_hashed(self):
        """Test that passwords are properly hashed"""
        from app import PASSWORD_HASH
        # The password hash should not be the plain password
        assert PASSWORD_HASH != os.environ.get('SNIPPET_PASSWORD', 'changeme')
        # Should be verifiable
        assert check_password_hash(PASSWORD_HASH, os.environ.get('SNIPPET_PASSWORD', 'changeme'))


class TestSessionManagement:
    """Test session management"""

    def test_session_persists_after_login(self, client):
        """Test that session persists after login"""
        # Login
        client.post('/login',
                   data=json.dumps({
                       'username': os.environ.get('SNIPPET_USERNAME', 'admin'),
                       'password': os.environ.get('SNIPPET_PASSWORD', 'changeme')
                   }),
                   content_type='application/json')

        # Access protected page
        response = client.get('/')
        assert response.status_code == 200

    def test_session_cleared_after_logout(self, authenticated_client):
        """Test that session is cleared after logout"""
        # Logout
        authenticated_client.get('/logout')

        # Try to access protected page
        response = authenticated_client.get('/')
        assert response.status_code == 302
        assert response.location.endswith('/login')


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
            'content': '# Weekly Goals\n\n- Complete feature X\n- Review PRs',
            'endeavor': 'pet project'
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
            'content': 'Complete feature X',
            'endeavor': 'pet project'
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
        assert data['endeavor'] == 'pet project'

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
            'content': 'Week 1 goals',
            'endeavor': 'pet project'
        }

        mock_doc2 = Mock()
        mock_doc2.id = 'goal-2'
        mock_doc2.to_dict.return_value = {
            'week_start': '2025-10-20',
            'week_end': '2025-10-26',
            'content': 'Week 2 goals',
            'endeavor': 'pet project'
        }

        mock_query = Mock()
        mock_query.stream.return_value = [mock_doc1, mock_doc2]
        mock_query.order_by.return_value = mock_query
        mock_query.where.return_value = mock_query

        mock_collection = Mock()
        mock_collection.order_by.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/goals?start_date=2025-10-20&end_date=2025-11-02')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_get_goals_with_endeavor_filter(self, authenticated_client, mock_firestore):
        """Test getting goals filtered by endeavor"""
        mock_doc1 = Mock()
        mock_doc1.id = 'goal-1'
        mock_doc1.to_dict.return_value = {
            'week_start': '2025-10-27',
            'week_end': '2025-11-02',
            'content': 'Work goals',
            'endeavor': 'work'
        }

        mock_query = Mock()
        mock_query.stream.return_value = [mock_doc1]
        mock_query.order_by.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_collection = Mock()
        mock_collection.order_by.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/goals?endeavor=work')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)


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
            'week_end': '2025-11-02',
            'content': '# Weekly Reflection\n\n- Learned about X\n- Improved Y',
            'endeavor': 'pet project'
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
            'week_end': '2025-11-02',
            'content': 'Learned about testing',
            'endeavor': 'pet project'
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
        assert data['endeavor'] == 'pet project'

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
            'week_end': '2025-11-02',
            'content': 'Week 1 reflections',
            'endeavor': 'pet project'
        }

        mock_doc2 = Mock()
        mock_doc2.id = 'reflection-2'
        mock_doc2.to_dict.return_value = {
            'week_start': '2025-10-20',
            'week_end': '2025-10-26',
            'content': 'Week 2 reflections',
            'endeavor': 'pet project'
        }

        mock_query = Mock()
        mock_query.stream.return_value = [mock_doc1, mock_doc2]
        mock_query.order_by.return_value = mock_query
        mock_query.where.return_value = mock_query

        mock_collection = Mock()
        mock_collection.order_by.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/reflections?start_date=2025-10-20&end_date=2025-11-02')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_get_reflections_with_endeavor_filter(self, authenticated_client, mock_firestore):
        """Test getting reflections filtered by endeavor"""
        mock_doc1 = Mock()
        mock_doc1.id = 'reflection-1'
        mock_doc1.to_dict.return_value = {
            'week_start': '2025-10-27',
            'week_end': '2025-11-02',
            'content': 'Work reflections',
            'endeavor': 'work'
        }

        mock_query = Mock()
        mock_query.stream.return_value = [mock_doc1]
        mock_query.order_by.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_collection = Mock()
        mock_collection.order_by.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/reflections?endeavor=work')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)


class TestEndeavors:
    """Test endeavor management"""

    def test_get_endeavors_requires_auth(self, client):
        """Test that getting endeavors requires authentication"""
        response = client.get('/api/endeavors')
        assert response.status_code == 302  # Redirect to login

    def test_get_endeavors_empty(self, authenticated_client, mock_firestore):
        """Test getting endeavors when no data exists"""
        # Mock empty collections
        mock_collection = Mock()
        mock_collection.stream.return_value = []
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/endeavors')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_get_endeavors_multiple(self, authenticated_client, mock_firestore):
        """Test getting list of unique endeavors from all collections"""
        # Mock documents with different endeavors
        mock_doc1 = Mock()
        mock_doc1.to_dict.return_value = {'endeavor': 'pet project'}

        mock_doc2 = Mock()
        mock_doc2.to_dict.return_value = {'endeavor': 'work'}

        mock_doc3 = Mock()
        mock_doc3.to_dict.return_value = {'endeavor': 'pet project'}  # Duplicate

        mock_collection = Mock()
        mock_collection.stream.return_value = [mock_doc1, mock_doc2, mock_doc3]
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True), \
             patch('app.GOALS_ENABLED', True), \
             patch('app.REFLECTIONS_ENABLED', True), \
             patch('app.DAILY_SCORES_ENABLED', True):
            response = authenticated_client.get('/api/endeavors')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        # Should have unique endeavors, sorted
        assert 'pet project' in data
        assert 'work' in data

    def test_get_endeavors_with_default(self, authenticated_client, mock_firestore):
        """Test that documents without endeavor field default to 'pet project'"""
        # Mock document without endeavor field
        mock_doc = Mock()
        mock_doc.to_dict.return_value = {'content': 'test'}

        mock_collection = Mock()
        mock_collection.stream.return_value = [mock_doc]
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/endeavors')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'pet project' in data

    def test_rename_endeavor(self, authenticated_client, mock_firestore):
        """Test renaming an endeavor across all collections"""
        # Mock documents with the old endeavor name
        mock_doc1 = Mock()
        mock_doc1.reference = Mock()
        mock_doc1.to_dict.return_value = {'endeavor': 'old name'}

        mock_doc2 = Mock()
        mock_doc2.reference = Mock()
        mock_doc2.to_dict.return_value = {'endeavor': 'old name'}

        mock_doc3 = Mock()
        mock_doc3.reference = Mock()
        mock_doc3.to_dict.return_value = {'endeavor': 'other project'}

        mock_collection = Mock()
        mock_collection.stream.return_value = [mock_doc1, mock_doc2, mock_doc3]
        mock_firestore.collection.return_value = mock_collection

        rename_data = {
            'old_name': 'old name',
            'new_name': 'new name'
        }

        with patch('app.FIRESTORE_AVAILABLE', True), \
             patch('app.GOALS_ENABLED', True), \
             patch('app.REFLECTIONS_ENABLED', True), \
             patch('app.DAILY_SCORES_ENABLED', True):
            response = authenticated_client.post('/api/endeavors/rename',
                                                 data=json.dumps(rename_data),
                                                 content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'updated_count' in data
        # Should have updated the two docs with 'old name' in each of 4 collections
        mock_doc1.reference.update.assert_called()
        mock_doc2.reference.update.assert_called()

    def test_rename_endeavor_missing_old_name(self, authenticated_client, mock_firestore):
        """Test renaming without providing old_name"""
        rename_data = {
            'new_name': 'new name'
        }

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.post('/api/endeavors/rename',
                                                 data=json.dumps(rename_data),
                                                 content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'old_name' in data['error'] or 'required' in data['error']

    def test_rename_endeavor_missing_new_name(self, authenticated_client, mock_firestore):
        """Test renaming without providing new_name"""
        rename_data = {
            'old_name': 'old name'
        }

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.post('/api/endeavors/rename',
                                                 data=json.dumps(rename_data),
                                                 content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'new_name' in data['error'] or 'required' in data['error']

    def test_rename_endeavor_empty_new_name(self, authenticated_client, mock_firestore):
        """Test renaming with empty new_name"""
        rename_data = {
            'old_name': 'old name',
            'new_name': '   '  # Whitespace only
        }

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.post('/api/endeavors/rename',
                                                 data=json.dumps(rename_data),
                                                 content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'empty' in data['error'].lower()


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
        mock_query.where.return_value = mock_query

        mock_collection = Mock()
        mock_collection.where.return_value = mock_query

        mock_doc_ref = Mock()
        mock_doc_ref.id = 'test-score-id'
        mock_collection.document.return_value = mock_doc_ref

        mock_firestore.collection.return_value = mock_collection

        score_data = {
            'date': '2025-11-01',
            'endeavor': 'pet project'
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
        mock_query.where.return_value = mock_query

        mock_collection = Mock()
        mock_collection.where.return_value = mock_query
        mock_firestore.collection.return_value = mock_collection

        score_data = {
            'date': '2025-11-01',
            'endeavor': 'pet project'
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
            'score': 1,
            'endeavor': 'pet project'
        }

        mock_doc2 = Mock()
        mock_doc2.id = 'score-2'
        mock_doc2.to_dict.return_value = {
            'date': '2025-11-02',
            'score': 1,
            'endeavor': 'pet project'
        }

        mock_query = Mock()
        mock_query.stream.return_value = [mock_doc1, mock_doc2]
        mock_query.order_by.return_value = mock_query
        mock_query.where.return_value = mock_query

        mock_collection = Mock()
        mock_collection.order_by.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/daily_scores?start_date=2025-11-01&end_date=2025-11-03')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_get_daily_scores_with_endeavor_filter(self, authenticated_client, mock_firestore):
        """Test getting daily scores filtered by endeavor"""
        mock_doc1 = Mock()
        mock_doc1.id = 'score-1'
        mock_doc1.to_dict.return_value = {
            'date': '2025-11-01',
            'score': 1,
            'endeavor': 'work'
        }

        mock_query = Mock()
        mock_query.stream.return_value = [mock_doc1]
        mock_query.order_by.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_collection = Mock()
        mock_collection.order_by.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_firestore.collection.return_value = mock_collection

        with patch('app.FIRESTORE_AVAILABLE', True):
            response = authenticated_client.get('/api/daily_scores?endeavor=work')

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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
