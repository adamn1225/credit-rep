#!/bin/bash
# Set Railway environment variables for Flask app
# Run this after creating your web service in Railway

echo "🔧 Setting Railway environment variables..."
echo ""

# Check if railway CLI is available
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found"
    exit 1
fi

# Set environment variables
echo "📝 Adding environment variables..."

# Note: Replace these placeholder values with your actual keys before running
railway variables set FLASK_ENV=production
railway variables set FLASK_SECRET_KEY="<your-secret-key>"
railway variables set LOB_API_KEY="<your-lob-api-key>"
railway variables set OPENAI_API_KEY="<your-openai-api-key>"
railway variables set ANTHROPIC_API_KEY="<your-anthropic-api-key>"
railway variables set PLAID_CLIENT_ID="<your-plaid-client-id>"
railway variables set PLAID_SECRET="<your-plaid-secret>"
railway variables set PLAID_ENV="development"
railway variables set N8N_WEBHOOK_URL="https://n8n.whichone.ai/webhook/credit-reminders"
# Note: Set SENDGRID_API_KEY manually in Railway dashboard for security
# railway variables set SENDGRID_API_KEY="<your-key>"
railway variables set FROM_EMAIL="noah@nationwidetransportservices.com"

echo ""
echo "✅ Environment variables set!"
echo ""
echo "📋 Next steps:"
echo "   1. Verify variables: railway variables"
echo "   2. Deploy: git push origin main"
echo "   3. Monitor: railway logs -f"
echo ""
