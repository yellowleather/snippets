# Snippets - Personal Work Diary

A simple, personal snippets tool for tracking your daily work via weekly diary entries. Inspired by Google's internal snippets tool.

## Features

- 📝 Weekly diary entries with markdown support
- 📅 Date navigation and filtering
- 🔒 Password-protected (single user)
- ✨ Clean, Google-inspired UI
- 💾 SQLite database (no setup required)
- 🌐 Easy to deploy anywhere

## Quick Start

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your password (optional, default is "changeme"):**
   ```bash
   export SNIPPET_PASSWORD="your-secure-password"
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open in browser:**
   ```
   http://localhost:5000
   ```

5. **Login with:**
   - Username: `admin`
   - Password: `changeme` (or your custom password)

## Deployment Options

### Option 1: Deploy to Render.com (Free & Easy)

1. **Create account at [render.com](https://render.com)**

2. **Create a new Web Service:**
   - Connect your GitHub repository (or upload files)
   - Select "Python" as the environment
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`

3. **Add environment variables:**
   - `SECRET_KEY`: A random secret key (generate one: `python -c "import os; print(os.urandom(24).hex())"`)
   - `SNIPPET_PASSWORD`: Your secure password
   - `SNIPPET_USERNAME`: Your username (optional, defaults to "admin")

4. **Deploy!** Your app will be live at `https://your-app-name.onrender.com`

### Option 2: Deploy to Heroku

1. **Install Heroku CLI and login**

2. **Create a Procfile:**
   ```
   web: gunicorn app:app
   ```

3. **Deploy:**
   ```bash
   heroku create your-snippets-app
   heroku config:set SECRET_KEY="your-random-secret-key"
   heroku config:set SNIPPET_PASSWORD="your-secure-password"
   git push heroku main
   ```

### Option 3: Deploy to a VPS (DigitalOcean, Linode, etc.)

1. **SSH into your server**

2. **Install dependencies:**
   ```bash
   sudo apt update
   sudo apt install python3-pip nginx
   ```

3. **Clone your code and install requirements:**
   ```bash
   cd /var/www
   git clone your-repo
   cd your-repo
   pip3 install -r requirements.txt
   pip3 install gunicorn
   ```

4. **Create systemd service** (`/etc/systemd/system/snippets.service`):
   ```ini
   [Unit]
   Description=Snippets Application
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/var/www/your-repo
   Environment="SECRET_KEY=your-secret-key"
   Environment="SNIPPET_PASSWORD=your-password"
   ExecStart=/usr/local/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app

   [Install]
   WantedBy=multi-user.target
   ```

5. **Configure Nginx** (`/etc/nginx/sites-available/snippets`):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

6. **Enable and start:**
   ```bash
   sudo systemctl enable snippets
   sudo systemctl start snippets
   sudo ln -s /etc/nginx/sites-available/snippets /etc/nginx/sites-enabled/
   sudo systemctl restart nginx
   ```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SNIPPET_USERNAME` | Login username | `admin` |
| `SNIPPET_PASSWORD` | Login password | `changeme` |
| `SECRET_KEY` | Flask secret key for sessions | (random) |

## Usage

### Creating a Snippet

1. Click "Add Snippet" button
2. Write your content using markdown
3. Click "Publish"

### Editing a Snippet

1. Click "Edit" on any snippet
2. Modify the content
3. Click "Publish"

### Navigation

- Use date pickers to filter by date range
- Use arrow buttons to navigate weeks
- Click "Go to current week" to jump to today

### Markdown Support

The editor supports standard markdown:
- **Bold**: `**text**`
- *Italic*: `*text*`
- ~~Strikethrough~~: `~~text~~`
- Lists: `- item` or `1. item`
- Links: `[text](url)`
- Headers: `# H1`, `## H2`, etc.

## Security Notes

⚠️ **Important Security Recommendations:**

1. **Always change the default password!**
2. Use a strong, unique password
3. Use HTTPS in production (Render/Heroku provide this automatically)
4. Keep your SECRET_KEY truly secret and random
5. Consider adding rate limiting for login attempts

## Database

The app uses SQLite with a single database file: `snippets.db`

To backup your data, simply copy this file. To restore, replace it.

## Customization

### Change the Theme

Edit `/static/css/style.css` to customize colors, fonts, and styling.

### Add More Features

The codebase is simple and well-commented. Some ideas:
- Add tags/categories
- Export to PDF or Markdown
- Search functionality
- Multiple users with separate notebooks
- Email reminders

## Troubleshooting

**Can't login:**
- Check your username and password
- Make sure environment variables are set correctly
- Check browser console for errors

**Snippets not saving:**
- Check file permissions on `snippets.db`
- Check server logs for errors

**App won't start:**
- Verify all dependencies are installed
- Check for port conflicts (default: 5000)
- Review error messages in console

## License

MIT License - feel free to modify and use as you wish!

## Support

For issues or questions, check the code comments or create an issue in your repository.
