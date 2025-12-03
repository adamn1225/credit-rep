import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor

# PostgreSQL database connection
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/nextcredit')

# Railway provides postgres:// but psycopg2 needs postgresql://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

def get_db_connection():
    """Get database connection (PostgreSQL)"""
    conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Users table (create first for foreign keys)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            first_name TEXT,
            last_name TEXT,
            full_name TEXT,
            phone TEXT,
            role TEXT DEFAULT 'user',
            
            -- Billing/Address fields
            address_line1 TEXT,
            address_line2 TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            country TEXT DEFAULT 'US',
            
            -- Profile fields
            occupation TEXT,
            annual_income DECIMAL(12,2),
            monthly_income DECIMAL(12,2),
            
            -- Marketing/Legal flags
            agree_tos BOOLEAN DEFAULT FALSE,
            agree_privacy BOOLEAN DEFAULT FALSE,
            marketing_emails BOOLEAN DEFAULT FALSE,
            
            -- Account status
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            email_verified BOOLEAN DEFAULT FALSE,
            phone_verified BOOLEAN DEFAULT FALSE
        )
    """)
    
    # User Accounts table (derogatory accounts to dispute)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_accounts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            bureau TEXT NOT NULL,
            creditor_name TEXT NOT NULL,
            account_number TEXT NOT NULL,
            account_type TEXT,
            balance REAL,
            status TEXT DEFAULT 'pending',
            reason TEXT,
            notes TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # Login Tokens table (for magic link authentication)
    c.execute("""
        CREATE TABLE IF NOT EXISTS login_tokens (
            id SERIAL PRIMARY KEY,
            email TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0
        )
    """)
    
    # User Sessions table (track login sessions for 30-day and device verification)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            device_fingerprint TEXT,
            ip_address TEXT,
            user_agent TEXT,
            verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # Disputes table (with user isolation)
    c.execute("""
        CREATE TABLE IF NOT EXISTS disputes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            account_id INTEGER,
            account_number TEXT,
            bureau TEXT,
            creditor_name TEXT,
            description TEXT,
            sent_date TIMESTAMP,
            tracking_id TEXT,
            status TEXT DEFAULT 'pending',
            expected_response_date TIMESTAMP,
            follow_up_sent INTEGER DEFAULT 0,
            escalation_level INTEGER DEFAULT 0,
            resolution TEXT,
            resolved_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (account_id) REFERENCES user_accounts(id) ON DELETE SET NULL
        )
    """)
    
    # Letter templates table
    c.execute("""
        CREATE TABLE IF NOT EXISTS letter_templates (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            template_type TEXT DEFAULT 'initial',
            content TEXT NOT NULL,
            is_ai_generated INTEGER DEFAULT 0,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)
    
    # Dispute history/audit log
    c.execute("""
        CREATE TABLE IF NOT EXISTS dispute_history (
            id SERIAL PRIMARY KEY,
            dispute_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_status TEXT,
            new_status TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dispute_id) REFERENCES disputes(id) ON DELETE CASCADE
        )
    """)
    
    # Documents table (credit reports, responses, evidence)
    c.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            account_id INTEGER,
            dispute_id INTEGER,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            mime_type TEXT,
            document_type TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ai_analysis TEXT,
            ai_analyzed_at TIMESTAMP,
            description TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (account_id) REFERENCES user_accounts(id) ON DELETE SET NULL,
            FOREIGN KEY (dispute_id) REFERENCES disputes(id) ON DELETE SET NULL
        )
    """)
    
    # Plaid Items table (stores Plaid access tokens)
    c.execute("""
        CREATE TABLE IF NOT EXISTS plaid_items (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            item_id TEXT UNIQUE NOT NULL,
            access_token TEXT NOT NULL,
            institution_id TEXT,
            institution_name TEXT,
            consent_expiration_time TIMESTAMP,
            cursor TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_sync TIMESTAMP,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # Plaid Accounts table (stores linked bank/credit accounts)
    c.execute("""
        CREATE TABLE IF NOT EXISTS plaid_accounts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            plaid_item_id INTEGER NOT NULL,
            plaid_account_id TEXT UNIQUE NOT NULL,
            name TEXT,
            official_name TEXT,
            type TEXT,
            subtype TEXT,
            mask TEXT,
            current_balance REAL,
            available_balance REAL,
            credit_limit REAL,
            currency TEXT DEFAULT 'USD',
            last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (plaid_item_id) REFERENCES plaid_items(id) ON DELETE CASCADE
        )
    """)
    
    # Plaid Transactions table (stores transaction history)
    c.execute("""
        CREATE TABLE IF NOT EXISTS plaid_transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            plaid_account_id INTEGER NOT NULL,
            plaid_transaction_id TEXT UNIQUE NOT NULL,
            amount REAL NOT NULL,
            date DATE NOT NULL,
            authorized_date DATE,
            name TEXT NOT NULL,
            merchant_name TEXT,
            category TEXT,
            payment_channel TEXT,
            pending INTEGER DEFAULT 0,
            transaction_type TEXT,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (plaid_account_id) REFERENCES plaid_accounts(id) ON DELETE CASCADE
        )
    """)
    
    # Create default admin user if not exists
    c.execute("SELECT COUNT(*) FROM users WHERE username = %s", ('admin',))
    count = c.fetchone()
    if count and (count[0] if isinstance(count, tuple) else count['count']) == 0:
        admin_hash = generate_password_hash('admin123')
        c.execute(
            "INSERT INTO users (username, password_hash, role, full_name, email) VALUES (%s, %s, %s, %s, %s)",
            ('admin', admin_hash, 'admin', 'System Administrator', 'admin@nextcredit.app')
        )
    
    conn.commit()
    conn.close()

def log_dispute(user_id, account_number, bureau, description, tracking_id=None, status="sent", creditor_name=None, account_id=None):
    """Log a dispute with user isolation"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Calculate expected response date (30 days from send)
    expected_date = (datetime.utcnow() + timedelta(days=30))
    
    c.execute("""
        INSERT INTO disputes 
        (user_id, account_id, account_number, bureau, creditor_name, description, sent_date, tracking_id, status, expected_response_date) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (user_id, account_id, account_number, bureau, creditor_name, description, 
          datetime.utcnow(), tracking_id, status, expected_date))
    
    result = c.fetchone()
    dispute_id = result['id'] if isinstance(result, dict) else result[0]
    
    # Log to history
    history_note = f'Letter sent via Lob (tracking: {tracking_id})' if tracking_id else 'Dispute created'
    c.execute("""
        INSERT INTO dispute_history (dispute_id, action, new_status, notes)
        VALUES (%s, %s, %s, %s)
    """, (dispute_id, 'created', status, history_note))
    
    conn.commit()
    conn.close()
    return dispute_id

# --- User Management Functions ---
def get_user(username):
    """Get user by username"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = c.fetchone()
    conn.close()
    return user

def verify_user(username, password):
    """Verify user credentials"""
    user = get_user(username)
    if user and check_password_hash(user['password_hash'], password):
        # Update last login
        update_last_login(username)
        return True, user['role']
    return False, None

def create_user(username, password, role='user'):
    """Create a new user"""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        password_hash = generate_password_hash(password)
        c.execute(
            "INSERT INTO users (username, password_hash, role, email) VALUES (%s, %s, %s, %s)",
            (username, password_hash, role, f"{username}@temp.local")
        )
        conn.commit()
        return True, "User created successfully"
    except psycopg2.IntegrityError:
        conn.rollback()
        return False, "Username already exists"
    finally:
        conn.close()

def update_password(username, new_password):
    """Update user password"""
    conn = get_db_connection()
    c = conn.cursor()
    password_hash = generate_password_hash(new_password)
    c.execute(
        "UPDATE users SET password_hash = %s WHERE username = %s",
        (password_hash, username)
    )
    conn.commit()
    conn.close()

def update_last_login(username):
    """Update user's last login timestamp"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE users SET last_login = %s WHERE username = %s",
        (datetime.utcnow(), username)
    )
    conn.commit()
    conn.close()

def update_last_login_by_email(email):
    """Update user's last login timestamp by email"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE users SET last_login = %s WHERE email = %s",
        (datetime.utcnow(), email)
    )
    conn.commit()
    conn.close()

def list_users():
    """List all users (without password hashes)"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, username, role, created_at, last_login FROM users")
    users = c.fetchall()
    conn.close()
    return users

# --- User Accounts Management ---
def add_user_account(user_id, bureau, creditor_name, account_number, reason, **kwargs):
    """Add a derogatory account for a user"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO user_accounts 
        (user_id, bureau, creditor_name, account_number, reason, account_type, balance, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (user_id, bureau, creditor_name, account_number, reason,
          kwargs.get('account_type'), kwargs.get('balance'), kwargs.get('notes')))
    result = c.fetchone()
    account_id = result['id'] if isinstance(result, dict) else result[0]
    conn.commit()
    conn.close()
    return account_id

def get_user_accounts(user_id, status=None):
    """Get all accounts for a user"""
    conn = get_db_connection()
    c = conn.cursor()
    
    if status:
        c.execute(
            "SELECT * FROM user_accounts WHERE user_id = %s AND status = %s ORDER BY uploaded_at DESC",
            (user_id, status)
        )
    else:
        c.execute(
            "SELECT * FROM user_accounts WHERE user_id = %s ORDER BY uploaded_at DESC",
            (user_id,)
        )
    
    accounts = c.fetchall()
    conn.close()
    return accounts

def update_account_status(account_id, status, notes=None):
    """Update account status"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE user_accounts SET status = %s, notes = %s WHERE id = %s",
        (status, notes, account_id)
    )
    conn.commit()
    conn.close()

# --- Disputes Management (with user isolation) ---
def get_user_disputes(user_id, status=None):
    """Get all disputes for a specific user"""
    conn = get_db_connection()
    c = conn.cursor()
    
    if status:
        c.execute(
            "SELECT * FROM disputes WHERE user_id = %s AND status = %s ORDER BY sent_date DESC",
            (user_id, status)
        )
    else:
        c.execute(
            "SELECT * FROM disputes WHERE user_id = %s ORDER BY sent_date DESC",
            (user_id,)
        )
    
    disputes = c.fetchall()
    conn.close()
    return disputes

def update_dispute_status(dispute_id, new_status, notes=None):
    """Update dispute status with history tracking"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get old status
    c.execute("SELECT status FROM disputes WHERE id = %s", (dispute_id,))
    result = c.fetchone()
    old_status = result['status'] if result else None
    
    # Update dispute
    c.execute(
        "UPDATE disputes SET status = %s WHERE id = %s",
        (new_status, dispute_id)
    )
    
    # Log to history
    c.execute("""
        INSERT INTO dispute_history (dispute_id, action, old_status, new_status, notes)
        VALUES (%s, %s, %s, %s, %s)
    """, (dispute_id, 'status_change', old_status, new_status, notes))
    
    conn.commit()
    conn.close()

def get_dispute_history(dispute_id):
    """Get history for a dispute"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM dispute_history WHERE dispute_id = %s ORDER BY created_at ASC",
        (dispute_id,)
    )
    history = c.fetchall()
    conn.close()
    return history

def get_pending_followups(days_threshold=30):
    """Get disputes that need follow-up (past expected response date)"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""
        SELECT * FROM disputes 
        WHERE status IN ('sent', 'delivered') 
        AND follow_up_sent = 0
        AND expected_response_date < NOW()
        ORDER BY expected_response_date ASC
    """)
    
    disputes = c.fetchall()
    conn.close()
    return disputes

def get_disputes_awaiting_response(user_id):
    """Get disputes sent >30 days ago without uploaded bureau response documents"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""
        SELECT d.* 
        FROM disputes d
        WHERE d.user_id = %s
        AND d.status IN ('sent', 'delivered')
        AND d.expected_response_date < NOW()
        AND NOT EXISTS (
            SELECT 1 FROM documents doc
            WHERE doc.dispute_id = d.id
            AND doc.document_type = 'bureau_response'
        )
        ORDER BY d.expected_response_date ASC
    """, (user_id,))
    
    disputes = c.fetchall()
    conn.close()
    return disputes

def mark_followup_sent(dispute_id):
    """Mark that a follow-up letter has been sent"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE disputes 
        SET follow_up_sent = 1, escalation_level = escalation_level + 1
        WHERE id = %s
    """, (dispute_id,))
    
    c.execute("""
        INSERT INTO dispute_history (dispute_id, action, notes)
        VALUES (%s, %s, %s)
    """, (dispute_id, 'follow_up_sent', 'Escalation follow-up letter sent'))
    
    conn.commit()
    conn.close()

# --- Document Management ---
def add_document(user_id, filename, original_filename, file_path, file_size, mime_type, 
                 document_type, description=None, account_id=None, dispute_id=None):
    """Add a document to the database"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO documents 
        (user_id, filename, original_filename, file_path, file_size, mime_type, 
         document_type, description, account_id, dispute_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (user_id, filename, original_filename, file_path, file_size, mime_type,
          document_type, description, account_id, dispute_id))
    result = c.fetchone()
    doc_id = result['id'] if isinstance(result, dict) else result[0]
    conn.commit()
    conn.close()
    return doc_id

def get_user_documents(user_id, document_type=None, account_id=None, dispute_id=None):
    """Get documents for a user with optional filters"""
    conn = get_db_connection()
    c = conn.cursor()
    
    query = "SELECT * FROM documents WHERE user_id = %s"
    params = [user_id]
    
    if document_type:
        query += " AND document_type = %s"
        params.append(document_type)
    if account_id:
        query += " AND account_id = %s"
        params.append(account_id)
    if dispute_id:
        query += " AND dispute_id = %s"
        params.append(dispute_id)
    
    query += " ORDER BY upload_date DESC"
    
    c.execute(query, params)
    documents = c.fetchall()
    conn.close()
    return [dict(doc) for doc in documents]

def update_document_analysis(doc_id, analysis_result):
    """Store AI analysis results for a document"""
    import json
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE documents 
        SET ai_analysis = %s, ai_analyzed_at = %s
        WHERE id = %s
    """, (json.dumps(analysis_result), datetime.utcnow(), doc_id))
    conn.commit()
    conn.close()

def get_document_by_id(doc_id, user_id):
    """Get a specific document (with user validation)"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM documents WHERE id = %s AND user_id = %s",
        (doc_id, user_id)
    )
    doc = c.fetchone()
    conn.close()
    return dict(doc) if doc else None

def delete_document(doc_id, user_id):
    """Delete a document (with user validation)"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM documents WHERE id = %s AND user_id = %s", (doc_id, user_id))
    conn.commit()
    conn.close()

# --- Statistics ---
def get_user_stats(user_id):
    """Get statistics for a user"""
    conn = get_db_connection()
    c = conn.cursor()
    
    stats = {}
    
    c.execute("SELECT COUNT(*) FROM user_accounts WHERE user_id = %s", (user_id,))
    stats['total_accounts'] = c.fetchone()['count']
    
    c.execute("SELECT COUNT(*) FROM user_accounts WHERE user_id = %s AND status = 'pending'", (user_id,))
    stats['pending_accounts'] = c.fetchone()['count']
    
    c.execute("SELECT COUNT(*) FROM disputes WHERE user_id = %s", (user_id,))
    stats['total_disputes'] = c.fetchone()['count']
    
    c.execute("SELECT COUNT(*) FROM disputes WHERE user_id = %s AND status = 'delivered'", (user_id,))
    stats['delivered'] = c.fetchone()['count']
    
    c.execute("SELECT COUNT(*) FROM disputes WHERE user_id = %s AND status IN ('sent', 'in_transit', 'queued')", (user_id,))
    stats['in_transit'] = c.fetchone()['count']
    
    c.execute("SELECT COUNT(*) FROM disputes WHERE user_id = %s AND status IN ('failed', 'invalid_tracking_id')", (user_id,))
    stats['failed'] = c.fetchone()['count']
    
    c.execute("SELECT COUNT(*) FROM disputes WHERE user_id = %s AND status = 'resolved'", (user_id,))
    stats['resolved'] = c.fetchone()['count']
    
    conn.close()
    return stats

# --- Plaid Integration Functions ---
def save_plaid_item(user_id, item_id, access_token, institution_id=None, institution_name=None):
    """Save Plaid item (bank connection)"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO plaid_items 
        (user_id, item_id, access_token, institution_id, institution_name)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (user_id, item_id, access_token, institution_id, institution_name))
    result = c.fetchone()
    plaid_item_id = result['id'] if isinstance(result, dict) else result[0]
    conn.commit()
    conn.close()
    return plaid_item_id

def get_plaid_items(user_id):
    """Get all Plaid items for a user"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM plaid_items WHERE user_id = %s AND status = 'active' ORDER BY created_at DESC",
        (user_id,)
    )
    items = c.fetchall()
    conn.close()
    return [dict(item) for item in items]

def get_plaid_item_by_id(plaid_item_id, user_id):
    """Get a specific Plaid item (with user validation)"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM plaid_items WHERE id = %s AND user_id = %s",
        (plaid_item_id, user_id)
    )
    item = c.fetchone()
    conn.close()
    return dict(item) if item else None

def update_plaid_item_cursor(plaid_item_id, cursor):
    """Update transaction sync cursor for Plaid item"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE plaid_items 
        SET cursor = %s, last_sync = %s
        WHERE id = %s
    """, (cursor, datetime.utcnow(), plaid_item_id))
    conn.commit()
    conn.close()

def save_plaid_account(user_id, plaid_item_id, account_data):
    """Save or update a Plaid account"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if account exists
    c.execute(
        "SELECT id FROM plaid_accounts WHERE plaid_account_id = %s",
        (account_data['plaid_account_id'],)
    )
    existing = c.fetchone()
    
    if existing:
        # Update existing account
        c.execute("""
            UPDATE plaid_accounts 
            SET name = %s, official_name = %s, type = %s, subtype = %s, mask = %s,
                current_balance = %s, available_balance = %s, credit_limit = %s,
                currency = %s, last_synced = %s
            WHERE plaid_account_id = %s
        """, (
            account_data['name'], account_data.get('official_name'), 
            account_data['type'], account_data['subtype'], account_data['mask'],
            account_data.get('current_balance'), account_data.get('available_balance'),
            account_data.get('limit'), account_data['currency'],
            datetime.utcnow(), account_data['plaid_account_id']
        ))
        account_id = existing['id']
    else:
        # Insert new account
        c.execute("""
            INSERT INTO plaid_accounts 
            (user_id, plaid_item_id, plaid_account_id, name, official_name, type, subtype, 
             mask, current_balance, available_balance, credit_limit, currency)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id, plaid_item_id, account_data['plaid_account_id'],
            account_data['name'], account_data.get('official_name'),
            account_data['type'], account_data['subtype'], account_data['mask'],
            account_data.get('current_balance'), account_data.get('available_balance'),
            account_data.get('limit'), account_data['currency']
        ))
        result = c.fetchone()
        account_id = result['id'] if isinstance(result, dict) else result[0]
    
    conn.commit()
    conn.close()
    return account_id

def get_plaid_accounts(user_id, plaid_item_id=None):
    """Get Plaid accounts for a user"""
    conn = get_db_connection()
    c = conn.cursor()
    
    if plaid_item_id:
        c.execute(
            "SELECT * FROM plaid_accounts WHERE user_id = %s AND plaid_item_id = %s ORDER BY name",
            (user_id, plaid_item_id)
        )
    else:
        c.execute(
            "SELECT * FROM plaid_accounts WHERE user_id = %s ORDER BY name",
            (user_id,)
        )
    
    accounts = c.fetchall()
    conn.close()
    return [dict(acc) for acc in accounts]

def save_plaid_transaction(user_id, plaid_account_id, transaction_data):
    """Save or update a Plaid transaction"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if transaction exists
    c.execute(
        "SELECT id FROM plaid_transactions WHERE plaid_transaction_id = %s",
        (transaction_data['plaid_transaction_id'],)
    )
    existing = c.fetchone()
    
    # Get internal plaid_account_id from plaid_account_id
    c.execute(
        "SELECT id FROM plaid_accounts WHERE plaid_account_id = %s",
        (transaction_data['plaid_account_id'],)
    )
    account = c.fetchone()
    
    if not account:
        conn.close()
        return None
    
    internal_account_id = account['id']
    
    if existing:
        # Update existing transaction
        c.execute("""
            UPDATE plaid_transactions 
            SET amount = %s, date = %s, authorized_date = %s, name = %s, 
                merchant_name = %s, category = %s, payment_channel = %s, 
                pending = %s, transaction_type = %s, synced_at = %s
            WHERE plaid_transaction_id = %s
        """, (
            transaction_data['amount'], transaction_data['date'],
            transaction_data.get('authorized_date'), transaction_data['name'],
            transaction_data.get('merchant_name'), str(transaction_data.get('category', [])),
            transaction_data['payment_channel'], transaction_data['pending'],
            transaction_data.get('transaction_type'), datetime.utcnow(),
            transaction_data['plaid_transaction_id']
        ))
        txn_id = existing['id']
    else:
        # Insert new transaction
        c.execute("""
            INSERT INTO plaid_transactions 
            (user_id, plaid_account_id, plaid_transaction_id, amount, date, 
             authorized_date, name, merchant_name, category, payment_channel, 
             pending, transaction_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id, internal_account_id, transaction_data['plaid_transaction_id'],
            transaction_data['amount'], transaction_data['date'],
            transaction_data.get('authorized_date'), transaction_data['name'],
            transaction_data.get('merchant_name'), str(transaction_data.get('category', [])),
            transaction_data['payment_channel'], transaction_data['pending'],
            transaction_data.get('transaction_type')
        ))
        result = c.fetchone()
        txn_id = result['id'] if isinstance(result, dict) else result[0]
    
    conn.commit()
    conn.close()
    return txn_id

def search_plaid_transactions(user_id, creditor_name=None, min_amount=None, max_amount=None, 
                              start_date=None, end_date=None, limit=100):
    """Search Plaid transactions with filters"""
    conn = get_db_connection()
    c = conn.cursor()
    
    query = "SELECT * FROM plaid_transactions WHERE user_id = %s"
    params = [user_id]
    
    if creditor_name:
        query += " AND (name ILIKE %s OR merchant_name ILIKE %s)"
        params.extend([f'%{creditor_name}%', f'%{creditor_name}%'])
    
    if min_amount:
        query += " AND amount >= %s"
        params.append(min_amount)
    
    if max_amount:
        query += " AND amount <= %s"
        params.append(max_amount)
    
    if start_date:
        query += " AND date >= %s"
        params.append(start_date)
    
    if end_date:
        query += " AND date <= %s"
        params.append(end_date)
    
    query += " ORDER BY date DESC LIMIT %s"
    params.append(limit)
    
    c.execute(query, params)
    transactions = c.fetchall()
    conn.close()
    return [dict(txn) for txn in transactions]

def delete_plaid_item(plaid_item_id, user_id):
    """Delete a Plaid item and all associated data"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get account IDs to delete transactions
    c.execute(
        "SELECT id FROM plaid_accounts WHERE plaid_item_id = %s AND user_id = %s",
        (plaid_item_id, user_id)
    )
    accounts = c.fetchall()
    
    account_ids = [acc['id'] for acc in accounts]
    
    # Delete transactions
    if account_ids:
        c.execute(
            f"DELETE FROM plaid_transactions WHERE plaid_account_id = ANY(%s)",
            (account_ids,)
        )
    
    # Delete accounts
    c.execute("DELETE FROM plaid_accounts WHERE plaid_item_id = %s AND user_id = %s", (plaid_item_id, user_id))
    
    # Delete item
    c.execute("DELETE FROM plaid_items WHERE id = %s AND user_id = %s", (plaid_item_id, user_id))
    
    conn.commit()
    conn.close()

# --- Magic Link Authentication Functions ---

def create_login_token(email, token, expires_at):
    """Create a login token for magic link authentication"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO login_tokens (email, token, expires_at)
        VALUES (%s, %s, %s)
        RETURNING id
    """, (email, token, expires_at))
    
    result = c.fetchone()
    token_id = result['id'] if isinstance(result, dict) else result[0]
    conn.commit()
    conn.close()
    return token_id

def verify_login_token(token):
    """Verify and consume a login token"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if token exists, is unused, and not expired
    c.execute("""
        SELECT email, expires_at 
        FROM login_tokens 
        WHERE token = %s AND used = 0 AND expires_at > NOW()
    """, (token,))
    token_data = c.fetchone()
    
    if not token_data:
        conn.close()
        return None
    
    email = token_data['email']
    
    # Mark token as used
    c.execute("UPDATE login_tokens SET used = 1 WHERE token = %s", (token,))
    
    conn.commit()
    conn.close()
    
    return email

def cleanup_expired_tokens():
    """Delete expired and used tokens (housekeeping)"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""
        DELETE FROM login_tokens 
        WHERE used = 1 OR expires_at < NOW() - INTERVAL '1 day'
    """)
    
    conn.commit()
    deleted_count = c.rowcount
    conn.close()
    return deleted_count

def get_user_by_email(email):
    """Get user by email address"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute(
        "SELECT * FROM users WHERE email = %s AND is_active = 1",
        (email,)
    )
    user = c.fetchone()
    
    conn.close()
    
    if user:
        return dict(user)
    return None

# --- Session Management Functions ---

def create_user_session(user_id, device_fingerprint=None, ip_address=None, user_agent=None):
    """Create a verified session for a user (30-day expiration)"""
    import secrets
    
    conn = get_db_connection()
    c = conn.cursor()
    
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=30)
    
    c.execute("""
        INSERT INTO user_sessions 
        (user_id, session_token, device_fingerprint, ip_address, user_agent, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING session_token
    """, (user_id, session_token, device_fingerprint, ip_address, user_agent, expires_at))
    
    result = c.fetchone()
    conn.commit()
    conn.close()
    return result['session_token']

def verify_user_session(user_id, device_fingerprint=None):
    """Check if user has a valid session for this device"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""
        SELECT * FROM user_sessions 
        WHERE user_id = %s AND device_fingerprint = %s 
        AND expires_at > NOW()
        ORDER BY last_activity DESC LIMIT 1
    """, (user_id, device_fingerprint))
    session = c.fetchone()
    
    conn.close()
    return dict(session) if session else None

def update_session_activity(session_token):
    """Update last activity timestamp for a session"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""
        UPDATE user_sessions 
        SET last_activity = NOW() 
        WHERE session_token = %s
    """, (session_token,))
    
    conn.commit()
    conn.close()

def cleanup_expired_sessions():
    """Delete expired sessions (housekeeping)"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("DELETE FROM user_sessions WHERE expires_at < NOW()")
    
    conn.commit()
    deleted_count = c.rowcount
    conn.close()
    return deleted_count

def create_user_with_email(email, password, first_name=None, last_name=None, phone=None, 
                          agree_tos=False, marketing_emails=False, role='user'):
    """Create a new user account with email (for signup)"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        print(f"[DB] Creating user with email: {email}")
        
        # Generate username from email if not provided
        username = email.split('@')[0].lower()
        
        # Make username unique if it already exists
        base_username = username
        counter = 1
        while True:
            c.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
            result = c.fetchone()
            count = result[0] if isinstance(result, tuple) else result['count']
            
            if count == 0:
                break
            username = f"{base_username}{counter}"
            counter += 1
        
        print(f"[DB] Username will be: {username}")
        
        # Check if email already exists
        c.execute("SELECT COUNT(*) FROM users WHERE email = %s", (email,))
        result = c.fetchone()
        count = result[0] if isinstance(result, tuple) else result['count']
        
        if count > 0:
            conn.close()
            print(f"[DB] Email already exists: {email}")
            return False, "Email already exists"
        
        # Create user
        password_hash = generate_password_hash(password)
        full_name = f"{first_name} {last_name}".strip() if first_name or last_name else None
        
        print(f"[DB] Inserting user into database...")
        c.execute("""
            INSERT INTO users (username, password_hash, email, first_name, last_name, full_name, 
                             phone, role, agree_tos, agree_privacy, marketing_emails, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
        """, (username, password_hash, email, first_name, last_name, full_name, 
               phone, role, agree_tos, agree_tos, marketing_emails))
        
        conn.commit()
        conn.close()
        print(f"[DB] ✅ User created successfully: {email}")
        return True, "User created successfully"
    
    except Exception as e:
        print(f"[DB] ❌ Error creating user: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False, f"Database error: {str(e)}"
