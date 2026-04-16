# Database Schema & Setup Guide

## Overview

The Logistics AI backend uses MySQL 8.0 for persistent data storage. The database schema is automatically initialized on first container startup using `init.sql`.

---

## Quick Start

### 1. **First Time Setup**
```bash
cd c:\PROJECTS\logistics-ai\logistics-ai\backend
docker-compose up --build
```

**What happens:**
- MySQL container starts
- `init.sql` runs automatically (mounted in `/docker-entrypoint-initdb.d/`)
- All tables are created
- Default admin user is inserted
- Default configuration is populated

### 2. **Verify Database is Ready**
```bash
docker-compose exec db mysql -u logistics_user -p logistics_db -e "SHOW TABLES;"
```

**Output shows tables:**
```
Tables_in_logistics_db
users
audit_logs
shipment_events
decision_history
system_config
```

---

## Database Schema

### **users** Table
Stores user accounts and access control.

| Column | Type | Notes |
|--------|------|-------|
| id | INT PK | Auto-increment |
| username | VARCHAR(255) | Unique, indexed |
| email | VARCHAR(255) | Unique, indexed |
| password_hash | VARCHAR(512) | Hashed password |
| full_name | VARCHAR(255) | User's display name |
| role | ENUM | admin, operator, viewer |
| is_active | BOOLEAN | Account status |
| created_at | TIMESTAMP | Auto-set on insert |
| updated_at | TIMESTAMP | Auto-update on modification |
| last_login_at | TIMESTAMP NULL | Tracks last login |

**Indexes:** username, email, is_active

---

### **audit_logs** Table
Tracks all user actions for compliance and debugging.

| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT PK | Auto-increment |
| user_id | INT FK | Links to users.id |
| action | VARCHAR(255) | e.g., 'update_shipment', 'view_decision' |
| resource_type | VARCHAR(100) | Type of resource affected |
| resource_id | INT | ID of affected resource |
| old_value | JSON | Previous value |
| new_value | JSON | New value |
| ip_address | VARCHAR(45) | IPv4/IPv6 address |
| user_agent | VARCHAR(512) | Browser/client info |
| status | ENUM | success, failure |
| error_message | TEXT | Error details if failed |
| created_at | TIMESTAMP | When action occurred |

**Indexes:** user_id, created_at, resource (type+id), action

**Relationships:**
- `user_id` → `users.id` (ON DELETE SET NULL)

---

### **shipment_events** Table
Logs all events (updates, alerts, location changes) for each shipment.

| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT PK | Auto-increment |
| shipment_id | VARCHAR(100) | Shipment identifier |
| event_type | VARCHAR(100) | 'delay', 'delivery', 'alert', etc. |
| event_description | TEXT | Detailed description |
| location | VARCHAR(255) | Current location |
| latitude | DECIMAL(10,8) | GPS latitude |
| longitude | DECIMAL(11,8) | GPS longitude |
| metadata | JSON | Extra data (weather, congestion, etc.) |
| severity | ENUM | info, warning, critical |
| created_at | TIMESTAMP | When event occurred |

**Indexes:** shipment_id, event_type, created_at, severity

---

### **decision_history** Table
Stores all AI recommendations and approvals.

| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT PK | Auto-increment |
| shipment_id | VARCHAR(100) | Target shipment |
| decision_type | VARCHAR(100) | Type of decision |
| recommendation | TEXT | AI recommendation text |
| confidence_score | FLOAT | 0-100, with constraint |
| status | ENUM | pending, approved, rejected, executed |
| approved_by | INT FK | User who approved |
| approval_notes | TEXT | Approval comments |
| executed_at | TIMESTAMP NULL | When decision was executed |
| created_at | TIMESTAMP | When AI decided |
| updated_at | TIMESTAMP | Last status change |

**Indexes:** shipment_id, decision_type, status, created_at

**Relationships:**
- `approved_by` → `users.id` (ON DELETE SET NULL)

---

### **system_config** Table
Stores application configuration and settings.

| Column | Type | Notes |
|--------|------|-------|
| id | INT PK | Auto-increment |
| config_key | VARCHAR(255) | Unique config name |
| config_value | TEXT | JSON or plain value |
| config_type | VARCHAR(50) | 'integer', 'boolean', 'string' |
| is_encrypted | BOOLEAN | Whether to encrypt in transit |
| created_at | TIMESTAMP | When created |
| updated_at | TIMESTAMP | Last update |

**Default configs:**
- `alert_threshold_high`: 90
- `alert_threshold_medium`: 75
- `alert_threshold_low`: 50
- `max_shipment_delay_hours`: 24

---

## Data Model Diagram

```
users (1) ──→ (N) audit_logs
       └──→ (N) decision_history

shipment_events [independent - no FK]

decision_history [references users for approvals]
```

---

## How Schema Initialization Works

1. **First Startup:**
   ```bash
   docker-compose up --build
   ```
   - MySQL container starts
   - Docker waits for startup
   - Mounts `./init.sql` to `/docker-entrypoint-initdb.d/01-init.sql`
   - MySQL automatically executes all `.sql` files in `/docker-entrypoint-initdb.d/`
   - Schema is created in `logistics_db` database
   - Default data is inserted

2. **Subsequent Startups:**
   ```bash
   docker-compose start
   ```
   - Persistent volume `db_data` is used
   - Existing data is preserved
   - `init.sql` does NOT re-run (volume already initialized)

3. **Data Persistence:**
   - All data is stored in `db_data` volume
   - Volume survives `docker-compose stop` and `docker-compose start`
   - Volume only deleted with `docker-compose down -v`

---

## Resetting the Database

### Option 1: **Soft Reset** (Keep Docker, Reseed Data)
```bash
docker-compose exec db mysql -u root -proot_password -e "DROP DATABASE logistics_db; CREATE DATABASE logistics_db;"
docker-compose exec db mysql -u root -proot_password logistics_db < init.sql
```

### Option 2: **Hard Reset** (Remove Container & Volume)
```bash
docker-compose down -v
docker-compose up --build
```

**What happens:**
- Stops and removes containers
- Deletes the `db_data` volume
- On next `up --build`, everything is recreated fresh
- Schema is reinitialized from `init.sql`

### Option 3: **Remove Volume Only**
```bash
docker volume rm logistics-ai_db_data
docker-compose up
```

---

## Accessing the Database

### **MySQL CLI from Host**
```bash
# Using mysql-client (if installed locally)
mysql -h 127.0.0.1 -u logistics_user -p logistics_db -e "SELECT * FROM users;"
```

### **MySQL CLI from Container**
```bash
docker-compose exec db mysql -u logistics_user -p logistics_db
```
Then at the prompt:
```sql
USE logistics_db;
SHOW TABLES;
SELECT * FROM users;
DESC audit_logs;
```

### **Backup Database**
```bash
docker-compose exec db mysqldump -u logistics_user -p logistics_db > backup.sql
```

### **Restore from Backup**
```bash
docker-compose exec -T db mysql -u logistics_user -p logistics_db < backup.sql
```

---

## Performance Optimizations

The schema includes strategic indexes:

| Table | Indexes | Purpose |
|-------|---------|---------|
| users | username, email, is_active | Fast lookups by credentials |
| audit_logs | user_id, created_at, resource, action | Audit trails & filtering |
| shipment_events | shipment_id, event_type, created_at, severity | Fast event retrieval |
| decision_history | shipment_id, decision_type, status, created_at | Decision tracking |

**Composite Index:** 
- `(shipment_id, created_at)` - Query recent events for a shipment
- `(resource_type, resource_id)` - Audit logs for specific resource

---

## Connecting from Python/FastAPI

```python
from sqlalchemy import create_engine

# Using environment variables
DB_HOST = os.getenv("DB_HOST", "db")
DB_USER = os.getenv("DB_USER", "logistics_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "logistics_password")
DB_NAME = os.getenv("DB_NAME", "logistics_db")

# Create connection string
database_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# Create engine
engine = create_engine(database_url, pool_pre_ping=True)

# Test connection
with engine.connect() as connection:
    result = connection.execute(text("SELECT 1"))
    print(result.fetchone())  # (1,)
```

---

## Troubleshooting

### **Tables not created?**
```bash
# Check MySQL logs
docker-compose logs db

# Manually verify database
docker-compose exec db mysql -u root -proot_password -e "SHOW DATABASES;"
```

### **Connection refused?**
```bash
# Ensure db service is running and healthy
docker-compose ps

# Check health status
docker-compose exec db mysqladmin ping -u root -proot_password
```

### **Permission denied for logistics_user?**
```bash
# Reconnect with root
docker-compose exec db mysql -u root -proot_password

# Then run:
mysql> GRANT ALL PRIVILEGES ON logistics_db.* TO 'logistics_user'@'%';
mysql> FLUSH PRIVILEGES;
```

### **Volume permission issues (Linux)?**
```bash
# Fix permissions on db_data volume
sudo chmod 755 /var/lib/docker/volumes/logistics-ai_db_data/_data
```

---

## Production Considerations

1. **Change default passwords** in `.env` before deployment
2. **Encrypt password_hash** - Consider bcrypt or Argon2
3. **Set up automated backups** - Use cron + mysqldump
4. **Enable SSL/TLS** - For database connections
5. **Use separate admin account** - Don't share user credentials
6. **Monitor database performance** - Track slow queries
7. **Regular schema reviews** - Audit unused tables/columns

---

## File Structure

```
backend/
├── docker-compose.yml       # Service orchestration
├── Dockerfile              # Backend image definition
├── init.sql                # Schema initialization ← YOU ARE HERE
├── requirements.txt        # Python dependencies
├── .env                    # Runtime environment variables
├── .env.example           # Configuration template
├── .dockerignore          # Files excluded from build
└── app/
    ├── config.py          # App configuration
    └── ...
```

---

## Next Steps

1. Start the stack: `docker-compose up --build`
2. Verify tables: See "Accessing the Database" section
3. Create models in FastAPI (SQLAlchemy ORM)
4. Add API endpoints to CRUD data
5. Set up migrations (Alembic) for schema changes

