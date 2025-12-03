# Plaid Integration Setup Guide

## 🎉 What's New?

We've integrated **Plaid** to unlock powerful banking features:

1. **🏦 Automatic Account Discovery** - Import bank accounts directly
2. **💳 Payment Proof Generator** - Find transactions proving you paid creditors
3. **✅ Account Verification** - Prove account ownership for disputes
4. **🔄 Transaction Sync** - Keep payment history up-to-date

---

## 📋 Setup Instructions

### 1. Get Your Plaid API Credentials

1. Go to [Plaid Dashboard](https://dashboard.plaid.com/signup)
2. Sign up for a **free** Plaid account
3. Create a new application
4. Navigate to **Team Settings → Keys**
5. Copy your:
   - `client_id`
   - `secret` (for sandbox environment)

### 2. Configure Environment Variables

Create a `.env` file (or update existing) with your Plaid credentials:

```bash
# Plaid API (Banking Integration)
PLAID_CLIENT_ID=your_client_id_here
PLAID_SECRET=your_secret_here
PLAID_ENV=sandbox  # Use 'sandbox' for testing, 'development' for real data (with limited banks), 'production' for live
```

**Environment Options:**
- `sandbox` - Test mode with fake banks (Chase Sandbox, Bank of America Sandbox, etc.)
- `development` - Real banks but limited to your test accounts
- `production` - Full access (requires Plaid approval)

### 3. Restart Your Flask App

```bash
# Stop the current server (Ctrl+C)
python app.py
```

### 4. Initialize Database Tables

The new Plaid tables will be created automatically on first run:
- `plaid_items` - Stores bank connections
- `plaid_accounts` - Stores linked accounts
- `plaid_transactions` - Stores transaction history

---

## 🚀 Using Plaid Features

### Connect a Bank Account

1. Navigate to **Connect Bank** in the main menu
2. Click **"Connect New Bank"**
3. Select your bank from the Plaid Link modal
4. Enter credentials (in sandbox, use test credentials from Plaid docs)
5. Select accounts to link
6. Done! Accounts will be imported automatically

### Find Payment Proof

1. Go to **My Accounts**
2. Find an account you want proof of payment for
3. Click the **bank icon** button (🏦 Find Payment Proof)
4. System will search all linked bank accounts for payments to that creditor
5. View transactions and generate PDF evidence

### Test Credentials (Sandbox Mode)

When in `sandbox` mode, use these test credentials:

**Username:** `user_good`  
**Password:** `pass_good`

This will simulate a successful bank connection with test transaction data.

---

## 🎯 Feature Roadmap

### ✅ Completed
- [x] Plaid Link integration
- [x] Account sync
- [x] Transaction search
- [x] Payment proof finder
- [x] Bank account management

### 🔜 Coming Soon
- [ ] PDF generation for payment proof
- [ ] Automatic dispute creation from Plaid data
- [ ] Collections account detection
- [ ] Debt-to-income calculator
- [ ] Budget analyzer for credit rebuilding

---

## 🔐 Security Notes

- Your bank credentials **never** touch our servers
- Plaid uses bank-level 256-bit encryption
- We only store read-only access tokens
- Users can disconnect banks anytime
- All data is isolated per user

---

## 🐛 Troubleshooting

### "Plaid credentials not configured" error

Make sure your `.env` file has valid `PLAID_CLIENT_ID` and `PLAID_SECRET`.

### Link modal doesn't open

Check browser console for errors. Ensure Plaid CDN script loads correctly.

### Transactions not showing

1. Make sure you've synced the account (click "Sync Now")
2. Transactions may take 1-2 days to appear in sandbox
3. Check that creditor name matches exactly

### Can't connect to production banks in sandbox

This is expected! Sandbox only works with test credentials. Upgrade to `development` mode to test with real banks.

---

## 📚 Resources

- [Plaid Quickstart Guide](https://plaid.com/docs/quickstart/)
- [Plaid Link Documentation](https://plaid.com/docs/link/)
- [Test Credentials](https://plaid.com/docs/sandbox/test-credentials/)
- [Plaid Dashboard](https://dashboard.plaid.com/)

---

## 💬 Support

If you encounter issues:
1. Check the console logs for errors
2. Verify your Plaid credentials
3. Ensure you're using the correct environment (sandbox/development/production)
4. Review Plaid's status page: https://status.plaid.com/

Enjoy your new banking superpowers! 🚀
