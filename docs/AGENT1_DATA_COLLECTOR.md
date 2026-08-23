# Agent 1: Data Collector

## 📋 Visão Geral

O **Agent 1 (Data Collector)** é o primeiro agente do pipeline MCP de 7 agentes. Sua responsabilidade é:

1. **Coletar dados históricos OHLC** de ativos B3 via yfinance
2. **Calcular indicadores técnicos** (RSI, MACD, ATR, Bollinger Bands)
3. **Normalizar e validar** qualidade dos dados
4. **Retornar JSON estruturado** para o próximo agente no pipeline

## 🏗️ Arquitetura

### Entrada Esperada

```python
{
    "strategy": "iron_condor_v2",           # Nome da estratégia
    "asset": "PETR4",                       # Ticker B3 (normalizado automaticamente)
    "date_range": {
        "start": "2024-01-01",              # YYYY-MM-DD
        "end": "2024-08-22"                 # YYYY-MM-DD
    },
    "indicators": ["rsi", "macd", "atr", "bb"],  # Indicadores a calcular
    "data_source": "yfinance"               # Fonte de dados (padrão)
}
```

### Saída Esperada

```json
{
    "ohlc": [
        {
            "date": "2024-01-01",
            "o": 28.50,
            "h": 28.75,
            "l": 28.40,
            "c": 28.65,
            "v": 1250000
        }
    ],
    "indicators": {
        "rsi": [45.2, 48.5, ...],
        "macd": {
            "line": [...],
            "signal": [...],
            "histogram": [...]
        },
        "atr": [0.35, 0.38, ...],
        "bb": {
            "upper": [...],
            "middle": [...],
            "lower": [...]
        }
    },
    "meta": {
        "asset": "PETR4",
        "source": "yfinance",
        "records_count": 504,
        "gaps_detected": 0,
        "data_quality_score": 0.98,
        "timestamp": "2024-08-22T15:30:45.123456"
    }
}
```

## 🔧 Implementação

### Estrutura de Arquivos

```
backend/
├─ agents/
│  ├─ mcp_agents/
│  │  ├─ __init__.py
│  │  ├─ base.py           # Base abstrata MCPAgent
│  │  └─ data_collector.py  # Agent 1: Data Collector
│
├─ domain/
│  └─ mcp_models.py         # Pydantic DTOs para pipeline
│
└─ core/
   └─ cache.py              # Cache com TTL (Redis + fallback)
```

### Componentes Principais

#### 1. **Base Class (MCPAgent)**

```python
class MCPAgent(ABC):
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa entrada e retorna saída."""
        pass
```

Cada agente do pipeline herda dessa classe e implementa `async process()`.

#### 2. **Data Collector Agent**

```python
class DataCollectorAgent(MCPAgent):
    def __init__(self):
        self.cache_ttl_success = 3600  # 1 hora
        self.cache_ttl_error = 60       # 1 minuto
        self.timeout = 10               # segundos
    
    async def process(self, input_data: Dict) -> Dict:
        # 1. Validar entrada (Pydantic)
        # 2. Fetch OHLC (yfinance + cache)
        # 3. Calcular indicadores (pandas_ta)
        # 4. Validar qualidade
        # 5. Retornar output
```

#### 3. **Pipeline Interno**

```
Input JSON
    ↓
Validação Pydantic (DataCollectorInput)
    ↓
Fetch OHLC (yfinance)
    - Com cache TTL 3600s (sucesso) / 60s (erro)
    - Normaliza colunas: Open, High, Low, Close, Volume
    - Async via loop.run_in_executor()
    ↓
Calcular Indicadores (pandas_ta)
    - RSI (length=14)
    - MACD (fast=12, slow=26, signal=9)
    - ATR (length=14)
    - Bollinger Bands (length=20, std=2.0)
    ↓
Validar Qualidade (0.0-1.0)
    - Penaliza gaps (até -20%)
    - Penaliza indicadores inválidos (até -10%)
    ↓
Output Dict com ohlc, indicators, meta
```

## 🧪 Testes

### Suite Completa

```bash
pytest tests/test_mcp_agents.py -v
```

### Testes Disponíveis

| Teste | Descrição | Status |
|-------|-----------|--------|
| `test_agent_initialization` | Inicializa com valores corretos | ✅ |
| `test_data_collector_input_validation` | Valida entrada com Pydantic | ✅ |
| `test_data_collector_fetch_petr4` | Busca dados reais de PETR4 | ✅ |
| `test_data_collector_complete_indicators` | Calcula 4 indicadores | ✅ |
| `test_data_collector_subset_indicators` | Permite subset de indicadores | ✅ |
| `test_data_collector_invalid_ticker` | Falha gracioso com ticker inválido | ✅ |
| `test_data_collector_invalid_date_range` | Falha gracioso com data range invertido | ✅ |
| `test_data_collector_ticker_normalization` | Normaliza ticker (maiúsculas, remove .SA) | ✅ |
| `test_cache_hit_on_repeated_call` | Cache funciona corretamente | ✅ |
| `test_quality_score_calculation` | Quality score 0.0-1.0 | ✅ |

### Executar Testes Específicos

```bash
# Apenas testes de PETR4
pytest tests/test_mcp_agents.py::TestDataCollectorAgent::test_data_collector_fetch_petr4 -v

# Apenas testes de cache
pytest tests/test_mcp_agents.py::TestDataCollectorCache -v

# Com output verbose
pytest tests/test_mcp_agents.py -v -s
```

## 📊 Indicadores Técnicos

### RSI (Relative Strength Index)

- **Período:** 14 dias
- **Interpretação:** 0-100, >70 sobrecomprado, <30 sobrevendido
- **Output:** Lista de floats

### MACD (Moving Average Convergence Divergence)

- **Parâmetros:** fast=12, slow=26, signal=9
- **Output:** Dict com 3 listas (line, signal, histogram)

### ATR (Average True Range)

- **Período:** 14 dias
- **Interpretação:** Volatilidade absoluta
- **Output:** Lista de floats

### Bollinger Bands

- **Período:** 20 dias
- **Desvio Padrão:** 2.0
- **Output:** Dict com 3 listas (upper, middle, lower)

## 🔐 Cache Strategy

### Cache Key

```
ohlc:{asset}:{start_date}:{end_date}
```

### TTL (Time To Live)

- **Sucesso:** 3600 segundos (1 hora) — Dados históricos não mudam
- **Erro:** 60 segundos (1 minuto) — Retry mais rápido em caso de falha temporária

### Fallback

Se Redis não está disponível, usa cache em memória com mesma TTL.

## 🚀 Uso em Produção

### Exemplo: Invocar via Async

```python
from backend.agents.mcp_agents.data_collector import DataCollectorAgent

agent = DataCollectorAgent()

input_data = {
    "strategy": "iron_condor_v2",
    "asset": "PETR4",
    "date_range": {"start": "2024-06-01", "end": "2024-08-22"},
    "indicators": ["rsi", "macd", "atr", "bb"]
}

output = await agent.process(input_data)
print(f"Coletou {output['meta']['records_count']} candles")
print(f"Quality: {output['meta']['data_quality_score']:.1%}")
```

### Exemplo: Com Loop de Múltiplos Ativos

```python
import asyncio

assets = ["PETR4", "VALE3", "ITUB4"]
tasks = []

for asset in assets:
    task = agent.process({
        "strategy": "test",
        "asset": asset,
        "date_range": {"start": "2024-06-01", "end": "2024-08-22"}
    })
    tasks.append(task)

# Executar em paralelo
results = await asyncio.gather(*tasks)
```

## 📈 Performance

### Benchmarks (Local)

| Ativo | Candles | Indicadores | Tempo Total | Com Cache |
|-------|---------|-------------|-------------|-----------|
| PETR4 | 58 | 4 | ~7s | ~50ms |
| VALE3 | 61 | 4 | ~7s | ~50ms |
| ITUB4 | 60 | 4 | ~6s | ~50ms |

### Otimizações

- ✅ Async/await para I/O (yfinance + cache)
- ✅ Cache com TTL para evitar refetches
- ✅ Executor para operações síncronas pesadas
- ✅ Lazy indicator calculation (apenas indicadores solicitados)

## 🔍 Debugging

### Logs

```python
import logging

logging.basicConfig(level=logging.DEBUG)

# Ativa logs de data_collector
logger = logging.getLogger("data_collector")
logger.setLevel(logging.DEBUG)
```

### Erros Comuns

| Erro | Causa | Solução |
|------|-------|---------|
| `ValueError: No data available for PETR4` | Ticker inválido ou sem dados | Verificar ticker B3 |
| `'DataFrame' object has no attribute 'ta'` | pandas_ta não importado | Adicionar `import pandas_ta` |
| `AttributeError: 'int' object has no attribute 'days'` | Cache corrompido | Limpar cache |

## 📚 Dependências

- `yfinance==0.2.43` — Fetch OHLC histórico
- `pandas==2.3.3` — Manipulação de data frames
- `pandas_ta==0.4.71b0` — Indicadores técnicos
- `pydantic==2.7.1` — Validação de entrada
- `pytest==9.0.3` — Testes
- `pytest-asyncio==0.24.0` — Suporte async em testes

## 🔗 Próximos Passos

Após Agent 1 validado:

- **Agent 2:** Hypothesis Generator (grid search de parâmetros)
- **Agent 3:** Backtest Engine (simula operações)
- **Agent 4:** Metrics Analyzer (calcula KPIs)
- **Agent 5:** Validator (threshold checks)
- **Agent 6:** Signal Generator (formata JSON)
- **Agent 7:** Signal Registry (storage + vector DB)

## 📝 Notas

- Ticker é normalizado automaticamente (maiúsculas, remove `.SA`)
- Data range pode ser invertida (retorna gracioso com output vazio)
- Quality score reflete confiabilidade dos dados (0.0-1.0)
- Indicadores são opcionais — especificar apenas os necessários

---

**Data Criação:** 2024-08-22  
**Status:** ✅ Concluído e Testado  
**Próximo:** Agent 2 - Hypothesis Generator
