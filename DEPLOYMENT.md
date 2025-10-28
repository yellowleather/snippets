# Deployment Guide

This guide covers deploying your Snippets app to various hosting platforms. All options listed are **free** or have generous free tiers.

## Option 1: Render.com (Recommended - Easiest)

**Pros:** Free tier, automatic HTTPS, easy setup, no credit card required
**Cons:** App sleeps after 15 minutes of inactivity (takes ~30 seconds to wake up)

### Steps:

1. **Push your code to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Sign up at [render.com](https://render.com)**

3. **Create a new Web Service:**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Name:** snippets (or your choice)
     - **Environment:** Python 3
     - **Build Command:** `pip install -r requirements.txt gunicorn`
     - **Start Command:** `gunicorn app:app`
     - **Plan:** Free

4. **Add Environment Variables:**
   Click "Environment" tab and add:
   ```
   SECRET_KEY = [generate random string with: python -c "import os; print(os.urandom(24).hex())"]
   SNIPPET_PASSWORD = your-secure-password-here
   SNIPPET_USERNAME = admin (optional)
   ```

5. **Deploy!** 
   - Click "Create Web Service"
   - Your app will be live at: `https://your-app-name.onrender.com`
   - Initial build takes 2-3 minutes

6. **Important:** Bookmark your app URL! The free tier sleeps after inactivity.

---

## Option 2: Railway.app

**Pros:** Easy deployment, generous free tier ($5/month credit), doesn't sleep
**Cons:** Requires credit card (but won't charge unless you exceed free tier)

### Steps:

1. **Sign up at [railway.app](https://railway.app)**

2. **Deploy from GitHub:**
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway auto-detects Python app

3. **Add Environment Variables:**
   - Click your service → "Variables" tab
   - Add: `SECRET_KEY`, `SNIPPET_PASSWORD`, `SNIPPET_USERNAME`

4. **Get your URL:**
   - Click "Settings" → "Generate Domain"
   - Your app is live at the generated URL!

---

## Option 3: Fly.io

**Pros:** Good free tier, doesn't sleep, fast global deployment
**Cons:** Requires credit card, slightly more complex setup

### Steps:

1. **Install Fly CLI:**
   ```bash
   # macOS
   brew install flyctl
   
   # Linux
   curl -L https://fly.io/install.sh | sh
   
   # Windows
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. **Sign up and login:**
   ```bash
   fly auth signup
   fly auth login
   ```

3. **Initialize app:**
   ```bash
   fly launch
   ```
   - Choose app name
   - Select region closest to you
   - Say "No" to PostgreSQL
   - Say "No" to Redis

4. **Set secrets:**
   ```bash
   fly secrets set SECRET_KEY="your-random-secret-key"
   fly secrets set SNIPPET_PASSWORD="your-password"
   ```

5. **Deploy:**
   ```bash
   fly deploy
   ```

Your app is live at: `https://your-app-name.fly.dev`

---

## Option 4: PythonAnywhere (Great for Beginners)

**Pros:** Very beginner-friendly, free tier available
**Cons:** Free tier has some limitations, manual setup

### Steps:

1. **Sign up at [pythonanywhere.com](https://www.pythonanywhere.com)**

2. **Upload your code:**
   - Go to "Files" tab
   - Upload all your files or clone from GitHub

3. **Create virtual environment:**
   Open Bash console:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 myenv
   pip install -r requirements.txt
   ```

4. **Configure Web App:**
   - Go to "Web" tab → "Add a new web app"
   - Choose "Manual configuration" → Python 3.10
   - Set:
     - **Source code:** /home/yourusername/your-app-folder
     - **Working directory:** /home/yourusername/your-app-folder
     - **WSGI file:** Edit to point to your app

5. **Edit WSGI configuration:**
   ```python
   import sys
   path = '/home/yourusername/your-app-folder'
   if path not in sys.path:
       sys.path.append(path)
   
   from app import app as application
   ```

6. **Reload your web app**

Your app is live at: `https://yourusername.pythonanywhere.com`

---

## Option 5: Self-Hosting on a VPS (Most Control)

**Best for:** If you have a VPS (DigitalOcean, Linode, Vultr, etc.)

### Quick Setup with Docker:

```bash
# 1. SSH into your server
ssh user@your-server-ip

# 2. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 3. Clone your repo
git clone YOUR_REPO_URL
cd snippets

# 4. Create .env file
cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32)
SNIPPET_USERNAME=admin
SNIPPET_PASSWORD=your-password
EOF

# 5. Run with Docker Compose
docker-compose up -d

# 6. Setup Nginx reverse proxy (optional but recommended)
# See full VPS guide in README.md
```

Your app runs on port 5000. Set up Nginx to serve it with HTTPS.

---

## Comparison Table

| Platform | Free Tier | Sleep/Wake | HTTPS | Ease | Credit Card |
|----------|-----------|------------|-------|------|-------------|
| **Render** | ✅ Yes | Sleeps after 15min | ✅ Auto | ⭐⭐⭐⭐⭐ Easy | ❌ No |
| **Railway** | ✅ $5/month | ❌ No sleep | ✅ Auto | ⭐⭐⭐⭐ Easy | ✅ Yes |
| **Fly.io** | ✅ Yes | ❌ No sleep | ✅ Auto | ⭐⭐⭐ Moderate | ✅ Yes |
| **PythonAnywhere** | ✅ Yes | ❌ No sleep | ✅ Auto | ⭐⭐⭐ Moderate | ❌ No |
| **VPS** | Varies | ❌ No sleep | ⚙️ Manual | ⭐⭐ Advanced | ✅ Yes |

---

## Recommendations

- **Complete Beginner:** PythonAnywhere or Render
- **Want it free forever:** Render or Railway
- **Need it to never sleep:** Railway or Fly.io  
- **Want full control:** VPS with Docker
- **Best overall:** Render (easiest) or Railway (most reliable)

---

## After Deployment

1. **Change your password immediately!** Default is "changeme"
2. **Bookmark your app URL**
3. **Set up a custom domain** (optional but recommended)
4. **Create your first snippet!**

## Troubleshooting Deployments

### App won't start:
- Check build logs for errors
- Verify all environment variables are set
- Ensure requirements.txt includes all dependencies

### Can't login:
- Verify PASSWORD is set correctly in environment variables
- Check username (default is "admin")
- Clear browser cookies and try again

### Database errors:
- Check file permissions
- Ensure writable storage (some platforms need configuration)

### "Application Error" page:
- Check application logs
- Verify all environment variables
- Ensure Flask app is running on correct port

Need help? Check the logs - they usually tell you exactly what's wrong!
