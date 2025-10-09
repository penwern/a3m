# Running a3m with PostgreSQL in Docker

This guide shows you how to run a3m with PostgreSQL using Docker Compose for high-performance concurrent package processing.

## Quick Start

1. **Create environment file:**
   ```bash
   cp .env.postgres.example .env
   ```

2. **Edit `.env` and set at minimum:**
   ```bash
   A3M_DB_PASSWORD=your_secure_password_here
   A3M_SECRET_KEY=your_secret_key_minimum_50_characters_long
   A3M_CONCURRENT_PACKAGES=4  # Adjust based on your CPU count
   ```

3. **Start the services:**
   ```bash
   docker compose -f compose.postgres.yml up -d
   ```

4. **Check logs:**
   ```bash
   docker compose -f compose.postgres.yml logs -f a3m
   ```

5. **Stop the services:**
   ```bash
   docker compose -f compose.postgres.yml down
   ```

## Services

The Docker Compose setup includes:

### 1. PostgreSQL Database (`postgres`)
- **Image:** `postgres:15-alpine`
- **Port:** 5432 (exposed for debugging)
- **Volume:** `a3m-postgres-data` (persistent storage)
- **Network:** `a3m-network`

### 2. a3m Server (`a3m`)
- **Build:** Local Dockerfile
- **Port:** 7000 (gRPC API)
- **Volume:** `a3m-pipeline-data` (persistent storage)
- **Network:** `a3m-network`
- **Depends on:** PostgreSQL (waits for health check)

### 3. pgAdmin (Optional)
- **Image:** `dpage/pgadmin4:latest`
- **Port:** 5050 (web interface)
- **Profile:** `tools` (disabled by default)

To start with pgAdmin:
```bash
docker compose -f compose.postgres.yml --profile tools up -d
```

Access pgAdmin at http://localhost:5050

## Configuration

### Environment Variables

All configuration is done via environment variables in the `.env` file:

#### Database Configuration
- `A3M_DB_PASSWORD` - PostgreSQL password (required)

#### Concurrency Settings
- `A3M_CONCURRENT_PACKAGES` - Number of packages to process concurrently (default: 4)
- `A3M_WORKER_THREADS` - Worker threads per package (default: 8)
- `A3M_RPC_THREADS` - RPC server threads (default: 4)
- `A3M_BATCH_SIZE` - Database batch size (default: 128)

#### Application Settings
- `A3M_DEBUG` - Debug mode (default: false)
- `A3M_TIME_ZONE` - Timezone (default: UTC)
- `A3M_SECRET_KEY` - Django secret key (required for production)

See `.env.postgres.example` for complete list.

### Tuning Concurrency

The `A3M_CONCURRENT_PACKAGES` setting controls how many packages are processed simultaneously:

**Recommended values:**
- **CPU cores:** Set to half of your CPU count
- **4 cores:** `A3M_CONCURRENT_PACKAGES=2`
- **8 cores:** `A3M_CONCURRENT_PACKAGES=4`
- **16 cores:** `A3M_CONCURRENT_PACKAGES=8`
- **32 cores:** `A3M_CONCURRENT_PACKAGES=16`

**Note:** With SQLite, this is always limited to 1. PostgreSQL enables true concurrency.

## Database Management

### Accessing the Database

Connect to PostgreSQL from host:
```bash
docker compose -f compose.postgres.yml exec postgres psql -U a3m_user -d a3m_database
```

Or from another container:
```bash
psql -h postgres -U a3m_user -d a3m_database
```

### Running Migrations

Migrations run automatically on container start. To run manually:
```bash
docker compose -f compose.postgres.yml exec a3m a3md migrate
```

### Backup Database

```bash
docker compose -f compose.postgres.yml exec postgres pg_dump -U a3m_user -d a3m_database > backup.sql
```

### Restore Database

```bash
cat backup.sql | docker compose -f compose.postgres.yml exec -T postgres psql -U a3m_user -d a3m_database
```

### View Database Size

```bash
docker compose -f compose.postgres.yml exec postgres psql -U a3m_user -d a3m_database -c "
SELECT
    pg_size_pretty(pg_database_size('a3m_database')) as database_size,
    pg_size_pretty(pg_total_relation_size('\"Files\"')) as files_table_size,
    pg_size_pretty(pg_total_relation_size('\"Events\"')) as events_table_size;
"
```

## Monitoring

### View Logs

All services:
```bash
docker compose -f compose.postgres.yml logs -f
```

Just a3m:
```bash
docker compose -f compose.postgres.yml logs -f a3m
```

Just PostgreSQL:
```bash
docker compose -f compose.postgres.yml logs -f postgres
```

### Check Service Health

```bash
docker compose -f compose.postgres.yml ps
```

### Monitor Database Connections

```bash
docker compose -f compose.postgres.yml exec postgres psql -U a3m_user -d a3m_database -c "
SELECT
    count(*) as total_connections,
    state,
    wait_event_type
FROM pg_stat_activity
WHERE datname = 'a3m_database'
GROUP BY state, wait_event_type;
"
```

### Check Database Performance

```bash
docker compose -f compose.postgres.yml exec postgres psql -U a3m_user -d a3m_database -c "
SELECT
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    n_tup_ins,
    n_tup_upd,
    n_tup_del
FROM pg_stat_user_tables
ORDER BY seq_scan DESC
LIMIT 10;
"
```

## Troubleshooting

### Container won't start

Check logs:
```bash
docker compose -f compose.postgres.yml logs a3m
docker compose -f compose.postgres.yml logs postgres
```

### Database connection errors

1. Verify PostgreSQL is healthy:
   ```bash
   docker compose -f compose.postgres.yml ps postgres
   ```

2. Test connection manually:
   ```bash
   docker compose -f compose.postgres.yml exec a3m /bin/sh -c "
   apt-get update && apt-get install -y postgresql-client &&
   psql -h postgres -U a3m_user -d a3m_database -c 'SELECT version();'
   "
   ```

3. Check password matches in `.env`:
   ```bash
   grep A3M_DB_PASSWORD .env
   ```

### Migration errors

Reset and rerun migrations:
```bash
# Drop and recreate database (WARNING: destroys all data)
docker compose -f compose.postgres.yml exec postgres psql -U a3m_user -d postgres -c "
DROP DATABASE IF EXISTS a3m_database;
CREATE DATABASE a3m_database OWNER a3m_user;
"

# Restart a3m to run migrations
docker compose -f compose.postgres.yml restart a3m
```

### Slow performance

1. **Increase concurrent packages:**
   ```bash
   # In .env
   A3M_CONCURRENT_PACKAGES=8  # Increase based on CPU
   ```

2. **Check database load:**
   ```bash
   docker stats a3m-postgres
   ```

3. **Tune PostgreSQL parameters** in `compose.postgres.yml`:
   - `shared_buffers` - Increase for more memory
   - `work_mem` - Increase for complex queries
   - `max_connections` - Increase for more concurrent connections

4. **Monitor database locks:**
   ```bash
   docker compose -f compose.postgres.yml exec postgres psql -U a3m_user -d a3m_database -c "
   SELECT * FROM pg_locks WHERE NOT granted;
   "
   ```

### Out of memory

Set resource limits in `compose.postgres.yml`:
```yaml
services:
  a3m:
    deploy:
      resources:
        limits:
          cpus: '8'
          memory: 8G
```

### Disk space issues

Check volume usage:
```bash
docker system df -v
```

Clean up old data:
```bash
docker volume prune
```

## Production Deployment

For production deployments:

1. **Use secrets management** instead of `.env` file
2. **Set strong passwords** for database and Django secret key
3. **Remove port exposures** that aren't needed
4. **Enable SSL/TLS** for PostgreSQL connections
5. **Set up backups** with cron jobs
6. **Monitor metrics** with Prometheus/Grafana
7. **Use Docker secrets** for sensitive values
8. **Set resource limits** appropriately
9. **Enable log rotation** for container logs
10. **Use persistent volumes** with backup strategies

### Example Production Override

Create `compose.postgres.prod.yml`:
```yaml
services:
  postgres:
    ports: []  # Don't expose PostgreSQL
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  a3m:
    volumes:
      - "a3m-pipeline-data:/home/a3m/.local/share/a3m:rw"
      # Remove code mount in production
    deploy:
      resources:
        limits:
          cpus: '16'
          memory: 16G
        reservations:
          cpus: '8'
          memory: 8G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Run with:
```bash
docker compose -f compose.postgres.yml -f compose.postgres.prod.yml up -d
```

## Maintenance

### Update images

```bash
docker compose -f compose.postgres.yml pull
docker compose -f compose.postgres.yml up -d
```

### Rebuild a3m

```bash
docker compose -f compose.postgres.yml build a3m
docker compose -f compose.postgres.yml up -d a3m
```

### Clean up

Stop and remove containers:
```bash
docker compose -f compose.postgres.yml down
```

Remove volumes (WARNING: destroys all data):
```bash
docker compose -f compose.postgres.yml down -v
```

Remove everything including images:
```bash
docker compose -f compose.postgres.yml down -v --rmi all
```

## Performance Tips

1. **Use SSD storage** for PostgreSQL volumes
2. **Allocate sufficient memory** to PostgreSQL (at least 2GB)
3. **Tune `shared_buffers`** to 25% of available RAM
4. **Monitor and adjust** `work_mem` for query performance
5. **Use connection pooling** (already configured)
6. **Regular VACUUM** operations (automated by PostgreSQL)
7. **Monitor slow queries** and add indexes as needed
8. **Set realistic `CONCURRENT_PACKAGES`** based on workload

## Next Steps

- Read [PostgreSQL Setup Guide](../examples/postgresql-setup.md) for detailed configuration
- See [Settings Documentation](settings.rst) for all configuration options
- Check [Development Guide](development.rst) for local development setup
