# 🐳 Docker Cheat Sheet - Water Quality API

## 📋 Essential Commands

### 🚀 Starting the API

```bash
# Start all containers (in background/detached mode)
sudo docker-compose up -d

# Start and see logs in real-time (blocks terminal)
sudo docker-compose up

# Start and rebuild images (if you changed Dockerfile)
sudo docker-compose up --build -d
```

### 🛑 Stopping the API

```bash
# Stop all containers (keeps data - database, volumes)
sudo docker-compose down

# Stop and remove ALL data (volumes, database - CAREFUL!)
sudo docker-compose down -v

# Stop specific service only (e.g., just the web container)
sudo docker-compose stop web
```

### 🔄 Restarting Services

```bash
# Restart all services
sudo docker-compose restart

# Restart specific service (e.g., after code changes)
sudo docker-compose restart web

# Restart database
sudo docker-compose restart db
```

### 📊 Viewing Logs

```bash
# View logs in real-time (all services)
sudo docker-compose logs -f

# View logs for specific service only
sudo docker-compose logs -f web

# View last 50 lines of logs
sudo docker-compose logs --tail=50

# View logs with timestamps
sudo docker-compose logs -f --tail=50 --timestamps

# View logs for specific time range
sudo docker-compose logs --since 10m  # Last 10 minutes
```

### 📦 Container Status

```bash
# List all running containers
sudo docker-compose ps

# List all containers (including stopped)
sudo docker ps -a

# Check container resource usage (CPU, memory)
sudo docker stats
```

### 🔨 Rebuilding from Zero

```bash
# Nuclear option: Stop, remove everything, rebuild, start
sudo docker-compose down -v && sudo docker-compose build --no-cache && sudo docker-compose up -d

# Step by step:
sudo docker-compose down -v           # Stop and remove volumes
sudo docker-compose build --no-cache  # Rebuild images from scratch
sudo docker-compose up -d             # Start fresh containers
```

### 🧹 Cleaning Up Docker

```bash
# Remove unused images, containers, networks (SAFE - keeps running containers)
sudo docker system prune

# Remove EVERYTHING including volumes (DANGEROUS - removes all data!)
sudo docker system prune -a --volumes

# Remove only dangling images (untagged images)
sudo docker image prune

# See disk usage by Docker
sudo docker system df
```

### 🔍 Debugging Commands

```bash
# Enter a running container (interactive shell)
sudo docker-compose exec web bash

# Run a one-off command in container
sudo docker-compose exec web python manage.py migrate

# Check if services are healthy
sudo docker-compose ps

# View container details
sudo docker inspect water_quality_api-web-1

# View container logs with error filtering
sudo docker-compose logs web | grep -i error
```

### 🗄️ Database Commands

```bash
# Enter PostgreSQL shell
sudo docker-compose exec db psql -U yd -d water_quality_db

# Backup database
sudo docker-compose exec db pg_dump -U yd water_quality_db > backup.sql

# Restore database
sudo docker-compose exec -T db psql -U yd water_quality_db < backup.sql

# View database logs
sudo docker-compose logs db --tail=100
```

### 🔧 Common Workflows

#### After Code Changes (Python files):
```bash
# Just restart the web service (fastest)
sudo docker-compose restart web
```

#### After Requirements Changes:
```bash
# Rebuild and restart
sudo docker-compose up --build -d
```

#### After Docker Configuration Changes:
```bash
# Stop, rebuild, start
sudo docker-compose down
sudo docker-compose build --no-cache
sudo docker-compose up -d
```

#### Fresh Start (Keep Database):
```bash
# Stop, rebuild, start (keeps data)
sudo docker-compose down
sudo docker-compose up --build -d
```

#### Complete Fresh Start (No Data):
```bash
# Nuclear option - wipes everything
sudo docker-compose down -v
sudo docker-compose build --no-cache
sudo docker-compose up -d
```

### 🌐 Accessing Services

```bash
# API: http://localhost:8000
# PostgreSQL: localhost:5433
# Admin: http://localhost:8000/admin
```

### 📝 Useful Aliases (Add to ~/.bashrc)

```bash
# Add these to your ~/.bashrc file for shortcuts
alias dcup='sudo docker-compose up -d'
alias dcdown='sudo docker-compose down'
alias dclogs='sudo docker-compose logs -f --tail=50'
alias dcrestart='sudo docker-compose restart'
alias dcps='sudo docker-compose ps'
alias dcweb='sudo docker-compose restart web && sudo docker-compose logs -f web'
alias dcnuke='sudo docker-compose down -v && sudo docker-compose build --no-cache && sudo docker-compose up -d'

# Then reload: source ~/.bashrc
```

### ⚠️ Troubleshooting

#### Disk Space Full:
```bash
# Check disk usage
df -h

# Clean Docker (safe)
sudo docker system prune -a

# Check Docker disk usage
sudo docker system df
```

#### Port Already in Use:
```bash
# Find what's using port 8000
sudo lsof -i :8000

# Kill process using the port
sudo kill -9 <PID>

# Or change port in docker-compose.yml
```

#### Container Won't Start:
```bash
# Check logs
sudo docker-compose logs web --tail=100

# Remove and recreate
sudo docker-compose down
sudo docker-compose up -d

# If still failing, rebuild
sudo docker-compose build --no-cache
```

#### Database Connection Issues:
```bash
# Check if database is running
sudo docker-compose ps db

# Check database logs
sudo docker-compose logs db --tail=50

# Restart database
sudo docker-compose restart db

# If corrupted, wipe and recreate
sudo docker-compose down -v
sudo docker-compose up -d
```

### 🎯 Quick Reference

| Task | Command |
|------|---------|
| Start API | `sudo docker-compose up -d` |
| Stop API | `sudo docker-compose down` |
| View logs | `sudo docker-compose logs -f` |
| Restart web | `sudo docker-compose restart web` |
| Fresh start | `sudo docker-compose down && sudo docker-compose up -d` |
| Nuclear option | `sudo docker-compose down -v && sudo docker-compose build --no-cache && sudo docker-compose up -d` |
| Clean Docker | `sudo docker system prune` |
| Enter container | `sudo docker-compose exec web bash` |
| Check status | `sudo docker-compose ps` |

### 💡 Pro Tips

1. **Always check logs first**: `sudo docker-compose logs -f web`
2. **Use `-d` flag**: Run containers in background (detached mode)
3. **Restart is faster than rebuild**: For code changes, just restart
4. **Watch disk space**: Docker can fill up disk quickly
5. **Don't use `down -v` unless you want to lose data**
6. **Use `--tail` with logs**: Avoid overwhelming output

### 🔒 Without sudo (Optional)

If you don't want to use `sudo` every time:
```bash
# Add your user to docker group
sudo usermod -aG docker $USER

# Logout and login again, then:
docker-compose up -d  # No sudo needed!
```

---

**Your Current Setup:**
- **API Port**: 8000
- **Database Port**: 5433
- **Database Name**: water_quality_db
- **Docker Data Location**: /home/docker-data (320GB available)
