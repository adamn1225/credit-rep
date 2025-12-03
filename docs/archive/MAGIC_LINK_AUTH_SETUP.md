# Magic Link Authentication Setup Guide

## Overview

Next Credit now uses **passwordless authentication** via magic links sent to user email addresses. This is more secure and user-friendly than traditional password-based authentication.

## How It Works

1. User enters their email address on the login page
2. System generates a secure, one-time-use token (valid for 15 minutes)
3. SendGrid sends an email with a magic link
4. User clicks the link to log in automatically
5. Token is marked as "used" and cannot be reused

## Setup Instructions

### 1. Get SendGrid API Key

1. Go to [SendGrid](https://sendgrid.com/) and create an account (free tier works)
2. Navigate to **Settings → API Keys**
3. Click **Create API Key**
4. Give it a name (e.g., "Next Credit Auth")
5. Select **Full Access** or at least **Mail Send** permissions
6. Copy the API key (you'll only see it once!)

### 2. Configure Environment Variables

Add these to your `.env` file:

```bash
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FROM_EMAIL=noreply@yourdomain.com  # Or use a SendGrid verified email
```

**Important:** If you don't have a verified domain, you can use a SendGrid email like:
- `noreply@sendgrid.net` (requires verification)
- Or verify a single sender email in SendGrid settings

### 3. Update Existing Users with Email Addresses

Run the migration script to add email addresses to existing users:

```bash
python migrate_add_emails.py
```

This will prompt you to enter email addresses for any users that don't have one.

### 4. Test the Magic Link Flow

1. Start the Flask app:
   ```bash
   python app.py
   ```

2. Go to http://localhost:5000/login

3. Enter a user's email address

4. Check the email inbox for the magic link

5. Click the link to log in automatically

## Creating New Users

When creating new users via the admin panel (`/admin/users`), **email is now required**. Users cannot log in without an email address.

## Development Mode

If SendGrid is not configured, the app will:
- Show a warning message
- In development mode (`FLASK_ENV=development`), display the magic link in a flash message for testing

## Security Features

- ✅ Tokens expire after 15 minutes
- ✅ Tokens are one-time-use (marked as "used" after login)
- ✅ Tokens are cryptographically secure (32-byte URL-safe)
- ✅ Old tokens are automatically cleaned up
- ✅ Email addresses are case-insensitive and trimmed

## Database Changes

New table: `login_tokens`

```sql
CREATE TABLE login_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL,
    used INTEGER DEFAULT 0
);
```

## Troubleshooting

### "SendGrid API key not configured"
- Make sure `SENDGRID_API_KEY` is in your `.env` file
- Restart the Flask app after adding the key

### "No account found with that email address"
- User doesn't exist or email is incorrect
- Run `migrate_add_emails.py` to add emails to existing users
- Create new users with email addresses via admin panel

### Email not received
- Check spam/junk folder
- Verify sender email in SendGrid settings
- Check SendGrid activity logs for delivery status
- Ensure `FROM_EMAIL` is a verified sender

### "This login link is invalid or has expired"
- Link expired (>15 minutes old)
- Link already used
- Request a new magic link

## Benefits Over Password Auth

1. **More Secure** - No passwords to steal, crack, or forget
2. **Better UX** - No password reset flows needed
3. **Email Verification** - Proves user has access to their email
4. **Simpler** - Users don't need to remember passwords
5. **Modern** - Used by Slack, Notion, Medium, etc.

## Production Deployment

For Railway/production deployment:

1. Add environment variables in Railway dashboard:
   - `SENDGRID_API_KEY`
   - `FROM_EMAIL`

2. Ensure PostgreSQL is configured (DATABASE_URL)

3. Database migration will run automatically on startup

4. All existing routes work the same way

## API Endpoints

### POST /login
- Accepts: `email` (form data)
- Sends magic link email
- Returns login page with success message

### GET /verify-email/<token>
- Validates token
- Logs user in if valid
- Redirects to dashboard or login page

## Email Template

The magic link email includes:
- Professional HTML template with gradient header
- Clear call-to-action button
- Plain text fallback
- Security notice about 15-minute expiration
- Next Credit branding

## Future Enhancements

Possible additions:
- [ ] 2FA with TOTP codes
- [ ] SMS magic links via Twilio
- [ ] Backup codes for emergency access
- [ ] Device/browser fingerprinting
- [ ] Login history and notifications

---

**Questions?** Check the SendGrid dashboard for email delivery logs and debugging info.
