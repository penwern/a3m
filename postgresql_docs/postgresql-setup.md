# PostgreSQL Configuration for a3m

This guide explains how to configure a3m to use PostgreSQL for concurrent package processing.

## Why PostgreSQL?

By default, a3m uses SQLite, which limits concurrent package processing to 1 due to write contention. PostgreSQL enables true concurrency, allowing multiple packages to be processed simultaneously, which significantly improves throughput.

## Prerequisites

- PostgreSQL 12 or later
- Access to create databases and users

## Setup Instructions

### 1. Install PostgreSQL

On Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
```

On macOS with Homebrew:
```bash
brew install postgresql
brew services start postgresql
```

### 2. Create Database and User

Connect to PostgreSQL:
```bash
sudo -u postgres psql
```

Create the database and user:
```sql
CREATE DATABASE a3m_database;
CREATE USER a3m_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE a3m_database TO a3m_user;
\q
```

### 3. Configure a3m

#### Option A: Configuration File

Create or edit `/etc/a3m/a3m.cfg`:

```ini
[a3m]
db_engine = django.db.backends.postgresql
db_name = a3m_database
db_user = a3m_user
db_password = your_secure_password
db_host = localhost
db_port = 5432
```

#### Option B: Environment Variables

```bash
export A3M_DB_ENGINE=django.db.backends.postgresql
export A3M_DB_NAME=a3m_database
export A3M_DB_USER=a3m_user
export A3M_DB_PASSWORD=your_secure_password
export A3M_DB_HOST=localhost
export A3M_DB_PORT=5432
```

### 4. Initialize the Database

Run migrations to create the database schema:
```bash
a3md migrate
```

Or if running via Python:
```bash
python manage.py migrate
```

### 5. Verify Configuration

Start a3md and check that it connects to PostgreSQL:
```bash
a3md
```

You should see logs indicating successful database connection.

## Concurrency Configuration

With PostgreSQL, a3m automatically enables concurrent package processing. The default is half of your CPU count, rounded up.

To override this:

```ini
[a3m]
concurrent_packages = 4  # Process 4 packages concurrently
```

Or via environment variable:
```bash
export A3M_CONCURRENT_PACKAGES=4
```

## Docker Compose Example

Here's a complete example using Docker Compose:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: a3m_database
      POSTGRES_USER: a3m_user
      POSTGRES_PASSWORD: your_secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U a3m_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  a3m:
    image: ghcr.io/artefactual-labs/a3m:latest
    environment:
      A3M_DB_ENGINE: django.db.backends.postgresql
      A3M_DB_NAME: a3m_database
      A3M_DB_USER: a3m_user
      A3M_DB_PASSWORD: your_secure_password
      A3M_DB_HOST: postgres
      A3M_DB_PORT: 5432
      A3M_CONCURRENT_PACKAGES: 4
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "7000:7000"

volumes:
  postgres_data:
```

## Performance Tuning

For optimal PostgreSQL performance with a3m:

### Connection Pooling

The default `CONN_MAX_AGE` is set to 3600 seconds (1 hour), which enables connection pooling. Adjust if needed in your Django settings.

### PostgreSQL Configuration

Consider tuning these PostgreSQL settings in `postgresql.conf`:

```ini
# For concurrent writes
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
```

### Monitoring

Monitor database connections:
```sql
SELECT * FROM pg_stat_activity WHERE datname = 'a3m_database';
```

Check for locks:
```sql
SELECT * FROM pg_locks WHERE NOT granted;
```

## Troubleshooting

### Connection Refused

If you get "connection refused" errors:

1. Check PostgreSQL is running:
   ```bash
   sudo systemctl status postgresql
   ```

2. Verify PostgreSQL is listening on the correct host:
   In `postgresql.conf`, ensure:
   ```ini
   listen_addresses = '*'  # or 'localhost' for local-only
   ```

3. Check `pg_hba.conf` for authentication settings:
   ```
   host    a3m_database    a3m_user    127.0.0.1/32    md5
   ```

### Authentication Failed

- Verify username and password are correct
- Check `pg_hba.conf` authentication method
- Try connecting with psql to verify credentials:
  ```bash
  psql -h localhost -U a3m_user -d a3m_database
  ```

### Migration Errors

If migrations fail:

1. Ensure the user has necessary privileges:
   ```sql
   GRANT ALL PRIVILEGES ON DATABASE a3m_database TO a3m_user;
   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO a3m_user;
   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO a3m_user;
   ```

2. Check PostgreSQL logs:
   ```bash
   sudo tail -f /var/log/postgresql/postgresql-*.log
   ```

## Security Considerations

1. Use strong passwords for database users
2. Restrict database access to necessary hosts only
3. Enable SSL/TLS for database connections in production
4. Regularly update PostgreSQL security patches
5. Use connection pooling to limit resource exhaustion
6. Consider using environment variables or secrets management for credentials

## Switching from SQLite to PostgreSQL

To migrate from SQLite to PostgreSQL:

1. Export data from SQLite (if needed):
   ```bash
   python manage.py dumpdata > backup.json
   ```

2. Configure PostgreSQL as shown above

3. Run migrations:
   ```bash
   python manage.py migrate
   ```

4. Import data (if needed):
   ```bash
   python manage.py loaddata backup.json
   ```

Note: Direct database migration tools like `pgloader` may also work but require careful testing.
