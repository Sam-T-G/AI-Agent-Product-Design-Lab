# Deployment Guide

## Overview

This guide covers deploying the AI Agent Product Design Lab to production environments.

## Prerequisites

- Production-ready code (tests passing, linting clean)
- Environment variables configured
- Database set up (if using PostgreSQL)
- Domain name (optional, for custom domains)

## Frontend Deployment

### Vercel (Recommended)

1. **Connect Repository**

   - Import project from GitHub/GitLab
   - Vercel auto-detects Next.js

2. **Configure Environment Variables**

   ```
   NEXT_PUBLIC_API_BASE_URL=https://your-api-domain.com/api
   ```

3. **Deploy**

   - Automatic on push to main branch
   - Preview deployments for PRs

4. **Custom Domain** (optional)
   - Add domain in Vercel dashboard
   - Configure DNS records

### Netlify

1. **Connect Repository**

   - Import from Git provider

2. **Build Settings**

   - Build command: `npm run build`
   - Publish directory: `.next`

3. **Environment Variables**

   - Add in Netlify dashboard
   - `NEXT_PUBLIC_API_BASE_URL`

4. **Deploy**
   - Automatic on push

## Backend Deployment

### Fly.io

1. **Install Fly CLI**

   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Initialize**

   ```bash
   cd backend
   fly launch
   ```

3. **Set Secrets**

   ```bash
   fly secrets set GEMINI_API_KEY=your_key
   fly secrets set DATABASE_URL=your_db_url
   ```

4. **Deploy**
   ```bash
   fly deploy
   ```

### Render

1. **Create Web Service**

   - Connect repository
   - Select Python environment

2. **Build Command**

   ```
   pip install -r requirements.txt
   ```

3. **Start Command**

   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

4. **Environment Variables**
   - Add in Render dashboard
   - `GEMINI_API_KEY`
   - `DATABASE_URL`

### Railway

1. **Deploy from GitHub**

   - Connect repository
   - Auto-detects Python

2. **Configure**

   - Add environment variables
   - Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

3. **Deploy**
   - Automatic on push

### Google Cloud Run

1. **Create Dockerfile**

   ```dockerfile
   FROM python:3.10-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
   ```

2. **Build and Deploy**

   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/agent-lab-api
   gcloud run deploy agent-lab-api --image gcr.io/PROJECT_ID/agent-lab-api
   ```

3. **Set Secrets**
   ```bash
   gcloud run services update agent-lab-api \
     --set-env-vars GEMINI_API_KEY=your_key
   ```

## Database Setup

### PostgreSQL (Production)

1. **Create Database**

   - Use managed service (AWS RDS, Google Cloud SQL, etc.)
   - Or use database-as-a-service (Supabase, Neon, etc.)

2. **Update DATABASE_URL**

   ```
   DATABASE_URL=postgresql://user:password@host:5432/dbname
   ```

3. **Run Migrations**
   ```bash
   python -m db.migrate
   ```

### SQLite (Development Only)

- Not recommended for production
- Use for local development only

## Environment Variables

### Backend Production

```bash
GEMINI_API_KEY=your_production_key
DATABASE_URL=postgresql://...
CORS_ORIGINS=https://your-frontend-domain.com
LOG_LEVEL=INFO
PORT=8000
```

### Frontend Production

```bash
NEXT_PUBLIC_API_BASE_URL=https://your-api-domain.com/api
```

## Security Checklist

- [ ] API keys stored as secrets (never in code)
- [ ] CORS configured for specific origins
- [ ] HTTPS enabled (required for production)
- [ ] Rate limiting configured
- [ ] Input validation on all endpoints
- [ ] Error messages don't leak sensitive info
- [ ] Database credentials secured
- [ ] Logging configured (no sensitive data in logs)

## Monitoring

### Recommended Tools

- **Error Tracking**: Sentry
- **Analytics**: PostHog or Plausible
- **Uptime Monitoring**: UptimeRobot or Pingdom
- **Logging**: Cloud provider logs or Datadog

### Health Check Endpoint

Add to backend:

```python
@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

## Performance Optimization

### Frontend

- Enable Next.js Image Optimization
- Use CDN for static assets
- Enable compression
- Optimize bundle size

### Backend

- Enable connection pooling
- Use async/await for I/O operations
- Cache agent definitions
- Implement request rate limiting

## Scaling Considerations

### Horizontal Scaling

- Stateless backend (can run multiple instances)
- Load balancer for API
- Database connection pooling

### Vertical Scaling

- Increase instance size for more CPU/memory
- Monitor resource usage

## Cost Optimization

- Use Gemini Flash for simple tasks
- Implement caching to reduce API calls
- Set max tokens per request
- Monitor usage and set alerts

## Rollback Plan

1. Keep previous deployment version
2. Test rollback procedure
3. Document rollback steps
4. Have database backup strategy

## Post-Deployment

1. Verify all endpoints working
2. Test agent creation and execution
3. Monitor error logs
4. Check performance metrics
5. Update documentation with production URLs

## Troubleshooting

### Common Issues

**CORS errors**

- Check CORS_ORIGINS configuration
- Verify frontend URL matches allowed origins

**Database connection errors**

- Verify DATABASE_URL format
- Check network/firewall rules
- Ensure database is accessible

**API key errors**

- Verify GEMINI_API_KEY is set correctly
- Check API key has proper permissions
- Verify quota not exceeded

**Build failures**

- Check Node.js/Python versions match
- Verify all dependencies in requirements.txt/package.json
- Check build logs for specific errors
