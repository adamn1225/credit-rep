import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Use PostgreSQL in production (Railway), SQLite for local dev
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    # Railway provides postgres:// but psycopg2 needs postgresql://
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    USE_POSTGRES = True
    import psycopg2
    from psycopg2.extras import RealDictCursor
else:
    USE_POSTGRES = False
    DB_PATH = "disputes.db"

def get_db_connection():
    """Get database connection (PostgreSQL or SQLite)"""
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        conn.cursor_factory = RealDictCursor
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Users table (create first for foreign keys)
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                full_name TEXT,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                full_name TEXT,
                role TEXT DEFAULT 'user',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
    
    # User Accounts table (derogatory accounts to dispute)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bureau TEXT NOT NULL,
            creditor_name TEXT NOT NULL,
            account_number TEXT NOT NULL,
            account_type TEXT,
            balance REAL,
            status TEXT DEFAULT 'pending',
            reason TEXT,
            notes TEXT,
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # Disputes table (with user isolation)
    c.execute("""
        CREATE TABLE IF NOT EXISTS disputes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_id INTEGER,
            account_number TEXT,
            bureau TEXT,
            creditor_name TEXT,
            description TEXT,
            sent_date TEXT,
            tracking_id TEXT,
            status TEXT DEFAULT 'pending',
            expected_response_date TEXT,
            follow_up_sent INTEGER DEFAULT 0,
            escalation_level INTEGER DEFAULT 0,
            resolution TEXT,
            resolved_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (account_id) REFERENCES user_accounts(id) ON DELETE SET NULL
        )
    """)
    
    # Letter templates table
    c.execute("""
        CREATE TABLE IF NOT EXISTS letter_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            template_type TEXT DEFAULT 'initial',
            content TEXT NOT NULL,
            is_ai_generated INTEGER DEFAULT 0,
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)
    
    # Dispute history/audit log
    c.execute("""
        CREATE TABLE IF NOT EXISTS dispute_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dispute_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_status TEXT,
            new_status TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dispute_id) REFERENCES disputes(id) ON DELETE CASCADE
        )
    """)
    
    # Documents table (credit reports, responses, evidence)
    c.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_id INTEGER,
            dispute_id INTEGER,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            mime_type TEXT,
            document_type TEXT NOT NULL,
            upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
            ai_analysis TEXT,
            ai_analyzed_at TEXT,
            description TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (account_id) REFERENCES user_accounts(id) ON DELETE SET NULL,
            FOREIGN KEY (dispute_id) REFERENCES disputes(id) ON DELETE SET NULL
        )
    """)
    
    # Create default admin user if not exists
    c.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if c.fetchone()[0] == 0:
        admin_hash = generate_password_hash('admin123')
        c.execute(
            "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
            ('admin', admin_hash, 'admin', 'System Administrator')
        )
    
    conn.commit()
    conn.close()

def log_dispute(user_id, account_number, bureau, description, tracking_id=None, status="sent", creditor_name=None, account_id=None):
    """Log a dispute with user isolation"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Calculate expected response date (30 days from send)
    from datetime import timedelta
    expected_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
    
    c.execute("""
        INSERT INTO disputes 
        (user_id, account_id, account_number, bureau, creditor_name, description, sent_date, tracking_id, status, expected_response_date) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, account_id, account_number, bureau, creditor_name, description, 
          datetime.utcnow().isoformat(), tracking_id, status, expected_date))
    
    dispute_id = c.lastrowid
    
    # Log to history
    history_note = f'Letter sent via Lob (tracking: {tracking_id})' if tracking_id else 'Dispute created'
    c.execute("""
        INSERT INTO dispute_history (dispute_id, action, new_status, notes)
        VALUES (?, ?, ?, ?)
    """, (dispute_id, 'created', status, history_note))
    
    conn.commit()
    conn.close()
    return dispute_id

# --- User Management Functions ---
def get_user(username):
    """Get user by username"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    user = c.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        password_hash = generate_password_hash(password)
        c.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, password_hash, role)
        )
        conn.commit()
        return True, "User created successfully"
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    finally:
        conn.close()

def update_password(username, new_password):
    """Update user password"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    password_hash = generate_password_hash(new_password)
    c.execute(
        "UPDATE users SET password_hash = ? WHERE username = ?",
        (password_hash, username)
    )
    conn.commit()
    conn.close()

def update_last_login(username):
    """Update user's last login timestamp"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE users SET last_login = ? WHERE username = ?",
        (datetime.utcnow().isoformat(), username)
    )
    conn.commit()
    conn.close()

def list_users():
    """List all users (without password hashes)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    users = c.execute("SELECT id, username, role, created_at, last_login FROM users").fetchall()
    conn.close()
    return users

# --- User Accounts Management ---
def add_user_account(user_id, bureau, creditor_name, account_number, reason, **kwargs):
    """Add a derogatory account for a user"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO user_accounts 
        (user_id, bureau, creditor_name, account_number, reason, account_type, balance, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, bureau, creditor_name, account_number, reason,
          kwargs.get('account_type'), kwargs.get('balance'), kwargs.get('notes')))
    conn.commit()
    account_id = c.lastrowid
    conn.close()
    return account_id

def get_user_accounts(user_id, status=None):
    """Get all accounts for a user"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if status:
        accounts = c.execute(
            "SELECT * FROM user_accounts WHERE user_id = ? AND status = ? ORDER BY uploaded_at DESC",
            (user_id, status)
        ).fetchall()
    else:
        accounts = c.execute(
            "SELECT * FROM user_accounts WHERE user_id = ? ORDER BY uploaded_at DESC",
            (user_id,)
        ).fetchall()
    
    conn.close()
    return accounts

def update_account_status(account_id, status, notes=None):
    """Update account status"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE user_accounts SET status = ?, notes = ? WHERE id = ?",
        (status, notes, account_id)
    )
    conn.commit()
    conn.close()

# --- Disputes Management (with user isolation) ---
def get_user_disputes(user_id, status=None):
    """Get all disputes for a specific user"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if status:
        disputes = c.execute(
            "SELECT * FROM disputes WHERE user_id = ? AND status = ? ORDER BY sent_date DESC",
            (user_id, status)
        ).fetchall()
    else:
        disputes = c.execute(
            "SELECT * FROM disputes WHERE user_id = ? ORDER BY sent_date DESC",
            (user_id,)
        ).fetchall()
    
    conn.close()
    return disputes

def update_dispute_status(dispute_id, new_status, notes=None):
    """Update dispute status with history tracking"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get old status
    old_status = c.execute("SELECT status FROM disputes WHERE id = ?", (dispute_id,)).fetchone()[0]
    
    # Update dispute
    c.execute(
        "UPDATE disputes SET status = ? WHERE id = ?",
        (new_status, dispute_id)
    )
    
    # Log to history
    c.execute("""
        INSERT INTO dispute_history (dispute_id, action, old_status, new_status, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (dispute_id, 'status_change', old_status, new_status, notes))
    
    conn.commit()
    conn.close()

def get_dispute_history(dispute_id):
    """Get history for a dispute"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    history = c.execute(
        "SELECT * FROM dispute_history WHERE dispute_id = ? ORDER BY created_at ASC",
        (dispute_id,)
    ).fetchall()
    conn.close()
    return history

def get_pending_followups(days_threshold=30):
    """Get disputes that need follow-up (past expected response date)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    disputes = c.execute("""
        SELECT * FROM disputes 
        WHERE status IN ('sent', 'delivered') 
        AND follow_up_sent = 0
        AND expected_response_date < datetime('now')
        ORDER BY expected_response_date ASC
    """).fetchall()
    
    conn.close()
    return disputes

def get_disputes_awaiting_response(user_id):
    """Get disputes sent >30 days ago without uploaded bureau response documents"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    disputes = c.execute("""
        SELECT d.* 
        FROM disputes d
        WHERE d.user_id = ?
        AND d.status IN ('sent', 'delivered')
        AND d.expected_response_date < datetime('now')
        AND NOT EXISTS (
            SELECT 1 FROM documents doc
            WHERE doc.dispute_id = d.id
            AND doc.document_type = 'bureau_response'
        )
        ORDER BY d.expected_response_date ASC
    """, (user_id,)).fetchall()
    
    conn.close()
    return disputes

def mark_followup_sent(dispute_id):
    """Mark that a follow-up letter has been sent"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE disputes 
        SET follow_up_sent = 1, escalation_level = escalation_level + 1
        WHERE id = ?
    """, (dispute_id,))
    
    c.execute("""
        INSERT INTO dispute_history (dispute_id, action, notes)
        VALUES (?, ?, ?)
    """, (dispute_id, 'follow_up_sent', 'Escalation follow-up letter sent'))
    
    conn.commit()
    conn.close()

# --- Document Management ---
def add_document(user_id, filename, original_filename, file_path, file_size, mime_type, 
                 document_type, description=None, account_id=None, dispute_id=None):
    """Add a document to the database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO documents 
        (user_id, filename, original_filename, file_path, file_size, mime_type, 
         document_type, description, account_id, dispute_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, filename, original_filename, file_path, file_size, mime_type,
          document_type, description, account_id, dispute_id))
    conn.commit()
    doc_id = c.lastrowid
    conn.close()
    return doc_id

def get_user_documents(user_id, document_type=None, account_id=None, dispute_id=None):
    """Get documents for a user with optional filters"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = "SELECT * FROM documents WHERE user_id = ?"
    params = [user_id]
    
    if document_type:
        query += " AND document_type = ?"
        params.append(document_type)
    if account_id:
        query += " AND account_id = ?"
        params.append(account_id)
    if dispute_id:
        query += " AND dispute_id = ?"
        params.append(dispute_id)
    
    query += " ORDER BY upload_date DESC"
    
    documents = c.execute(query, params).fetchall()
    conn.close()
    return [dict(doc) for doc in documents]

def update_document_analysis(doc_id, analysis_result):
    """Store AI analysis results for a document"""
    import json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE documents 
        SET ai_analysis = ?, ai_analyzed_at = ?
        WHERE id = ?
    """, (json.dumps(analysis_result), datetime.utcnow().isoformat(), doc_id))
    conn.commit()
    conn.close()

def get_document_by_id(doc_id, user_id):
    """Get a specific document (with user validation)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    doc = c.execute(
        "SELECT * FROM documents WHERE id = ? AND user_id = ?",
        (doc_id, user_id)
    ).fetchone()
    conn.close()
    return dict(doc) if doc else None

def delete_document(doc_id, user_id):
    """Delete a document (with user validation)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM documents WHERE id = ? AND user_id = ?", (doc_id, user_id))
    conn.commit()
    conn.close()
    
    conn.commit()
    conn.close()

# --- Statistics ---
def get_user_stats(user_id):
    """Get statistics for a user"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    stats = {
        'total_accounts': c.execute("SELECT COUNT(*) FROM user_accounts WHERE user_id = ?", (user_id,)).fetchone()[0],
        'pending_accounts': c.execute("SELECT COUNT(*) FROM user_accounts WHERE user_id = ? AND status = 'pending'", (user_id,)).fetchone()[0],
        'total_disputes': c.execute("SELECT COUNT(*) FROM disputes WHERE user_id = ?", (user_id,)).fetchone()[0],
        'delivered': c.execute("SELECT COUNT(*) FROM disputes WHERE user_id = ? AND status = 'delivered'", (user_id,)).fetchone()[0],
        'in_transit': c.execute("SELECT COUNT(*) FROM disputes WHERE user_id = ? AND status IN ('sent', 'in_transit', 'queued')", (user_id,)).fetchone()[0],
        'failed': c.execute("SELECT COUNT(*) FROM disputes WHERE user_id = ? AND status IN ('failed', 'invalid_tracking_id')", (user_id,)).fetchone()[0],
        'resolved': c.execute("SELECT COUNT(*) FROM disputes WHERE user_id = ? AND status = 'resolved'", (user_id,)).fetchone()[0],
    }
    
    conn.close()
    return stats
