# DeepSeaGuard Docker Setup

This guide will help you run DeepSeaGuard using Docker with Redis, Celery, and all services.

## Prerequisites

1. **Docker Desktop** installed on your system
   - Download from: https://www.docker.com/products/docker-desktop/
   - Make sure Docker is running

2. **Docker Compose** (usually included with Docker Desktop)

## Quick Start

### Option 1: Using the provided scripts

**Windows:**
```bash
start-docker.bat
```

**Linux/Mac:**
```bash
chmod +x start-docker.sh
./start-docker.sh
```

### Option 2: Manual commands

```bash
# Build and start all services
docker-compose up --build -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

## Services

The Docker setup includes:

| Service | Port | Description |
|---------|------|-------------|
| **FastAPI App** | 8000 | Main application with API endpoints |
| **Redis** | 6379 | Message broker for Celery |
| **Celery Worker** | - | Background task processing |
| **Celery Beat** | - | Scheduled task scheduler |
| **Flower** | 5555 | Celery monitoring dashboard |

## Access Points

- **🌐 FastAPI App**: http://localhost:8000
- **📚 API Documentation**: http://localhost:8000/docs
- **🔍 Celery Monitor**: http://localhost:5555
- **🏥 Health Check**: http://localhost:8000/health

## Useful Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs for specific service
docker-compose logs -f app
docker-compose logs -f celery-worker
docker-compose logs -f redis

# Restart a specific service
docker-compose restart app

# Rebuild and start
docker-compose up --build -d

# Remove all containers and volumes
docker-compose down -v

# Check resource usage
docker stats
```

## Development

For development with live code reloading:

```bash
# The app service is configured with --reload flag
# Changes to your code will automatically restart the server
```

## Troubleshooting

### Port conflicts
If ports 8000, 6379, or 5555 are already in use:

1. Stop the conflicting service
2. Or modify the ports in `docker-compose.yml`

### Redis connection issues
```bash
# Check Redis status
docker-compose exec redis redis-cli ping

# Should return: PONG
```

### Celery worker issues
```bash
# Check Celery worker logs
docker-compose logs celery-worker

# Restart Celery worker
docker-compose restart celery-worker
```

### Database issues
```bash
# Reinitialize database
docker-compose exec app python src/database/init.py
```

## Production Deployment

For production, consider:

1. **Environment variables**: Use `.env` file or Docker secrets
2. **Database**: Use PostgreSQL instead of SQLite
3. **Redis**: Use managed Redis service
4. **Monitoring**: Add Prometheus/Grafana
5. **SSL**: Add reverse proxy with HTTPS

## Scaling

To scale Celery workers:

```bash
# Scale to 4 workers
docker-compose up -d --scale celery-worker=4
```

## Data Persistence

- **Redis data**: Stored in `redis_data` volume
- **App data**: Stored in `app_data` volume
- **Logs**: Mounted to `./logs` directory
- **Uploads**: Mounted to `./uploads` directory

## Cleanup

```bash
# Stop and remove everything
docker-compose down -v --remove-orphans

# Remove all images
docker-compose down --rmi all
``` 