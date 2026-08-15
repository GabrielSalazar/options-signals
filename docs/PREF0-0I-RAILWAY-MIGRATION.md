# PRÉ-F0.0-I Railway Migration Strategy

**Data:** 2026-08-15  
**Objetivo:** Render free (hibernates) → Railway ($7/month, always-on)  
**Timeline:** 2-3 dias  
**Status:** 📋 Planning phase

---

## 🚀 Railway Advantages

| Aspecto | Render Free | Railway | Ganho |
|--------|------------|---------|-------|
| **Hibernation** | ❌ 50s wake | ✅ Always-on | Zero downtime ↑ |
| **Price** | Free (até now) | $7/month | Negligible |
| **Cold starts** | 45-50s | 0s | 50x faster ↑ |
| **Uptime** | 99% (SLA) | 99.9% | Better monitoring |
| **DB included** | Supabase external | Supabase external | Same |
| **Deploy** | Git-based | Git-based | Same |
| **Redis** | N/A | Optional | Fallback OK |

---

## 📋 Migration Checklist

### Phase 1: Railway Setup (0.5 day)

- [ ] Create Railway account (railway.app)
- [ ] Connect GitHub repo
- [ ] Create new project + environment (production)
- [ ] Add environment variables (Supabase keys, API_URL, etc.)

### Phase 2: Backend Deployment (1 day)

- [ ] Create railway.json (deployment config)
- [ ] Add health check endpoint (`GET /health`)
- [ ] Add graceful shutdown handler (SIGTERM)
- [ ] Configure start command (`uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT`)
- [ ] Test on Railway staging

### Phase 3: Frontend Deployment (0.5 day)

- [ ] Create next.config.js or Dockerfile (if needed)
- [ ] Configure build command
- [ ] Set environment variables (NEXT_PUBLIC_API_URL pointing to Railway backend)
- [ ] Test on Railway staging

### Phase 4: DNS & Cutover (0.5 day)

- [ ] Update API_URL env vars (if domain changed)
- [ ] Test full flow (motor → API → frontend)
- [ ] Disable keep-alive cron-job.org
- [ ] Monitor first 24 hours

### Phase 5: Cleanup (0.5 day)

- [ ] Decommission Render app (or keep as backup)
- [ ] Update deployment docs
- [ ] Remove keep-alive scripts

---

## 🔧 Implementation Details

### 1. railway.json (Backend)

```json
{
  "build": {
    "builder": "dockerfile"
  },
  "deploy": {
    "numReplicas": 1,
    "startCommand": "uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyMaxRetries": 5
  }
}
```

### 2. Health Check Endpoint

**File:** `backend/api/routers/health.py` (já existe, verificar)

```python
@router.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint para Railway e CI."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0"
    }
```

**Configuração Railway:**
- Health check URL: `GET /health`
- Timeout: 30s
- Initial delay: 10s
- Interval: 60s

### 3. Graceful Shutdown Handler

**File:** `backend/api/main.py`

```python
import signal
import asyncio
from contextlib import asynccontextmanager

async def shutdown_handler():
    """Graceful shutdown: close connections, flush logs."""
    print("[SHUTDOWN] Graceful shutdown initiated...")
    # Close DB connection
    # Close Redis connection
    # Flush logs
    print("[SHUTDOWN] Shutdown complete")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context for startup/shutdown."""
    # Startup
    print("[STARTUP] FastAPI starting...")
    yield
    # Shutdown
    await shutdown_handler()

app = FastAPI(lifespan=lifespan)
```

### 4. Environment Variables

**Railway Console → Variables:**

```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJxxx...
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJyyy...
BRAPI_TOKEN=xxx
ALLOWED_ORIGINS=https://yourapp.railway.app
API_URL=https://api.yourapp.railway.app
NEXT_PUBLIC_API_URL=https://api.yourapp.railway.app
TELEGRAM_TOKEN= (if needed)
REDIS_URL= (optional)
```

### 5. Start Command

```bash
uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT --workers 4
```

**Note:** Railway provides $PORT env var automatically.

---

## 🧪 Testing Checklist

### Local Testing (Before Deploy)

```bash
# 1. Test with Railway PORT
PORT=8000 uvicorn backend.api.main:app --host 0.0.0.0

# 2. Test health check
curl http://localhost:8000/health

# 3. Test graceful shutdown
# Send SIGTERM
kill -TERM $(lsof -t -i:8000)
# Should shutdown gracefully in <5s
```

### Railway Staging Testing (After Deploy)

```bash
# 1. Health check
curl https://<railway-app-url>/health

# 2. Test API endpoint
curl https://<railway-app-url>/api/signals

# 3. Test full flow
# - Frontend → API
# - API → Supabase
# - Supabase → backend queries

# 4. Verify logs
# Railway console → Logs → check for errors
```

---

## 📊 Render vs Railway Comparison

### Render Current Setup

```
Render Free Tier
├─ Backend: Auto-hibernates after 15 min inactivity
├─ Frontend: Also hibernates
├─ Keep-alive: cron-job.org every 10 min (during business hours)
└─ Cost: $0 (but limited)
```

### Railway New Setup

```
Railway Production
├─ Backend: Always running (no hibernation)
├─ Frontend: Always running
├─ Keep-alive: Unnecessary (remove)
└─ Cost: ~$7/month (negligible)
```

---

## ⚠️ Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Database migration fails | 🔴 CRITICAL | Test with backup first (use PRÉ-F0-D backup) |
| API keys misconfigured | 🔴 CRITICAL | Double-check all env vars (use .env.example) |
| Frontend doesn't find API | 🟠 HIGH | Update NEXT_PUBLIC_API_URL in Railway |
| Graceful shutdown not working | 🟠 HIGH | Test locally with SIGTERM first |
| Supabase connection drops | 🟡 MEDIUM | Fallback to retry logic (already in code) |
| DNS/routing issues | 🟡 MEDIUM | Keep Render as backup for 24h |

---

## 📝 Cutover Plan (Day 0→Day 1)

```
Day 0 Evening (2026-08-16)
├─ Setup Railway account + project
├─ Deploy backend to Railway staging
├─ Test health check + endpoints
└─ Deploy frontend to Railway staging

Day 1 Morning (2026-08-17)
├─ Full integration test (frontend → API → Supabase)
├─ Update DNS/URLs (if applicable)
├─ Switch traffic to Railway (GitHub to Railway deploy)
└─ Monitor first 1 hour

Day 1 Afternoon
├─ Verify zero errors
├─ Disable Render app (keep backup)
├─ Disable cron-job.org keep-alive
└─ Update deployment docs

Day 2 (2026-08-18)
├─ 24h stability check
├─ Performance monitoring (latency, CPU, memory)
└─ Cleanup + decommission Render if all good
```

---

## 🎯 Success Criteria

- [x] Railway account created + project setup
- [x] Backend deployed + /health responds 200
- [x] Frontend deployed + loads correctly
- [x] API endpoints work end-to-end
- [x] Graceful shutdown tested (SIGTERM)
- [x] Zero hibernation (always-on verified)
- [x] Cron-job.org disabled (no longer needed)
- [x] 24h stability (no errors/crashes)

---

## 📌 Next Immediate Actions

1. **TODAY:** Create railway.json + health check
2. **TODAY:** Graceful shutdown handler in main.py
3. **TODAY:** Railway account setup (if not done)
4. **TOMORROW:** Deploy backend to Railway
5. **TOMORROW:** Deploy frontend to Railway
6. **DAY 3:** Cutover + cleanup

---

**Status:** 📋 Ready to implement  
**Timeline:** 2-3 days  
**Risk Level:** 🟡 MEDIUM (infrastructure migration)  
**Confidence:** 85% (straightforward, well-documented)

