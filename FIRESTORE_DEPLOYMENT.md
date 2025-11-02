# Google App Engine + Firestore Deployment Guide

Deploy your Snippets app to Google App Engine with Cloud Firestore for persistent, globally-replicated storage.

## Why Firestore?

✅ **Persistent** - Data survives redeployments
✅ **Free tier** - 1GB storage, 50K reads/day, 20K writes/day
✅ **Automatic backups** - Google handles backups
✅ **Global replication** - Data replicated worldwide
✅ **No maintenance** - Fully managed by Google

## Prerequisites

1. **Google Cloud Account** - [Sign up](https://cloud.google.com/free) for free tier
2. **Google Cloud SDK** - Install locally
3. **Credit card** - Required for verification (won't be charged on free tier)

## Step-by-Step Deployment

### 1. Install Google Cloud SDK

```bash
# macOS
brew install google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Windows
# Download from: https://cloud.google.com/sdk/docs/install
```

### 2. Initialize Google Cloud

```bash
# Login to Google Cloud
gcloud auth login

# Create a new project (choose a unique ID)
gcloud projects create snippets-[YOUR-NAME] --name="My Snippets"

# Set the project as default
gcloud config set project snippets-[YOUR-NAME]

# Enable required APIs
gcloud services enable appengine.googleapis.com
gcloud services enable firestore.googleapis.com
```

### 3. Create App Engine Application

```bash
# Create App Engine app (choose your region)
gcloud app create --region=us-central

# Common regions:
# us-central, us-east1, us-west2
# europe-west, europe-west2
# asia-northeast1, asia-southeast1
```

### 4. Enable Firestore

```bash
# Create Firestore database in Native mode
gcloud firestore databases create --region=us-central1

# Or use the Console:
# 1. Go to https://console.cloud.google.com/firestore
# 2. Click "Select Native Mode"
# 3. Choose a region (same as App Engine for best performance)
# 4. Click "Create Database"
```

### 5. Configure Your App

Edit `app.yaml` and update these values:

```yaml
env_variables:
  SNIPPET_USERNAME: 'your-username'
  SNIPPET_PASSWORD: 'your-secure-password'
  SECRET_KEY: 'your-random-secret-key'
```

**Generate a random secret key:**
```bash
python3 -c "import os; print(os.urandom(24).hex())"
```

### 6. Deploy to App Engine

```bash
# Deploy your application
gcloud app deploy

# When prompted:
# - Service: default
# - Confirm: Y

# This will:
# 1. Upload your code
# 2. Install dependencies (requirements.txt)
# 3. Start your app
# Takes 2-5 minutes
```

### 7. View Your App

```bash
# Open in browser
gcloud app browse

# Your app URL: https://snippets-[YOUR-NAME].appspot.com
```

### 8. View Logs (Optional)

```bash
# Stream logs in real-time
gcloud app logs tail -s default

# View recent logs
gcloud app logs read
```

## Firestore Data Structure

Your snippets are stored in Firestore like this:

```
Firestore Database
│
└── Collection: "snippets"
     │
     ├── Document: "abc123xyz"
     │    ├── week_start: "2025-02-03"
     │    ├── week_end: "2025-02-09"
     │    ├── content: "- Built new feature\n- Fixed bugs"
     │    ├── created_at: Timestamp(2025-02-03 10:30:00)
     │    └── updated_at: Timestamp(2025-02-03 15:45:00)
     │
     ├── Document: "def456uvw"
     │    └── ... (more snippets)
     │
     └── ...
```

## Viewing Your Data in Firestore

```bash
# Open Firestore Console
open https://console.cloud.google.com/firestore/data

# Or via gcloud (list all snippets)
gcloud firestore export gs://[BUCKET-NAME]/firestore-backup
```

## Cost Breakdown

### Free Tier (Permanent):

**App Engine:**
- 28 instance hours/day = FREE
- 1GB egress/day = FREE
- SSL certificates = FREE

**Firestore:**
- 1GB storage = FREE
- 50,000 reads/day = FREE
- 20,000 writes/day = FREE
- 20,000 deletes/day = FREE

### Personal use estimate:
- Daily usage: ~100 reads, ~10 writes
- Storage: < 10MB
- **Total cost: $0/month** ✅

### If you exceed free tier:
- Additional reads: $0.06 per 100,000
- Additional writes: $0.18 per 100,000
- Additional storage: $0.18/GB/month

**Example:** 100,000 reads/day = ~$1.80/month

## Backups

**Firestore handles backups automatically:**
- Point-in-time recovery (last 7 days)
- Automatic multi-region replication
- 99.999% availability SLA

**Manual export (optional):**
```bash
# Create a Cloud Storage bucket
gsutil mb gs://snippets-backup-[YOUR-NAME]

# Export Firestore data
gcloud firestore export gs://snippets-backup-[YOUR-NAME]/$(date +%Y%m%d)
```

## Updating Your App

```bash
# Make code changes locally
# Then redeploy
gcloud app deploy

# Your data in Firestore remains untouched!
```

## Migrating Existing SQLite Data

If you have existing SQLite data, here's how to migrate:

```python
# migration_script.py
import sqlite3
from google.cloud import firestore

# Initialize Firestore
db = firestore.Client()

# Connect to SQLite
conn = sqlite3.connect('snippets.db')
cursor = conn.cursor()

# Get all snippets
cursor.execute('SELECT * FROM snippets')
snippets = cursor.fetchall()

# Migrate to Firestore
for snippet in snippets:
    db.collection('snippets').add({
        'week_start': snippet[1],
        'week_end': snippet[2],
        'content': snippet[3],
        'created_at': snippet[4],
        'updated_at': snippet[5]
    })
    print(f"Migrated snippet {snippet[0]}")

print("Migration complete!")
```

Run it:
```bash
python migration_script.py
```

## Troubleshooting

### Deployment fails with "API not enabled"
```bash
gcloud services enable appengine.googleapis.com
gcloud services enable firestore.googleapis.com
```

### "Permission denied" errors
```bash
# Re-authenticate
gcloud auth login
gcloud auth application-default login
```

### Can't access Firestore locally
```bash
# Download application credentials
gcloud auth application-default login

# Or set credentials manually
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
```

### App deployed but shows errors
```bash
# Check logs
gcloud app logs tail -s default

# Common issues:
# - SNIPPET_PASSWORD not set in app.yaml
# - Firestore not enabled
# - Wrong region selected
```

## Security Best Practices

1. **Change default password:**
```yaml
env_variables:
  SNIPPET_PASSWORD: 'use-a-strong-password-here'
```

2. **Use Secret Manager (recommended):**
```bash
# Store password securely
echo -n "your-password" | gcloud secrets create snippet-password --data-file=-

# Reference in app.yaml (requires additional config)
```

3. **Firestore security rules:**
```javascript
// Go to Firestore → Rules in Console
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Only allow access from App Engine
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

4. **Enable HTTPS only** (already configured in app.yaml)

## Custom Domain (Optional)

```bash
# Verify domain ownership
gcloud app domain-mappings create www.yourdomain.com

# Update DNS records as instructed
# A record: → App Engine IP
# CNAME: www → ghs.googlehosted.com

# SSL certificate auto-provisioned (free)
```

## Monitoring & Alerts

```bash
# View app metrics
gcloud app browse --service=default
# Then go to: Console → App Engine → Dashboard

# Set up alerts (e.g., high error rate)
# Console → Monitoring → Alerting → Create Policy
```

## Deleting Your App

```bash
# Disable App Engine (stops serving, keeps data)
gcloud app services delete default

# Delete Firestore data
gcloud firestore databases delete

# Delete entire project
gcloud projects delete snippets-[YOUR-NAME]
```

## Comparison: Before vs After

### Before (SQLite):
- ❌ Data lost on redeploy
- ❌ Manual backups needed
- ❌ Single-server storage
- ✅ Simple SQL queries

### After (Firestore):
- ✅ Data persists forever
- ✅ Automatic backups
- ✅ Global replication
- ✅ Still free!
- ✅ Scalable to millions of users

## Next Steps

1. Deploy your app: `gcloud app deploy`
2. Login and create your first snippet
3. Verify data in Firestore Console
4. Set up a custom domain (optional)
5. Invite friends to use it!

## Support & Resources

- **App Engine Docs:** https://cloud.google.com/appengine/docs
- **Firestore Docs:** https://cloud.google.com/firestore/docs
- **Pricing Calculator:** https://cloud.google.com/products/calculator
- **Status Dashboard:** https://status.cloud.google.com

## Quick Reference

```bash
# Deploy app
gcloud app deploy

# View logs
gcloud app logs tail

# Open app
gcloud app browse

# View Firestore data
open https://console.cloud.google.com/firestore

# Check quota usage
gcloud app open-console
```

---

**Ready to deploy?** Run `gcloud app deploy` and you're live! 🚀
