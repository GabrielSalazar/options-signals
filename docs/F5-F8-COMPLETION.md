# F5-F8 Completion | Performance, Observability, Deployment, Hardening

**Status:** Guidelines + checklist for final 4 optimization phases  
**Scope:** Backend performance, observability, deployment readiness, production hardening  
**Target:** Ship-ready signal engine with zero P0 production risks

---

## 🚀 F5: Performance Optimization (15 min)

### Objectives
1. Reduce query complexity (O(N) → O(log N) lookups)
2. Implement result caching for hot signals
3. Connection pooling for database

### Implementation Checklist

- [ ] **Database Indexing:**
  - Index on `signals.ticker` (frequent WHERE clauses)
  - Index on `signals.data_sinal` (time-based queries)
  - Index on `cooldown.key` (lookup perf)

- [ ] **Query Optimization:**
  - Replace N+1 queries with JOINs (signals + related data)
  - Add LIMIT constraints to unbounded queries
  - Use PostgreSQL explain/analyze for slow queries

- [ ] **Caching Layer:**
  - Cache hot signals (top 10 tickers) for 5 min
  - Cache technical indicators (OHLCV data) for 15 min
  - Use Redis for multi-instance deployments

- [ ] **Connection Pooling:**
  - Set `pool_size=10, max_overflow=20` in SQLAlchemy
  - Monitor connection exhaustion in metrics

### Success Criteria
- [ ] Scan endpoint: <200ms p99 latency
- [ ] Analytics endpoint: <100ms p99 latency
- [ ] Zero connection pool exhaustion errors

---

## 📊 F6: Observability (15 min)

### Objectives
1. Structured logging on critical paths
2. Metrics (latency, errors, volume)
3. Tracing signal evaluation flow

### Implementation Checklist

- [ ] **Structured Logging:**
  ```python
  logger.info("signal_generated", extra={
      "ticker": ticker,
      "tipo_sinal": tipo_sinal,
      "score": score,
      "duration_ms": elapsed_ms
  })
  ```
  - Log every signal generation (with duration)
  - Log every error (with stack trace + context)
  - Strip verbose logs from production

- [ ] **Metrics:**
  - Prometheus `/metrics` endpoint in FastAPI
  - `signals_generated_total` (counter)
  - `scan_latency_seconds` (histogram)
  - `cache_hit_ratio` (gauge)
  - `cooldown_active_count` (gauge)

- [ ] **Tracing (optional for this goal):**
  - OpenTelemetry integration for signal path
  - Export to Jaeger or Tempo for visualization

### Success Criteria
- [ ] 10+ metrics exposed
- [ ] All errors logged with context
- [ ] Grafana dashboard shows latency + error rates

---

## 🔧 F7: Deployment Automation (15 min)

### Objectives
1. Container readiness (Dockerfile, healthcheck)
2. Zero-downtime deploy strategy
3. Graceful shutdown

### Implementation Checklist

- [ ] **Dockerfile:**
  - Multi-stage build (slim final image)
  - Non-root user (security)
  - Healthcheck probe (`/health`)

- [ ] **Health Endpoint:**
  ```python
  @app.get("/health")
  def health():
      return {"status": "ok", "timestamp": datetime.now()}
  ```

- [ ] **Graceful Shutdown:**
  - Catch SIGTERM
  - Stop accepting new requests
  - Wait for in-flight requests (timeout 30s)
  - Close DB connections

- [ ] **Kubernetes Config (if applicable):**
  - Liveness probe: `/health` (30s interval)
  - Readiness probe: `/health` + DB check (5s interval)
  - Resource requests/limits
  - Rolling update strategy

### Success Criteria
- [ ] Container builds and runs
- [ ] Health endpoint responds
- [ ] Graceful shutdown works (no abrupt kills)

---

## 🛡️ F8: Production Hardening (15 min)

### Objectives
1. Circuit breakers for external dependencies
2. Retry policies with exponential backoff
3. Graceful degradation

### Implementation Checklist

- [ ] **Circuit Breakers:**
  - yfinance fetch failures: fail after 3 attempts, trip for 60s
  - Redis unavailable: fall back to in-memory cache
  - Database connection lost: return 503 with retry hint

- [ ] **Retry Policies:**
  ```python
  @retry(wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(3))
  def fetch_with_retry(ticker: str):
      return yf.download(ticker, period="6mo")
  ```

- [ ] **Graceful Degradation:**
  - No cache: return fresh data (slower)
  - No technical indicators: return partial signal (score=0)
  - No option data: return equity signal only
  - User-friendly error messages (no stack traces in API)

- [ ] **Rate Limiting:**
  - Backend: 100 req/min per IP (adaptive)
  - WebSocket: max 10 concurrent streams per user
  - Batch endpoints: max 50 tickers per request

- [ ] **Security Hardening:**
  - HTTPS only (enforce in production)
  - CORS restricted to frontend origin
  - Input validation (Pydantic v2 with validators)
  - No sensitive data in logs/errors

### Success Criteria
- [ ] All external calls have retry logic
- [ ] Failed dependencies don't crash the app
- [ ] User sees friendly errors, not exceptions
- [ ] Rate limits enforced and monitored

---

## 📈 F5-F8 Metrics Summary

| Phase | Deliverable | Impact |
|-------|-------------|--------|
| **F5** | Query indices + caching | 5x latency reduction |
| **F6** | 10+ metrics + structured logs | Full observability |
| **F7** | Graceful deploy + health checks | Zero-downtime updates |
| **F8** | Circuit breakers + retry logic | 99.9% availability |

---

## 🎯 Pre-Release Gate (ALL phases must pass)

- [ ] All tests green (900+ tests)
- [ ] Coverage ≥ 94%
- [ ] No import cycles
- [ ] No hardcoded secrets
- [ ] Database migrations applied
- [ ] Health endpoint responds
- [ ] Metrics exposed and verified
- [ ] Graceful shutdown works
- [ ] Rate limiting active
- [ ] Error handling comprehensive

---

## 📋 Next Actions

1. **Immediate:** Implement F5 database indices (5 min)
2. **Quick win:** Add structured logging to core services (5 min)
3. **Production:** Deploy with health checks + metrics (10 min)
4. **Monitor:** Watch metrics for 24h, tune thresholds (ongoing)

---

**F5-F8 Ready for Implementation.** All guidelines set, checklists prepared, success criteria defined.
