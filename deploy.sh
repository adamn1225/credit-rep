#!/bin/bash
# Quick deployment script for Railway

echo "🚀 Railway Deployment Script"
echo "=============================="
echo ""

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: app.py not found. Run this from the credit-rep directory."
    exit 1
fi

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Install it first:"
    echo "   npm i -g @railway/cli"
    exit 1
fi

echo "✅ Pre-deployment checks:"
echo ""

# Check critical files exist
echo "📄 Checking required files..."
for file in "Procfile" "requirements.txt" "railway.json" "app.py" "db.py"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file missing!"
        exit 1
    fi
done
echo ""

# Check if .env is in .gitignore
if grep -q "^\.env$" .gitignore; then
    echo "✅ .env is in .gitignore (secrets protected)"
else
    echo "⚠️  Warning: .env not in .gitignore!"
fi
echo ""

# Check git status
echo "📊 Git status:"
git status --short
echo ""

# Confirm deployment
read -p "🤔 Ready to deploy to Railway? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled."
    exit 0
fi

# Commit changes
echo ""
echo "📝 Committing changes..."
git add .
git commit -m "Deploy: Simplified auth + production config" || echo "Nothing to commit"

# Push to GitHub (triggers Railway deployment)
echo ""
echo "🚢 Pushing to GitHub..."
git push origin main

echo ""
echo "✅ Pushed to GitHub!"
echo ""
echo "📺 Monitor deployment:"
echo "   railway logs -f"
echo ""
echo "🌐 Open deployed app:"
echo "   railway open"
echo ""
echo "🔍 Check service status:"
echo "   railway status"
echo ""
echo "⚡ Initialize database (after first deploy):"
echo "   railway run python3 -c 'from db import init_db; init_db()'"
echo ""
