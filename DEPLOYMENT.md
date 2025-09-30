# Deployment Guide

Complete guide for deploying the Cruise Employee English Assessment Platform to production.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Database Setup](#database-setup)
- [Application Deployment](#application-deployment)
- [Docker Deployment](#docker-deployment)
- [Production Configuration](#production-configuration)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

**Minimum Requirements:**
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB
- OS: Ubuntu 20.04 LTS or later, CentOS 8+, or Windows Server 2019+

**Recommended for Production:**
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 50GB+ SSD
- OS: Ubuntu 22.04 LTS

### Required Software

- Python 3.10 or higher
- PostgreSQL 15 or higher
- Redis 7 or higher
- Nginx (for production)
- Git
- Docker & Docker Compose (for containerized deployment)

## Environment Setup

### 1. Create Production User

```bash
# Create application user
sudo useradd -m -s /bin/bash cruiseassess
sudo usermod -aG sudo cruiseassess

# Switch to application user
sudo su - cruiseassess
```

### 2. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip
sudo apt install -y postgresql-15 postgresql-contrib-15
sudo apt install -y redis-server
sudo apt install -y nginx
sudo apt install -y git curl wget
sudo apt install -y build-essential libpq-dev
```

**CentOS/RHEL:**
```bash
sudo dnf install -y python310 python3-pip
sudo dnf install -y postgresql15-server postgresql15-contrib
sudo dnf install -y redis
sudo dnf install -y nginx
sudo dnf install -y git
sudo dnf install -y gcc postgresql-devel
```

### 3. Clone Repository

```bash
cd /opt
sudo git clone <repository-url> cruise-assessment
sudo chown -R cruiseassess:cruiseassess cruise-assessment
cd cruise-assessment
```

### 4. Create Virtual Environment

```bash
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## Database Setup

### 1. Configure PostgreSQL

```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql <<EOF
CREATE DATABASE english_assessment;
CREATE USER assess_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE english_assessment TO assess_user;
ALTER DATABASE english_assessment OWNER TO assess_user;
\q
EOF
```

### 2. Configure PostgreSQL for Production

Edit `/etc/postgresql/15/main/postgresql.conf`:

```ini
# Connection Settings
listen_addresses = 'localhost'
max_connections = 100
shared_buffers = 256MB

# Performance
effective_cache_size = 1GB
maintenance_work_mem = 128MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 2621kB
min_wal_size = 1GB
max_wal_size = 4GB

# Logging
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_rotation_age = 1d
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_min_duration_statement = 1000
```

Edit `/etc/postgresql/15/main/pg_hba.conf`:

```
# Allow local connections
local   all             all                                     peer
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

### 3. Run Database Migrations

```bash
cd /opt/cruise-assessment
source venv/bin/activate

# Run migrations
alembic upgrade head

# Load question bank
python -c "
import asyncio
from src.main.python.core.database import async_session_maker
from src.main.python.data.question_bank_loader import QuestionBankLoader

async def load_questions():
    async with async_session_maker() as db:
        loader = QuestionBankLoader(db)
        await loader.load_all_questions()
        print('Questions loaded successfully')

asyncio.run(load_questions())
"
```

## Application Deployment

### 1. Create Environment File

Create `/opt/cruise-assessment/.env`:

```env
# Application
APP_NAME=Cruise Employee English Assessment Platform
VERSION=1.0.0
DEBUG=False
HOST=0.0.0.0
PORT=8000

# Security
SECRET_KEY=<generate-secure-random-key-here>
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_ORIGINS=["https://yourdomain.com"]

# Database
DATABASE_URL=postgresql://assess_user:your_secure_password@localhost:5432/english_assessment

# AI Services
OPENAI_API_KEY=<your-openai-api-key>
ANTHROPIC_API_KEY=<your-anthropic-api-key>

# Redis
REDIS_URL=redis://localhost:6379

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Assessment Settings
PASS_THRESHOLD_TOTAL=70
PASS_THRESHOLD_SAFETY=0.8
PASS_THRESHOLD_SPEAKING=12

# Session Settings
SESSION_TIMEOUT_SECONDS=14400
SESSION_WARNING_SECONDS=300
SESSION_SECURE_COOKIE=True
SESSION_ROTATION_INTERVAL=1800

# Security Settings
CSRF_ENABLED=True
CSRF_COOKIE_SECURE=True
RATE_LIMIT_ENABLED=True

# File Storage
AUDIO_UPLOAD_DIR=/opt/cruise-assessment/data/audio
STATIC_FILES_DIR=/opt/cruise-assessment/static
```

Generate secure secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Configure Redis

```bash
# Start Redis
sudo systemctl start redis
sudo systemctl enable redis

# Configure Redis
sudo nano /etc/redis/redis.conf
```

Key Redis settings:

```conf
bind 127.0.0.1
port 6379
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

Restart Redis:

```bash
sudo systemctl restart redis
```

### 3. Create Systemd Service

Create `/etc/systemd/system/cruise-assessment.service`:

```ini
[Unit]
Description=Cruise Assessment Platform
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=cruiseassess
Group=cruiseassess
WorkingDirectory=/opt/cruise-assessment
Environment="PATH=/opt/cruise-assessment/venv/bin"
ExecStart=/opt/cruise-assessment/venv/bin/uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info \
    --access-log \
    --proxy-headers
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cruise-assessment
sudo systemctl start cruise-assessment
sudo systemctl status cruise-assessment
```

### 4. Configure Nginx

Create `/etc/nginx/sites-available/cruise-assessment`:

```nginx
upstream cruise_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Max upload size (for audio files)
    client_max_body_size 50M;

    # Static files
    location /static/ {
        alias /opt/cruise-assessment/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Application
    location / {
        proxy_pass http://cruise_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
    }

    # WebSocket support (future)
    location /ws/ {
        proxy_pass http://cruise_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

Enable site and restart Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/cruise-assessment /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5. Setup SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

## Docker Deployment

### 1. Build Docker Image

```bash
cd /opt/cruise-assessment
docker build -t cruise-assessment:latest .
```

### 2. Docker Compose Setup

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  web:
    image: cruise-assessment:latest
    restart: always
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://assess_user:password@db:5432/english_assessment
      - REDIS_URL=redis://redis:6379
    env_file:
      - .env
    depends_on:
      - db
      - redis
    volumes:
      - ./data:/app/data
      - ./static:/app/static
      - ./logs:/app/logs

  db:
    image: postgres:15
    restart: always
    environment:
      - POSTGRES_DB=english_assessment
      - POSTGRES_USER=assess_user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    restart: always
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  nginx:
    image: nginx:latest
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./static:/var/www/static:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - web

volumes:
  postgres_data:
  redis_data:
```

### 3. Deploy with Docker Compose

```bash
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml logs -f
```

## Production Configuration

### Security Checklist

- [ ] Set `DEBUG=False`
- [ ] Change `SECRET_KEY` to secure random value
- [ ] Set `SESSION_SECURE_COOKIE=True`
- [ ] Set `CSRF_COOKIE_SECURE=True`
- [ ] Configure `ALLOWED_ORIGINS` with actual domain
- [ ] Enable HTTPS/SSL
- [ ] Configure firewall (UFW/firewalld)
- [ ] Set strong database password
- [ ] Enable rate limiting
- [ ] Configure security headers in Nginx
- [ ] Restrict database to localhost only
- [ ] Set up fail2ban for SSH protection

### Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP
sudo ufw allow 443/tcp    # HTTPS
sudo ufw enable

# Firewalld (CentOS)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### Database Tuning

```bash
# Adjust PostgreSQL for production workload
sudo -u postgres psql -d english_assessment -c "
CREATE INDEX idx_assessments_user_id ON assessments(user_id);
CREATE INDEX idx_assessments_status ON assessments(status);
CREATE INDEX idx_assessments_created_at ON assessments(created_at);
CREATE INDEX idx_responses_assessment_id ON assessment_responses(assessment_id);
CREATE INDEX idx_responses_question_id ON assessment_responses(question_id);
CREATE INDEX idx_questions_module_division ON questions(module_type, division);
"
```

## Monitoring & Maintenance

### Logging

Application logs location: `/opt/cruise-assessment/logs/`

View logs:

```bash
# Application logs
sudo journalctl -u cruise-assessment -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

### Health Checks

```bash
# Check application health
curl http://localhost:8000/health

# Check database connection
sudo -u postgres psql -d english_assessment -c "SELECT 1;"

# Check Redis
redis-cli ping
```

### Monitoring Tools

**Option 1: Simple monitoring script**

Create `/opt/cruise-assessment/monitor.sh`:

```bash
#!/bin/bash

# Check if application is running
if ! systemctl is-active --quiet cruise-assessment; then
    echo "Application down, restarting..."
    systemctl restart cruise-assessment
fi

# Check disk space
DISK_USAGE=$(df -h /opt | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "WARNING: Disk usage is ${DISK_USAGE}%"
fi

# Check memory
MEM_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
if [ "$MEM_USAGE" -gt 90 ]; then
    echo "WARNING: Memory usage is ${MEM_USAGE}%"
fi
```

Add to crontab:

```bash
*/5 * * * * /opt/cruise-assessment/monitor.sh >> /var/log/cruise-monitor.log 2>&1
```

## Backup & Recovery

### Database Backup

Create backup script `/opt/cruise-assessment/backup-db.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/opt/cruise-assessment/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
sudo -u postgres pg_dump english_assessment | gzip > $BACKUP_FILE

# Keep only last 30 days of backups
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
```

Schedule daily backups:

```bash
0 2 * * * /opt/cruise-assessment/backup-db.sh >> /var/log/db-backup.log 2>&1
```

### Restore from Backup

```bash
# Stop application
sudo systemctl stop cruise-assessment

# Restore database
gunzip -c /opt/cruise-assessment/backups/db_backup_TIMESTAMP.sql.gz | \
    sudo -u postgres psql english_assessment

# Start application
sudo systemctl start cruise-assessment
```

## Troubleshooting

### Application won't start

```bash
# Check logs
sudo journalctl -u cruise-assessment -n 50

# Check if port is in use
sudo netstat -tulpn | grep 8000

# Check environment variables
sudo systemctl show cruise-assessment --property=Environment
```

### Database connection errors

```bash
# Verify database is running
sudo systemctl status postgresql

# Test connection
sudo -u postgres psql -d english_assessment

# Check DATABASE_URL in .env
```

### High memory usage

```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head -n 10

# Reduce Uvicorn workers
# Edit /etc/systemd/system/cruise-assessment.service
# Change --workers 4 to --workers 2
sudo systemctl daemon-reload
sudo systemctl restart cruise-assessment
```

### Slow performance

```bash
# Check database queries
sudo -u postgres psql -d english_assessment -c "
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"

# Check Redis performance
redis-cli --latency
```

## Updates & Maintenance

### Update Application

```bash
# Navigate to application directory
cd /opt/cruise-assessment

# Pull latest changes
sudo -u cruiseassess git pull

# Activate virtual environment
source venv/bin/activate

# Update dependencies
pip install -r requirements.txt --upgrade

# Run migrations
alembic upgrade head

# Restart application
sudo systemctl restart cruise-assessment
```

### Zero-Downtime Updates

```bash
# Using multiple workers, reload one at a time
sudo systemctl reload cruise-assessment
```

---

**Document Version**: 1.0
**Last Updated**: 2025-09-30
**Support**: Development Team
