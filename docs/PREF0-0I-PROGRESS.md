# PRÉ-F0.0-I Progress — Railway Migration

**Data:** 2026-08-15  
**Status:** 🟡 50% COMPLETO (preparation phase done, deployment pending)  
**Tempo investido:** ~1 hora  

---

## ✅ Completado

### 1. Strategy & Planning
- ✅ `docs/PREF0-0I-RAILWAY-MIGRATION.md` — Complete migration guide
- ✅ Timeline mapped (2-3 days)
- ✅ Risks identified & mitigated
- ✅ Success criteria defined

### 2. Deployment Configuration
- ✅ `railway.json` — Railway deployment config (health checks, start command)
- ✅ `Dockerfile` — Updated to Python 3.12 (optimized for Railway)
- ✅ Health check endpoint verified (already exists in `health.py`)

### 3. Graceful Shutdown
- ✅ `backend/api/main.py` — Enhanced lifespan context manager
  - Better STARTUP logging
  - GRACEFUL SHUTDOWN on SIGTERM
  - Connection cleanup
  - Error handling

### 4. Deployment Automation
- ✅ `scripts/deploy_railway.sh` — Railway CLI deployment script
  - Authentication via RAILWAY_TOKEN
  - Docker build
  - Health check post-deployment
  - Automated checks

---

## 📋 Pendente (Próximos Passos)

### Phase 1: Railway Account Setup (0.5 day)
- [ ] Create Railway account (railway.app)
- [ ] Connect GitHub repository
- [ ] Create new project "b3-options-signals"
- [ ] Set environment variables in Railway console
  - SUPABASE_URL
  - SUPABASE_SERVICE_ROLE_KEY
  - NEXT_PUBLIC_SUPABASE_URL
  - NEXT_PUBLIC_SUPABASE_ANON_KEY
  - BRAPI_TOKEN
  - ALLOWED_ORIGINS=https://<railway-domain>
  - API_URL=https://<railway-api-domain>
  - NEXT_PUBLIC_API_URL=https://<railway-api-domain>

### Phase 2: Backend Deployment (1 day)
- [ ] Deploy backend to Railway staging
- [ ] Verify health endpoint (`GET /health` → 200)
- [ ] Test API endpoints
- [ ] Monitor logs for errors
- [ ] Verify graceful shutdown (SIGTERM test)

### Phase 3: Frontend Deployment (0.5 day)
- [ ] Deploy frontend to Railway (or keep on Render, test)
- [ ] Update NEXT_PUBLIC_API_URL in Railway env
- [ ] Test full flow (frontend → API → Supabase)
- [ ] Verify no CORS errors

### Phase 4: Cutover (0.5 day)
- [ ] Switch DNS/URLs to Railway
- [ ] Disable Render app (keep as backup)
- [ ] Disable cron-job.org keep-alive
- [ ] Monitor first 1 hour
- [ ] Update deployment docs

### Phase 5: Cleanup (0.5 day)
- [ ] Verify 24h stability
- [ ] Decommission Render (if all good)
- [ ] Archive deployment notes
- [ ] Update README

---

## 🔧 Configuration Ready

### railway.json
```json
{
  "build": { "builder": "dockerfile" },
  "deploy": {
    "startCommand": "uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT --workers 4",
    "healthchecks": {
      "startup": {
        "path": "/health",
        "initialDelaySeconds": 10,
        "timeoutSeconds": 30,
        "periodSeconds": 60
      }
    }
  }
}
```

### Dockerfile
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["sh", "-c", "uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

### Graceful Shutdown (main.py)
```python
# New enhanced lifespan:
# - STARTUP logging
# - GRACEFUL SHUTDOWN on SIGTERM
# - Scheduler shutdown
# - Connection cleanup
# - Error handling
```

---

## 🎯 Environment Variables for Railway

```
# Required (from .env.example)
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
BRAPI_TOKEN=

# Railway-specific
ALLOWED_ORIGINS=https://b3-options-signals.railway.app
API_URL=https://api.b3-options-signals.railway.app
NEXT_PUBLIC_API_URL=https://api.b3-options-signals.railway.app

# Optional
TELEGRAM_TOKEN=
REDIS_URL=
```

---

## 📊 Status Summary

| Component | Status | Notes |
|-----------|--------|-------|
| **Strategy** | ✅ Complete | 2-3 day timeline |
| **railway.json** | ✅ Ready | Health checks configured |
| **Dockerfile** | ✅ Ready | Python 3.12, optimized |
| **Graceful shutdown** | ✅ Ready | SIGTERM handler in place |
| **Deploy script** | ✅ Ready | Automated deployment |
| **Account setup** | 🟡 Pending | Requires manual Railway account |
| **Environment vars** | 🟡 Pending | Will configure in Railway console |
| **Backend deploy** | 🟡 Pending | After account setup |
| **Frontend deploy** | 🟡 Pending | After backend working |
| **Cutover** | 🟡 Pending | Final DNS/monitoring |
| **Cleanup** | 🟡 Pending | Render decommission |

---

## 🚀 Next Actions

### TODAY (if time permits)
1. Create Railway account
2. Connect GitHub repo to Railway
3. Set environment variables

### TOMORROW (2026-08-16)
1. Deploy backend (using `scripts/deploy_railway.sh`)
2. Test health endpoint
3. Verify graceful shutdown

### DAY 3 (2026-08-17)
1. Deploy frontend
2. Full integration test
3. Cutover & monitoring

---

## ⚠️ Blockers

- ⏳ Railway account creation (requires manual signup)
- ⏳ Supabase credentials (reuse from Render)
- ⏳ Domain setup (Railway provides subdomain by default)

---

## 📈 Benefits of Railway Over Render

| Feature | Render Free | Railway $7 | Gain |
|---------|------------|-----------|------|
| Hibernation | ❌ (50s) | ✅ (None) | Always-on ✓ |
| Cold starts | 45-50s | 0s | 50x faster ✓ |
| Keep-alive | Needed | Not needed | Simpler ✓ |
| Price | Free | $7/month | Negligible |
| Reliability | 99% | 99.9% | Better ✓ |

---

**Status:** 🟡 50% PRÉ-F0.0-I (preparation done, deployment pending)  
**Next:** Railway account + backend deployment  
**Timeline:** 2-3 days remaining (1-2 can be done today/tomorrow)  
**Risk:** 🟡 MEDIUM (infrastructure change, but well-prepared)

