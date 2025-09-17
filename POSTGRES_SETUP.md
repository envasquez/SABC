# PostgreSQL Setup for SABC

This guide explains how to set up and use PostgreSQL with Docker for local development and deployment.

## Local Development with Docker

### Prerequisites
- Docker and Docker Compose installed
- Python 3.11+ environment with dependencies installed

### Starting PostgreSQL

1. Start the PostgreSQL container:
```bash
docker-compose up -d
```

2. Verify the container is running:
```bash
docker ps
```

3. Initialize the database schema:
```bash
export DATABASE_URL="postgresql://postgres:dev123@localhost:5432/sabc"
python scripts/init_postgres.py
```

4. Create an admin user:
```bash
export DATABASE_URL="postgresql://postgres:dev123@localhost:5432/sabc"
python scripts/bootstrap_admin_postgres.py
```

5. Start the application with PostgreSQL:
```bash
export DATABASE_URL="postgresql://postgres:dev123@localhost:5432/sabc"
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Environment Variables

For PostgreSQL development, set:
```bash
export DATABASE_URL="postgresql://postgres:dev123@localhost:5432/sabc"
```

For SQLite development (default):
```bash
unset DATABASE_URL
# or
export DATABASE_URL="sqlite:///sabc.db"
```

### Database Management

#### Stop PostgreSQL:
```bash
docker-compose down
```

#### Remove PostgreSQL data (reset database):
```bash
docker-compose down -v
docker-compose up -d
# Then re-run init_postgres.py and bootstrap_admin_postgres.py
```

#### Access PostgreSQL directly:
```bash
docker exec -it sabc-postgres psql -U postgres -d sabc
```

#### View logs:
```bash
docker-compose logs postgres
```

## DigitalOcean App Platform Deployment

### Database Configuration

1. Create a PostgreSQL database in DigitalOcean:
   - Go to Databases in DigitalOcean control panel
   - Create a PostgreSQL 15 database
   - Note the connection details

2. Set environment variables in App Platform:
   - `DATABASE_URL`: Connection string from DigitalOcean database
   - `SECRET_KEY`: Random secret for sessions
   - `LOG_LEVEL`: `INFO`

### App Platform Configuration

The `.do/app.yaml` file is configured for:
- GitHub auto-deployment from main branch
- PostgreSQL database connection
- Health checks and scaling

### Deployment Steps

1. Push code to GitHub
2. Connect DigitalOcean App Platform to your GitHub repo
3. Set environment variables in App Platform
4. Deploy the application

## Database Compatibility

The application automatically detects the database type from `DATABASE_URL`:

- **SQLite**: Uses INTEGER PRIMARY KEY, BOOLEAN values 0/1
- **PostgreSQL**: Uses SERIAL PRIMARY KEY, BOOLEAN values true/false

SQL queries are automatically converted for compatibility using `core/db_utils.py`.

## Migration from SQLite

To migrate existing SQLite data to PostgreSQL:

1. Export data from SQLite:
```bash
python -c "
from core.database import db
import json
tables = ['anglers', 'events', 'polls', 'poll_options', 'poll_votes', 'tournaments', 'results', 'team_results', 'news', 'dues', 'officer_positions']
data = {}
for table in tables:
    data[table] = [dict(row._mapping) for row in db(f'SELECT * FROM {table}')]
with open('export.json', 'w') as f:
    json.dump(data, f, indent=2, default=str)
"
```

2. Import data to PostgreSQL:
```bash
export DATABASE_URL="postgresql://postgres:dev123@localhost:5432/sabc"
python -c "
from core.database import db
import json
with open('export.json', 'r') as f:
    data = json.load(f)
for table, rows in data.items():
    for row in rows:
        columns = ', '.join(row.keys())
        placeholders = ', '.join([f':{k}' for k in row.keys()])
        db(f'INSERT INTO {table} ({columns}) VALUES ({placeholders})', row)
"
```

## Troubleshooting

### Connection Issues
- Ensure Docker container is running: `docker ps`
- Check PostgreSQL logs: `docker-compose logs postgres`
- Verify connection string matches container settings

### Permission Issues
- Ensure user has proper database permissions
- Check that database 'sabc' exists

### Schema Issues
- Run `python scripts/init_postgres.py` to recreate schema
- Check for conflicting table names or constraints

### Boolean Conversion Issues
- The app automatically handles SQLite (0/1) vs PostgreSQL (true/false)
- If manual queries fail, use the `core/db_utils.py` helper functions