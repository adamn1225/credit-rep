# Credit Disputer - Development Roadmap

## ✅ Phase 1: Core Multi-User Features - COMPLETE!
- [x] Multi-user database schema (users, user_accounts, disputes, templates, history)
- [x] User authentication with password hashing
- [x] Flask web application with Bootstrap UI
- [x] Session-based user isolation
- [x] Dashboard with statistics
- [x] Manual dispute creation
- [x] Lob API integration for physical mail
- [x] PDF generation with ReportLab
- [x] Status tracking
- [x] **User Accounts Management UI**
  - View all derogatory accounts
  - Add accounts manually with full details
  - Update account status (pending → disputed → resolved)
  - Link accounts to disputes
  - Recent accounts widget on dashboard
  - Stats cards for account tracking
- [x] **Bulk CSV Upload** ✨ NEW!
  - Upload page with CSV parser
  - CSV template download
  - Validation and error handling
  - Batch import multiple accounts
- [x] **AI Letter Generation (OpenAI GPT-4)** ✨ NEW!
  - Integration with OpenAI API
  - `generate_dispute_letter_ai()` function
  - Personalized letters based on account details
  - Preview letters before sending
  - Fallback to template if AI fails
  - API endpoint for real-time generation
  
## 🔄 In Progress
- [ ] **Testing & Integration**
  - Test CSV upload with sample data
  - Test AI letter generation with OpenAI key
  - Integrate AI letters with dispute creation flow
  
## 📋 Backlog

### Phase 2: Automation & Workflows
- [ ] **Automated Follow-ups**
  - Cron job or n8n workflow to check `expected_response_date`
  - Query `get_pending_followups()` function
  - Auto-generate escalation letters (AI)
  - Auto-send via Lob API

- [ ] **n8n Integration** (Optional)
  - Self-host n8n for workflow automation
  - Create workflows: CSV upload → AI generation → Lob send
  - Schedule daily status checks
  - Trigger email notifications

- [ ] **Email Notifications**
  - SendGrid or Mailgun integration
  - Send emails on: dispute delivered, response needed, status change
  - Add user email preferences in settings

### Phase 3: Enhanced Dashboard & Reporting
- [ ] **Better Dashboard**
  - Timeline view of disputes over months/years
  - Success rate by bureau (Experian, TransUnion, Equifax)
  - Account-level tracking (show all disputes per account)
  - Filters: date range, bureau, status, account

- [ ] **Export Reports**
  - PDF reports with dispute summary
  - CSV export of all disputes
  - Per-account dispute history

### Phase 4: Deployment & Scaling
- [ ] **Railway Deployment**
  - Add `Procfile` for Railway
  - Add `railway.toml` config
  - Migrate from SQLite to PostgreSQL
  - Update `db.py` to use `DATABASE_URL` env var
  - Set up environment variables in Railway

- [ ] **Database Migration**
  - Create migration script: SQLite → PostgreSQL
  - Add connection pooling for PostgreSQL
  - Update all queries for PostgreSQL compatibility

### Phase 5: Future Enhancements
- [ ] **User Registration & Management**
  - Self-service user registration (family members)
  - Admin dashboard to manage users
  - Role-based permissions (admin vs user)

- [ ] **Payment/Subscription System** (If selling to agencies)
  - Stripe integration
  - Tiered pricing: disputes per month
  - Usage tracking and billing

- [ ] **Mobile App** (Optional)
  - React Native or Flutter
  - View disputes on mobile
  - Upload photos of credit reports

- [ ] **Credit Report Parsing** (OCR)
  - Upload PDF/image of credit report
  - Auto-extract derogatory accounts
  - Populate user_accounts table automatically

---

## Notes
- **Priority**: Multi-user isolation is complete in database. Next steps are CSV upload and AI integration.
- **Target Users**: Family initially, potential sale to credit repair agencies later.
- **Architecture**: Flask + PostgreSQL on Railway with AI and automation.
