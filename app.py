from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import csv
import subprocess
import json
from functools import wraps
import pandas as pd
import os
import requests
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from db import (
    init_db, verify_user, update_password, get_user, create_user,
    get_user_disputes, get_user_stats, log_dispute,
    get_user_accounts, add_user_account, update_account_status, list_users,
    add_document, get_user_documents, get_document_by_id, delete_document,
    update_document_analysis, get_disputes_awaiting_response,
    save_plaid_item, get_plaid_items, get_plaid_item_by_id, update_plaid_item_cursor,
    save_plaid_account, get_plaid_accounts, save_plaid_transaction,
    search_plaid_transactions, delete_plaid_item,
    get_user_by_email, create_user_with_email, update_last_login_by_email
)
from document_analyzer import analyze_document
import plaid_integration
import hashlib

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'documents'

# Production security settings
if os.getenv('FLASK_ENV') == 'production':
    app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JavaScript access
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

DB_PATH = "disputes.db"
CSV_PATH = "data/accounts.csv"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Helper Functions ---
def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('❌ Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_user():
    """Inject username and role into all templates"""
    return {
        'username': session.get('username'),
        'role': session.get('role')
    }

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_disputes():
    """Load disputes for current user"""
    user_id = session.get('user_id')
    if not user_id:
        return []
    return get_user_disputes(user_id)

def load_csv_queue():
    """Load pending disputes from database for current user"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return pd.DataFrame()
        
        conn = get_db_connection()
        # Get pending disputes from database
        query = """
            SELECT d.id, d.account_number, d.bureau, d.creditor_name, 
                   d.description as reason, d.status, d.sent_date
            FROM disputes d
            WHERE d.user_id = ? AND d.status = 'pending'
            ORDER BY d.sent_date DESC
        """
        df = pd.read_sql_query(query, conn, params=(user_id,))
        conn.close()
        return df
    except Exception as e:
        print(f"Error loading queue: {e}")
        return pd.DataFrame()

def get_status_color(status):
    """Return color for status badge"""
    colors = {
        "delivered": "success",
        "in_transit": "warning",
        "queued": "info",
        "sent": "info",
        "failed": "danger",
        "invalid_tracking_id": "danger",
        "pending": "secondary"
    }
    return colors.get(status, "secondary")

def get_pdf_path(account_number, bureau):
    """Get path to PDF file"""
    base_dir = Path("disputes/generated")
    bureau_dir = bureau.lower()
    pdf_path = base_dir / bureau_dir / f"{account_number}.pdf"
    return pdf_path if pdf_path.exists() else None

def append_to_csv(data):
    """Append dispute to CSV queue"""
    file_exists = Path(CSV_PATH).exists()
    with open(CSV_PATH, "a", newline="") as csvfile:
        fieldnames = ["bureau", "creditor_name", "account_number", "reason", "status", "date_added"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

# --- Routes ---
@app.route('/')
def landing():
    """Public landing page"""
    # If user is already logged in, redirect to dashboard
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')


@app.route('/dashboard')
@login_required
def dashboard():
    """Redirect old index route to dashboard"""
    return index()


@app.route('/app')
@login_required
def index():
    """Dashboard home page"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Session expired. Please log in again.', 'warning')
        return redirect(url_for('login'))
    
    # Get user-specific stats
    stats = get_user_stats(user_id)
    disputes = get_user_disputes(user_id)
    accounts = get_user_accounts(user_id)
    queue = load_csv_queue()
    
    # Get disputes awaiting bureau responses (sent >30 days ago without uploaded response)
    awaiting_response = get_disputes_awaiting_response(user_id)
    
    # Add delivery rate
    total = stats['total_disputes']
    delivered = stats['delivered']
    stats['delivery_rate'] = round((delivered / total * 100) if total > 0 else 0, 1)
    stats['queue_count'] = len(queue)
    stats['awaiting_response'] = len(awaiting_response)
    
    # Get recent accounts (last 5)
    recent_accounts = accounts[:5] if len(accounts) > 5 else accounts
    
    return render_template('dashboard.html', 
                         disputes=disputes, 
                         stats=stats,
                         recent_accounts=recent_accounts,
                         awaiting_response=awaiting_response,
                         get_status_color=get_status_color,
                         username=session.get('username'))

def get_device_fingerprint():
    """Generate a device fingerprint from user agent and IP"""
    user_agent = request.headers.get('User-Agent', '')
    ip_address = request.remote_addr or ''
    fingerprint_str = f"{user_agent}:{ip_address}"
    return hashlib.sha256(fingerprint_str.encode()).hexdigest()


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User signup page"""
    if request.method == 'POST':
        try:
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            email = request.form.get('email', '').strip().lower()
            phone = request.form.get('phone', '').strip()
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            agree_tos = request.form.get('agree_tos')
            
            print(f"\n=== SIGNUP ATTEMPT ===")
            print(f"Email: {email}")
            print(f"Name: {first_name} {last_name}")
            print(f"Phone: {phone}")
            print(f"Agree TOS: {agree_tos}")
            
            # Use email as username (before @ symbol)
            username = email.split('@')[0].lower()
            full_name = f"{first_name} {last_name}".strip()
            
            # Validation
            if not all([first_name, last_name, email, phone, password]):
                print(f"Validation failed: Missing fields")
                flash('❌ All fields are required.', 'danger')
                return render_template('signup.html')
            
            if not agree_tos:
                print(f"Validation failed: TOS not accepted")
                flash('❌ You must accept the Terms of Service and Privacy Policy.', 'danger')
                return render_template('signup.html')
            
            if password != confirm_password:
                print(f"Validation failed: Passwords don't match")
                flash('❌ Passwords do not match.', 'danger')
                return render_template('signup.html')
            
            if len(password) < 6:
                print(f"Validation failed: Password too short")
                flash('❌ Password must be at least 6 characters.', 'danger')
                return render_template('signup.html')
            
            # Create user
            print(f"Creating user with email: {email}")
            success, message = create_user_with_email(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                agree_tos=bool(agree_tos),
                marketing_emails=bool(request.form.get('marketing_emails'))
            )
            
            print(f"User creation result: success={success}, message={message}")
            
            if not success:
                print(f"ERROR: User creation failed - {message}")
                flash(f'❌ {message}', 'danger')
                return render_template('signup.html')
            
            print(f"✅ User created successfully: {email}")
            
            flash(f'✅ Account created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"❌ SIGNUP ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'❌ An error occurred: {str(e)}', 'danger')
            return render_template('signup.html')
    
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page - email + password only"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            flash('❌ Please enter your email and password.', 'danger')
            return render_template('login.html')
        
        # Get user by email
        user = get_user_by_email(email)
        if user and check_password_hash(user['password_hash'], password):
            # Update last login
            update_last_login_by_email(email)
            
            # Log user in
            session.permanent = True
            session['email'] = email
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['username'] = user['username']
            
            name = user.get('first_name') or email.split('@')[0]
            flash(f'✅ Welcome back, {name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('❌ Invalid email or password.', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/add-dispute', methods=['GET', 'POST'])
@login_required
def add_dispute():
    """Add new dispute page"""
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        bureau = request.form.get('bureau')
        creditor = request.form.get('creditor')
        account = request.form.get('account')
        reason = request.form.get('reason')
        immediate_send = request.form.get('immediate_send') == 'on'
        
        if all([bureau, creditor, account, reason]):
            # Log dispute with user_id (tracking_id will be added when actually sent)
            dispute_id = log_dispute(
                user_id=user_id,
                account_number=account,
                bureau=bureau,
                description=reason,  # Fixed: use 'description' parameter
                tracking_id=None,     # Will be updated when sent via Lob
                status='pending',
                creditor_name=creditor
            )
            
            flash(f'✅ Added {bureau} dispute for {creditor}!', 'success')
            
            if immediate_send:
                # Run batch immediately
                result = subprocess.run(['python3', 'batch_processor.py'], 
                    capture_output=True, text=True, cwd=os.getcwd())
                if result.returncode == 0:
                    flash('✅ Dispute sent immediately!', 'success')
                else:
                    flash('⚠️ Added to queue, but send failed. Check logs.', 'warning')
            
            return redirect(url_for('dashboard'))
        else:
            flash('All fields are required.', 'warning')
    
    return render_template('add_dispute.html', username=session.get('username'))

@app.route('/accounts', methods=['GET', 'POST'])
@login_required
def accounts():
    """User accounts management page"""
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_account':
            # Add new account
            bureau = request.form.get('bureau')
            creditor = request.form.get('creditor_name')
            account_number = request.form.get('account_number')
            account_type = request.form.get('account_type')
            balance = request.form.get('balance')
            reason = request.form.get('reason')
            notes = request.form.get('notes')
            
            if all([bureau, creditor, account_number, reason]):
                add_user_account(
                    user_id=user_id,
                    bureau=bureau,
                    creditor_name=creditor,
                    account_number=account_number,
                    reason=reason,
                    account_type=account_type,
                    balance=float(balance) if balance else None,
                    notes=notes
                )
                flash(f'✅ Added account: {creditor} - {account_number}', 'success')
                return redirect(url_for('accounts'))
            else:
                flash('❌ Bureau, creditor, account number, and reason are required.', 'danger')
        
        elif action == 'update_status':
            # Update account status
            account_id = request.form.get('account_id')
            new_status = request.form.get('status')
            notes = request.form.get('notes')
            
            if account_id and new_status:
                update_account_status(account_id, new_status, notes)
                flash(f'✅ Account status updated to: {new_status}', 'success')
                return redirect(url_for('accounts'))
    
    # Load user accounts
    accounts_list = get_user_accounts(user_id)
    
    # Get counts by status
    stats = {
        'total': len(accounts_list),
        'pending': len([a for a in accounts_list if a['status'] == 'pending']),
        'disputed': len([a for a in accounts_list if a['status'] == 'disputed']),
        'resolved': len([a for a in accounts_list if a['status'] == 'resolved']),
        'verified': len([a for a in accounts_list if a['status'] == 'verified'])
    }
    
    return render_template('accounts.html',
                         accounts=accounts_list,
                         stats=stats,
                         username=session.get('username'))

@app.route('/upload-accounts', methods=['GET', 'POST'])
@login_required
def upload_accounts():
    """Bulk CSV upload for accounts"""
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('❌ No file selected', 'danger')
            return redirect(url_for('upload_accounts'))
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('❌ No file selected', 'danger')
            return redirect(url_for('upload_accounts'))
        
        if not file.filename.endswith('.csv'):
            flash('❌ File must be a CSV', 'danger')
            return redirect(url_for('upload_accounts'))
        
        try:
            # Read CSV
            df = pd.read_csv(file)
            
            # Validate required columns
            required_columns = ['bureau', 'creditor_name', 'account_number', 'reason']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                flash(f'❌ Missing required columns: {", ".join(missing_columns)}', 'danger')
                return redirect(url_for('upload_accounts'))
            
            # Import accounts
            success_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Skip rows with missing required fields
                    if pd.isna(row['bureau']) or pd.isna(row['creditor_name']) or \
                       pd.isna(row['account_number']) or pd.isna(row['reason']):
                        error_count += 1
                        errors.append(f"Row {index + 2}: Missing required field")
                        continue
                    
                    add_user_account(
                        user_id=user_id,
                        bureau=str(row['bureau']).strip(),
                        creditor_name=str(row['creditor_name']).strip(),
                        account_number=str(row['account_number']).strip(),
                        reason=str(row['reason']).strip(),
                        account_type=str(row.get('account_type', '')).strip() if pd.notna(row.get('account_type')) else None,
                        balance=float(row['balance']) if pd.notna(row.get('balance')) else None,
                        notes=str(row.get('notes', '')).strip() if pd.notna(row.get('notes')) else None
                    )
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            # Show results
            if success_count > 0:
                flash(f'✅ Successfully imported {success_count} account(s)!', 'success')
            
            if error_count > 0:
                flash(f'⚠️ {error_count} row(s) failed to import. Check errors below.', 'warning')
                for error in errors[:5]:  # Show first 5 errors
                    flash(f'  • {error}', 'warning')
                if len(errors) > 5:
                    flash(f'  • ... and {len(errors) - 5} more errors', 'warning')
            
            if success_count > 0:
                return redirect(url_for('accounts'))
                
        except Exception as e:
            flash(f'❌ Error processing file: {str(e)}', 'danger')
            return redirect(url_for('upload_accounts'))
    
    return render_template('upload_accounts.html', username=session.get('username'))

@app.route('/download-template')
@login_required
def download_template():
    """Download CSV template for bulk upload"""
    # Create template CSV
    template_data = {
        'bureau': ['Experian', 'TransUnion', 'Equifax'],
        'creditor_name': ['Capital One', 'Chase Bank', 'Discover'],
        'account_number': ['1234', '5678', '9012'],
        'account_type': ['Credit Card', 'Auto Loan', 'Credit Card'],
        'balance': [1500.00, 8500.50, 2300.00],
        'reason': ['Not my account', 'Already paid', 'Incorrect balance'],
        'notes': ['Never opened this account', 'Paid in full 2023', 'Balance should be $1000']
    }
    
    df = pd.DataFrame(template_data)
    
    # Save to temporary file
    temp_file = Path('/tmp/accounts_template.csv')
    df.to_csv(temp_file, index=False)
    
    return send_file(temp_file, 
                     as_attachment=True,
                     download_name='accounts_template.csv',
                     mimetype='text/csv')

@app.route('/api/generate-letter', methods=['POST'])
@login_required
def api_generate_letter():
    """API endpoint to generate AI letter preview"""
    try:
        from ai_generator import generate_dispute_letter_ai
        
        data = request.get_json()
        account_info = {
            'bureau': data.get('bureau'),
            'creditor_name': data.get('creditor_name'),
            'account_number': data.get('account_number'),
            'reason': data.get('reason'),
            'account_type': data.get('account_type', ''),
            'balance': data.get('balance', ''),
            'notes': data.get('notes', '')
        }
        
        # Check if OpenAI API key is configured
        if not os.getenv('OPENAI_API_KEY'):
            return jsonify({
                'success': False,
                'error': 'OpenAI API key not configured. Please add OPENAI_API_KEY to your .env file.'
            }), 400
        
        letter_content = generate_dispute_letter_ai(account_info)
        
        return jsonify({
            'success': True,
            'letter': letter_content
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/preview-letter/<int:account_id>')
@login_required
def preview_letter(account_id):
    """Preview AI-generated letter for an account"""
    user_id = session.get('user_id')
    
    # Get account details
    conn = get_db_connection()
    account = conn.execute(
        'SELECT * FROM user_accounts WHERE id = ? AND user_id = ?',
        (account_id, user_id)
    ).fetchone()
    conn.close()
    
    if not account:
        flash('❌ Account not found', 'danger')
        return redirect(url_for('accounts'))
    
    return render_template('preview_letter.html',
                         account=account,
                         username=session.get('username'))

@app.route('/send-batch', methods=['GET'])
@login_required
def send_batch():
    """Send batch page - review pending disputes"""
    queue = load_csv_queue()
    
    return render_template('send_batch.html', 
                         queue=queue.to_dict('records') if not queue.empty else [],
                         username=session.get('username'))

@app.route('/generate-batch', methods=['POST'])
@login_required
def generate_batch():
    """Generate PDFs for pending disputes (no sending yet)"""
    from generator import render_letter, generate_pdf
    
    user_id = session.get('user_id')
    conn = get_db_connection()
    
    # Get pending disputes
    disputes = conn.execute("""
        SELECT d.*, ua.creditor_name, ua.account_type, ua.balance, ua.notes
        FROM disputes d
        LEFT JOIN user_accounts ua ON d.account_id = ua.id
        WHERE d.user_id = ? AND d.status = 'pending'
    """, (user_id,)).fetchall()
    
    conn.close()
    
    if not disputes:
        flash('⚠️ No pending disputes to generate.', 'warning')
        return redirect(url_for('send_batch'))
    
    generated_count = 0
    for dispute in disputes:
        try:
            # Prepare account info - handle None values from LEFT JOIN
            account_info = {
                'bureau': dispute['bureau'],
                'creditor_name': dispute['creditor_name'] or 'Unknown',
                'account_number': dispute['account_number'],
                'reason': dispute['description'],
                'account_type': dispute['account_type'] if dispute['account_type'] else '',
                'balance': dispute['balance'] if dispute['balance'] else '',
                'notes': dispute['notes'] if dispute['notes'] else ''
            }
            
            # Generate letter with AI
            letter_text = render_letter(account_info, use_ai=True)
            
            # Generate PDF
            bureau_dir = Path(f"disputes/generated/{dispute['bureau'].lower()}")
            bureau_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = bureau_dir / f"{dispute['account_number']}.pdf"
            generate_pdf(letter_text, pdf_path)
            
            generated_count += 1
            
        except Exception as e:
            flash(f'❌ Error generating PDF for {dispute["account_number"]}: {str(e)}', 'danger')
    
    flash(f'✅ Generated {generated_count} PDF letter(s)! Review them before sending.', 'success')
    return redirect(url_for('review_batch'))

@app.route('/review-batch', methods=['GET'])
@login_required
def review_batch():
    """Review generated PDFs before sending to Lob"""
    user_id = session.get('user_id')
    conn = get_db_connection()
    
    # Get pending disputes with PDF paths
    disputes = conn.execute("""
        SELECT d.*, ua.creditor_name
        FROM disputes d
        LEFT JOIN user_accounts ua ON d.account_id = ua.id
        WHERE d.user_id = ? AND d.status = 'pending'
    """, (user_id,)).fetchall()
    
    conn.close()
    
    # Check which PDFs exist
    disputes_with_pdfs = []
    for dispute in disputes:
        pdf_path = Path(f"disputes/generated/{dispute['bureau'].lower()}/{dispute['account_number']}.pdf")
        if pdf_path.exists():
            disputes_with_pdfs.append({
                'id': dispute['id'],
                'bureau': dispute['bureau'],
                'creditor_name': dispute['creditor_name'],
                'account_number': dispute['account_number'],
                'description': dispute['description'],
                'pdf_exists': True
            })
    
    return render_template('review_batch.html',
                         disputes=disputes_with_pdfs,
                         username=session.get('username'))

@app.route('/send-to-lob', methods=['POST'])
@login_required
def send_to_lob():
    """Actually send generated PDFs via Lob API (costs money!)"""
    # Run the batch script which sends to Lob
    result = subprocess.run(['python3', 'batch_processor.py'], 
                          capture_output=True, 
                          text=True,
                          cwd=Path.cwd())
    
    if result.returncode == 0:
        flash('✅ Letters sent via Lob! Check dashboard for tracking.', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash(f'❌ Send failed: {result.stderr}', 'danger')
        return redirect(url_for('review_batch'))

@app.route('/check-status', methods=['POST'])
@login_required
def check_status():
    """Check delivery status"""
    result = subprocess.run(['python3', 'batch_processor.py', '--check-status'], 
                          capture_output=True, 
                          text=True,
                          cwd=Path.cwd())
    
    if result.returncode == 0:
        flash('✅ Status check complete!', 'success')
    else:
        flash(f'❌ Status check failed: {result.stderr}', 'warning')
    
    return redirect(url_for('dashboard'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Settings page"""
    if request.method == 'POST':
        # Handle settings updates
        action = request.form.get('action')
        
        if action == 'personal_info':
            # Update personal info in .env or config
            flash('✅ Personal information updated!', 'success')
        elif action == 'change_password':
            # Change password logic
            current_pw = request.form.get('current_password')
            new_pw = request.form.get('new_password')
            confirm_pw = request.form.get('confirm_password')
            
            # Verify current password
            username = session.get('username')
            valid, _ = verify_user(username, current_pw)
            
            if not valid:
                flash('❌ Current password is incorrect.', 'danger')
            elif new_pw != confirm_pw:
                flash('❌ New passwords do not match.', 'danger')
            elif len(new_pw) < 6:
                flash('❌ Password must be at least 6 characters.', 'danger')
            else:
                update_password(username, new_pw)
                flash('✅ Password updated successfully!', 'success')
        elif action == 'save_template':
            # Save template
            template_content = request.form.get('template_content')
            template_path = Path("disputes/templates/dispute_letter.j2")
            template_path.write_text(template_content)
            flash('✅ Template saved!', 'success')
    
    # Load current template
    template_path = Path("disputes/templates/dispute_letter.j2")
    template_content = template_path.read_text() if template_path.exists() else ""
    
    return render_template('settings.html', 
                         template_content=template_content,
                         username=session.get('username'))

@app.route('/download/<int:dispute_id>')
@login_required
def download_pdf(dispute_id):
    """Download PDF for a dispute"""
    conn = get_db_connection()
    dispute = conn.execute('SELECT * FROM disputes WHERE id = ?', (dispute_id,)).fetchone()
    conn.close()
    
    if dispute:
        pdf_path = get_pdf_path(dispute['account_number'], dispute['bureau'])
        if pdf_path:
            return send_file(pdf_path, 
                           as_attachment=True,
                           download_name=f"{dispute['bureau']}_{dispute['account_number']}.pdf",
                           mimetype='application/pdf')
    
    flash('PDF not found.', 'warning')
    return redirect(url_for('dashboard'))

@app.route('/admin/users', methods=['GET', 'POST'])
@admin_required
def admin_users():
    """Admin page to manage users"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create_user':
            username = request.form.get('username')
            password = request.form.get('password')
            role = request.form.get('role', 'user')
            email = request.form.get('email')
            full_name = request.form.get('full_name')
            
            if not email:
                flash('❌ Email address is required for magic link authentication.', 'danger')
                return redirect(url_for('admin_users'))
            
            if username and password and email:
                success, message = create_user(username, password, role)
                if success:
                    # Update additional fields
                    conn = get_db_connection()
                    conn.execute(
                        "UPDATE users SET email = ?, full_name = ? WHERE username = ?",
                        (email, full_name, username)
                    )
                    conn.commit()
                    conn.close()
                    flash(f'✅ User "{username}" created successfully!', 'success')
                else:
                    flash(f'❌ {message}', 'danger')
            else:
                flash('❌ Username, password, and email are required.', 'danger')
            
            return redirect(url_for('admin_users'))
        
        elif action == 'toggle_status':
            user_id = request.form.get('user_id')
            is_active = request.form.get('is_active') == '1'
            
            # Prevent toggling yourself
            if int(user_id) == session.get('user_id'):
                flash('❌ You cannot deactivate your own account!', 'danger')
                return redirect(url_for('admin_users'))
            
            conn = get_db_connection()
            conn.execute(
                "UPDATE users SET is_active = ? WHERE id = ?",
                (1 if is_active else 0, user_id)
            )
            conn.commit()
            conn.close()
            
            status = 'activated' if is_active else 'deactivated'
            flash(f'✅ User {status} successfully!', 'success')
            return redirect(url_for('admin_users'))
        
        elif action == 'delete_user':
            user_id = request.form.get('user_id')
            
            # Prevent deleting yourself
            if int(user_id) == session.get('user_id'):
                flash('❌ You cannot delete your own account!', 'danger')
                return redirect(url_for('admin_users'))
            
            conn = get_db_connection()
            # Get username before deleting
            user = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
            if user:
                conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()
                flash(f'✅ User "{user["username"]}" deleted successfully!', 'success')
            conn.close()
            
            return redirect(url_for('admin_users'))
    
    # Load all users
    users = list_users()
    
    return render_template('admin_users.html',
                         users=users,
                         username=session.get('username'))

@app.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for dashboard stats (for charts)"""
    disputes = load_disputes()
    
    # Status distribution
    status_counts = {}
    bureau_counts = {}
    
    for d in disputes:
        status = d['status']
        bureau = d['bureau']
        status_counts[status] = status_counts.get(status, 0) + 1
        bureau_counts[bureau] = bureau_counts.get(bureau, 0) + 1
    
    # Timeline data
    timeline = {}
    for d in disputes:
        date = d['sent_date'][:10] if d['sent_date'] else 'Unknown'
        timeline[date] = timeline.get(date, 0) + 1
    
    return jsonify({
        'status_distribution': status_counts,
        'bureau_distribution': bureau_counts,
        'timeline': timeline
    })

@app.route('/documents', methods=['GET', 'POST'])
@login_required
def documents():
    """Document management page"""
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        # Handle file upload
        if 'document' not in request.files:
            flash('❌ No file selected', 'danger')
            return redirect(url_for('documents'))
        
        file = request.files['document']
        if file.filename == '':
            flash('❌ No file selected', 'danger')
            return redirect(url_for('documents'))
        
        if not allowed_file(file.filename):
            flash('❌ Only PDF, PNG, JPG files are allowed', 'danger')
            return redirect(url_for('documents'))
        
        document_type = request.form.get('document_type')
        description = request.form.get('description')
        account_id = request.form.get('account_id') or None
        dispute_id = request.form.get('dispute_id') or None
        
        # Save file
        original_filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{original_filename}"
        
        # Create user folder
        user_folder = Path(app.config['UPLOAD_FOLDER']) / f"user_{user_id}" / document_type
        user_folder.mkdir(parents=True, exist_ok=True)
        
        file_path = user_folder / filename
        file.save(str(file_path))
        
        file_size = file_path.stat().st_size
        mime_type = file.content_type
        
        # Add to database
        doc_id = add_document(
            user_id=user_id,
            filename=filename,
            original_filename=original_filename,
            file_path=str(file_path),
            file_size=file_size,
            mime_type=mime_type,
            document_type=document_type,
            description=description,
            account_id=account_id,
            dispute_id=dispute_id
        )
        
        flash(f'✅ Document uploaded successfully!', 'success')
        
        # Trigger AI analysis in background (for now, do it synchronously)
        if file_path.suffix.lower() == '.pdf':
            flash('🤖 AI analysis started...', 'info')
            return redirect(url_for('analyze_document_view', doc_id=doc_id))
        
        return redirect(url_for('documents'))
    
    # GET request - show documents
    doc_type_filter = request.args.get('type')
    documents_list = get_user_documents(user_id, document_type=doc_type_filter)
    
    # Get counts by type
    all_docs = get_user_documents(user_id)
    doc_stats = {
        'total': len(all_docs),
        'credit_reports': len([d for d in all_docs if d['document_type'] == 'credit_report']),
        'bureau_responses': len([d for d in all_docs if d['document_type'] == 'bureau_response']),
        'evidence': len([d for d in all_docs if d['document_type'] in ['evidence', 'bank_statement', 'receipt', 'other']]),
        'analyzed': len([d for d in all_docs if d['ai_analysis']])
    }
    
    # Get accounts and disputes for linking
    accounts = get_user_accounts(user_id)
    disputes = get_user_disputes(user_id)
    
    return render_template('documents.html',
                         documents=documents_list,
                         doc_stats=doc_stats,
                         accounts=accounts,
                         disputes=disputes,
                         username=session.get('username'))

@app.route('/analyze-document/<int:doc_id>')
@login_required
def analyze_document_view(doc_id):
    """Analyze a document with AI"""
    user_id = session.get('user_id')
    doc = get_document_by_id(doc_id, user_id)
    
    if not doc:
        flash('❌ Document not found', 'danger')
        return redirect(url_for('documents'))
    
    # Check if already analyzed
    if doc['ai_analysis']:
        analysis = json.loads(doc['ai_analysis'])
    else:
        # Perform AI analysis
        try:
            analysis = analyze_document(
                doc['file_path'],
                doc['document_type'],
                context=doc.get('description')
            )
            
            # Save analysis
            update_document_analysis(doc_id, analysis)
            
            flash('✅ AI analysis complete!', 'success')
        except Exception as e:
            flash(f'❌ Analysis failed: {str(e)}', 'danger')
            analysis = {"error": str(e)}
    
    return render_template('analyze_document.html',
                         document=doc,
                         analysis=analysis,
                         username=session.get('username'))

@app.route('/download-document/<int:doc_id>')
@login_required
def download_document(doc_id):
    """Download a document"""
    user_id = session.get('user_id')
    doc = get_document_by_id(doc_id, user_id)
    
    if not doc:
        flash('❌ Document not found', 'danger')
        return redirect(url_for('documents'))
    
    return send_file(doc['file_path'], 
                    as_attachment=True,
                    download_name=doc['original_filename'])

@app.route('/delete-document/<int:doc_id>', methods=['POST'])
@login_required
def delete_document_route(doc_id):
    """Delete a document"""
    user_id = session.get('user_id')
    doc = get_document_by_id(doc_id, user_id)
    
    if not doc:
        flash('❌ Document not found', 'danger')
        return redirect(url_for('documents'))
    
    # Delete file from filesystem
    try:
        Path(doc['file_path']).unlink()
    except:
        pass
    
    # Delete from database
    delete_document(doc_id, user_id)
    
    flash('✅ Document deleted', 'success')
    return redirect(url_for('documents'))

# --- n8n Integration API Endpoints ---

@app.route('/api/pending-responses', methods=['GET'])
def api_pending_responses():
    """API endpoint for n8n to fetch pending responses (scheduled check)"""
    # Simple API key authentication
    api_key = request.headers.get('X-API-Key')
    if api_key != os.getenv('FLASK_SECRET_KEY'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Get all users with pending responses
    from db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query for overdue disputes without responses
    query = """
        SELECT 
            u.id as user_id,
            u.username,
            u.email,
            u.full_name,
            d.id as dispute_id,
            d.bureau,
            d.creditor_name,
            d.account_number,
            d.sent_date,
            d.expected_response_date,
            julianday('now') - julianday(d.sent_date) as days_waiting
        FROM disputes d
        JOIN users u ON d.user_id = u.id
        WHERE d.status IN ('sent', 'delivered')
        AND d.expected_response_date < datetime('now')
        AND NOT EXISTS (
            SELECT 1 FROM documents doc
            WHERE doc.dispute_id = d.id
            AND doc.document_type = 'bureau_response'
        )
        ORDER BY d.expected_response_date ASC
    """
    
    if hasattr(conn, 'row_factory'):  # SQLite
        cursor.execute(query)
        results = [dict(row) for row in cursor.fetchall()]
    else:  # PostgreSQL
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'count': len(results),
        'pending_responses': results
    })

@app.route('/api/send-reminder', methods=['POST'])
@login_required
def api_send_reminder():
    """Manually trigger n8n reminder for specific dispute"""
    user_id = session.get('user_id')
    data = request.json
    dispute_id = data.get('dispute_id')
    
    # Get dispute and user info
    from db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            u.email,
            u.full_name,
            d.bureau,
            d.creditor_name,
            d.account_number,
            d.sent_date,
            julianday('now') - julianday(d.sent_date) as days_waiting
        FROM disputes d
        JOIN users u ON d.user_id = u.id
        WHERE d.id = ? AND d.user_id = ?
    """
    
    if hasattr(conn, 'row_factory'):  # SQLite
        cursor.execute(query, (dispute_id, user_id))
        result = cursor.fetchone()
    else:  # PostgreSQL
        cursor.execute(query, (dispute_id, user_id))
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            result = dict(zip(columns, row))
        else:
            result = None
    
    conn.close()
    
    if not result:
        return jsonify({'error': 'Dispute not found'}), 404
    
    # Call n8n webhook
    n8n_url = os.getenv('N8N_WEBHOOK_URL')
    if not n8n_url or 'YOUR_WEBHOOK_ID' in n8n_url:
        return jsonify({'error': 'n8n webhook not configured'}), 500
    
    try:
        response = requests.post(
            n8n_url,
            json={
                'type': 'manual_reminder',
                'user_email': result['email'] if isinstance(result, dict) else result[0],
                'user_name': result['full_name'] if isinstance(result, dict) else result[1],
                'bureau': result['bureau'] if isinstance(result, dict) else result[2],
                'creditor': result['creditor_name'] if isinstance(result, dict) else result[3],
                'account_number': result['account_number'] if isinstance(result, dict) else result[4],
                'sent_date': result['sent_date'] if isinstance(result, dict) else result[5],
                'days_waiting': int(result['days_waiting'] if isinstance(result, dict) else result[6]),
                'dashboard_url': url_for('index', _external=True)
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify({'success': True, 'message': 'Reminder sent'})
        else:
            return jsonify({'error': 'n8n workflow failed', 'details': response.text}), 500
            
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Failed to connect to n8n', 'details': str(e)}), 500

# --- Plaid Integration Routes ---

@app.route('/connect-bank')
@login_required
def connect_bank():
    """Plaid Link connection page"""
    user_id = session.get('user_id')
    username = session.get('username')
    
    # Get existing Plaid connections
    plaid_items = get_plaid_items(user_id)
    
    return render_template('connect_bank.html',
                         plaid_items=plaid_items,
                         username=username)

@app.route('/api/plaid/create-link-token', methods=['POST'])
@login_required
def create_plaid_link_token():
    """Create Plaid Link token for frontend"""
    try:
        user_id = session.get('user_id')
        username = session.get('username')
        
        # Create link token (without redirect_uri for simpler setup)
        link_token = plaid_integration.create_link_token(
            user_id=user_id,
            username=username
        )
        
        return jsonify({'link_token': link_token})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/plaid/exchange-token', methods=['POST'])
@login_required
def exchange_plaid_token():
    """Exchange public token for access token and sync accounts"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        public_token = data.get('public_token')
        
        if not public_token:
            return jsonify({'error': 'Missing public_token'}), 400
        
        # Exchange token
        token_data = plaid_integration.exchange_public_token(public_token)
        
        # Save to database
        plaid_item_id = save_plaid_item(
            user_id=user_id,
            item_id=token_data['item_id'],
            access_token=token_data['access_token']
        )
        
        # Fetch and save accounts
        accounts_data = plaid_integration.get_accounts(token_data['access_token'])
        
        for account in accounts_data['accounts']:
            save_plaid_account(user_id, plaid_item_id, account)
        
        # Start initial transaction sync (background task would be better)
        try:
            sync_result = plaid_integration.sync_transactions(token_data['access_token'])
            
            # Save transactions
            for txn in sync_result['transactions']:
                save_plaid_transaction(user_id, txn['plaid_account_id'], txn)
            
            # Update cursor
            update_plaid_item_cursor(plaid_item_id, sync_result['cursor'])
            
        except Exception as sync_error:
            print(f"Transaction sync error: {sync_error}")
            # Continue even if sync fails
        
        return jsonify({
            'success': True,
            'accounts_imported': len(accounts_data['accounts'])
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/plaid/sync-accounts/<int:plaid_item_id>', methods=['POST'])
@login_required
def sync_plaid_accounts(plaid_item_id):
    """Manually sync Plaid accounts and transactions"""
    try:
        user_id = session.get('user_id')
        
        # Get Plaid item
        plaid_item = get_plaid_item_by_id(plaid_item_id, user_id)
        if not plaid_item:
            return jsonify({'error': 'Plaid item not found'}), 404
        
        access_token = plaid_item['access_token']
        
        # Sync accounts
        accounts_data = plaid_integration.get_accounts(access_token)
        for account in accounts_data['accounts']:
            save_plaid_account(user_id, plaid_item_id, account)
        
        # Sync transactions
        cursor = plaid_item.get('cursor')
        sync_result = plaid_integration.sync_transactions(access_token, cursor=cursor)
        
        txn_count = 0
        for txn in sync_result['transactions']:
            save_plaid_transaction(user_id, txn['plaid_account_id'], txn)
            txn_count += 1
        
        # Update cursor
        update_plaid_item_cursor(plaid_item_id, sync_result['cursor'])
        
        return jsonify({
            'success': True,
            'accounts_synced': len(accounts_data['accounts']),
            'transactions_synced': txn_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/plaid/disconnect/<int:plaid_item_id>', methods=['POST'])
@login_required
def disconnect_plaid_item(plaid_item_id):
    """Disconnect a Plaid bank connection"""
    try:
        user_id = session.get('user_id')
        delete_plaid_item(plaid_item_id, user_id)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/payment-proof/<int:account_id>')
@login_required
def payment_proof(account_id):
    """Search for payment proof transactions for an account"""
    user_id = session.get('user_id')
    
    # Get account details
    conn = get_db_connection()
    account = conn.execute(
        'SELECT * FROM user_accounts WHERE id = ? AND user_id = ?',
        (account_id, user_id)
    ).fetchone()
    conn.close()
    
    if not account:
        flash('❌ Account not found', 'danger')
        return redirect(url_for('accounts'))
    
    # Get Plaid items
    plaid_items = get_plaid_items(user_id)
    
    if not plaid_items:
        flash('⚠️ No bank accounts connected. Connect a bank to search for payment proof.', 'warning')
        return redirect(url_for('connect_bank'))
    
    # Search transactions across all Plaid items
    all_transactions = []
    creditor_name = account['creditor_name']
    
    for plaid_item in plaid_items:
        try:
            transactions = plaid_integration.search_payment_transactions(
                access_token=plaid_item['access_token'],
                creditor_name=creditor_name
            )
            all_transactions.extend(transactions)
        except Exception as e:
            print(f"Error searching transactions: {e}")
            continue
    
    # Generate proof data
    if all_transactions:
        proof_data = plaid_integration.generate_payment_proof_data(all_transactions, creditor_name)
    else:
        proof_data = None
    
    return render_template('payment_proof.html',
                         account=account,
                         proof_data=proof_data,
                         transactions=all_transactions,
                         username=session.get('username'))

@app.route('/api/plaid/accounts')
@login_required
def api_plaid_accounts():
    """API endpoint to get all Plaid accounts"""
    try:
        user_id = session.get('user_id')
        accounts = get_plaid_accounts(user_id)
        
        return jsonify({'accounts': accounts})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Initialize database
    from db import init_db
    init_db()
    
    # Run Flask app
    # In production, gunicorn will handle this
    # In development, run with debug mode
    is_production = os.getenv('FLASK_ENV') == 'production'
    app.run(
        debug=not is_production,
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000))
    )
