# Production Deployment Guide

**Project**: Spotter ELD - Trip Planner with FMCSA HOS Compliance
**Target Platforms**: Railway, Render, AWS, Google Cloud, Azure

## Quick Start: Railway Deployment

Railway is the recommended platform for v1.1.0 submission due to ease of setup and PostgreSQL/Redis support.

### Prerequisites
- GitHub account with repository access
- Railway account (free tier available)
- PostgreSQL and Redis instances (Railway provides these)

### Step 1: Connect Repository to Railway

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Authorize GitHub and select `spotter-eld-logging-api` repo
4. Railway will auto-detect the `Dockerfile.prod`

### Step 2: Configure Environment Variables

In Railway dashboard, add the following variables:

```bash
# Django Configuration
DEBUG=False
DJANGO_SECRET_KEY=<generate-new-key>
ALLOWED_HOSTS=<your-railway-domain>

# Database (Railway auto-provides this)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Redis Cache (Railway auto-provides this)
REDIS_URL=redis://user:password@host:port

# CORS Configuration (for Vercel frontend)
CORS_ALLOWED_ORIGINS=https://frontend.vercel.app

# API Configuration
API_USER_AGENT=SpotterELD/1.0 (support@spotter-eld.app)

# Logging
LOG_LEVEL=INFO
```

### Step 3: Generate Django Secret Key

Run locally or use an online generator:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output and paste into Railway's `DJANGO_SECRET_KEY` variable.

### Step 4: Add PostgreSQL and Redis Services

In Railway dashboard:

1. Click **"Add Service"** → **"Database"** → **"PostgreSQL"**
2. Click **"Add Service"** → **"Database"** → **"Redis"**
3. These auto-populate `DATABASE_URL` and `REDIS_URL` variables

### Step 5: Deploy

Railway will automatically:
1. Build the Docker image from `Dockerfile.prod`
2. Run migrations via `docker-entrypoint.sh`
3. Start Gunicorn server on port 8000
4. Assign a public domain (e.g., `spotter-api.railway.app`)

### Step 6: Verify Deployment

Test your live backend:

```bash
curl https://your-railway-domain/health/
# Expected response: {"status": "ok"}
```

Test full API endpoint:

```bash
curl -X POST https://your-railway-domain/api/plan-route/ \
  -H "Content-Type: application/json" \
  -d '{
    "current_location": "Chicago, IL",
    "pickup_location": "Indianapolis, IN",
    "dropoff_location": "Dallas, TX",
    "cycle_hours_used": 30
  }'
```

## Docker Image Building

### Local Build and Test

```bash
# Build production image locally
docker build -f Dockerfile.prod -t spotter-eld:latest .

# Run container locally
docker run -it \
  -e DEBUG=False \
  -e DJANGO_SECRET_KEY=your-secret \
  -e DATABASE_URL=postgresql://user:pass@db:5432/spotter \
  -e REDIS_URL=redis://redis:6379/0 \
  -p 8000:8000 \
  spotter-eld:latest

# Test endpoint
curl http://localhost:8000/health/
```

### GitHub Container Registry (GHCR)

Images are automatically built and pushed on git tags.

#### Manual Build and Push

```bash
# Build
docker build -f Dockerfile.prod -t ghcr.io/fworks-tech/spotter-eld-logging-api:v1.0.0 .

# Push (requires GHCR_TOKEN)
echo $GHCR_TOKEN | docker login ghcr.io -u <username> --password-stdin
docker push ghcr.io/fworks-tech/spotter-eld-logging-api:v1.0.0
```

#### Pull from GHCR

```bash
docker pull ghcr.io/fworks-tech/spotter-eld-logging-api:v1.0.0
```

## Automated Releases

### Tag a Release

```bash
# Create and push a semantic version tag
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

This triggers:
1. GitHub Actions: Build and push production image to GHCR
2. Tests: Run full test suite on the image
3. Release: Create GitHub release with deployment instructions

## Alternative Platforms

### Render.com

1. Create account and new **"Web Service"**
2. Connect GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn spotter.wsgi:application --bind 0.0.0.0:8000`
5. Add environment variables (same as Railway)
6. Add PostgreSQL and Redis services
7. Deploy

### AWS ECS / EC2

1. Push image to Amazon ECR
2. Create ECS task definition with image URI
3. Create ECS service pointing to task definition
4. Configure ALB for load balancing
5. Set RDS PostgreSQL and ElastiCache Redis endpoints

### Docker Hub

Push to Docker Hub instead of GHCR:

```bash
docker tag spotter-eld:latest youruser/spotter-eld:latest
docker push youruser/spotter-eld:latest
```

Update `REGISTRY` in `.github/workflows/docker-build-push.yml`:

```yaml
REGISTRY: docker.io
IMAGE_NAME: youruser/spotter-eld-logging-api
```

## Production Checklist

Before deployment:

- [ ] Generate new `DJANGO_SECRET_KEY`
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Configure `CORS_ALLOWED_ORIGINS` with frontend URL
- [ ] Set up PostgreSQL database
- [ ] Set up Redis cache
- [ ] Set `DATABASE_URL` and `REDIS_URL`
- [ ] Test health endpoint: `GET /health/`
- [ ] Test API endpoint: `POST /api/plan-route/`
- [ ] Monitor logs for errors
- [ ] Set up monitoring/alerting

## Monitoring and Logs

### Railway Logs

In Railway dashboard:
1. Select your service
2. Click **"Logs"** tab
3. View real-time application logs

### Common Issues

**Issue**: 502 Bad Gateway
- Check Django migrations ran: `python manage.py migrate`
- Check `DATABASE_URL` is correct
- Review application logs for errors

**Issue**: CORS errors from frontend
- Verify `CORS_ALLOWED_ORIGINS` includes your frontend domain
- Check frontend sends requests to correct API URL

**Issue**: Timeout errors
- Check `REDIS_URL` connectivity
- Check `DATABASE_URL` connectivity
- Increase timeout values in request configuration

**Issue**: Out of memory
- Increase container resources in Railway
- Reduce Gunicorn worker count (currently 4)

## Rolling Back

If a deployment fails:

1. Railway: Click **"Rollback"** button on previous deployment
2. GHCR: Redeploy previous image version:
   ```bash
   docker pull ghcr.io/fworks-tech/spotter-eld-logging-api:v1.0.0  # previous version
   docker tag ghcr.io/fworks-tech/spotter-eld-logging-api:v1.0.0 spotter-eld:latest
   docker run ...
   ```

## Scaling

For production scale:

1. **Gunicorn Workers**: Increase `--workers` in `Dockerfile.prod` (currently 4)
   - Rule: 2-4 × CPU cores
   - Each worker uses ~50-100MB RAM

2. **Database Connections**: Adjust `DATABASE_CONN_MAX_AGE` in `settings.py`
   - Default: 600 seconds
   - Increase for high-concurrency

3. **Redis**: Use dedicated Redis instance with replication
   - Development: Single-node Redis fine
   - Production: Redis Sentinel or Cluster for HA

4. **Load Balancing**: Railway handles this automatically
   - Scale to multiple instances via Railway dashboard

## Security Best Practices

- ✅ Non-root user in Docker image (appuser)
- ✅ Health checks configured
- ✅ Multi-stage build reduces image size
- ✅ No secrets in image (use environment variables)
- ✅ HTTPS enabled by default (Railway/Render)
- [ ] Set up Web Application Firewall (WAF) - optional
- [ ] Enable DDoS protection - optional
- [ ] Regular dependency updates - schedule monthly

## Troubleshooting

### SSH into Container (Railway)

```bash
# Not directly available; use logs or connect via Railway CLI
railway logs -f
```

### Run One-off Commands

```bash
# Via Railway CLI
railway run python manage.py shell

# Via Docker locally
docker run --rm -it spotter-eld:latest python manage.py shell
```

### Reset Database

⚠️ **WARNING**: This deletes all data

```bash
python manage.py migrate zero trips  # Revert trips app
python manage.py migrate               # Reapply migrations
```

## Support

- **Documentation**: See [ARCHITECTURE.md](ARCHITECTURE.md), [API_CONTRACT.md](API_CONTRACT.md)
- **Issues**: Report via GitHub Issues
- **Questions**: Contact support@spotter-eld.app
