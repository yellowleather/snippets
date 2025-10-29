#!/bin/bash

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the app
echo "🚀 Starting Snippets app..."
echo "📍 http://localhost:5001"
echo ""
./venv/bin/python app.py
