🚀 READY TO DEPLOY - Quick Start Guide
=====================================

## ✅ Pre-Deployment Complete

- [x] SQLite files removed (PostgreSQL-only)
- [x] Magic link/MFA simplified to email+password only
- [x] Production security settings added
- [x] Railway configuration files created
- [x] All changes committed to git
- [x] Railway CLI linked to project: zucchini-reverence
- [x] PostgreSQL database created on Railway

## 📋 Deployment Steps

### 1️⃣ Set Environment Variables (One-time setup)

Run this script to add all environment variables to Railway:

```bash
./set_railway_vars.sh
```

Or manually set them in Railway Dashboard → Settings → Variables:
- Copy all values from `.env.railway` file

### 2️⃣ Push to GitHub (Triggers Auto-Deploy)

```bash
git push origin main
```

Railway will automatically detect the push and deploy your app!

### 3️⃣ Initialize Database (After first deploy)

```bash
railway run python3 -c "from db import init_db; init_db()"
```

### 4️⃣ Create Admin User

```bash
railway run python3 -c "
from db import create_user_with_email
success, msg = create_user_with_email(
    email='noah@nationwidetransportservices.com',
    password='YOUR_SECURE_PASSWORD_HERE',
    first_name='Noah',
    last_name='Admin',
    phone='',
    agree_tos=True,
    marketing_emails=False
)
print(f'Result: {success} - {msg}')
"
```

**⚠️ IMPORTANT: Change the password before running!**

### 5️⃣ Monitor Deployment

```bash
# Watch deployment logs
railway logs -f

# Check service status
railway status

# Open deployed app
railway open
```

## 🌐 Your App URLs

- **Production URL**: https://nextcredit.up.railway.app
- **Railway Dashboard**: https://railway.app/project/zucchini-reverence

## 🧪 Post-Deployment Testing

1. Visit https://nextcredit.up.railway.app
2. Test signup flow
3. Test login flow
4. Verify dashboard access
5. Test dispute creation
6. Check document upload

## 🔧 Troubleshooting

**Database not initialized?**
```bash
railway run python3 -c "from db import init_db; init_db()"
```

**Check environment variables:**
```bash
railway variables
```

**View logs:**
```bash
railway logs --tail 100
```

**Connect to production database:**
```bash
railway connect Postgres
```

## 📝 Next Steps After Successful Deploy

1. Test all features in production
2. Set up custom domain (optional)
3. Enable monitoring/alerts in Railway
4. Configure automatic backups
5. Consider re-enabling email features (SendGrid)

## 🆘 Emergency Rollback

If something goes wrong:
1. Go to Railway Dashboard
2. Settings → Deployments
3. Select previous working deployment
4. Click "Redeploy"

---

**Ready to deploy?** Run: `git push origin main`
