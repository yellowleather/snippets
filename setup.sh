#!/bin/bash

echo "🚀 Snippets App Setup"
echo "====================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Generate secret key
SECRET_KEY=$(python3 -c "import os; print(os.urandom(24).hex())")

# Prompt for password
echo "🔒 Setup Authentication"
echo "-----------------------"
read -p "Enter username (default: admin): " USERNAME
USERNAME=${USERNAME:-admin}

read -sp "Enter password (default: changeme): " PASSWORD
echo ""
PASSWORD=${PASSWORD:-changeme}

# Create .env file
echo "📝 Creating .env file..."
cat > .env << EOF
SECRET_KEY=$SECRET_KEY
SNIPPET_USERNAME=$USERNAME
SNIPPET_PASSWORD=$PASSWORD
EOF
echo "✓ .env file created"
echo ""

# Initialize database
echo "🗄️  Initializing database..."
python3 -c "from app import init_db; init_db()"
echo "✓ Database initialized"
echo ""

echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "  1. source venv/bin/activate"
echo "  2. export \$(cat .env | xargs)"
echo "  3. python app.py"
echo ""
echo "Or simply run: ./run.sh"
echo ""
echo "Your app will be available at: http://localhost:5001"
echo "Login with username: $USERNAME"
