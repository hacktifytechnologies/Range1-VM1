#!/usr/bin/env python3
"""
=============================================================================
  PURPLE TEAM RANGE - SCENARIO 1
  Government e-Procurement Portal (GePP)
  
  VULNERABLE BY DESIGN - For authorized security training only.
  
  Vulnerabilities planted:
    1. Default credentials on user login  (procurement / procurement123)
    2. SQL Injection on admin login        (authentication bypass + dump)
    3. Database contains pivot reference   (Scenario 2 - Tomcat server)
=============================================================================
"""

import sqlite3
import os
import logging
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g, jsonify
)

# ── Logging Configuration (for Blue Team detection) ──────────────────────────
logging.basicConfig(
    filename='/var/log/gepp/gepp_app.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(remote_addr)s | %(message)s'
)

class RequestFormatter(logging.Formatter):
    def format(self, record):
        record.remote_addr = request.remote_addr if request else 'N/A'
        return super().format(record)

handler = logging.FileHandler('/var/log/gepp/gepp_app.log')
handler.setFormatter(RequestFormatter(
    '%(asctime)s | %(levelname)s | %(remote_addr)s | %(message)s'
))

app = Flask(__name__)
app.secret_key = 'gepp-s3cr3t-k3y-2024'  # Intentionally weak for the range
DATABASE = '/opt/gepp/gepp_database.db'

# ── Database Helpers ─────────────────────────────────────────────────────────

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# ── Public Routes ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Landing page - Government e-Procurement Portal"""
    db = get_db()
    tenders = db.execute(
        'SELECT * FROM tenders WHERE status = "Open" ORDER BY deadline ASC LIMIT 6'
    ).fetchall()
    return render_template('index.html', tenders=tenders)

@app.route('/tenders')
def tenders():
    """Public tender listing"""
    db = get_db()
    tenders = db.execute('SELECT * FROM tenders ORDER BY published_date DESC').fetchall()
    return render_template('tenders.html', tenders=tenders)

@app.route('/tender/<int:tender_id>')
def tender_detail(tender_id):
    db = get_db()
    tender = db.execute('SELECT * FROM tenders WHERE id = ?', (tender_id,)).fetchone()
    return render_template('tender_detail.html', tender=tender)

# ── User Login (Default Credentials) ────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    VULNERABILITY: Default credentials
    Username: procurement
    Password: procurement123
    """
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        app.logger.info(f'USER_LOGIN_ATTEMPT | user={username}')
        
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ? AND password = ?',
            (username, password)
        ).fetchone()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            app.logger.info(f'USER_LOGIN_SUCCESS | user={username}')
            flash('Login successful. Welcome to GePP.', 'success')
            return redirect(url_for('vendor_dashboard'))
        else:
            app.logger.warning(f'USER_LOGIN_FAILED | user={username}')
            flash('Invalid credentials. Please try again.', 'danger')
    
    return render_template('login.html')

@app.route('/vendor/dashboard')
def vendor_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    bids = db.execute(
        'SELECT b.*, t.title as tender_title FROM bids b '
        'JOIN tenders t ON b.tender_id = t.id WHERE b.vendor_id = ?',
        (session['user_id'],)
    ).fetchall()
    return render_template('vendor_dashboard.html', bids=bids)

# ── Admin Login (SQL INJECTION VULNERABILITY) ────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """
    ╔══════════════════════════════════════════════════════════════════╗
    ║  VULNERABILITY: SQL INJECTION - Authentication Bypass           ║
    ║                                                                  ║
    ║  The admin login uses string concatenation instead of            ║
    ║  parameterized queries. This allows:                             ║
    ║    - Auth bypass:  ' OR 1=1 --                                   ║
    ║    - UNION-based extraction                                      ║
    ║    - Database enumeration via sqlmap                              ║
    ╚══════════════════════════════════════════════════════════════════╝
    """
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        app.logger.info(f'ADMIN_LOGIN_ATTEMPT | user={username} | pass_length={len(password)}')
        
        # ═══ VULNERABLE QUERY ═══════════════════════════════════════════
        # Using string formatting instead of parameterized query
        # This is the intentional SQL injection point
        query = f"SELECT * FROM admin_users WHERE username = '{username}' AND password = '{password}'"
        
        app.logger.info(f'ADMIN_SQL_QUERY | query={query}')
        # ════════════════════════════════════════════════════════════════
        
        db = get_db()
        try:
            admin = db.execute(query).fetchone()
            
            if admin:
                session['admin_id'] = admin['id']
                session['admin_user'] = admin['username']
                session['is_admin'] = True
                app.logger.info(f'ADMIN_LOGIN_SUCCESS | user={username}')
                flash('Welcome to the Administration Panel.', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                app.logger.warning(f'ADMIN_LOGIN_FAILED | user={username}')
                flash('Invalid administrator credentials.', 'danger')
        except sqlite3.OperationalError as e:
            # Log the SQL error (helps blue team detect injection attempts)
            app.logger.error(f'ADMIN_SQL_ERROR | user={username} | error={str(e)}')
            flash('An error occurred. Please try again.', 'danger')
    
    return render_template('admin_login.html')

# ── Admin Dashboard ──────────────────────────────────────────────────────────

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    db = get_db()
    stats = {
        'total_tenders': db.execute('SELECT COUNT(*) FROM tenders').fetchone()[0],
        'open_tenders': db.execute("SELECT COUNT(*) FROM tenders WHERE status='Open'").fetchone()[0],
        'total_vendors': db.execute('SELECT COUNT(*) FROM users').fetchone()[0],
        'total_bids': db.execute('SELECT COUNT(*) FROM bids').fetchone()[0],
    }
    recent_bids = db.execute(
        'SELECT b.*, t.title as tender_title, u.username as vendor_name '
        'FROM bids b JOIN tenders t ON b.tender_id = t.id '
        'JOIN users u ON b.vendor_id = u.id ORDER BY b.submitted_at DESC LIMIT 10'
    ).fetchall()
    return render_template('admin_dashboard.html', stats=stats, recent_bids=recent_bids)

@app.route('/admin/tenders')
def admin_tenders():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    db = get_db()
    tenders = db.execute('SELECT * FROM tenders ORDER BY id DESC').fetchall()
    return render_template('admin_tenders.html', tenders=tenders)

@app.route('/admin/vendors')
def admin_vendors():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    db = get_db()
    vendors = db.execute('SELECT * FROM users ORDER BY id').fetchall()
    return render_template('admin_vendors.html', vendors=vendors)

@app.route('/admin/internal-systems')
def admin_internal():
    """Page that reveals internal infrastructure - pivot point to Scenario 2"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    db = get_db()
    systems = db.execute('SELECT * FROM internal_systems').fetchall()
    return render_template('admin_internal.html', systems=systems)

# ── API Endpoint (also vulnerable for sqlmap automation) ─────────────────────

@app.route('/api/admin/verify', methods=['POST'])
def api_admin_verify():
    """
    API endpoint for admin verification - also vulnerable to SQLi
    This gives sqlmap a clean POST endpoint to work with
    """
    data = request.get_json() or request.form
    username = data.get('username', '')
    password = data.get('password', '')
    
    app.logger.info(f'API_ADMIN_VERIFY | user={username}')
    
    # Same vulnerable query pattern
    query = f"SELECT * FROM admin_users WHERE username = '{username}' AND password = '{password}'"
    
    db = get_db()
    try:
        result = db.execute(query).fetchone()
        if result:
            return jsonify({
                'status': 'success',
                'message': 'Authentication successful',
                'user': result['username'],
                'role': result['role']
            })
        else:
            return jsonify({'status': 'fail', 'message': 'Invalid credentials'}), 401
    except sqlite3.OperationalError as e:
        app.logger.error(f'API_SQL_ERROR | error={str(e)}')
        return jsonify({'status': 'error', 'message': 'Database error'}), 500

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# ── Error Handlers ───────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message='Page Not Found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', code=500, message='Internal Server Error'), 500

# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    os.makedirs('/var/log/gepp', exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=False)
