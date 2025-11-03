#!/bin/bash
# Deployment script for Google App Engine
# Loads secrets from .env.production (gitignored)

set -e  # Exit on error

echo "🚀 Deploying to Google App Engine..."

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo "❌ Error: .env.production not found!"
    echo "Create it with your secrets first."
    exit 1
fi

# Load environment variables from .env.production
source .env.production

# Validate required variables
if [ -z "$SECRET_KEY" ] || [ -z "$SNIPPET_PASSWORD" ]; then
    echo "❌ Error: SECRET_KEY or SNIPPET_PASSWORD not set in .env.production"
    exit 1
fi

echo "✅ Loaded secrets from .env.production"
echo "📝 Generating app.yaml from template..."

# Create app.yaml from template with secrets
sed -e "s|__SNIPPET_USERNAME__|$SNIPPET_USERNAME|g" \
    -e "s|__SNIPPET_PASSWORD__|$SNIPPET_PASSWORD|g" \
    -e "s|__SECRET_KEY__|$SECRET_KEY|g" \
    app.yaml.template > app.yaml

echo "📦 Deploying to App Engine..."

# Deploy
gcloud app deploy --quiet

# Clean up app.yaml (remove secrets)
rm -f app.yaml

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Your app is live at:"
gcloud app browse --no-launch-browser 2>&1 | grep "https://" || echo "   Run: gcloud app browse"
echo ""
echo "🔐 Login credentials:"
echo "   Username: $SNIPPET_USERNAME"
echo "   Password: [hidden for security]"
echo ""
