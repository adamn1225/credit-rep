# n8n Integration Setup Guide

This guide will help you set up automated email reminders for bureau responses using n8n.

---

## 📋 Overview

**What This Does:**
- ✅ **Manual Reminders**: Users can click "Send Reminder" button → triggers email
- ✅ **Automatic Daily Check**: n8n runs at 9AM daily → checks for overdue responses → sends emails automatically
- ✅ **Beautiful HTML Emails**: Professional templates with dispute details
- ✅ **Dashboard Links**: One-click access to upload responses

---

## 🚀 Setup Steps

### Step 1: Import Workflow to n8n

1. Login to `https://n8n.whichone.ai`
2. Click **"Workflows"** in sidebar
3. Click **"+ New"** → Import from File
4. Upload: `n8n-workflow-credit-reminders.json`
5. Workflow will open in editor

---

### Step 2: Configure SMTP Credentials

#### Option A: Gmail (Recommended)
1. In n8n, go to **Credentials** → **+ Add Credential**
2. Search for **"SMTP"**
3. Fill in:
   - **User**: your-email@gmail.com
   - **Password**: Use **App Password** (not regular password)
     - Go to: https://myaccount.google.com/apppasswords
     - Generate app password for "Mail"
   - **Host**: smtp.gmail.com
   - **Port**: 587
   - **SSL/TLS**: Enable
4. Click **Save**

#### Option B: Other Email Services
- **SendGrid**: smtp.sendgrid.net (Port 587)
- **Mailgun**: smtp.mailgun.org (Port 587)
- **AWS SES**: email-smtp.us-east-1.amazonaws.com (Port 587)

---

### Step 3: Configure API Key Credential

1. In n8n, go to **Credentials** → **+ Add Credential**
2. Search for **"Header Auth"**
3. Name it: `Flask API Key`
4. Fill in:
   - **Name**: `X-API-Key`
   - **Value**: Copy your `FLASK_SECRET_KEY` from `.env`
5. Click **Save**

---

### Step 4: Update Workflow Nodes

#### A. "Send Email Reminder" Node
1. Click the **"Send Email Reminder"** node
2. **Credentials**: Select your SMTP credential
3. **From Email**: Change `noreply@yoursite.com` to your email
4. Click **Save**

#### B. "Send Scheduled Reminder" Node
1. Click the **"Send Scheduled Reminder"** node
2. **Credentials**: Select your SMTP credential
3. **From Email**: Change `noreply@yoursite.com` to your email
4. In the email HTML, replace:
   ```
   https://your-railway-app.railway.app
   ```
   With your actual Railway URL (e.g., `https://credit-disputer.railway.app`)
5. Click **Save**

#### C. "Check Pending (Scheduled)" Node
1. Click this node
2. **URL**: Replace with your Railway app URL:
   ```
   https://your-app.railway.app/api/pending-responses
   ```
3. **Credentials**: Select "Flask API Key"
4. Click **Save**

#### D. "Daily 9AM Check" Node
1. Click this node
2. **Cron Expression**: `0 9 * * *` (9AM daily)
   - Change if you want different time (e.g., `0 18 * * *` for 6PM)
3. Click **Save**

---

### Step 5: Activate Webhook

1. Click **"Webhook Trigger"** node
2. Click **"Listen for Test Event"**
3. Copy the webhook URL (e.g., `https://n8n.whichone.ai/webhook/abc123`)
4. Click **"Stop Listening"**

---

### Step 6: Update Flask App

1. Open your `.env` file (local)
2. Update the webhook URL:
   ```bash
   N8N_WEBHOOK_URL=https://n8n.whichone.ai/webhook/abc123
   ```
   (Use the URL you copied in Step 5)

3. Add to Railway environment variables:
   - Go to Railway dashboard → Your project → Variables
   - Add: `N8N_WEBHOOK_URL` = `https://n8n.whichone.ai/webhook/abc123`

---

### Step 7: Activate Workflow

1. In n8n workflow editor, toggle **"Active"** switch (top right)
2. Status should show: ✅ **Active**
3. Both triggers (Webhook + Schedule) are now live!

---

## 🧪 Testing

### Test Manual Reminder (via Dashboard)

1. Login to your Credit Disputer app
2. Go to **Dashboard**
3. You should see overdue disputes with "Upload Response" button
4. Click button → should send email immediately
5. Check your email inbox

### Test Scheduled Check (via n8n)

1. In n8n workflow, click **"Daily 9AM Check"** node
2. Click **"Execute Node"** (play button)
3. Should see green checkmark
4. Click **"Loop Each User"** → **"Send Scheduled Reminder"**
5. Verify emails sent

### Test API Endpoint Directly

```bash
# Get pending responses
curl -H "X-API-Key: YOUR_FLASK_SECRET_KEY" \
  https://your-app.railway.app/api/pending-responses

# Should return JSON with overdue disputes
```

---

## 📧 Email Customization

### Change Email Design

Edit nodes in n8n:
- **"Send Email Reminder"** → Message field (HTML)
- **"Send Scheduled Reminder"** → Message field (HTML)

### Available Variables

```javascript
{{ $json.user_name }}        // User's full name
{{ $json.user_email }}       // Email address
{{ $json.bureau }}           // Experian/TransUnion/Equifax
{{ $json.creditor }}         // Creditor name
{{ $json.account_number }}   // Account number
{{ $json.sent_date }}        // When dispute was sent
{{ $json.days_waiting }}     // Days since sent
{{ $json.dashboard_url }}    // Link to dashboard
```

---

## ⏰ Schedule Customization

### Change Daily Check Time

Edit **"Daily 9AM Check"** node:
- `0 9 * * *` = 9:00 AM daily
- `0 18 * * *` = 6:00 PM daily
- `0 9 * * 1` = 9:00 AM Mondays only
- `0 9,18 * * *` = 9:00 AM and 6:00 PM daily

### Multiple Reminders Per Day

Duplicate the schedule trigger:
1. Right-click **"Daily 9AM Check"**
2. Click **Duplicate**
3. Rename to "Daily 6PM Check"
4. Change cron: `0 18 * * *`
5. Connect to **"Check Pending (Scheduled)"**

---

## 🔐 Security Notes

- ✅ API Key authentication prevents unauthorized access
- ✅ User email addresses never exposed
- ✅ HTTPS only (both Railway and n8n)
- ✅ Webhook URL is secret (don't commit to Git)

---

## 🐛 Troubleshooting

### Emails Not Sending

**Check:**
1. SMTP credentials correct?
2. Gmail: Using App Password, not regular password?
3. n8n workflow is **Active**?
4. Check n8n execution history for errors

### Webhook Not Triggering

**Check:**
1. `N8N_WEBHOOK_URL` set in Railway environment variables?
2. Webhook URL matches in n8n?
3. Check Railway logs: `heroku logs --tail` (or Railway dashboard)

### No Overdue Disputes Found

**Check:**
1. Disputes exist in database?
2. Sent date is >30 days ago?
3. No bureau response uploaded yet?
4. Test API: `curl -H "X-API-Key: ..." /api/pending-responses`

---

## 📊 Monitoring

### n8n Execution History

1. In n8n, click **"Executions"** in sidebar
2. See all workflow runs with success/failure
3. Click execution to see detailed logs
4. Filter by: Success, Error, Waiting

### Flask Logs (Railway)

```bash
# View live logs
railway logs --follow

# Search for reminder events
railway logs | grep "send-reminder"
```

---

## 🚀 Advanced Features

### Add SMS Notifications (Twilio)

1. In n8n workflow, add **Twilio** node after email
2. Credentials: Twilio Account SID + Auth Token
3. Send SMS to: `{{ $json.phone_number }}`
4. Message: "Bureau response expected. Upload now: {{ $json.dashboard_url }}"

### Add Slack Notifications

1. Add **Slack** node
2. Post to channel: `#credit-disputes`
3. Message: "{{ $json.user_name }} has {{ $json.days_waiting }} day overdue response"

### Track Reminder Sent

Add database update after sending:
1. Add **HTTP Request** node
2. URL: `https://your-app.railway.app/api/mark-reminder-sent`
3. Body: `{ "dispute_id": {{ $json.dispute_id }} }`

---

## 📝 Summary

✅ **Manual Reminders**: Click button → instant email
✅ **Daily Auto-Check**: 9AM check → emails sent automatically
✅ **Beautiful Emails**: HTML templates with dispute details
✅ **Easy Testing**: Execute nodes manually in n8n
✅ **Secure**: API key auth + HTTPS only

---

**Need Help?**
- n8n Docs: https://docs.n8n.io
- Community: https://community.n8n.io
- Check workflow execution history for errors

---

**Last Updated:** November 17, 2025  
**Author:** Next Noetics LLC
