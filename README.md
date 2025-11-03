# Snippets - Personal Weekly Diary

A simple, password-protected weekly diary application for tracking your work snippets. Inspired by Google's internal snippets tool.

## Features

- 📝 Weekly markdown-based diary entries
- 📅 Date range filtering and week navigation
- 🔒 Single-user password authentication
- ✨ Clean, Google-inspired UI
- ☁️ Cloud-hosted on Google App Engine
- 💾 Firestore database (persistent, globally accessible)
- 🚀 Free tier eligible deployment

## Architecture

- **Frontend**: Vanilla JavaScript with marked.js for markdown rendering
- **Backend**: Python Flask application
- **Database**: Google Cloud Firestore (Native Mode)
- **Hosting**: Google App Engine (Python 3.12)
- **Authentication**: Session-based with password hashing

## Project Structure

```
snippets/
├── app.py                 # Flask application
├── requirements.txt       # Python dependencies
├── deploy.sh             # Deployment script
├── app.yaml.template     # App Engine config template
├── .env.production       # Production secrets (gitignored)
├── templates/
│   ├── index.html        # Main application UI
│   └── login.html        # Login page
└── static/
    ├── css/style.css     # Styles
    └── js/app.js         # Frontend logic
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

The script will:
- Load secrets from `.env.production`
- Generate `app.yaml` with environment variables
- Deploy to Google App Engine
- Clean up temporary files

Your app will be live at: `https://YOUR_PROJECT_ID.appspot.com`

### Login

- **Username**: `admin` (or as configured in `.env.production`)
- **Password**: As set in `.env.production`

## How Snippets Work

- **Week Definition**: Monday to Sunday (ISO week standard)
- **Default View**: Current week minus 4 weeks to current week
- **Date Selection**:
  - Start date must be a Monday
  - End date must be a Sunday
  - Only complete weeks are shown
- **Add Snippet**: Click "Add Snippet" for weeks without entries
- **Edit**: Click "Edit" on existing snippets
- **Order**: Displayed in reverse chronological order (latest first)

## Markdown Support

The editor supports standard markdown:

- **Bold**: `**text**`
- *Italic*: `*text*`
- ~~Strikethrough~~: `~~text~~`
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

⚠️ **Important**: Always use a strong, unique password in production.

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

### Backup Data

Firestore provides automatic backups. To export data:

```bash
gcloud firestore export gs://YOUR_BUCKET/backups
```

## Cost

This application runs on Google Cloud's **free tier**:

- App Engine F1 instance: **Free** (28 instance hours/day)
- Firestore: **Free** (1 GB storage, 50K reads/day, 20K writes/day)
- Typical usage for personal diary: **$0/month**

## Troubleshooting

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

### Index errors
- Firestore may require indexes for complex queries
- Follow the URL in error message to create indexes automatically

## Development

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

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

This is a personal project, but feel free to fork and adapt for your needs!

---

**Live URL**: https://YOUR_PROJECT_ID.appspot.com
