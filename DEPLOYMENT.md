# Railway Deployment Guide

## Pre-Deployment Checklist

### ✅ Completed
- [x] PostgreSQL-only database (no SQLite)
- [x] Simplified email+password authentication
- [x] gunicorn configured in requirements.txt
- [x] Procfile created
- [x] railway.json configured
- [x] .gitignore includes .env
- [x] Railway project linked: `zucchini-reverence`
- [x] PostgreSQL database created on Railway

### 📋 Deployment Steps

#### 1. Set Environment Variables in Railway Dashboard

Go to Railway project → Settings → Variables and add:

```bash
FLASK_ENV=production
FLASK_SECRET_KEY=<generate-your-secret-key>
LOB_API_KEY=<your-lob-api-key>
OPENAI_API_KEY=<your-openai-api-key>
ANTHROPIC_API_KEY=<your-anthropic-api-key>
PLAID_CLIENT_ID=<your-plaid-client-id>
PLAID_SECRET=<your-plaid-secret>
PLAID_ENV=development
N8N_WEBHOOK_URL=https://n8n.whichone.ai/webhook/credit-reminders
SENDGRID_API_KEY=<your-sendgrid-api-key>
FROM_EMAIL=noah@nationwidetransportservices.com
```

**Note:** `DATABASE_URL` is automatically injected by Railway Postgres - do NOT set it manually.

#### 2. Initialize Database on Railway

After first deployment, run this command locally to initialize tables:

```bash
railway run python3 -c "from db import init_db; init_db(); print('Database initialized!')"
```

Or connect via Railway CLI and run:

```bash
railway connect Postgres
# Then in psql:
\dt  # Check if tables exist
```

#### 3. Create Admin User

After database is initialized:

```bash
railway run python3 -c "
from db import create_user_with_email
success, msg = create_user_with_email(
    email='admin@nextcredit.app',
    password='CHANGE_THIS_PASSWORD',
    first_name='Admin',
    last_name='User',
    phone='',
    agree_tos=True,
    marketing_emails=False
)
print(f'Admin created: {success} - {msg}')
"
```

**Important:** Change the password above before running!

#### 4. Deploy to Railway

```bash
# Commit all changes
git add .
git commit -m "Configure for Railway deployment"

# Push to GitHub (Railway auto-deploys from main branch)
git push origin main
```

Railway will automatically:
1. Detect Python project
2. Install dependencies from requirements.txt
3. Run the start command from Procfile/railway.json
4. Inject DATABASE_URL from Postgres service
5. Expose the app on a public URL

#### 5. Monitor Deployment

```bash
# View deployment logs
railway logs

# Check service status
railway status

# Open deployed app
railway open
```

#### 6. Post-Deployment Testing

- [ ] Visit Railway URL and verify homepage loads
- [ ] Test signup flow with a new email
- [ ] Test login with created account
- [ ] Verify dashboard loads
- [ ] Test creating a dispute
- [ ] Check document upload
- [ ] Verify database persistence (logout/login)

## Database Connection Info

**Production (Railway):**
```
postgresql://postgres:fnJqTSwcMseGRyZFsPcXtBHVPgXjNoxs@postgres.railway.internal:5432/railway
```

**Local Development:**
```
postgresql://postgres:postgres@localhost:5432/nextcredit
```

## Troubleshooting

### Database Tables Not Created
```bash
railway run python3 -c "from db import init_db; init_db()"
```

### Environment Variables Not Loading
Check Railway dashboard → Settings → Variables
Verify DATABASE_URL is present (injected automatically)

### App Won't Start
Check logs: `railway logs`
Common issues:
- Missing dependencies in requirements.txt
- DATABASE_URL not accessible
- Port binding (Railway sets $PORT automatically)

### Database Connection Failed
Verify Postgres service is running in Railway
Check DATABASE_URL format matches PostgreSQL connection string

## Rollback

If deployment fails, rollback in Railway dashboard:
Settings → Deployments → [Select previous deployment] → Redeploy

## Local Testing with Production Database

```bash
# Connect to Railway Postgres from local
railway run python3 app.py

# Or set DATABASE_URL temporarily
export DATABASE_URL="postgresql://postgres:fnJqTSwcMseGRyZFsPcXtBHVPgXjNoxs@postgres.railway.internal:5432/railway"
python3 app.py
```

## Security Notes

- ✅ .env is in .gitignore (not committed to git)
- ✅ Secrets stored in Railway environment variables
- ✅ FLASK_ENV=production (disables debug mode)
- ✅ SESSION_COOKIE_SECURE should be True in production (add to app.py)
- ⚠️  Change default admin password after creation
- ⚠️  Consider enabling HTTPS-only cookies
- ⚠️  Add rate limiting for login attempts (future enhancement)

## Next Steps After Deployment

1. **Custom Domain**: Add custom domain in Railway settings
2. **Email Service**: Re-enable SendGrid or switch to alternative
3. **Monitoring**: Set up Railway metrics/alerts
4. **Backups**: Configure Postgres automated backups
5. **CDN**: Consider Cloudflare for static assets
6. **Rate Limiting**: Add Flask-Limiter for API protection
