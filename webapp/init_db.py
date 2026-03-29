#!/usr/bin/env python3
"""
Database initialization for GePP - Government e-Procurement Portal
Seeds all tables with realistic government procurement data.
Includes the pivot reference to Scenario 2 (Tomcat server).
"""

import sqlite3
import os

DATABASE = '/opt/gepp/gepp_database.db'

def init_db():
    os.makedirs('/opt/gepp', exist_ok=True)
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # ── Admin Users Table ────────────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            department TEXT,
            last_login TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')

    # ── Regular Users (Vendors) ──────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            company_name TEXT NOT NULL,
            contact_person TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            gst_number TEXT,
            pan_number TEXT,
            registration_status TEXT DEFAULT 'Active',
            role TEXT NOT NULL DEFAULT 'vendor',
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')

    # ── Tenders ──────────────────────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_number TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            department TEXT NOT NULL,
            description TEXT,
            category TEXT,
            estimated_value REAL,
            earnest_money REAL,
            published_date TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'Open',
            documents_url TEXT,
            created_by INTEGER,
            FOREIGN KEY (created_by) REFERENCES admin_users(id)
        )
    ''')

    # ── Bids ─────────────────────────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id INTEGER NOT NULL,
            vendor_id INTEGER NOT NULL,
            bid_amount REAL NOT NULL,
            technical_score REAL,
            status TEXT DEFAULT 'Submitted',
            submitted_at TEXT DEFAULT (datetime('now')),
            remarks TEXT,
            FOREIGN KEY (tender_id) REFERENCES tenders(id),
            FOREIGN KEY (vendor_id) REFERENCES users(id)
        )
    ''')

    # ── Sensitive: Confidential Bid Evaluations ──────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS bid_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bid_id INTEGER NOT NULL,
            evaluator TEXT NOT NULL,
            score REAL,
            comments TEXT,
            recommendation TEXT,
            evaluated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (bid_id) REFERENCES bids(id)
        )
    ''')

    # ── Sensitive: Financial Records ─────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS financial_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id INTEGER,
            vendor_id INTEGER,
            payment_amount REAL,
            payment_date TEXT,
            payment_status TEXT,
            bank_reference TEXT,
            account_number TEXT,
            ifsc_code TEXT,
            FOREIGN KEY (tender_id) REFERENCES tenders(id),
            FOREIGN KEY (vendor_id) REFERENCES users(id)
        )
    ''')

    # ══════════════════════════════════════════════════════════════════════
    # ═══ PIVOT TABLE: Internal Systems (leads to Scenario 2) ═════════════
    # ══════════════════════════════════════════════════════════════════════
    c.execute('''
        CREATE TABLE IF NOT EXISTS internal_systems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            system_name TEXT NOT NULL,
            hostname TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            port INTEGER,
            service TEXT,
            platform TEXT,
            credentials TEXT,
            status TEXT DEFAULT 'Active',
            notes TEXT,
            last_checked TEXT DEFAULT (datetime('now'))
        )
    ''')

    # ── Secret Notes (bonus discovery for Red Team) ──────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS secret_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT,
            subject TEXT,
            content TEXT,
            classification TEXT DEFAULT 'CONFIDENTIAL',
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')

    # ════════════════════════════════════════════════════════════════════════
    # SEED DATA
    # ════════════════════════════════════════════════════════════════════════

    # ── Admin Users ──────────────────────────────────────────────────────
    admins = [
        ('admin', 'Pr0cur3m3nt@2024!', 'Rajesh Kumar Sharma', 'rajesh.sharma@gepp.gov.in', 'super_admin', 'IT Division'),
        ('procurement_officer', 'GePP#Officer2024', 'Priya Nair', 'priya.nair@gepp.gov.in', 'admin', 'Procurement Division'),
        ('finance_head', 'F1n@nc3H3ad!', 'Arun Mehta', 'arun.mehta@gepp.gov.in', 'finance_admin', 'Finance Division'),
        ('audit_admin', 'Aud1t@cc3ss!', 'Sunita Reddy', 'sunita.reddy@gepp.gov.in', 'auditor', 'Audit Division'),
    ]
    for a in admins:
        c.execute('INSERT OR IGNORE INTO admin_users (username, password, full_name, email, role, department) VALUES (?,?,?,?,?,?)', a)

    # ── Vendor Users (including default creds) ───────────────────────────
    vendors = [
        ('procurement', 'procurement123', 'TechServe Solutions Pvt. Ltd.', 'Vikram Singh', 'vikram@techserve.in', '+91-9876543210', '27AADCT1234F1ZH', 'AADCT1234F'),
        ('infraworks', 'infra@2024', 'InfraWorks Engineering Ltd.', 'Deepak Patel', 'deepak@infraworks.co.in', '+91-9123456780', '24BBCDI5678G2ZK', 'BBCDI5678G'),
        ('greenbuild', 'green#build1', 'GreenBuild Contractors', 'Anitha Menon', 'anitha@greenbuild.in', '+91-8765432100', '32CCDEG9012H3ZL', 'CCDEG9012H'),
        ('mediplus', 'medi2024plus', 'MediPlus Health Supplies', 'Karthik Rajan', 'karthik@mediplus.in', '+91-7654321090', '33DDEFH3456I4ZM', 'DDEFH3456I'),
        ('smartgov_tech', 'sg0v2024!', 'SmartGov Technologies', 'Neha Gupta', 'neha@smartgov.in', '+91-6543210980', '07EEFGI7890J5ZN', 'EEFGI7890J'),
    ]
    for v in vendors:
        c.execute('INSERT OR IGNORE INTO users (username, password, company_name, contact_person, email, phone, gst_number, pan_number) VALUES (?,?,?,?,?,?,?,?)', v)

    # ── Tenders ──────────────────────────────────────────────────────────
    tenders_data = [
        ('GEPP/2024/IT/001', 'Supply and Installation of Desktop Computers for District Offices',
         'Ministry of Electronics & IT', 'Procurement of 500 desktop computers with monitors, keyboards and UPS for district-level e-governance offices across 12 districts.',
         'IT Equipment', 2500000.00, 50000.00, '2024-01-15', '2025-06-30', 'Open'),
        ('GEPP/2024/INFRA/002', 'Construction of Government Data Centre - Phase II',
         'Department of Telecommunications', 'Design, construction, and commissioning of a Tier-III data centre facility with 200 rack capacity, redundant power, and cooling systems.',
         'Infrastructure', 85000000.00, 1700000.00, '2024-02-01', '2025-07-15', 'Open'),
        ('GEPP/2024/MED/003', 'Annual Rate Contract for Medical Supplies - District Hospitals',
         'Ministry of Health & Family Welfare', 'Annual rate contract for supply of medical consumables, surgical instruments, and diagnostic kits to 45 district hospitals.',
         'Medical Supplies', 12000000.00, 240000.00, '2024-01-20', '2025-05-31', 'Open'),
        ('GEPP/2024/SW/004', 'Development of Integrated e-Procurement Portal v2.0',
         'National Informatics Centre', 'End-to-end development of next-generation e-procurement portal with AI-based bid evaluation, blockchain audit trail, and multi-language support.',
         'Software Development', 45000000.00, 900000.00, '2024-03-01', '2025-08-31', 'Open'),
        ('GEPP/2023/ELEC/005', 'Supply of Solar Panels for Government Buildings',
         'Ministry of New & Renewable Energy', 'Procurement and installation of 1MW rooftop solar panel systems across 25 government buildings in the national capital region.',
         'Electrical', 35000000.00, 700000.00, '2023-11-01', '2024-12-31', 'Closed'),
        ('GEPP/2024/SEC/006', 'CCTV Surveillance System for Border Checkpoints',
         'Ministry of Home Affairs', 'Supply, installation and 3-year AMC of IP-based CCTV surveillance with analytics at 50 border checkpoints.',
         'Security Equipment', 28000000.00, 560000.00, '2024-03-15', '2025-09-30', 'Open'),
        ('GEPP/2024/VEH/007', 'Procurement of Electric Vehicles for Government Fleet',
         'Ministry of Road Transport', 'Purchase of 100 electric sedans and 50 electric buses for government department use, including charging infrastructure.',
         'Vehicles', 95000000.00, 1900000.00, '2024-02-20', '2025-10-31', 'Open'),
        ('GEPP/2024/FUR/008', 'Office Furniture for New Secretariat Complex',
         'Central Public Works Department', 'Supply and installation of modular office furniture for 2000 workstations in the new integrated secretariat complex.',
         'Furniture', 18000000.00, 360000.00, '2024-04-01', '2025-06-15', 'Open'),
    ]
    for t in tenders_data:
        c.execute('INSERT OR IGNORE INTO tenders (tender_number, title, department, description, category, estimated_value, earnest_money, published_date, deadline, status) VALUES (?,?,?,?,?,?,?,?,?,?)', t)

    # ── Bids ─────────────────────────────────────────────────────────────
    bids_data = [
        (1, 1, 2350000.00, 82.5, 'Under Review', '2024-02-10', 'Competitive pricing with 3-year warranty'),
        (1, 5, 2480000.00, 78.0, 'Under Review', '2024-02-12', 'Includes on-site support'),
        (3, 4, 11500000.00, 88.0, 'Shortlisted', '2024-02-15', 'ISO 13485 certified'),
        (4, 1, 42000000.00, 91.0, 'Under Review', '2024-03-20', 'Agile development with DevSecOps'),
        (4, 5, 44500000.00, 85.0, 'Submitted', '2024-03-22', 'Includes 2-year support'),
        (6, 2, 26500000.00, 79.0, 'Submitted', '2024-04-01', 'Make in India compliant'),
        (7, 2, 90000000.00, 86.0, 'Under Review', '2024-03-15', 'BIS certified vehicles'),
        (8, 3, 17200000.00, 83.0, 'Submitted', '2024-04-10', 'Green certified materials'),
    ]
    for b in bids_data:
        c.execute('INSERT OR IGNORE INTO bids (tender_id, vendor_id, bid_amount, technical_score, status, submitted_at, remarks) VALUES (?,?,?,?,?,?,?)', b)

    # ── Bid Evaluations (Sensitive) ──────────────────────────────────────
    evals = [
        (1, 'Rajesh Kumar Sharma', 82.5, 'Good technical proposal. Pricing competitive. Vendor has track record.', 'RECOMMENDED'),
        (2, 'Rajesh Kumar Sharma', 78.0, 'Adequate proposal but higher cost. Consider as backup.', 'WAITLISTED'),
        (3, 'Priya Nair', 88.0, 'Excellent quality certifications. Strong supply chain.', 'HIGHLY RECOMMENDED'),
        (4, 'Rajesh Kumar Sharma', 91.0, 'Outstanding technical approach. DevSecOps pipeline is best in class.', 'HIGHLY RECOMMENDED'),
    ]
    for e in evals:
        c.execute('INSERT OR IGNORE INTO bid_evaluations (bid_id, evaluator, score, comments, recommendation) VALUES (?,?,?,?,?)', e)

    # ── Financial Records (Sensitive) ────────────────────────────────────
    finance = [
        (5, 3, 17500000.00, '2024-06-15', 'Completed', 'NEFT-2024061500123', '9876543210123456', 'SBIN0001234'),
        (5, 2, 34000000.00, '2024-07-01', 'Completed', 'NEFT-2024070100456', '1234567890654321', 'HDFC0002345'),
        (1, 1, 1175000.00, '2024-08-10', 'Pending', 'NEFT-2024081000789', '5678901234567890', 'ICIC0003456'),
    ]
    for f in finance:
        c.execute('INSERT OR IGNORE INTO financial_records (tender_id, vendor_id, payment_amount, payment_date, payment_status, bank_reference, account_number, ifsc_code) VALUES (?,?,?,?,?,?,?,?)', f)

    # ══════════════════════════════════════════════════════════════════════
    # ═══ INTERNAL SYSTEMS TABLE - PIVOT TO SCENARIO 2 ════════════════════
    # ══════════════════════════════════════════════════════════════════════
    systems = [
        ('GePP Primary Portal', 'gepp-web-01.govt.internal', '10.x.x.x', 5000, 'Flask/Python', 'Ubuntu 22.04', 'N/A - This server', 'Active',
         'Primary e-procurement portal. Flask application on Python 3.10.'),
        ('GePP Database Server', 'gepp-db-01.govt.internal', '10.x.x.x.x', 3306, 'MySQL 8.0', 'Ubuntu 22.04', 'dbadmin / Pr0cur3DB@2024', 'Active',
         'Primary database server. Nightly backups to NAS.'),
        ('Procurement Portal v2 (Tomcat)', 'Undisclosed', 'x.x.x.x', 8080, 'Apache Tomcat 9.0.65', 'Linux', 'Undisclosed', 'Active',
         'New procurement portal under development. Running Apache Tomcat x.y. Manager console enabled. Default deployment path: undisclosed. WAR file deployment is enabled.'),
        ('Internal Mail Server', 'mail.govt.internal', '10.x.x.x', 25, 'Postfix', 'Ubuntu 22.04', 'N/A', 'Active',
         'Internal email relay for procurement notifications.'),
        ('NAS Backup Server', 'nas-backup.govt.internal', '10.x.x.x', 445, 'SMB/CIFS', 'Synology DSM', 'admin / b@ckup2024!', 'Active',
         'Network attached storage for database and document backups.'),
        ('LDAP Directory', 'ldap.govt.internal', '10.x.x.x.', 389, 'OpenLDAP', 'Ubuntu 22.04', 'cn=admin / Ld@p2024Admin', 'Active',
         'Central authentication directory for all internal services.'),
    ]
    for s in systems:
        c.execute('INSERT OR IGNORE INTO internal_systems (system_name, hostname, ip_address, port, service, platform, credentials, status, notes) VALUES (?,?,?,?,?,?,?,?,?)', s)

    # ── Secret Notes ─────────────────────────────────────────────────────
    notes = [
        ('Rajesh Sharma', 'Tomcat Migration Plan',
         'We are migrating procurement services to the new Tomcat server at x.x.x.x:8080. '
         'The manager console is still using default credentials (Undisclosed). '
         'URGENT: Change before go-live. WAR deployment is enabled for the dev team.',
         'CONFIDENTIAL'),
        ('Priya Nair', 'Vendor Database Audit',
         'Completed audit of vendor registrations. Found 3 vendors with expired GST certificates. '
         'Flagged for compliance review. Report submitted to audit_admin.',
         'INTERNAL'),
        ('Arun Mehta', 'Budget Allocation FY2024-25',
         'Total procurement budget: INR 450 Crore. IT allocation: 85 Cr. Infrastructure: 200 Cr. '
         'Medical: 60 Cr. Remaining: 105 Cr for miscellaneous.',
         'RESTRICTED'),
        ('Rajesh Sharma', 'SSH Keys for Server Access',
         'Emergency SSH access to procurement-v2 server: ssh admin@195.x.x.x -p 2222. '
         'Key file stored at /opt/keys/procurement-v2.pem on this server.',
         'TOP SECRET'),
    ]
    for n in notes:
        c.execute('INSERT OR IGNORE INTO secret_notes (author, subject, content, classification) VALUES (?,?,?,?)', n)

    conn.commit()
    conn.close()
    print("[+] Database initialized successfully at", DATABASE)
    print("[+] Tables created: admin_users, users, tenders, bids, bid_evaluations, financial_records, internal_systems, secret_notes")
    print("[+] Default vendor creds: procurement / procurement123")
    print("[+] Admin SQLi target: /admin/login")

if __name__ == '__main__':
    init_db()
