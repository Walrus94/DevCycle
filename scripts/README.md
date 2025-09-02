# DevCycle Scripts

This directory contains scripts for different environments and purposes.

## Structure

### Database Scripts
- **`init-db.sql`** - Database initialization script
  - Creates roles, permissions, and default users
  - Used by docker-compose.yml for local development
  - Can be used for cloud deployment when needed

## Usage

### Local Development
Use docker-compose for all services:
```bash
# Start all services
docker-compose up -d

# Start specific services
docker-compose up -d postgres redis kafka

# Start with development tools (pgAdmin, Kafka UI)
docker-compose --profile dev up -d

# Stop services
docker-compose down
```

### Cloud Deployment
The `init-db.sql` script can be used for cloud database initialization:
- **GCP Cloud SQL**: Can be referenced in deployment configs
- **AWS RDS**: Can be used in database setup procedures
- **Production**: Modify script to remove default users if needed

## Environment Variables

Docker-compose uses these environment variables (with defaults):
- `DOCKER_POSTGRES_DB` (default: devcycle)
- `DOCKER_POSTGRES_USER` (default: postgres)
- `DOCKER_POSTGRES_PASSWORD` (default: devcycle123)
- `DOCKER_POSTGRES_PORT` (default: 5432)
- `DOCKER_PGADMIN_EMAIL` (default: admin@devcycle.dev)
- `DOCKER_PGADMIN_PASSWORD` (default: admin123)
- `DOCKER_REDIS_PORT` (default: 6379)
- `DOCKER_REDIS_PASSWORD` (default: empty)

## Security Notes

⚠️ **Important**: 
- **Development**: `init-db.sql` contains hardcoded development passwords
- **Production**: Modify script to remove default users or use environment variables
- Use secret management in production environments
- Never use development passwords in production
