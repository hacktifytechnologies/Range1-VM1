#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
#  PURPLE TEAM RANGE — SCENARIO 1 DEPLOYMENT SCRIPT
#  Government e-Procurement Portal (GePP)
#  
#  Run as root on the target VM:
#    chmod +x deploy.sh && sudo ./deploy.sh
# ═══════════════════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║   PURPLE TEAM RANGE — SCENARIO 1 DEPLOYMENT                ║"
    echo "║   Government e-Procurement Portal (GePP)                   ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

banner

# ── 1. System Dependencies ───────────────────────────────────────────────
echo -e "${YELLOW}[*] Installing system dependencies...${NC}"
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv sqlite3 nginx rsyslog auditd -qq

# ── 2. Application Setup ────────────────────────────────────────────────
echo -e "${YELLOW}[*] Setting up application directory...${NC}"
APP_DIR="/opt/gepp"
mkdir -p $APP_DIR
mkdir -p /var/log/gepp

# Copy application files (adjust source path as needed)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp -r "$SCRIPT_DIR/webapp/"* "$APP_DIR/"

# ── 3. Python Environment ───────────────────────────────────────────────
echo -e "${YELLOW}[*] Creating Python virtual environment...${NC}"
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate
pip install -q flask gunicorn

# ── 4. Initialize Database ──────────────────────────────────────────────
echo -e "${YELLOW}[*] Initializing database with seed data...${NC}"
python3 init_db.py

# ── 5. Create systemd Service ───────────────────────────────────────────
echo -e "${YELLOW}[*] Creating systemd service...${NC}"
cat > /etc/systemd/system/gepp.service << 'EOF'
[Unit]
Description=GePP - Government e-Procurement Portal
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/gepp
Environment="PATH=/opt/gepp/venv/bin"
ExecStart=/opt/gepp/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 2 --access-logfile /var/log/gepp/access.log --error-logfile /var/log/gepp/error.log app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# ── 6. Nginx Reverse Proxy ──────────────────────────────────────────────
echo -e "${YELLOW}[*] Configuring Nginx reverse proxy...${NC}"
cat > /etc/nginx/sites-available/gepp << 'EOF'
server {
    listen 80;
    server_name _;

    # Logging — critical for Blue Team detection
    access_log /var/log/nginx/gepp_access.log;
    error_log  /var/log/nginx/gepp_error.log;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/gepp /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# ── 7. File Permissions ─────────────────────────────────────────────────
echo -e "${YELLOW}[*] Setting permissions...${NC}"
chown -R www-data:www-data $APP_DIR
chmod 755 $APP_DIR
chmod 664 $APP_DIR/gepp_database.db
chown -R www-data:www-data /var/log/gepp

# ── 8. Configure Audit Logging (for Blue Team) ──────────────────────────
echo -e "${YELLOW}[*] Configuring auditd rules for Blue Team...${NC}"
cat >> /etc/audit/rules.d/gepp.rules << 'EOF'
# Monitor database file access
-w /opt/gepp/gepp_database.db -p rwa -k gepp_database
# Monitor application config changes
-w /opt/gepp/app.py -p wa -k gepp_app_config
# Monitor log file tampering
-w /var/log/gepp/ -p wa -k gepp_logs
# Monitor admin login attempts
-w /opt/gepp/templates/admin_login.html -p r -k gepp_admin_page
EOF

systemctl restart auditd 2>/dev/null || true

# ── 9. Rsyslog Configuration ────────────────────────────────────────────
echo -e "${YELLOW}[*] Configuring rsyslog for centralized logging...${NC}"
cat > /etc/rsyslog.d/gepp.conf << 'EOF'
# GePP Application Logs
if $programname == 'gunicorn' then /var/log/gepp/syslog_gepp.log
& stop
EOF
systemctl restart rsyslog

# ── 10. Start Services ──────────────────────────────────────────────────
echo -e "${YELLOW}[*] Starting GePP service...${NC}"
systemctl daemon-reload
systemctl enable gepp
systemctl start gepp

# ── 11. Verification ────────────────────────────────────────────────────
sleep 2
if systemctl is-active --quiet gepp; then
    echo -e "${GREEN}[✓] GePP service is running${NC}"
else
    echo -e "${RED}[✗] GePP service failed to start. Check: journalctl -u gepp${NC}"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  DEPLOYMENT COMPLETE${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Portal URL:      ${BLUE}http://<SERVER_IP>${NC}"
echo -e "  Vendor Login:    ${BLUE}http://<SERVER_IP>/login${NC}"
echo -e "  Admin Login:     ${BLUE}http://<SERVER_IP>/admin/login${NC}  (SQLi target)"
echo ""
echo -e "  Default Vendor:  ${YELLOW}procurement / procurement123${NC}"
echo -e "  SQLi Bypass:     ${YELLOW}' OR 1=1 -- ${NC}"
echo ""
echo -e "  ${RED}LOG LOCATIONS (for Blue Team):${NC}"
echo -e "    App logs:    /var/log/gepp/gepp_app.log"
echo -e "    Access log:  /var/log/gepp/access.log"
echo -e "    Nginx log:   /var/log/nginx/gepp_access.log"
echo -e "    Nginx error: /var/log/nginx/gepp_error.log"
echo -e "    Audit log:   /var/log/audit/audit.log"
echo ""
