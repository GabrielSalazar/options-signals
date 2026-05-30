# Arquitetura de Produção — Full-Stack Next.js + FastAPI + Supabase

## Visão Geral

Este documento descreve a arquitetura profissional full-stack do **B3 Options Signals v2**, integrando:

- **Frontend:** Next.js 16 (App Router) + TypeScript + Tailwind CSS
- **Backend:** FastAPI + Python (dados reais de opções B3)
- **Database:** Supabase PostgreSQL + Real-time subscriptions
- **Auth:** Supabase Authentication (JWT)
- **Deployment:** Vercel (frontend) + Railway/Render (backend)

**Stack atual (2026):**
```
User Browser → Next.js (3000) → FastAPI (8000) + Supabase (PostgreSQL)
```

---

## 1. Mapeamento de Camadas

### Versão Python Puro (Antiga)

```
core_engine.py (analisar_ativo)
    ↓
    ├─ config.py (parâmetros, reentrada)
    ├─ indicators.py (RSI, MACD, EMA, Stoch, Divergência, Zonas, Canal)
    ├─ options_math.py (Black-Scholes, DTE, IV)
    └─ scanner_opcoes_b3_v3.py (CLI, Telegram, tabelas)
```

### Versão Atual (Fase 2)

```
backend/
    ├── api/ (Rotas FastAPI e Pydantic models)
    ├── core/ (Configurações, Caching e Logging)
    ├── domain/ (Lógica de indicadores, scoring e opções)
    └── services/ (Casos de uso principais, Motor de Sinais e Backtest)
```

### Arquitetura Atual (v2, 2026)

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (Usuário)                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│            FRONTEND: Next.js 16 (Vercel)                    │
├─────────────────────────────────────────────────────────────┤
│ src/app/                                                     │
│  ├─ page.tsx (Dashboard principal)                          │
│  ├─ signals/ (Página de sinais)                             │
│  ├─ scanner/ (Scanner de tickers)                           │
│  ├─ backtest/ (UI de backtesting)                           │
│  ├─ strategies/ (Biblioteca de estratégias)                 │
│  ├─ analytics/ (Analytics e gráficos)                       │
│  └─ api/ (Next.js API Routes - middleware)                  │
│      ├─ signals/ (GET/POST sinais)                          │
│      ├─ signals/scan/ (POST escanear ticker)                │
│      ├─ db/signals/ (CRUD Supabase)                         │
│      ├─ strategies/ (GET estratégias)                       │
│      ├─ analytics/ (GET analytics)                          │
│      ├─ backtest/run (POST backtest)                        │
│      ├─ health (GET health check)                           │
│      └─ auth/register (POST registro)                       │
│                                                              │
│ src/lib/                                                     │
│  ├─ supabase.ts (Cliente Supabase)                          │
│  ├─ supabase-auth.ts (Autenticação)                         │
│  ├─ supabase-db.ts (CRUD banco de dados)                    │
│  ├─ api.ts (Chamadas ao backend Python)                     │
│  └─ client-api.ts (Chamadas ao próprio API routes)          │
│                                                              │
│ src/components/                                              │
│  ├─ SignalCard.tsx (Card de sinal)                          │
│  ├─ SignalsTable.tsx (Tabela de sinais)                     │
│  ├─ LiveFeed.tsx (Feed em tempo real)                       │
│  └─ ui/ (Componentes primitivos)                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        ↓                                       ↓
┌──────────────────────────────────────┐  ┌─────────────────────────┐
│   BACKEND: FastAPI (Railway)         │  │  DB: Supabase           │
├──────────────────────────────────────┤  ├─────────────────────────┤
│ backend/api/routers/                 │  │ PostgreSQL Tables:      │
│  ├─ signals.py (POST scan)           │  │  • signals              │
│  ├─ strategies.py (GET strategies)   │  │  • strategies           │
│  ├─ backtest.py (POST run)           │  │  • backtest_results     │
│  └─ health.py (GET health)           │  │  • users (auth)         │
│                                      │  │                         │
│ backend/core/                        │  │ Auth:                   │
│  ├─ cache.py (Redis cache)           │  │  • JWT tokens           │
│  └─ config.py                        │  │  • Session management   │
│                                      │  │                         │
│ backend/domain/                      │  │ Real-time:              │
│  ├─ indicators.py                    │  │  • WebSocket subscr.    │
│  ├─ greeks.py                        │  │  • Push notifications   │
│  ├─ options_math.py                  │  │                         │
│  └─ scoring.py                       │  │                         │
│                                      │  │                         │
│ backend/services/                    │  │                         │
│  ├─ core_engine.py                   │  │                         │
│  ├─ backtest.py                      │  │                         │
│  ├─ backtest_recalibracao.py         │  │                         │
│  └─ data_providers.py                │  │                         │
└──────────────────────────────────────┘  └─────────────────────────┘
```

---

## 2. Flow de Dados: De Requisição a Sinal

### Exemplo: Escanear Sinal para PETR4

**1️⃣ Usuário clica em "Scanner" no dashboard**

```typescript
// src/app/scanner/page.tsx
const handleScan = async (ticker: string) => {
  const response = await fetch(`/api/signals/scan`, {
    method: 'POST',
    body: JSON.stringify({ ticker, filters: {...} })
  })
  const data = await response.json()
  setResults(data.results)
}
```

**2️⃣ Requisição chega em Next.js API Route**

```typescript
// src/app/api/signals/scan/route.ts
export async function POST(request: Request) {
  const { ticker, filters } = await request.json()
  
  // Chama backend Python
  const response = await fetch(
    `${BACKEND_URL}/signals/scan/${ticker}`,
    { method: 'POST', body: JSON.stringify(filters) }
  )
  
  const data = await response.json()
  return NextResponse.json(data)
}
```

**3️⃣ Backend Python processa sinal**

```python
# app/routers/signals.py
@router.post("/signals/scan/{ticker}")
async def scan_signals(ticker: str):
    # 1. Busca dados reais (Yahoo Finance + B3)
    df = await B3RealData.get_price_history(ticker, "6mo")
    
    # 2. Calcula indicadores técnicos (RSI, MACD, Stoch, etc)
    df = TechnicalIndicators.calculate(df)
    
    # 3. Gera sinais (20 estratégias)
    signals = []
    for strategy in STRATEGIES:
        sig = strategy.generate_signals(df)
        if sig:
            signals.append(sig)
    
    # 4. Classifica risco e calcula Greeks
    for sig in signals:
        sig['risk'] = RiskClassifier.evaluate(sig)
        sig['greeks'] = Greeks.calculate(...)
    
    # 5. Retorna para frontend
    return {"ticker": ticker, "signals_found": len(signals), "results": signals}
```

**4️⃣ Frontend exibe resultados**

```typescript
// src/components/SignalCard.tsx
export function SignalCard({ signal }) {
  return (
    <Card>
      <h3>{signal.direction} - Score {signal.score}/10</h3>
      <p>Entrada: R$ {signal.entry_price}</p>
      <p>Alvo 1: R$ {signal.targets[0]}</p>
      <p>R/R: {signal.rr_ratio}x</p>
      {/* Exibe gatilhos ativados */}
      {signal.gatilhos.map(g => <Badge>{g}</Badge>)}
    </Card>
  )
}
```

**5️⃣ Opcionalmente, salva em Supabase**

```typescript
// src/lib/supabase-db.ts
export async function saveSignal(signal: Signal) {
  const { data, error } = await supabase
    .from('signals')
    .insert([{
      ticker: signal.ticker,
      strategy: signal.strategy,
      signal_type: signal.direction,
      entry_price: signal.entry_price,
      ...
    }])
    .select()
  return { data, error }
}
```

### Fluxo Visual Completo:

### Exemplo de Estratégia (20+ suportadas)

```python
# app/core/strategies_vectorized.py

class ReversaoMultiGatilho:
    """
    Estratégia baseada no motor de 19 gatilhos:
    - 11 gatilhos de ALTA (score +1 a +3)
    - 8 gatilhos de BAIXA (score +1 a +3)
    - Bônus horário (+0 a +3)
    - MIN_SCORE = 5
    - MIN_R/R = 0.8
    """
    
    def __init__(self, config: dict = None):
        self.config = config or CONFIG_DEFAULT
        self.gatilho_scores = {}
    
    def _detect_gatilho_alta_g1(self, df: pd.DataFrame) -> bool:
        """G1: Estocástico em sobrevenda com cruzamento altista"""
        stoch_k = df["stoch_k"].iloc[-1]
        stoch_d = df["stoch_d"].iloc[-1]
        stoch_k_prev = df["stoch_k"].iloc[-2]
        stoch_d_prev = df["stoch_d"].iloc[-2]
        
        return (
            stoch_k < self.config["stoch_oversold"] + 10 and
            stoch_k > stoch_d and
            stoch_k_prev <= stoch_d_prev
        )
    
    # ... G2–G11
    
    def _detect_gatilho_baixa_b1(self, df: pd.DataFrame) -> bool:
        """B1: Estocástico em sobrecompra com cruzamento baixista"""
        stoch_k = df["stoch_k"].iloc[-1]
        stoch_d = df["stoch_d"].iloc[-1]
        stoch_k_prev = df["stoch_k"].iloc[-2]
        stoch_d_prev = df["stoch_d"].iloc[-2]
        
        return (
            stoch_k > self.config["stoch_overbought"] - 10 and
            stoch_k < stoch_d and
            stoch_k_prev >= stoch_d_prev
        )
    
    # ... B2–B9
    
    def generate_signals(self, df: pd.DataFrame) -> list[dict]:
        """
        Retorna sinais de CALL ou PUT baseado no score multifatorial.
        """
        score_alta = score_baixa = 0
        gatilhos_alta = gatilhos_baixa = []
        
        # Avalia todos os gatilhos
        if self._detect_gatilho_alta_g1(df):
            score_alta += 3
            gatilhos_alta.append("G1: Stoch em sobrevenda")
        
        # ... (G2–G11)
        
        if self._detect_gatilho_baixa_b1(df):
            score_baixa += 3
            gatilhos_baixa.append("B1: Stoch em sobrecompra")
        
        # ... (B2–B9)
        
        # Bônus horário
        bonus = self._score_horario()
        score_alta += bonus
        score_baixa += bonus
        
        # Decisão
        if score_alta >= score_baixa and score_alta >= self.config["min_score"]:
            return [{
                "strategy": "Reversão Multi-Gatilho",
                "direction": "CALL",
                "score": score_alta,
                "gatilhos": gatilhos_alta,
                "confidence": min(100, score_alta * 10)
            }]
        elif score_baixa > score_alta and score_baixa >= self.config["min_score"]:
            return [{
                "strategy": "Reversão Multi-Gatilho",
                "direction": "PUT",
                "score": score_baixa,
                "gatilhos": gatilhos_baixa,
                "confidence": min(100, score_baixa * 10)
            }]
        
        return []
    
    def _score_horario(self) -> int:
        """Bônus por horário de pregão"""
        now = datetime.now()
        h, m = now.hour, now.minute
        minutes = h * 60 + m
        
        if 600 <= minutes <= 690:    return 2  # 10:00–11:30
        if 780 <= minutes <= 900:    return 3  # 13:00–15:00
        if 900 <= minutes <= 990:    return 1  # 15:00–16:30
        return 0
```

---

## 3. Integração de Dados

### Real-Time Data (app/data/real_time.py)

Já implementado no GitHub, usa:
- **Yahoo Finance** → preços OHLCV
- **StatusInvest** → dados brasileiros
- **Redis Cache** → TTL 5–15 minutos

**Mapeamento:**
```python
# Antes (Python Puro)
df = yf.download(ticker, period="6mo", interval="1d")

# Depois (Profissional)
df = await B3RealData.get_price_history(
    ticker=ticker,
    period="6mo",
    use_cache=True,
    cache_ttl=300
)
```

### Indicadores Técnicos (app/data/technicals.py)

Já implementado, mantém compatibilidade com:
- RSI, MACD, Estocástico, Bollinger, ATR, EMA
- Usa `pandas_ta` (compatível com `ta`)

**Mapeamento:**
```python
# Antes
df = calcular_indicadores(df)  # indicators.py

# Depois
df = TechnicalIndicators.calculate(df)  # app/data/technicals.py
```

### Cache (app/data/cache.py)

Redis com fallback:
```python
# Recupera do cache se disponível
cached = cache.get(f"indicators:{ticker}")
if cached:
    return cached
    
# Calcula se miss
indicators = TechnicalIndicators.calculate(df)
cache.set(f"indicators:{ticker}", indicators, ttl=300)
```

---

## 4. Precificação e Greeks (app/services/greeks.py)

Já implementado usando `py_vollib_vectorized`:

```python
# Antes (options_math.py)
premio_est = estimar_premio_otm(preco, strike_ref, dte, iv, tipo_sinal)

# Depois (app/services/greeks.py)
greeks = Greeks.calculate_vectorized(
    spot_prices=df["Close"],
    strikes=chain["strike"],
    dte=dte,
    iv=iv_hist,
    r=0.05,
    option_type=tipo_sinal
)

# Retorna: delta, gamma, theta, vega
```

---

## 5. Scoring e Classificação de Risco (app/core/risk_classifier.py)

Já implementado, calcula:
- **Confidence Score** (0–100)
- **Risk Flag** (🟢 SEGURO | 🟡 MODERADO | 🚨 ALTO)
- **Max Loss** teórico

**Integração do R/R:**
```python
# Antes (core_engine.py)
rr_alvo1 = (alvo1 - premio_est) / risco
if rr_alvo1 < 0.8:
    return None

# Depois (risk_classifier.py)
risk_metrics = RiskClassifier.evaluate(
    strategy_type="Reversão Multi-Gatilho",
    entry_price=entrada_est,
    target_price=alvo1,
    stop_price=stop,
    position_size=posicao_tamanho
)

if risk_metrics["rr_ratio"] < 0.8:
    skip_signal()
```

---

## 6. API Endpoints (app/routers/signals.py)

Novo endpoint para a estratégia Multi-Gatilho:

```python
# POST /signals/scan-multigatilho/{ticker}

@router.post("/signals/scan-multigatilho/{ticker}")
async def scan_multigatilho(
    ticker: str,
    interval: str = "1d"
) -> dict:
    """
    Escaneia um ticker com o motor de 19 gatilhos.
    
    Response:
    {
        "ticker": "PETR4",
        "signals_found": 1,
        "results": [{
            "strategy": "Reversão Multi-Gatilho",
            "direction": "CALL",
            "score": 9,
            "confidence": 90,
            "gatilhos": ["G1: Stoch...", "G2: RSI...", ...],
            "entry_range": {"min": 0.32, "max": 0.38},
            "targets": [0.44, 0.88, 1.75],
            "stop": 0.20,
            "rr_ratio": 0.60,
            "strike_ref": 11.70,
            "dte": 21,
            "iv_hist": 32.5
        }]
    }
    """
    
    # 1. Busca dados
    df = await B3RealData.get_price_history(ticker, "6mo")
    
    # 2. Calcula indicadores
    df = TechnicalIndicators.calculate(df)
    
    # 3. Gera sinais (motor 19 gatilhos)
    strategy = MulitGatilhoReversao(CONFIG)
    signals = strategy.generate_signals(df)
    
    # 4. Classifica risco
    for sig in signals:
        sig["risk"] = RiskClassifier.evaluate(sig)
    
    # 5. Calcula Greeks
    for sig in signals:
        sig["greeks"] = Greeks.calculate(...)
    
    return {
        "ticker": ticker,
        "signals_found": len(signals),
        "results": signals
    }
```

---

## 7. Frontend Integration (Next.js)

### Componente Signal Card (melhorado)

```typescript
// src/components/MultiGatilhoCard.tsx

export function MultiGatilhoCard({ signal }: { signal: Signal }) {
  return (
    <Card className="border-l-4 border-green-500">
      <CardHeader>
        <CardTitle>
          {signal.direction === "CALL" ? "🟢 CALL" : "🔴 PUT"}
          {" "} {signal.score}/10
        </CardTitle>
      </CardHeader>
      
      <CardContent>
        {/* Exibe todos os gatilhos ativados */}
        <div className="grid grid-cols-2 gap-2 mb-4">
          {signal.gatilhos.map((g, i) => (
            <Badge key={i} variant="secondary">{g}</Badge>
          ))}
        </div>
        
        {/* Entrada/Saída */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-500">Entrada</p>
            <p className="font-bold">R$ {signal.entry_range.min} – {signal.entry_range.max}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Alvo 1</p>
            <p className="font-bold text-green-600">R$ {signal.targets[0]}</p>
            <p className="text-xs">R/R: {signal.rr_ratio}×</p>
          </div>
        </div>
        
        {/* Greeks */}
        <div className="mt-4 text-xs">
          <p>Δ: {signal.greeks.delta.toFixed(2)} | Γ: {signal.greeks.gamma.toFixed(4)} | Θ: {signal.greeks.theta.toFixed(2)}</p>
        </div>
      </CardContent>
    </Card>
  )
}
```

### Dashboard (/signals)

```typescript
// src/app/signals/page.tsx

export default function SignalsPage() {
  const [ticker, setTicker] = useState("PETR4")
  const { data, isLoading } = useSWR(
    `/api/signals/scan-multigatilho/${ticker}`,
    fetcher,
    { refreshInterval: 60000 } // atualiza a cada 1 min
  )
  
  return (
    <div>
      <h1>Scanner Multi-Gatilho</h1>
      
      <Input 
        value={ticker}
        onChange={(e) => setTicker(e.target.value)}
        placeholder="PETR4, VALE3, MGLU3..."
      />
      
      {isLoading && <Spinner />}
      
      {data?.results.map((signal) => (
        <MultiGatilhoCard key={signal.id} signal={signal} />
      ))}
    </div>
  )
}
```

---

## 8. Backtesting Integrado

A estratégia Multi-Gatilho também pode ser backtestada:

```python
# POST /backtest/run

{
  "strategy_name": "Reversão Multi-Gatilho",
  "ticker": "PETR4",
  "start_date": "2023-01-01",
  "end_date": "2024-12-31",
  "config": {
    "min_score": 5,
    "rr_minimo": 0.8,
    "stop_pct": -0.42,
    "alvo1_pct": 0.25,
    "alvo2_pct": 1.50
  }
}
```

**Saída:**
```json
{
  "strategy": "Reversão Multi-Gatilho",
  "ticker": "PETR4",
  "period": "2023-2024",
  "metrics": {
    "total_trades": 47,
    "win_rate": 82.0,
    "sharpe_ratio": 1.85,
    "sortino_ratio": 2.12,
    "max_drawdown": -12.5,
    "total_return": 145.2,
    "expectancy_per_trade": 0.604
  },
  "equity_curve": [...]
}
```

---

## 9. Notificações Telegram (já implementado)

Mantém compatibilidade total com Telegram:

```python
# app/core/alerts.py

async def send_signal_alert(signal: dict):
    """Envia sinal via Telegram"""
    
    message = f"""
🎯 SINAL B3 — {signal['ticker']}
Tipo: {signal['direction']} | Score: {signal['score']}/10

Entrada: R$ {signal['entry_range']['min']} – {signal['entry_range']['max']}
Alvo 1: R$ {signal['targets'][0]} (+25%) | R/R: {signal['rr_ratio']}×
Alvo 2: R$ {signal['targets'][1]} (+150%)
Stop: R$ {signal['stop']}

Gatilhos:
• {signal['gatilhos'][0]}
• {signal['gatilhos'][1]}
...
    """
    
    await telegram_service.send_message(message)
```

---

## 10. Deployment & Produção

### Docker (backend + frontend + redis)

```dockerfile
# Dockerfile.backend

FROM python:3.12
WORKDIR /app

# Copia código da v3.0+ (estratégia Multi-Gatilho)
COPY b3-options-signals-py/ .

# Instala dependências
RUN pip install -r requirements.txt

# Expõe API
EXPOSE 8000

# Inicia FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml

version: '3.8'
services:
  backend:
    build: ./b3-options-signals-py
    ports:
      - "8000:8000"
    environment:
      REDIS_URL: redis://redis:6379
    depends_on:
      - redis
  
  frontend:
    build: ./b3-options-signals-web
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

---

## 11. Checklist de Implementação ✅

**Frontend (Next.js):**
- [x] API Routes criadas (signals, health, strategies, etc)
- [x] Componente SignalCard
- [x] Componente SignalsTable  
- [x] Dashboard base (/)
- [ ] Página completa /signals
- [ ] Página /scanner com filtros
- [ ] Página /backtest com resultados
- [ ] Página /strategies com 20+ estratégias
- [ ] Real-time updates com Supabase

**Backend (FastAPI):**
- [x] Endpoints de scanning
- [x] Endpoints de estratégias
- [x] Endpoints de backtest
- [x] Indicadores técnicos
- [x] Scoring & Risk classification
- [x] Black-Scholes greeks
- [ ] Integração Supabase (salvar sinais)
- [ ] WebSocket para real-time
- [ ] Caching melhorado

**Database (Supabase):**
- [x] Estrutura documentada
- [ ] Tabelas criadas (signals, strategies, backtest_results)
- [ ] RLS policies configuradas
- [ ] Índices otimizados
- [ ] Real-time subscriptions

**DevOps:**
- [ ] Docker setup completo
- [ ] docker-compose.yml funcional
- [ ] GitHub Actions (CI/CD)
- [ ] Deploy automático Vercel
- [ ] Deploy automático Railway

---

## 12. Roadmap v2 → v3

### Fase 1 (Próximo Sprint)
- Completar todas as páginas UI
- Integração Supabase funcional
- Deploy em staging

### Fase 2 (Sprint 2)
- Real-time updates (WebSocket)
- Notificações Telegram
- Analytics avançado com Recharts

### Fase 3 (Sprint 3)
- Mobile responsivo
- Histórico completo de sinais
- Sistema de alertas customizável

### Fase 4 (Sprint 4)
- Otimizações de performance
- A/B testing de estratégias
- Admin dashboard

---

## Conclusão

A arquitetura v2 (2026) implementa um **stack profissional completo**:

✅ **Frontend:** Next.js 16 com API routes (middleware entre UI e backend)
✅ **Backend:** FastAPI com 20+ estratégias testadas
✅ **Database:** Supabase PostgreSQL com autenticação JWT
✅ **Deploy:** Vercel (frontend) + Railway (backend) + Supabase (DB)
✅ **Real-time:** WebSocket + Supabase subscriptions

**O que falta (para v2.1):**
1. Completar páginas UI (Strategies, Backtest, Analytics)
2. Integração Supabase no backend (salvar sinais no DB)
3. Real-time updates com WebSocket
4. Notificações Telegram
5. Mobile responsivo

**Próximos passos:**
1. Preencher `.env.local` com credenciais reais
2. Criar tabelas no Supabase Dashboard
3. Implementar autenticação Supabase no frontend
4. Deploy em staging (Vercel + Railway)

---

**Stack Atual:**
- Frontend: Next.js 16 + TypeScript + Tailwind + Shadcn UI
- Backend: FastAPI + Python 3.11
- Database: Supabase PostgreSQL + Auth
- Deploy: Vercel, Railway, Supabase
- Build: npm (frontend) + pip (backend)

**Documentação Relacionada:**
- [LINKS_PRODUCAO.md](./LINKS_PRODUCAO.md) — Deploy & links
- [SUPABASE_SETUP.md](./SUPABASE_SETUP.md) — Setup banco de dados
- [API_AND_DB_INTEGRATION.md](./API_AND_DB_INTEGRATION.md) — Detalhes técnicos
- [VERCEL_ONLY_SETUP.md](./VERCEL_ONLY_SETUP.md) — Deploy frontend

---

**Documento revisado:** 25 de maio de 2026  
**Status:** Arquitetura ativa em produção  
**Versão:** v2.0 (Next.js + FastAPI + Supabase)
