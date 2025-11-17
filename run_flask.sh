#!/bin/bash

# Next Credit Flask Runner
# This script starts the Flask web application

echo "🚀 Starting Next Credit (Flask)..."
echo ""

# Check if virtual environment exists
if [ -d ".venv" ]; then
    echo "✓ Virtual environment found"
    source .venv/bin/activate
else
    echo "⚠️  No virtual environment found. Creating one..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "✓ Virtual environment created"
fi

# Check if Flask dependencies are installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements-flask.txt
    echo "✓ Dependencies installed"
fi

# Initialize database if needed
echo "🗄️  Initializing database..."
python3 -c "from db import init_db; init_db(); print('✓ Database ready')"

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "   Create a .env file with your LOB_API_KEY and FLASK_SECRET_KEY"
fi

echo ""
echo "═══════════════════════════════════════════"
echo "  Next Credit Dashboard"
echo "═══════════════════════════════════════════"
echo ""
echo "  🌐 Local:    http://localhost:5000"
echo "  📱 Network:  http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "  Login with: admin / admin123"
echo ""
echo "  Press Ctrl+C to stop"
echo "═══════════════════════════════════════════"
echo ""

# Start Flask app
python3 app.py
