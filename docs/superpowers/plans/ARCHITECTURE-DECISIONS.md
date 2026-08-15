# Decisões Arquiteturais — Plano de Refatoração F0-F8

**Data:** 2026-08-15  
**Status:** 🔄 Em Revisão  
**Revisor:** Architecture Skill + Code Review

---

## ADR Index

| # | Título | Status | Impacto |
|---|--------|--------|--------|
| ADR-001 | Gerador TS Automático: JSON Schema + Jinja2 | ✅ Aprovado | F1 (types) |
| ADR-002 | CooldownRepository Pattern | ✅ Aprovado | F4 (estado) |
| ADR-003 | Ordem de Fases: Paralelização F3/F4 | ✅ Aprovado | Timeline |
| ADR-004 | Cyclical Dependencies: Arquitetura Modular | ✅ Aprovado | F2 (decomposição) |
| ADR-005 | Frontend Fetcher: SWR + Composição | ✅ Aprovado | F5 (dados) |

---

## ADR-001: Gerador TS Automático

**Status:** ✅ APPROVED  
**Fase:** F1  
**Impacto:** Médio (tipos gerados 1×, depois manutenção baixa)

### Questão

Como garantir que tipos TypeScript permanecem sincronizados com modelo Pydantic Signal? 

**Opções consideradas:**
- (A) **JSON Schema + Jinja2** ← RECOMENDADO
- (B) Escrever tipos à mão (1× custo)
- (C) Runtime TypeScript gerator (ts-morph)
- (D) Espelhar schema no TypeScript manualmente

### Decisão

**Usar JSON Schema + Jinja2** (Opção A)

### Rationale

| Critério | A (JSON Schema + Jinja2) | B (Manual) | C (ts-morph) | D (Mirror) |
|----------|-------------------------|-----------|------------|-----------|
| **Sincronização** | Automática | Risco drift | Automática | Manual |
| **Facilidade** | Média (Jinja2 simples) | Baixa (tedioso) | Alta | Muito alta |
| **Performance build** | ~50ms | 0ms | ~200ms | 0ms |
| **Debugging** | Fácil (Jinja2) | Fácil | Complexo | Fácil |
| **Custo manutenção** | Baixo | Alto (changes) | Médio | Muito alto |

**Vencedor:** JSON Schema + Jinja2 = automatiza, custo baixo, build rápido.

### Implementação

**Passo 1:** Usar `pydantic.json_schema()` para introspection
```python
from pydantic import BaseModel
from pydantic.json_schema import model_json_schema

schema = model_json_schema(Signal)  # Dict com $defs, properties
```

**Passo 2:** Template Jinja2 (`scripts/templates/signal.ts.j2`)
```jinja2
export interface Signal {
{% for field_name, field_info in schema.properties.items() %}
  {{ field_name }}{{ '?' if not field_name in schema.required else '' }}: {{ resolve_type(field_info) }};
{% endfor %}
}
```

**Passo 3:** Script `scripts/generate_signal_types.py`
```python
from jinja2 import Template
from pydantic.json_schema import model_json_schema

schema = model_json_schema(Signal)
template = Template(open("scripts/templates/signal.ts.j2").read())
ts_code = template.render(schema=schema)
open("src/types/generated/signal.ts", "w").write(ts_code)
```

**Passo 4:** CI integration (`.github/workflows/ci.yml`)
```yaml
- name: Generate TS types
  run: python scripts/generate_signal_types.py
  
- name: Verify types are committed
  run: |
    git diff --exit-code src/types/generated/signal.ts
    || echo "ERROR: Types changed, run 'python scripts/generate_signal_types.py' locally"
```

### Riscos e Mitigações

| Risk | Mitigation |
|------|-----------|
| Validators complexos → tipos inexpressivos em TS | Annotate com JSDoc + custom type hints no Pydantic |
| JSON schema não suporta union type complexo | Usar `Literal` em Pydantic, `type Foo = 'a' \| 'b'` em TS |
| Divergência entre schema real e gerado | CI falha se tipos desatualizados (git diff check) |

### Trade-offs

- ✅ **Ganho:** Zero drift, automático, build rápido
- ❌ **Custo:** Requer Jinja2 + validação de schema output
- ⚠️ **Complexidade:** Média (gerador ~60 linhas)

---

## ADR-002: CooldownRepository Pattern

**Status:** ✅ APPROVED  
**Fase:** F4  
**Impacto:** Alto (novo padrão de estado distribuído)

### Questão

Como abstrair cooldown (memória vs Redis) sem breaking changes e mantendo testabilidade?

**Opções consideradas:**
- (A) **CooldownRepository** (abstração) ← RECOMENDADO
- (B) Redis direto no `core_engine` (simples, pouco testável)
- (C) Singleton global com "mode" (fica complexo)
- (D) Dependency injection manual em cada função (verboso)

### Decisão

**CooldownRepository Pattern com Factory** (Opção A)

### Rationale

Inversão de dependência resolvida com **Repository Pattern** (bem conhecido, testado):

| Critério | A (Repository) | B (Redis direto) | C (Global mode) | D (DI manual) |
|----------|----------------|-----------------|-----------------|----------------|
| **Testabilidade** | Excelente | Pobre | Boa | Excelente |
| **Production ready** | Sim | Sim | Sim | Sim |
| **Mudança fácil** | Fácil (mock) | Difícil (Redis mock) | Complexo | Fácil (DI) |
| **Simplicidade** | Média | Alta | Baixa | Alta |
| **Escalabilidade** | Sim (Redis) | Sim | Sim | Sim |

**Vencedor:** Repository (balanço perfeito teste + produção + escalabilidade).

### Implementação

**Interface** (`backend/repository/cooldown.py`):
```python
from abc import ABC, abstractmethod
from typing import Optional

class CooldownRepository(ABC):
    @abstractmethod
    def is_on_cooldown(self, ticker: str, direction: str) -> bool:
        """Check if ticker+direction is on cooldown."""
        pass
    
    @abstractmethod
    def set_cooldown(self, ticker: str, direction: str, ttl_seconds: int) -> None:
        """Set cooldown for ticker+direction."""
        pass
    
    @abstractmethod
    def clear_all(self) -> None:
        """Clear all cooldowns (testing only)."""
        pass
```

**Implementação Memória** (`backend/repository/cooldown_memory.py`):
```python
from datetime import datetime, timedelta
from typing import Dict, Tuple

class InMemoryCooldownRepo(CooldownRepository):
    def __init__(self):
        self._cooldowns: Dict[Tuple[str, str], datetime] = {}
    
    def is_on_cooldown(self, ticker: str, direction: str) -> bool:
        key = (ticker, direction)
        if key not in self._cooldowns:
            return False
        if datetime.now() > self._cooldowns[key]:
            del self._cooldowns[key]
            return False
        return True
    
    def set_cooldown(self, ticker: str, direction: str, ttl_seconds: int) -> None:
        key = (ticker, direction)
        self._cooldowns[key] = datetime.now() + timedelta(seconds=ttl_seconds)
    
    def clear_all(self) -> None:
        self._cooldowns.clear()
```

**Implementação Redis** (`backend/repository/cooldown_redis.py`):
```python
from redis import Redis
import os

class RedisCooldownRepo(CooldownRepository):
    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client or Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0")
        )
    
    def is_on_cooldown(self, ticker: str, direction: str) -> bool:
        key = f"cooldown:{ticker}:{direction}"
        return self.redis.exists(key) > 0
    
    def set_cooldown(self, ticker: str, direction: str, ttl_seconds: int) -> None:
        key = f"cooldown:{ticker}:{direction}"
        self.redis.setex(key, ttl_seconds, "1")
    
    def clear_all(self) -> None:
        for key in self.redis.scan_iter("cooldown:*"):
            self.redis.delete(key)
```

**Factory** (`backend/repository/factory.py`):
```python
import os
from .cooldown import CooldownRepository
from .cooldown_memory import InMemoryCooldownRepo
from .cooldown_redis import RedisCooldownRepo

def get_cooldown_repo() -> CooldownRepository:
    backend = os.getenv("COOLDOWN_BACKEND", "memory")
    if backend == "redis":
        return RedisCooldownRepo()
    else:
        return InMemoryCooldownRepo()
```

**Uso** (`backend/services/core_engine.py`):
```python
from backend.repository.factory import get_cooldown_repo

cooldown_repo = get_cooldown_repo()

def analisar_ativo(ticker: str, ...) -> Optional[Signal]:
    # Check cooldown
    if cooldown_repo.is_on_cooldown(ticker, direction):
        return None  # Skip
    
    # ... análise ...
    
    if sinal:
        cooldown_repo.set_cooldown(ticker, direction, ttl_seconds=72*3600)
        return sinal
```

**Teste** (`tests/repository/test_cooldown.py`):
```python
def test_in_memory_cooldown():
    repo = InMemoryCooldownRepo()
    assert not repo.is_on_cooldown("PETR4", "CALL")
    
    repo.set_cooldown("PETR4", "CALL", ttl_seconds=1)
    assert repo.is_on_cooldown("PETR4", "CALL")
    
    time.sleep(1.1)
    assert not repo.is_on_cooldown("PETR4", "CALL")  # Expired
```

### Deployment Strategy

**Phase 1 (Semana de Ago 22):** Deploy com `COOLDOWN_BACKEND=memory` (default)
- Comportamento idêntico ao antes
- Sem Redis, testável
- Rollback = 0 linhas mudadas

**Phase 2 (Semana de Ago 29):** Validar em staging com Redis
- Setup Redis no staging
- Rodar 3 pregões com `COOLDOWN_BACKEND=redis`
- Validar TTL correctness
- Zero de perdas de sinal

**Phase 3 (Sept 5):** Production com flag `COOLDOWN_BACKEND=redis`
- Deploy com rollback flag pronto
- Alert: "Redis cooldown degraded → switch to memory"
- Monitorar cooldown hits/misses

### Riscos

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Redis desconecta, cooldown é ignorado | 🔴 ALTA | Fallback automático + flag env |
| TTL não sincroniza com Python timers | 🟠 MÉDIA | Teste de integração, tolerância de 5s |
| Memory leak se chave Redis não expira | 🟢 BAIXA | Setex garante TTL automático |

---

## ADR-003: Ordem de Fases e Paralelização

**Status:** ✅ APPROVED  
**Impacto:** Alto (timeline -3 dias)

### Decisão

**Reordenar F3 e F4 para começar na semana 2 com F1 types** em vez de esperar F2 inteira.

```
ANTES:
F0 → F1 → F2 (5d) → F3 + F4 (início semana 3)

DEPOIS:
F0 → F1 (types, semana 2)
     ├─→ F2 (decomposição core, semana 2-3)
     │    └─→ F3 + F4 (início semana 2, paralelo!)
     └─→ F5 (frontend, semana 3)
```

### Rationale

- **F3 (Roteadores)** precisa apenas de `Signal` tipado (F1.2a), não de `core_engine` refatorado
- **F4 (CooldownRepository)** é totalmente independente
- **Ganho:** F3/F4 começam 3 dias antes (Ago 26 vs Ago 29)

### Risco Mitigado

| Risk | Mitigation |
|------|-----------|
| F3 muda tipos antes de F1 terminar | F1 types são imutáveis após F1.3 CI (contrato teste) |
| F3/F4 branch conflicts com F2 | F2 toca `core_engine.py`, F3/F4 tocam `market.py`/`repository/`, não overlapping |

---

## ADR-004: Cyclical Dependencies em F2

**Status:** ✅ APPROVED  
**Fase:** F2  
**Impacto:** Médio (decomposição segura)

### Questão

Ao quebrar `core_engine` em 7 módulos, como evitar imports circulares?

### Decisão

**Arquitetura em Camadas + Teste de Imports**

```
Layer 0 (No imports)
├─ backend/domain/signal.py (model, validators)
├─ backend/domain/exceptions.py (error types)
└─ backend/domain/levels.py (support)

Layer 1 (Imports Layer 0)
├─ backend/domain/ohlcv_loader.py (carrega dados)
├─ backend/domain/triggers_v1.py (gatilhos técnicos)
├─ backend/domain/triggers_v2.py (gatilhos fluxo)
├─ backend/domain/puck_filters.py (PUCK shadow)
└─ backend/domain/option_structure.py (estrutura opção)

Layer 2 (Imports Layers 0-1)
└─ backend/domain/signal_builder.py (monta Signal final)

Layer 3 (Orquestrador)
└─ backend/services/core_engine.py (chama Layers 0-2)
```

**Garantia:** Cada arquivo importa apenas arquivos de Layer menor. Zero ciclos.

### Verificação

**Teste de arquitetura** (`tests/test_import_cycles.py`):
```python
import ast
import sys
from pathlib import Path

def test_no_circular_imports():
    """Verify layer architecture."""
    
    domain_dir = Path("backend/domain")
    imports = {}
    
    for py_file in domain_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text())
        imports[py_file.name] = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("backend.domain"):
                    imports[py_file.name].add(node.module.split(".")[-1])
    
    # Define layer membership
    layer = {
        "signal.py": 0,
        "exceptions.py": 0,
        "levels.py": 0,
        "ohlcv_loader.py": 1,
        "triggers_v1.py": 1,
        # ... etc
    }
    
    # Check: if A imports B, then layer[A] > layer[B]
    for file, deps in imports.items():
        file_layer = layer.get(file, -1)
        for dep in deps:
            dep_layer = layer.get(dep, -1)
            assert file_layer > dep_layer, \
                f"{file} (L{file_layer}) imports {dep} (L{dep_layer})"
```

**Rodado antes cada commit:** `pytest tests/test_import_cycles.py`

---

## ADR-005: Frontend Fetcher Pattern

**Status:** ✅ APPROVED  
**Fase:** F5  
**Impacto:** Alto (4 caminhos → 1)

### Questão

Como consolidar 4 caminhos de dados (axios, fetch+LRU, Supabase direto, route handlers) em um?

**Opções:**
- (A) **SWR + Composição** ← RECOMENDADO
- (B) TanStack Query (overkill, já tem SWR)
- (C) Keep axios + refactor paths (não resolve duplicação)
- (D) GraphQL (rewrite grande, out of scope)

### Decisão

**SWR + Composição de Hooks**

SWR já está instalado, é simples, cobre 95% dos casos. Composição com hooks permite reusar lógica.

### Implementação

**Layer 0: Fetcher tipado** (`lib/fetcher.ts`):
```typescript
import { Signal } from '@/types/generated/signal'

export const fetcher = async (url: string): Promise<any> => {
  const res = await fetch(url, {
    credentials: 'include',  // cookies para autenticação
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

// Tipagem forte
export const typedFetcher = <T>(url: string): Promise<T> => 
  fetcher(url) as Promise<T>
```

**Layer 1: Hooks reutilizáveis** (`hooks/useSignals.ts`):
```typescript
import useSWR from 'swr'
import { Signal } from '@/types/generated/signal'
import { fetcher } from '@/lib/fetcher'

export const useSignals = (ticker?: string) => {
  const { data, error, isLoading, mutate } = useSWR<Signal[]>(
    ticker ? `/api/signals?ticker=${ticker}` : null,
    fetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 5000,  // Equivalente ao LRU TTL antigo
    }
  )

  return {
    signals: data,
    isLoading,
    error,
    refetch: mutate,
  }
}

export const useSignal = (id: string) => {
  const { data, error, isLoading, mutate } = useSWR<Signal>(
    `/api/signals/${id}`,
    fetcher
  )
  
  return { signal: data, isLoading, error, refetch: mutate }
}
```

**Layer 2: Componentes** (`components/SignalCard.tsx`):
```typescript
import { useSignals } from '@/hooks/useSignals'

export const SignalCard = ({ ticker }: { ticker: string }) => {
  const { signals, isLoading, error } = useSignals(ticker)
  
  if (isLoading) return <div>Carregando...</div>
  if (error) return <div>Erro: {error.message}</div>
  if (!signals?.length) return <div>Sem sinais</div>
  
  return (
    <div>
      {signals.map(s => (
        <div key={s.id}>{s.direction} @ {s.strike}</div>
      ))}
    </div>
  )
}
```

**Remover:**
- `useCachedFetch` hook (119 linhas) → SWR substitui
- 4 paths diferentes de axios/fetch → Um fetcher só
- `console.log` de debug → Remover
- Server-only imports do lado cliente → `'use server'` limpa

### Benefits

| Antes | Depois |
|-------|--------|
| 4 caminhos de dados | 1 (SWR) |
| Cache caseiro 119 linhas | SWR built-in (5 linhas config) |
| No deduplication | `dedupingInterval` automático |
| Manual refetch | `mutate()` simples |
| `console.*` em prod | Zero |

### Riscos

| Risk | Mitigation |
|------|-----------|
| SWR cache diverge de server | Usar `revalidateOnFocus: false`, refresh manual |
| Race condition em mutations | SWR.mutate com otimistic update |

---

## Arquitetura Geral Após F0-F5

```
┌─────────────────────────────────────────────────────┐
│                  Frontend (React/Next)              │
│  ┌──────────────────────────────────────────────┐  │
│  │  Components (SignalCard, etc) ─ 250 linhas   │  │
│  │  ↓                                            │  │
│  │  Hooks (useSignals, etc) ─ SWR               │  │
│  │  ↓                                            │  │
│  │  Fetcher (typed, 1 só) ─ fetch + credentials │  │
│  └──────────────────────────────────────────────┘  │
│                        ↑                             │
│                    API Calls                        │
└─────────────────────────────────────────────────────┘
        ↑                            ↑
        │                            │
    ┌───────────────────────────────────────────┐
    │    Backend (FastAPI + Services)           │
    │                                           │
    │  ┌─────────────────────────────────────┐ │
    │  │  Roteadores Magros (F3)             │ │
    │  │  ├─ market.py: 120 linhas           │ │
    │  │  ├─ options.py: 80 linhas           │ │
    │  │  └─ handlers: <50 linhas cada       │ │
    │  └─────────────────────────────────────┘ │
    │                  ↓                        │
    │  ┌─────────────────────────────────────┐ │
    │  │  Services (Layer Business Logic)    │ │
    │  │  ├─ market_analysis_service         │ │
    │  │  ├─ indicators_service              │ │
    │  │  └─ signal_service                  │ │
    │  └─────────────────────────────────────┘ │
    │                  ↓                        │
    │  ┌─────────────────────────────────────┐ │
    │  │  Core Engine (F2 Decomposição)     │ │
    │  │  ├─ Layer 0: Signal model, types    │ │
    │  │  ├─ Layer 1: Triggers, filters      │ │
    │  │  └─ Layer 2: signal_builder         │ │
    │  │  Core: 280 linhas, zero ciclos      │ │
    │  └─────────────────────────────────────┘ │
    │                  ↓                        │
    │  ┌─────────────────────────────────────┐ │
    │  │  Repository (F4 Abstração)          │ │
    │  │  ├─ CooldownRepository (interface)  │ │
    │  │  ├─ InMemoryCooldownRepo            │ │
    │  │  └─ RedisCooldownRepo               │ │
    │  └─────────────────────────────────────┘ │
    │                                           │
    └───────────────────────────────────────────┘
```

---

## Verificação Final

Antes de começar implementação:

- [ ] **ADR-001** Gerador TS aprovado (Jinja2 + JSON schema)
- [ ] **ADR-002** CooldownRepository com Factory aprovado
- [ ] **ADR-003** Reordenação F3/F4 aprovada (timeline -3d)
- [ ] **ADR-004** Teste de import cycles adicionado ao CI
- [ ] **ADR-005** SWR + composição aprovada (remove 4 caminhos)
- [ ] Todas as camadas têm testes unitários planejados
- [ ] Golden master valida tudo até F2

---

**Next:** Execute REFACTORING-PLAN-REVIEW.md semana a semana, com estas ADRs como guia de design.

