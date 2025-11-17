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
from dotenv import load_dotenv
from db import (
    init_db, verify_user, update_password, get_user,
    get_user_disputes, get_user_stats, log_dispute,
    get_user_accounts, add_user_account, update_account_status
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

DB_PATH = "disputes.db"
CSV_PATH = "data/accounts.csv"

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
    """Load pending disputes from CSV"""
    try:
        if Path(CSV_PATH).exists():
            df = pd.read_csv(CSV_PATH)
            if 'status' in df.columns:
                return df[df['status'] == 'pending']
            return df
    except Exception as e:
        print(f"Error loading CSV: {e}")
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
    
    # Add delivery rate
    total = stats['total_disputes']
    delivered = stats['delivered']
    stats['delivery_rate'] = round((delivered / total * 100) if total > 0 else 0, 1)
    stats['queue_count'] = len(queue)
    
    # Get recent accounts (last 5)
    recent_accounts = accounts[:5] if len(accounts) > 5 else accounts
    
    return render_template('dashboard.html', 
                         disputes=disputes, 
                         stats=stats,
                         recent_accounts=recent_accounts,
                         get_status_color=get_status_color,
                         username=session.get('username'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        valid, role = verify_user(username, password)
        if valid:
            # Get user info to store user_id in session
            user = get_user(username)
            session.permanent = True
            session['username'] = username
            session['user_id'] = user['id']
            session['role'] = role
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
    
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
            # Log dispute with user_id
            dispute_id = log_dispute(
                user_id=user_id,
                account_number=account,
                bureau=bureau,
                creditor_name=creditor,
                reason=reason,
                status='pending'
            )
            
            flash(f'✅ Added {bureau} dispute for {creditor}!', 'success')
            
            if immediate_send:
                # Run batch immediately
                result = subprocess.run(['python3', 'main.py'], 
                                      capture_output=True, 
                                      text=True)
                if result.returncode == 0:
                    flash('✅ Dispute sent immediately!', 'success')
                else:
                    flash('⚠️ Added to queue, but send failed. Check logs.', 'warning')
            
            return redirect(url_for('index'))
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

@app.route('/send-batch', methods=['GET', 'POST'])
@login_required
def send_batch():
    """Send batch page"""
    queue = load_csv_queue()
    
    if request.method == 'POST':
        # Run the batch script
        result = subprocess.run(['python3', 'main.py'], 
                              capture_output=True, 
                              text=True,
                              cwd=Path.cwd())
        
        if result.returncode == 0:
            flash('✅ Batch sent successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash(f'❌ Batch failed: {result.stderr}', 'danger')
    
    return render_template('send_batch.html', 
                         queue=queue.to_dict('records') if not queue.empty else [],
                         username=session.get('username'))

@app.route('/check-status', methods=['POST'])
@login_required
def check_status():
    """Check delivery status"""
    result = subprocess.run(['python3', 'main.py', '--check-status'], 
                          capture_output=True, 
                          text=True,
                          cwd=Path.cwd())
    
    if result.returncode == 0:
        flash('✅ Status check complete!', 'success')
    else:
        flash(f'❌ Status check failed: {result.stderr}', 'warning')
    
    return redirect(url_for('index'))

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
    return redirect(url_for('index'))

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

if __name__ == '__main__':
    # Initialize database
    from db import init_db
    init_db()
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
