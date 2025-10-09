# a3m with PostgreSQL - Quick Start

Run a3m with PostgreSQL for concurrent package processing.

## Quick Start

1. **Set up environment:**
   ```bash
   cp .env.postgres.example .env
   ```

2. **Edit `.env` and set:**
   ```bash
   A3M_DB_PASSWORD=your_secure_password
   A3M_SECRET_KEY=your_secret_key_at_least_50_characters
   A3M_CONCURRENT_PACKAGES=4  # Adjust based on CPU count
   ```

3. **Start services:**
   ```bash
   docker compose -f compose.postgres.yml up -d
   ```

4. **Check status:**
   ```bash
   docker compose -f compose.postgres.yml ps
   docker compose -f compose.postgres.yml logs -f a3m
   ```

5. **Stop services:**
   ```bash
   docker compose -f compose.postgres.yml down
   ```

## What's Included

- **PostgreSQL 15** - High-performance database for concurrent operations
- **a3m Server** - Archival processing with concurrent package support
- **pgAdmin** (optional) - Web-based database management

## Performance Benefits

With PostgreSQL, a3m can process multiple packages concurrently:

- **SQLite (default):** 1 package at a time
- **PostgreSQL:** Multiple packages simultaneously (configurable)

### Recommended Concurrency Settings

Based on your CPU count:
- 4 CPUs → `A3M_CONCURRENT_PACKAGES=2`
- 8 CPUs → `A3M_CONCURRENT_PACKAGES=4`
- 16 CPUs → `A3M_CONCURRENT_PACKAGES=8`
- 32+ CPUs → `A3M_CONCURRENT_PACKAGES=16`

## Usage

### Access the API

The gRPC API is available at `localhost:7000`.

### Optional: Use pgAdmin

Start with pgAdmin for database management:

```bash
docker compose -f compose.postgres.yml --profile tools up -d
```

Access at: http://localhost:5050
- Email: `admin@a3m.local` (or from `.env`)
- Password: `admin` (or from `.env`)

### Database Commands

**Connect to database:**
```bash
docker compose -f compose.postgres.yml exec postgres \\
  psql -U a3m_user -d a3m_database
```

**Run migrations:**
```bash
docker compose -f compose.postgres.yml exec a3m a3md migrate
```

**Backup database:**
```bash
docker compose -f compose.postgres.yml exec postgres \\
  pg_dump -U a3m_user -d a3m_database > backup.sql
```

**Restore database:**
```bash
cat backup.sql | docker compose -f compose.postgres.yml exec -T postgres \\
  psql -U a3m_user -d a3m_database
```

## Troubleshooting

### Services won't start

```bash
# Check logs
docker compose -f compose.postgres.yml logs

# Check if PostgreSQL is healthy
docker compose -f compose.postgres.yml ps postgres
```

### Connection errors

```bash
# Verify password in .env matches
grep A3M_DB_PASSWORD .env

# Test database connection
docker compose -f compose.postgres.yml exec a3m /bin/sh -c "
  apt-get update && apt-get install -y postgresql-client &&
  psql -h postgres -U a3m_user -d a3m_database -c 'SELECT version();'
"
```

### Slow performance

1. Increase concurrent packages in `.env`:
   ```bash
   A3M_CONCURRENT_PACKAGES=8
   ```

2. Restart services:
   ```bash
   docker compose -f compose.postgres.yml restart a3m
   ```

## Documentation

- **Detailed setup:** [examples/postgresql-setup.md](examples/postgresql-setup.md)
- **Docker guide:** [docs/docker-postgres.md](docs/docker-postgres.md)
- **Settings:** [docs/settings.rst](docs/settings.rst)

## Architecture

```
┌─────────────┐
│   a3m API   │
│  (port 7000)│
└──────┬──────┘
       │
       ▼
┌──────────────┐
│  PostgreSQL  │
│  (port 5432) │
└──────────────┘
```

## Configuration Files

- `compose.postgres.yml` - Docker Compose configuration
- `.env.postgres.example` - Environment variables template
- `.env` - Your local configuration (not in git)

## Production Deployment

For production:

1. Use strong passwords
2. Don't expose PostgreSQL port publicly
3. Enable SSL/TLS for database connections
4. Set up automated backups
5. Monitor with Prometheus/Grafana
6. Use Docker secrets for credentials

See [docs/docker-postgres.md](docs/docker-postgres.md) for production configuration.

## Performance Monitoring

```bash
# Watch logs
docker compose -f compose.postgres.yml logs -f

# Monitor resources
docker stats

# Check database connections
docker compose -f compose.postgres.yml exec postgres \\
  psql -U a3m_user -d a3m_database -c "
    SELECT count(*), state
    FROM pg_stat_activity
    WHERE datname = 'a3m_database'
    GROUP BY state;
  "
```

## Cleanup

```bash
# Stop and remove containers
docker compose -f compose.postgres.yml down

# Remove volumes (WARNING: deletes all data)
docker compose -f compose.postgres.yml down -v

# Remove images too
docker compose -f compose.postgres.yml down -v --rmi all
```

## Support

- Issues: https://github.com/artefactual-labs/a3m/issues
- Documentation: https://a3m.readthedocs.io/

## License

GNU Affero General Public License v3 (AGPLv3)
