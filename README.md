# Snippets - Personal Weekly Diary

A simple, password-protected weekly diary application for tracking your work snippets. Inspired by Google's internal snippets tool.

## Features

- Weekly markdown-based diary entries
- Date range filtering and week navigation
- Single-user password authentication
- Clean, Google-inspired UI
- Cloud-hosted on Google App Engine
- Firestore database (persistent, globally accessible)
- Free tier eligible deployment
- Automated testing before deployment
- 89% test coverage with 27 unit tests

## Architecture

- **Frontend**: Vanilla JavaScript with marked.js for markdown rendering
- **Backend**: Python Flask application
- **Database**: Google Cloud Firestore (Native Mode)
- **Hosting**: Google App Engine (Python 3.12)
- **Authentication**: Session-based with PBKDF2-SHA256 password hashing
- **Testing**: pytest with coverage reporting

## Project Structure

```
snippets/
├── app.py                 # Flask application
├── test_app.py            # Unit tests
├── requirements.txt       # Python dependencies
├── deploy.sh              # Deployment script (runs tests first)
├── run_tests.sh           # Test runner script
├── app.yaml.template      # App Engine config template
├── .env.production        # Production secrets (gitignored)
├── templates/
│   ├── index.html         # Main application UI
│   └── login.html         # Login page
└── static/
    ├── css/style.css      # Styles
    └── js/app.js          # Frontend logic
```

## Quick Start

### Prerequisites

- Google Cloud account
- `gcloud` CLI installed and configured
- Python 3.12+

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd snippets
   ```

2. **Create your secrets file**
   ```bash
   cat > .env.production << 'EOF'
   SECRET_KEY=$(python3 -c "import os; print(os.urandom(24).hex())")
   SNIPPET_USERNAME=admin
   SNIPPET_PASSWORD=YourSecurePassword
   EOF
   ```

3. **Configure Google Cloud**
   ```bash
   # Set your project
   gcloud config set project YOUR_PROJECT_ID

   # Create App Engine app (first time only)
   gcloud app create --region=us-central

   # Create Firestore database in Native Mode
   gcloud firestore databases create \
     --location=nam5 \
     --type=firestore-native
   ```

### Deployment

Deploy with a single command:

```bash
./deploy.sh
```

The deployment script will:
1. Run all unit tests automatically
2. Abort deployment if any tests fail
3. Load secrets from `.env.production`
4. Generate `app.yaml` with environment variables
5. Deploy to Google App Engine
6. Clean up temporary files

Your app will be live at: `https://YOUR_PROJECT_ID.appspot.com`

### Login

- **Username**: `admin` (or as configured in `.env.production`)
- **Password**: As set in `.env.production`

## Testing

Run tests locally:

```bash
./run_tests.sh
```

This will:
- Create/validate virtual environment
- Install dependencies
- Run unit tests with coverage reporting

**Test coverage includes:**
- Authentication (login, logout, sessions)
- Snippet CRUD operations
- Date/week utilities
- Security (password hashing)
- Error handling
- Firestore integration

## How Snippets Work

- **Week Definition**: Monday to Sunday (ISO week standard)
- **Default View**: Current week minus 4 weeks to current week
- **Date Selection**:
  - Start date must be a Monday
  - End date must be a Sunday
  - Only complete weeks are shown
- **Add Snippet**: Click "Add Snippets" button for weeks without entries
- **Edit**: Click "Edit" button on existing snippets
- **Order**: Displayed in reverse chronological order (latest first)

## Markdown Support

The editor supports standard markdown:

- **Bold**: `**text**`
- *Italic*: `*text*`
- Strikethrough: `~~text~~`
- Bullets: `- item`
- Numbered lists: `1. item`
- Links: `[text](url)`
- Headers: `# H1`, `## H2`, etc.

## Security

- Secrets stored in `.env.production` (gitignored)
- Passwords hashed with PBKDF2-SHA256
- Session-based authentication
- HTTPS enforced in production
- App Engine handles TLS certificates automatically
- `app.yaml` generated dynamically, never committed to git

**Important**: Always use a strong, unique password in production.

## Configuration

### Environment Variables

All configuration is done via `.env.production`:

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Flask session secret (random hex string) | Yes |
| `SNIPPET_USERNAME` | Login username | Yes |
| `SNIPPET_PASSWORD` | Login password | Yes |

### App Engine Settings

Edit [app.yaml.template](app.yaml.template) to customize:

- `instance_class`: F1 (free tier) or higher
- `max_idle_instances`: Maximum instances when idle
- Scaling parameters
- Cache control headers

## Firestore Data Model

### Collection: `snippets`

Each document contains:

```javascript
{
  week_start: "2025-10-27",     // Monday (YYYY-MM-DD)
  week_end: "2025-11-02",       // Sunday (YYYY-MM-DD)
  content: "# Week summary...", // Markdown content
  created_at: Timestamp,        // Auto-generated
  updated_at: Timestamp         // Auto-updated
}
```

## Maintenance

### View Logs

```bash
gcloud app logs tail
```

### View Firestore Data

```bash
# Via console
open https://console.cloud.google.com/firestore

# Via CLI
gcloud firestore databases list
```

### Update Deployment

After making code changes:

```bash
./deploy.sh
```

Tests will run automatically before deployment proceeds.

### Backup Data

Firestore provides automatic backups. To export data manually:

```bash
gcloud firestore export gs://YOUR_BUCKET/backups
```

## Cost

This application runs on Google Cloud's **free tier**:

- App Engine F1 instance: **Free** (28 instance hours/day)
- Firestore: **Free** (1 GB storage, 50K reads/day, 20K writes/day)
- Typical usage for personal diary: **$0/month**

## Troubleshooting

### Tests failing during deployment

The deployment will automatically abort if tests fail. Check the test output for specific errors:

```bash
./run_tests.sh
```

### Can't login

- Verify credentials in `.env.production`
- Check browser console for errors
- Verify session cookies are enabled

### Deployment fails

- Ensure `gcloud` is authenticated: `gcloud auth list`
- Check project is set: `gcloud config get-value project`
- Verify App Engine app exists: `gcloud app describe`

### Snippets not loading

- Check Firestore is in Native Mode (not Datastore Mode)
- View logs: `gcloud app logs tail`
- Verify Firestore permissions
- Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+F5) to clear cache

### Index errors

- Firestore may require indexes for complex queries
- Follow the URL in error message to create indexes automatically

## Development

### Run Tests

```bash
./run_tests.sh
```

### Local Development

To run locally (requires Firestore credentials):

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export $(cat .env.production | xargs)

# Set Google Cloud credentials
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Run
python app.py
```

Visit: `http://localhost:5001`

## Files to Never Commit

The following files are gitignored and should never be committed:

- `.env.production` - Contains secrets
- `app.yaml` - Generated from template, contains secrets
- `snippets.db` - Old SQLite database (if exists)
- `venv/` - Virtual environment

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

This is a personal project, but feel free to fork and adapt for your needs!

---

**Live URL**: https://snippets-prakhar.uc.r.appspot.com
