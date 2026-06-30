# Melhorias Arquiteturais (pós-análise de código) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar os gaps críticos e de alto impacto identificados na análise arquitetural de 2026-06-30 (CI/CD inexistente, drift de schema do Supabase, RLS desabilitado, duplicação de lógica financeira Python×TS, dualidade frágil de gatilhos/score, débito de observabilidade/config) sem alterar o comportamento de produção fora do que cada task descreve explicitamente.

**Architecture:** Cada task é independente e testável isoladamente — não há uma "camada" sequencial como nos planos anteriores (Camada 0-2). Tasks de schema/Supabase (P0.2, P0.3, P0.4, P1.3, P1.5) exigem uma ação manual no Supabase Dashboard após o merge, seguindo a mesma disciplina já usada nas migrações 002-006. Tasks de código (a maioria) seguem TDD igual aos planos anteriores.

**Tech Stack:** Python/FastAPI/pytest (backend), Next.js/TypeScript/Vitest (frontend), Supabase/Postgres (dados), GitHub Actions (CI).

**Convenção de criticidade usada neste plano:**
- 🔴 **P0 — Crítico**: risco de segurança, integridade de dados, ou ausência de rede de proteção (CI). Fazer primeiro.
- 🟠 **P1 — Alto impacto**: bug silencioso real ou risco concreto de divergência de dados/comportamento.
- 🟡 **P2 — Médio impacto**: débito técnico que aumenta custo de manutenção, sem risco imediato de incidente.
- 🟢 **P3 — Baixo/médio**: qualidade/higiene, sem urgência.

**Convenção de dependência manual usada neste plano:**
- 🔧 **MANUAL** no cabeçalho da task = depois do merge, alguém precisa rodar algo fora do Claude Code (Supabase SQL Editor, configurar secret no GitHub, etc.) antes da mudança ter efeito real em produção. Isso é sinalizado explicitamente no Step final de cada task que precisar.
- Sem o marcador = a task é 100% autocontida (commit já é suficiente).

---

## Mapa de tasks por criticidade

| # | Task | Criticidade | Manual? |
|---|---|---|---|
| 1 | CI/CD básico (lint + testes + build) | 🔴 P0 | Sim (habilitar Actions no GitHub se desabilitado) |
| 2 | Reconstituir schema real de `signals` em migração versionada | 🔴 P0 | Sim (Supabase) |
| 3 | Habilitar RLS em todas as tabelas | 🔴 P0 | Sim (Supabase) |
| 4 | Migração formal das colunas órfãs (`book_until`, `greeks`, `score_ponderado`, `ponderado_passou`, `iv_mercado`) | 🔴 P0 | Sim (Supabase) |
| 5 | Teste de paridade Black-Scholes Python × TypeScript | 🟠 P1 | Não |
| 6 | Guard-rail de paridade gatilhos `core_engine` × `GATILHOS` | 🟠 P1 | Não |
| 7 | FK `trigger_outcomes.signal_id → signals.id` + CHECK constraints | 🟠 P1 | Sim (Supabase) |
| 8 | Corrigir migração `004` para idempotência | 🟠 P1 | Não |
| 9 | Investigar e decidir o destino do score ponderado (bug `vol_ratio`) | 🟠 P1 | Não |
| 10 | Repositório de acesso a dados (`SignalsRepository`) | 🟡 P2 | Não |
| 11 | `CONFIG` → Pydantic Settings com validação de schema | 🟡 P2 | Não |
| 12 | Consolidar hooks de fetch do frontend (`useCachedFetch`) | 🟡 P2 | Não |
| 13 | Agendar `cleanup_old_signals` no scheduler + retenção de `trigger_outcomes`/`iv_history` | 🟡 P2 | Não |
| 14 | Wrapper HTTP único com retry/timeout para `data_providers.py` | 🟡 P2 | Não |
| 15 | Lint Python (ruff) configurado e no CI | 🟢 P3 | Não |
| 16 | Dockerfile: healthcheck + usuário non-root | 🟢 P3 | Não |
| 17 | `.env.example` | 🟢 P3 | Não |
| 18 | Tipar `user`/`session` em `supabase-auth.ts` | 🟢 P3 | Não |
| 19 | Testes de componentes financeiros do frontend | 🟢 P3 | Não |

---

## 🔴 P0 — Crítico

### Task 1: CI/CD básico (lint + testes + build)

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Criar o workflow**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: python -m pytest tests/ -q --ignore=tests/test_market_analysis.py
      - run: python -m pytest tests/test_market_analysis.py -q -k "not test_analysis_dados_insuficientes_retorna_422" --no-header

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm ci
      - run: npm run lint
      - run: npm run test
      - run: npm run build
```

> Nota: o job `backend` roda `test_market_analysis.py` separado, excluindo `test_analysis_dados_insuficientes_retorna_422` (falha pré-existente e não relacionada, documentada em `melhorias-motor-sinais-v3` — não é desta task corrigi-la). Quando essa falha for corrigida separadamente, remover o `-k "not ..."` e juntar os dois `pytest` num só.

- [ ] **Step 2: Validar localmente o que o CI vai rodar**

Run: `python -m pytest tests/ -q --ignore=tests/test_market_analysis.py`
Expected: `605 passed` (ou número atual da suíte, sem failures)

Run: `npm run lint && npm run test && npm run build`
Expected: lint sem erros novos (a dívida de `any` pré-existente não bloqueia o lint hoje — confirmar rodando), testes Vitest passando, build do Next.js completando sem erro.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: adiciona pipeline de lint, testes e build (backend + frontend)"
```

- [ ] **Step 4 (🔧 MANUAL): habilitar Actions**

Depois do push, abrir a aba "Actions" do repositório no GitHub e confirmar que o workflow disparou no push para `main`. Se o repositório tiver Actions desabilitado por política da organização, habilitar em Settings → Actions → General.

---

### Task 2: Reconstituir schema real de `signals` em migração versionada

**Files:**
- Create: `supabase/migrations/007_signals_schema_completo.sql`

**Contexto:** `signals` nunca foi criada por uma migração — só existem `ALTER TABLE` incrementais (001, 002, 004, 006). Isso significa que reconstruir o banco do zero a partir do repositório não funciona. Esta task fecha esse gap documentando o `CREATE TABLE` retroativo com `IF NOT EXISTS` (não quebra o ambiente já existente, mas serve de fonte de verdade para qualquer ambiente novo).

- [ ] **Step 1 (🔧 MANUAL — pré-requisito): obter o schema real**

No Supabase Dashboard → SQL Editor, rodar e copiar o resultado:

```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'signals'
ORDER BY ordinal_position;
```

Colar o resultado numa mensagem para quem for executar esta task — sem isso, o `CREATE TABLE` do Step 2 não pode ser escrito com precisão (não adivinhe tipos/nullability).

- [ ] **Step 2: Escrever a migração com base no schema real coletado**

Usar o resultado do Step 1 para preencher `supabase/migrations/007_signals_schema_completo.sql`. Esqueleto mínimo a partir do que já se sabe pelo código (`signal_service.py`, `outcome_service.py`, `routers/signals.py`) — ajustar tipos/nullability conforme o Step 1:

```sql
CREATE TABLE IF NOT EXISTS signals (
    id                      BIGSERIAL PRIMARY KEY,
    ticker                  TEXT NOT NULL,
    tipo_sinal              TEXT NOT NULL,
    direcao                 TEXT,
    "timestamp"             TIMESTAMPTZ NOT NULL DEFAULT now(),
    score                   INTEGER,
    score_tecnico           INTEGER,
    bonus_sessao            INTEGER,
    preco_acao              NUMERIC,
    gatilhos                TEXT[],
    -- Camada 1 (IV)
    hv_20d                  NUMERIC,
    iv_impl                 NUMERIC,
    iv_source               TEXT,
    iv_rank                 NUMERIC,
    iv_premium              NUMERIC,
    iv_filter_decisao       TEXT,
    -- Camada 2 (motor de score)
    gatilhos_ids            TEXT[],
    familias_ativas         INTEGER,
    score_familias_capped   INTEGER,
    consenso_decisao        TEXT,
    setup                   TEXT,
    setup_params_shadow     JSONB,
    -- score ponderado (shadow)
    score_ponderado         NUMERIC,
    ponderado_passou        BOOLEAN,
    -- estrutura de opção / acompanhamento de book
    book_until              TIMESTAMPTZ,
    greeks                  JSONB,
    iv_mercado              NUMERIC
);

CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals (ticker);
CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals ("timestamp");
```

> Se o Step 1 revelar colunas além dessas (ou tipos diferentes), ajustar este `CREATE TABLE` para bater exatamente com a realidade antes de commitar — o objetivo é eliminar o drift, não criar um novo.

- [ ] **Step 3: Validar que a migração roda limpa contra um Postgres novo**

Run (requer Docker e `psql`/`supabase` CLI local, ou um Postgres descartável):
```bash
docker run --rm -d --name pg-test -e POSTGRES_PASSWORD=test -p 5433:5432 postgres:15
sleep 3
psql postgresql://postgres:test@localhost:5433/postgres -f supabase/migrations/007_signals_schema_completo.sql
```
Expected: `CREATE TABLE`, `CREATE INDEX` sem erro.

Run: `docker stop pg-test`

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/007_signals_schema_completo.sql
git commit -m "chore(db): adiciona migration 007 reconstituindo schema completo de signals (fecha drift)"
```

- [ ] **Step 5 (🔧 MANUAL): aplicar no Supabase**

Como `signals` já existe no ambiente real, o `CREATE TABLE IF NOT EXISTS` é um no-op seguro lá — mas ainda assim, rodar a migração `007` no SQL Editor do Supabase Dashboard para registro formal e para validar que o `IF NOT EXISTS` realmente não tenta recriar nada quebrado. Confirmar com `\d signals` (ou a UI de Table Editor) que nenhuma coluna sumiu.

---

### Task 3: Habilitar RLS em todas as tabelas

**Files:**
- Create: `supabase/migrations/008_enable_rls.sql`

**Contexto:** nenhuma tabela tem Row Level Security habilitado. O backend usa a `service_role` key (que ignora RLS), então isso só é avaliado como crítico se a `anon` key for usada em algum lugar do frontend — verificar isso é o primeiro passo desta task.

- [ ] **Step 1: Confirmar se a `anon` key é usada client-side**

Run: `grep -rn "NEXT_PUBLIC_SUPABASE" src/`

Se aparecer uso de `NEXT_PUBLIC_SUPABASE_ANON_KEY` em algum client component que faz query direta ao Supabase (não via API route do Next.js), a exposição é real e esta task é urgente. Se o frontend só fala com o backend FastAPI (que usa `service_role`) e a `anon` key só aparece em auth (login/sessão, não em queries de tabela), o risco é menor mas a RLS continua sendo defesa em profundidade recomendada.

- [ ] **Step 2: Escrever a migração habilitando RLS com policy permissiva para `service_role`**

```sql
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE trigger_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE iv_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE telegram_config ENABLE ROW LEVEL SECURITY;

-- service_role ignora RLS por padrão, mas a policy abaixo documenta a intenção
-- e cobre o caso de alguém futuramente usar a chave anon contra essas tabelas.
CREATE POLICY service_role_full_access ON signals
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_full_access ON trigger_outcomes
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_full_access ON iv_history
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_full_access ON telegram_config
  FOR ALL TO service_role USING (true) WITH CHECK (true);
```

> Se o Step 1 confirmar uso de `anon` key para leitura pública legítima (ex.: frontend lê `signals` direto), adicionar uma policy adicional `FOR SELECT TO anon USING (true)` na(s) tabela(s) específica(s) — não fazer isso por padrão em todas, para não reabrir a superfície de exposição sem necessidade confirmada.

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/008_enable_rls.sql
git commit -m "chore(db): adiciona migration 008 habilitando RLS em todas as tabelas"
```

- [ ] **Step 4 (🔧 MANUAL): aplicar no Supabase e validar**

Rodar no SQL Editor do Supabase Dashboard. Depois, testar que o backend (usando `service_role`) continua funcionando normalmente: `python -m pytest tests/test_signal_service.py tests/test_outcome_service.py -q` localmente não pega isso (são mocks) — validar rodando um scan real contra o Supabase de fato (`POST /scan` num ambiente de staging, se existir, ou um teste manual pontual) para confirmar que `service_role` realmente segue inserindo/lendo sem ser bloqueado pela RLS.

---

### Task 4: Migração formal das colunas órfãs

**Files:**
- Modify: nenhum arquivo de código (esta task só formaliza schema já em uso)
- (Já coberta pela Task 2 se o `CREATE TABLE` em `007` incluir `book_until`, `greeks`, `score_ponderado`, `ponderado_passou`, `iv_mercado` — ver Step 2 da Task 2.)

- [ ] **Step 1: Confirmar que a Task 2 já cobriu essas 5 colunas**

Run: `grep -E "book_until|greeks|score_ponderado|ponderado_passou|iv_mercado" supabase/migrations/007_signals_schema_completo.sql`

Expected: as 5 colunas aparecem.

Se a Task 2 ainda não foi feita ou o `CREATE TABLE` ficou incompleto, esta task vira: adicionar um `ALTER TABLE signals ADD COLUMN IF NOT EXISTS` para cada uma que faltar, num novo arquivo `supabase/migrations/009_colunas_orfas.sql`, seguindo o mesmo padrão das migrações 002/004/006. Caso a Task 2 já cubra tudo, **esta task não precisa de nenhum arquivo novo** — apenas marque como concluída referenciando a Task 2.

---

## 🟠 P1 — Alto impacto

### Task 5: Teste de paridade Black-Scholes Python × TypeScript

**Files:**
- Create: `tests/test_black_scholes_parity.py`
- Reference: `backend/domain/options_math.py`, `backend/domain/greeks.py`, `src/lib/black-scholes.ts`

**Contexto:** Python e TypeScript implementam Black-Scholes/gregas independentemente. Sem teste cruzado, as duas implementações podem divergir silenciosamente (ex.: `PayoffChart.tsx` busca do backend, `GreeksCalculator.tsx` calcula no client — podem mostrar valores diferentes). Como rodar TS dentro de um teste pytest não é direto, a estratégia é: gerar um vetor de casos fixos em Python, computar com a lib Python, e comparar contra valores de referência calculados manualmente (ou via uma chamada Node ao módulo TS) — abaixo a abordagem mais simples e robusta: rodar o `black-scholes.ts` via Node a partir do teste Python, usando `subprocess`.

- [ ] **Step 1: Criar um script Node standalone que expõe o cálculo TS via stdin/stdout JSON**

```typescript
// scripts/bs_parity_cli.ts
// Uso: echo '{"s":100,"k":105,"t":0.5,"r":0.1065,"sigma":0.3,"type":"call"}' | npx tsx scripts/bs_parity_cli.ts
import { blackScholes, greeks } from "../src/lib/black-scholes";

const input = JSON.parse(require("fs").readFileSync(0, "utf-8"));
const price = blackScholes(input.s, input.k, input.t, input.r, input.sigma, input.type);
const g = greeks(input.s, input.k, input.t, input.r, input.sigma, input.type);
console.log(JSON.stringify({ price, ...g }));
```

> Antes de escrever este arquivo, ler `src/lib/black-scholes.ts` para confirmar os nomes exatos exportados (`blackScholes`, `greeks` são placeholders de nome — usar os nomes reais de função/assinatura do arquivo). Ajustar o script para chamar exatamente o que existe.

- [ ] **Step 2: Escrever o teste de paridade em Python**

```python
import json
import subprocess
import pytest
from backend.domain.options_math import black_scholes_price  # ajustar para o nome real
from backend.domain.greeks import calcular_gregas  # ajustar para o nome real

CASOS = [
    {"s": 100.0, "k": 105.0, "t": 0.5, "r": 0.1065, "sigma": 0.30, "type": "call"},
    {"s": 100.0, "k": 95.0, "t": 0.25, "r": 0.1065, "sigma": 0.45, "type": "put"},
    {"s": 50.0, "k": 50.0, "t": 0.0833, "r": 0.1065, "sigma": 0.60, "type": "call"},
]


def _rodar_ts(caso: dict) -> dict:
    proc = subprocess.run(
        ["npx", "tsx", "scripts/bs_parity_cli.ts"],
        input=json.dumps(caso),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.parametrize("caso", CASOS)
def test_preco_bs_paridade_python_typescript(caso):
    preco_py = black_scholes_price(
        caso["s"], caso["k"], caso["t"], caso["r"], caso["sigma"], caso["type"]
    )
    resultado_ts = _rodar_ts(caso)
    assert preco_py == pytest.approx(resultado_ts["price"], rel=1e-3)
```

- [ ] **Step 3: Rodar e ajustar nomes/assinaturas reais**

Run: `python -m pytest tests/test_black_scholes_parity.py -v`

Esperado na primeira tentativa: provavelmente `ImportError`/`AttributeError` por nomes incorretos — ler `backend/domain/options_math.py`/`backend/domain/greeks.py`/`src/lib/black-scholes.ts` de fato e ajustar os Steps 1-2 para usar as assinaturas reais antes de seguir. Não prosseguir até o teste rodar com os nomes corretos (mesmo que ainda falhe por divergência real de valores — esse é o sinal que a task busca capturar).

- [ ] **Step 4: Se houver divergência real, documentar (não corrigir nesta task)**

Se `test_preco_bs_paridade_python_typescript` falhar por divergência de valor (não por erro de assinatura), isso é uma descoberta real — registrar a diferença encontrada (qual caso, qual delta) num comentário no teste com `pytest.mark.xfail(reason="...")` temporário, e abrir isso como achado para o usuário decidir prioridade de correção (fora do escopo mecânico desta task, que é instrumentar a detecção, não necessariamente corrigir a fórmula divergente).

- [ ] **Step 5: Commit**

```bash
git add tests/test_black_scholes_parity.py scripts/bs_parity_cli.ts
git commit -m "test: adiciona guarda de paridade Black-Scholes entre Python e TypeScript"
```

---

### Task 6: Guard-rail de paridade gatilhos `core_engine` × `GATILHOS`

**Files:**
- Test: `tests/test_scoring.py`
- Reference: `backend/services/core_engine.py` (`_avaliar_gatilhos`), `backend/domain/scoring.py` (`GATILHOS`)

**Contexto:** os 20 IDs de gatilho (G1-G11, B1-B9) existem soltos como literais string em `core_engine.py::_avaliar_gatilhos` e como chaves do dict `GATILHOS` em `scoring.py`. Se alguém adicionar um gatilho num lugar e esquecer o outro, `calcular_familias` ignora silenciosamente. Esta task adiciona um teste que falha se os dois conjuntos divergirem.

- [ ] **Step 1: Extrair os IDs literais usados em `_avaliar_gatilhos` via regex sobre o código-fonte**

```python
# tests/test_scoring.py (adicionar ao arquivo existente)
import inspect
import re

from backend.domain.scoring import GATILHOS
from backend.services import core_engine


def test_paridade_ids_avaliar_gatilhos_vs_registro_gatilhos():
    """Todo ID 'append'ado em ids_alta/ids_baixa dentro de _avaliar_gatilhos
    precisa existir como chave em GATILHOS — senão calcular_familias()
    o ignora silenciosamente (scoring.py: "if not info: continue")."""
    codigo = inspect.getsource(core_engine._avaliar_gatilhos)
    ids_no_codigo = set(re.findall(r'ids_(?:alta|baixa)\.append\("([GB]\d+)"\)', codigo))

    assert ids_no_codigo, (
        "Regex não encontrou nenhum ID — _avaliar_gatilhos pode ter mudado de "
        "formato (ex.: append deixou de usar string literal direta). Ajustar a regex."
    )
    faltando_no_registro = ids_no_codigo - set(GATILHOS.keys())
    assert not faltando_no_registro, (
        f"IDs disparados em _avaliar_gatilhos mas ausentes do registro GATILHOS: "
        f"{faltando_no_registro}. Adicione-os em backend/domain/scoring.py::GATILHOS "
        f"com sua família e pontuação."
    )
```

- [ ] **Step 2: Rodar e confirmar que passa hoje (baseline correto)**

Run: `python -m pytest tests/test_scoring.py::test_paridade_ids_avaliar_gatilhos_vs_registro_gatilhos -v`
Expected: `PASSED` (os 20 IDs já estão em paridade, conforme a análise confirmou — este teste é uma trava para o futuro, não uma correção de bug atual).

- [ ] **Step 3: Validar que o teste realmente pega regressão (sanity check manual)**

Temporariamente remova uma entrada de `GATILHOS` (ex.: comente a linha de `"G1"`) e rode o teste de novo — deve falhar com a mensagem do `assert`. Reverta a alteração depois.

Run: `python -m pytest tests/test_scoring.py::test_paridade_ids_avaliar_gatilhos_vs_registro_gatilhos -v`
Expected (com `G1` removido): `FAILED` com a mensagem listando `{'G1'}`.

Reverter a remoção antes do commit.

- [ ] **Step 4: Commit**

```bash
git add tests/test_scoring.py
git commit -m "test(score): adiciona guarda de paridade entre gatilhos disparados e registro GATILHOS"
```

---

### Task 7: FK `trigger_outcomes.signal_id → signals.id` + CHECK constraints

**Files:**
- Create: `supabase/migrations/010_constraints_integridade.sql`

- [ ] **Step 1: Escrever a migração**

```sql
-- FK: trigger_outcomes não deve sobreviver à exclusão do signal pai.
ALTER TABLE trigger_outcomes
  ADD CONSTRAINT fk_trigger_outcomes_signal
  FOREIGN KEY (signal_id) REFERENCES signals(id) ON DELETE CASCADE;

-- CHECK constraints em campos categóricos (evita typos silenciosos).
ALTER TABLE signals
  ADD CONSTRAINT chk_tipo_sinal CHECK (tipo_sinal IN ('CALL', 'PUT')),
  ADD CONSTRAINT chk_consenso_decisao CHECK (consenso_decisao IS NULL OR consenso_decisao IN ('passaria', 'bloquearia')),
  ADD CONSTRAINT chk_setup CHECK (setup IS NULL OR setup IN ('REVERSAO', 'CONTINUACAO', 'HIBRIDO'));

ALTER TABLE trigger_outcomes
  ADD CONSTRAINT chk_resultado_final CHECK (
    resultado_final IN ('alvo1', 'alvo2', 'alvo_final', 'stop', 'expirou', 'aberto', 'indeterminado')
  );
```

> Antes de aplicar: rodar a query de validação do Step 2 para garantir que não há dados existentes que violem essas constraints (senão o `ALTER TABLE ADD CONSTRAINT` falha).

- [ ] **Step 2 (🔧 MANUAL — pré-requisito): validar dados existentes não violam as constraints**

No SQL Editor do Supabase, antes de aplicar a migração:

```sql
SELECT DISTINCT tipo_sinal FROM signals WHERE tipo_sinal NOT IN ('CALL', 'PUT');
SELECT DISTINCT consenso_decisao FROM signals WHERE consenso_decisao IS NOT NULL AND consenso_decisao NOT IN ('passaria', 'bloquearia');
SELECT DISTINCT setup FROM signals WHERE setup IS NOT NULL AND setup NOT IN ('REVERSAO', 'CONTINUACAO', 'HIBRIDO');
SELECT DISTINCT resultado_final FROM trigger_outcomes WHERE resultado_final NOT IN ('alvo1', 'alvo2', 'alvo_final', 'stop', 'expirou', 'aberto', 'indeterminado');
SELECT to.signal_id FROM trigger_outcomes to LEFT JOIN signals s ON s.id = to.signal_id WHERE s.id IS NULL;
```

Se qualquer uma retornar linhas, ajustar a migração do Step 1 (ou limpar os dados órfãos/divergentes) antes de aplicar — não aplicar a migração com dados violadores, ela vai falhar.

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/010_constraints_integridade.sql
git commit -m "chore(db): adiciona migration 010 com FK trigger_outcomes->signals e CHECK constraints"
```

- [ ] **Step 4 (🔧 MANUAL): aplicar no Supabase**

Rodar no SQL Editor após confirmar o Step 2. Validar com um insert de teste que viole uma constraint (ex.: `INSERT INTO signals (ticker, tipo_sinal) VALUES ('TEST', 'INVALIDO')`) e confirmar que o Postgres rejeita.

---

### Task 8: Corrigir migração `004` para idempotência

**Files:**
- Modify: `supabase/migrations/004_camada1_iv_signals.sql`

**Contexto:** `ALTER TABLE signals RENAME COLUMN iv_hist TO hv_20d` falha se rodado duas vezes (a coluna `iv_hist` não existe mais na segunda execução). Isso quebra a premissa de que toda migração pode ser reaplicada com segurança.

- [ ] **Step 1: Ler a migração atual**

Run: `cat supabase/migrations/004_camada1_iv_signals.sql`

- [ ] **Step 2: Substituir o `RENAME COLUMN` direto por um bloco condicional idempotente**

Trocar a linha:
```sql
ALTER TABLE signals RENAME COLUMN iv_hist TO hv_20d;
```//
por:
```sql
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'signals' AND column_name = 'iv_hist'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'signals' AND column_name = 'hv_20d'
  ) THEN
    ALTER TABLE signals RENAME COLUMN iv_hist TO hv_20d;
  END IF;
END $$;
```

- [ ] **Step 3: Validar que o arquivo continua sintaticamente válido**

Run (contra um Postgres descartável, igual à Task 2):
```bash
docker run --rm -d --name pg-test2 -e POSTGRES_PASSWORD=test -p 5434:5432 postgres:15
sleep 3
psql postgresql://postgres:test@localhost:5434/postgres -c "CREATE TABLE signals (iv_hist NUMERIC);"
psql postgresql://postgres:test@localhost:5434/postgres -f supabase/migrations/004_camada1_iv_signals.sql
psql postgresql://postgres:test@localhost:5434/postgres -f supabase/migrations/004_camada1_iv_signals.sql
docker stop pg-test2
```
Expected: a segunda execução não falha (idempotência confirmada) — antes da correção, a segunda chamada falharia com `column "iv_hist" does not exist`.

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/004_camada1_iv_signals.sql
git commit -m "fix(db): torna RENAME COLUMN da migration 004 idempotente"
```

> Não é necessário reaplicar no Supabase — a migração já foi executada uma vez lá (rename já aconteceu). Esta correção é para proteger qualquer ambiente futuro/novo que rode as migrações do zero em sequência.

---

### Task 9: Investigar e decidir o destino do score ponderado (bug `vol_ratio`)

**Files:**
- Investigate: `backend/services/core_engine.py` (`_avaliar_gatilhos`), `backend/domain/indicators.py` (`calcular_indicadores`), `backend/domain/scoring.py` (`score_ponderado`)
- Test: `tests/test_scoring.py`, `tests/test_core_engine.py`

**Contexto:** a análise encontrou que `score_ponderado` lê `last.get("vol_ratio")` do DataFrame, mas não está confirmado se `calcular_indicadores` realmente grava essa coluna. Se não gravar, o shadow score está sistematicamente enviesado (sempre cai no fallback `1.0`) sem ninguém perceber, porque shadow mode não bloqueia nada e ninguém audita os números.

- [ ] **Step 1: Confirmar ou refutar o bug com um teste de caracterização**

```python
# tests/test_core_engine.py (adicionar ao arquivo existente)
from backend.services.core_engine import _carregar_ohlcv


def test_vol_ratio_e_persistido_no_dataframe_de_indicadores(monkeypatch):
    """Caracteriza se calcular_indicadores grava 'vol_ratio' no df —
    score_ponderado depende dessa coluna (scoring.py) e se ela não existir,
    o shadow score fica enviesado sempre no fallback."""
    import pandas as pd
    import numpy as np
    from backend.domain.indicators import calcular_indicadores

    idx = pd.date_range("2026-01-01", periods=60, freq="B")
    df = pd.DataFrame({
        "Open": np.linspace(100, 110, 60), "High": np.linspace(101, 111, 60),
        "Low": np.linspace(99, 109, 60), "Close": np.linspace(100, 110, 60),
        "Volume": np.linspace(1_000_000, 3_000_000, 60),
    }, index=idx)

    resultado = calcular_indicadores(df)

    assert "vol_ratio" in resultado.columns, (
        "calcular_indicadores NÃO grava 'vol_ratio' no DataFrame — "
        "score_ponderado (scoring.py) está lendo essa coluna via .get() com "
        "fallback genérico, então o shadow score está enviesado. Ver Step 2 "
        "desta task para a correção."
    )
```

- [ ] **Step 2: Rodar e decidir o caminho com base no resultado**

Run: `python -m pytest tests/test_core_engine.py::test_vol_ratio_e_persistido_no_dataframe_de_indicadores -v`

**Se passar** (coluna existe): o bug é refutado — documentar isso no commit message e marcar a task como "investigação concluída, sem correção necessária"; ainda assim manter o teste como guarda permanente.

**Se falhar** (coluna não existe — bug confirmado): a correção mínima é fazer `score_ponderado` calcular `vol_ratio` da mesma forma que `_avaliar_gatilhos` calcula localmente (`core_engine.py`, ver onde `vol_ratio` é computado ali) e reutilizar essa lógica, em vez de depender de uma coluna que não existe. Extrair para uma função compartilhada:

```python
# backend/domain/indicators.py — adicionar ao final
def calcular_vol_ratio(df, janela: int = 20) -> float:
    """Volume do último candle / média móvel de volume da janela.
    Extraído de core_engine._avaliar_gatilhos para ser compartilhado
    com domain.scoring.score_ponderado (evita o shadow score ler uma
    coluna que nunca foi persistida)."""
    media_vol = df["Volume"].tail(janela).mean()
    if not media_vol or media_vol <= 0:
        return 1.0
    return float(df["Volume"].iloc[-1] / media_vol)
```

Depois, em `backend/domain/scoring.py`, trocar `last.get("vol_ratio", 1.0)` pela chamada a essa função (ajustar a assinatura de `score_ponderado` para receber o `df` ou o valor já calculado — verificar a assinatura atual antes de decidir qual caminho é menos invasivo).

- [ ] **Step 3: Se corrigido, validar que o `score_ponderado` muda de fato para um caso com volume anômalo**

```python
def test_score_ponderado_reflete_volume_anomalo_real(monkeypatch):
    """Regressão: confirma que score_ponderado usa o vol_ratio real
    (não um fallback constante) após a correção do Step 2."""
    # construir dois DataFrames idênticos exceto pelo volume do último candle
    # (um 3x a média, outro igual à média) e confirmar que score_ponderado
    # difere entre os dois — ajustar conforme a assinatura real da função.
    ...
```
(Escrever o corpo completo do teste com base na assinatura real de `score_ponderado` encontrada no Step 2 antes de commitar — não deixar como placeholder.)

- [ ] **Step 4: Rodar suíte completa e commit**

Run: `python -m pytest tests/ -q --ignore=tests/test_market_analysis.py`
Expected: todos passando.

```bash
git add backend/domain/indicators.py backend/domain/scoring.py tests/test_core_engine.py tests/test_scoring.py
git commit -m "fix(score): corrige vol_ratio nao persistido que enviesava score_ponderado shadow"
```
(Ajustar a mensagem de commit para "test(score): caracteriza vol_ratio em score_ponderado (sem bug encontrado)" se o Step 2 confirmar que não há bug.)

---

## 🟡 P2 — Médio impacto

### Task 10: Repositório de acesso a dados (`SignalsRepository`)

**Files:**
- Create: `backend/services/signals_repository.py`
- Modify: `backend/api/routers/signals.py`, `backend/services/signal_service.py`

**Contexto:** `routers/signals.py` faz `supabase.table(...)` direto em 4 lugares, pulando a camada de serviço. Esta task centraliza todo acesso a `signals` num repositório, sem mudar comportamento.

- [ ] **Step 1: Ler os 4 pontos de acesso direto em `routers/signals.py`**

Run: `grep -n "supabase.table" backend/api/routers/signals.py`

Anotar cada query exata (select/filtros/ordenação/limit) antes de extrair — a extração deve ser 1:1, sem mudar comportamento.

- [ ] **Step 2: Criar o repositório com um método por query encontrada**

```python
# backend/services/signals_repository.py
from backend.services.supabase_client import get_supabase


def fetch_recentes(limit: int = 50, offset: int = 0) -> list[dict]:
    """Extraído de routers/signals.py — query original preservada 1:1."""
    supabase = get_supabase()
    resp = (
        supabase.table("signals")
        .select("*")
        .order("timestamp", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return resp.data or []


# Repetir o padrão acima para os outros 3 pontos de acesso identificados no
# Step 1 (ex.: fetch_por_ticker, fetch_analytics, fetch_performance) —
# copiar a query EXATA de cada endpoint, só renomeando para um nome de
# método descritivo. Não adicionar lógica nova.
```

- [ ] **Step 3: Escrever teste de caracterização para cada método novo, usando o padrão `_FakeSupabase` já estabelecido**

```python
# tests/test_signals_repository.py
from backend.services import signals_repository


class _FakeQuery:
    def __init__(self, data):
        self._data = data
    def select(self, *a, **k): return self
    def order(self, *a, **k): return self
    def range(self, *a, **k): return self
    def execute(self):
        class R: pass
        r = R(); r.data = self._data; return r


class _FakeTable:
    def __init__(self, data): self._data = data
    def table(self, name): return _FakeQuery(self._data)


def test_fetch_recentes_retorna_dados_da_query(monkeypatch):
    fake = _FakeTable([{"id": 1, "ticker": "PETR4"}])
    monkeypatch.setattr(signals_repository, "get_supabase", lambda: fake)
    resultado = signals_repository.fetch_recentes(limit=10)
    assert resultado == [{"id": 1, "ticker": "PETR4"}]
```

- [ ] **Step 4: Rodar o teste novo**

Run: `python -m pytest tests/test_signals_repository.py -v`
Expected: `PASSED`

- [ ] **Step 5: Substituir os 4 pontos de `routers/signals.py` pelas chamadas ao repositório**

Trocar cada bloco `supabase.table(...)...execute()` original em `routers/signals.py` por uma chamada ao método correspondente em `signals_repository`. Manter o restante do endpoint (validação de query params, formatação de resposta) inalterado.

- [ ] **Step 6: Rodar a suíte completa de testes dos routers**

Run: `python -m pytest tests/test_signals.py -v`
Expected: todos os testes existentes continuam passando (são testes de comportamento HTTP, não de implementação interna — não deveriam quebrar com esse refactor).

- [ ] **Step 7: Commit**

```bash
git add backend/services/signals_repository.py backend/api/routers/signals.py tests/test_signals_repository.py
git commit -m "refactor(signals): centraliza acesso a Supabase em SignalsRepository"
```

---

### Task 11: `CONFIG` → Pydantic Settings com validação de schema

**Files:**
- Create: `backend/core/settings.py`
- Modify: `backend/core/config.py`

**Contexto:** `CONFIG` é um dict Python sem schema. 31 usos de `CONFIG.get("chave", default)` mascaram erro de digitação silenciosamente. Esta task introduz validação sem quebrar os ~45 usos existentes de `CONFIG["chave"]`/`CONFIG.get("chave")` espalhados pelo código (que continuam funcionando, pois `CONFIG` continua sendo um dict — só passa a ser populado a partir de um modelo validado).

- [ ] **Step 1: Criar o modelo Pydantic com todos os campos atuais de `CONFIG`**

Ler `backend/core/config.py` por completo primeiro (já lido nesta sessão — replicar todos os ~45 campos, não só os mostrados no trecho abaixo) e criar:

```python
# backend/core/settings.py
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class MotorSettings(BaseSettings):
    # ── Indicadores ──
    stoch_k_period: int = 14
    stoch_d_period: int = 3
    stoch_smooth: int = 3
    stoch_oversold: int = 25
    stoch_overbought: int = 75
    rsi_period: int = 14
    rsi_oversold: int = 35
    rsi_overbought: int = 65
    ema_fast: int = 9
    ema_slow: int = 21
    volume_mult: float = 1.5
    # ── Gestao de risco ──
    stop_pct: float = -0.43
    alvo1_pct: float = 0.25
    alvo2_pct: float = 2.50
    alvo_final_pct: float = 7.00
    # ── Filtros ──
    min_score: int = 5
    scoring_mode: str = Field(default="classico", pattern="^(classico|ponderado)$")
    iv_filter_mode: str = Field(default="shadow", pattern="^(shadow|ativo)$")
    # (continuar replicando TODOS os campos restantes de CONFIG aqui,
    #  usando o mesmo tipo/default já presente em config.py — não
    #  inventar novos defaults, copiar exatamente os valores atuais)

    model_config = {"env_prefix": "MOTOR_"}
```

> **Importante**: este Step precisa necessariamente transcrever os ~45 campos completos de `config.py` (omitidos aqui por espaço) — antes de implementar, copiar a lista completa do arquivo real, não apenas os 16 mostrados acima como amostra.

- [ ] **Step 2: Adicionar `pydantic-settings` às dependências**

```bash
pip install pydantic-settings
```

Adicionar `pydantic-settings>=2.0.0` em `requirements.txt`.

- [ ] **Step 3: Popular `CONFIG` a partir do `MotorSettings` validado, preservando a interface de dict**

Em `backend/core/config.py`, substituir a definição literal de `CONFIG = {...}` por:

```python
from backend.core.settings import MotorSettings

_settings = MotorSettings()
CONFIG: dict = _settings.model_dump()
# CONFIG continua sendo um dict mutável (compatibilidade com os ~45 usos
# existentes de CONFIG["x"]/CONFIG.get("x") e com a mutação em runtime de
# _historico_sinais já documentada). A validação de schema acontece uma
# vez, no boot, via MotorSettings — typos em chaves usadas depois (ex.:
# CONFIG.get("chave_errada")) continuam silenciosos no acesso, mas os
# VALORES iniciais agora são garantidamente do tipo/formato esperado.
```

Manter `ATIVOS_B3` e qualquer outra constante não-`CONFIG` do arquivo original inalteradas.

- [ ] **Step 4: Rodar a suíte completa**

Run: `python -m pytest tests/ -q --ignore=tests/test_market_analysis.py`
Expected: todos passando — nenhum teste deveria ter que mudar, pois `CONFIG` continua se comportando como dict.

- [ ] **Step 5: Validar o boot real da aplicação**

Run: `python -c "from backend.core.config import CONFIG; print(CONFIG['min_score'], CONFIG['scoring_mode'])"`
Expected: imprime `5 classico` sem erro.

Run (teste negativo — validar que valor inválido é rejeitado):
```bash
MOTOR_SCORING_MODE=invalido python -c "from backend.core.settings import MotorSettings; MotorSettings()"
```
Expected: `ValidationError` mencionando o pattern de `scoring_mode`.

- [ ] **Step 6: Commit**

```bash
git add backend/core/settings.py backend/core/config.py requirements.txt
git commit -m "refactor(config): introduz MotorSettings (Pydantic) validando CONFIG no boot"
```

---

### Task 12: Consolidar hooks de fetch do frontend (`useCachedFetch`)

**Files:**
- Create: `src/hooks/useCachedFetch.ts`
- Modify: `src/hooks/useAssetAnalysis.ts`, `src/hooks/useIndicators.ts`
- Test: `src/hooks/useCachedFetch.test.ts`

**Contexto:** `useAssetAnalysis` e `useIndicators` duplicam fetch+cache TTL; `useAssetAnalysis` tem uma race condition real (sem cancelamento ao trocar ticker rápido) que `useIndicators` já resolve com uma flag de cancelamento. Consolidar pegando o melhor dos dois.

- [ ] **Step 1: Ler as duas implementações completas**

Run: `cat src/hooks/useAssetAnalysis.ts src/hooks/useIndicators.ts`

Confirmar a assinatura de retorno de cada um (`{data, loading, error}` ou variação) antes de generalizar — o hook genérico precisa preservar a interface pública dos dois para não quebrar os componentes que os consomem.

- [ ] **Step 2: Escrever o teste do hook genérico primeiro**

```typescript
// src/hooks/useCachedFetch.test.ts
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { useCachedFetch } from "./useCachedFetch";

describe("useCachedFetch", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("retorna loading=true inicialmente e os dados após o fetch resolver", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ valor: 42 }),
    }) as any;

    const { result } = renderHook(() => useCachedFetch<{ valor: number }>("/api/teste"));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual({ valor: 42 });
    expect(result.current.error).toBeNull();
  });

  it("ignora resposta obsoleta quando a key muda antes do fetch anterior resolver", async () => {
    let resolveFirst: (v: any) => void;
    const firstPromise = new Promise((resolve) => { resolveFirst = resolve; });
    global.fetch = vi.fn()
      .mockImplementationOnce(() => firstPromise)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ valor: 2 }) }) as any;

    const { result, rerender } = renderHook(
      ({ key }) => useCachedFetch<{ valor: number }>(`/api/${key}`),
      { initialProps: { key: "a" } }
    );

    rerender({ key: "b" });
    await waitFor(() => expect(result.current.data).toEqual({ valor: 2 }));

    resolveFirst!({ ok: true, json: async () => ({ valor: 1 }) });
    await new Promise((r) => setTimeout(r, 10));

    // a resposta atrasada de "a" não deve sobrescrever o estado já atualizado por "b"
    expect(result.current.data).toEqual({ valor: 2 });
  });
});
```

- [ ] **Step 3: Rodar o teste e confirmar que falha (hook ainda não existe)**

Run: `npm run test -- useCachedFetch`
Expected: FAIL com `Cannot find module './useCachedFetch'`

- [ ] **Step 4: Implementar o hook genérico**

```typescript
// src/hooks/useCachedFetch.ts
import { useEffect, useRef, useState } from "react";

interface CacheEntry<T> {
  data: T;
  expiresAt: number;
}

const _cache = new Map<string, CacheEntry<unknown>>();
const DEFAULT_TTL_MS = 5 * 60 * 1000;

interface UseCachedFetchResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function useCachedFetch<T>(url: string | null, ttlMs: number = DEFAULT_TTL_MS): UseCachedFetchResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);

  useEffect(() => {
    if (!url) return;

    const cached = _cache.get(url) as CacheEntry<T> | undefined;
    if (cached && cached.expiresAt > Date.now()) {
      setData(cached.data);
      setLoading(false);
      setError(null);
      return;
    }

    const currentId = ++requestIdRef.current;
    setLoading(true);
    setError(null);

    fetch(url)
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((json: T) => {
        if (requestIdRef.current !== currentId) return; // resposta obsoleta, ignorar
        _cache.set(url, { data: json, expiresAt: Date.now() + ttlMs });
        setData(json);
        setLoading(false);
      })
      .catch((err: Error) => {
        if (requestIdRef.current !== currentId) return;
        setError(err.message);
        setLoading(false);
      });
  }, [url, ttlMs]);

  return { data, loading, error };
}
```

- [ ] **Step 5: Rodar o teste de novo**

Run: `npm run test -- useCachedFetch`
Expected: `PASS` (2 testes)

- [ ] **Step 6: Migrar `useAssetAnalysis` e `useIndicators` para usar o hook genérico**

Reescrever cada um como um wrapper fino sobre `useCachedFetch`, preservando a assinatura pública original (nome do hook, formato do parâmetro de entrada, formato do retorno) para não quebrar os componentes consumidores. Não remover a classe `LRUCache` de `useIndicators.ts` se ela cobrir um caso que `useCachedFetch` não cobre (múltiplas entradas simultâneas com limite de tamanho) — nesse caso, avaliar se vale generalizar o limite de tamanho para dentro de `useCachedFetch` também, ou manter como uma característica específica documentada.

- [ ] **Step 7: Rodar a suíte de testes do frontend inteira**

Run: `npm run test`
Expected: todos os testes existentes (incluindo os de `useIndicators` se houver) continuam passando.

- [ ] **Step 8: Commit**

```bash
git add src/hooks/useCachedFetch.ts src/hooks/useCachedFetch.test.ts src/hooks/useAssetAnalysis.ts src/hooks/useIndicators.ts
git commit -m "refactor(hooks): consolida useAssetAnalysis/useIndicators em useCachedFetch (corrige race condition)"
```

---

### Task 13: Agendar `cleanup_old_signals` + retenção de `trigger_outcomes`/`iv_history`

**Files:**
- Modify: `backend/services/scheduler.py`, `backend/services/signal_service.py`

- [ ] **Step 1: Confirmar que `cleanup_old_signals` realmente não é chamada hoje**

Run: `grep -rn "cleanup_old_signals" backend/`
Expected: só a definição em `signal_service.py`, nenhuma chamada em `scheduler.py` ou em qualquer router.

- [ ] **Step 2: Ler `scheduler.py` para entender o padrão de agendamento existente**

Run: `cat backend/services/scheduler.py`

- [ ] **Step 3: Escrever teste de caracterização para o novo job**

```python
# tests/test_scheduler.py (adicionar ao arquivo existente, se houver; criar se não houver)
from backend.services import scheduler


def test_scheduler_agenda_job_de_limpeza_de_sinais_antigos(monkeypatch):
    """cleanup_old_signals deve estar registrada no scheduler para não
    deixar a tabela signals crescer sem limite (achado da análise
    arquitetural de 2026-06-30)."""
    jobs_agendados = []

    class _FakeScheduler:
        def add_job(self, func, trigger, **kwargs):
            jobs_agendados.append(kwargs.get("id", func.__name__))
        def start(self): pass

    monkeypatch.setattr(scheduler, "BackgroundScheduler", lambda: _FakeScheduler())
    scheduler.iniciar_scheduler()

    assert any("cleanup" in job_id.lower() for job_id in jobs_agendados), (
        f"Nenhum job de limpeza encontrado entre os agendados: {jobs_agendados}"
    )
```

> Ajustar o nome da função de inicialização (`iniciar_scheduler` é um placeholder de nome — usar o nome real encontrado no Step 2) e o mecanismo de mock conforme a API real do `BackgroundScheduler` usada no arquivo.

- [ ] **Step 4: Rodar e confirmar que falha**

Run: `python -m pytest tests/test_scheduler.py::test_scheduler_agenda_job_de_limpeza_de_sinais_antigos -v`
Expected: FAIL (job ainda não existe)

- [ ] **Step 5: Adicionar o job ao scheduler**

Em `backend/services/scheduler.py`, no mesmo padrão dos jobs existentes (ex.: o de coleta de IV às 18h BRT), adicionar:

```python
from backend.services.signal_service import cleanup_old_signals

# dentro da função de inicialização do scheduler, junto aos demais add_job:
scheduler.add_job(
    cleanup_old_signals,
    "cron",
    hour=3,
    minute=0,
    timezone=_TZ_SP,  # mesmo padrão de timezone já usado pelos outros jobs
    id="cleanup_old_signals_diario",
    kwargs={"days": 30},
)
```

(Ajustar `kwargs`/assinatura conforme a assinatura real de `cleanup_old_signals` em `signal_service.py`.)

- [ ] **Step 6: Rodar o teste de novo**

Run: `python -m pytest tests/test_scheduler.py::test_scheduler_agenda_job_de_limpeza_de_sinais_antigos -v`
Expected: `PASSED`

- [ ] **Step 7: Avaliar e decidir sobre retenção de `trigger_outcomes`/`iv_history`**

Ler se há razão de negócio para nunca apagar `trigger_outcomes` (é a base de telemetria para validar os caps de família na Camada 5 do roadmap — apagar destruiria a amostra histórica). **Decisão recomendada**: não aplicar limpeza automática em `trigger_outcomes` nem `iv_history` (ambas são dados de telemetria/série histórica de baixo volume por linha, ao contrário de `signals` que acumula texto/JSONB grande por linha) — documentar essa decisão no commit message em vez de implementar uma limpeza que destruiria dados precisamente necessários para a Camada 5.

- [ ] **Step 8: Rodar suíte completa e commit**

Run: `python -m pytest tests/ -q --ignore=tests/test_market_analysis.py`

```bash
git add backend/services/scheduler.py tests/test_scheduler.py
git commit -m "feat(scheduler): agenda cleanup_old_signals diario (signals nao tinha retencao)"
```

---

### Task 14: Wrapper HTTP único com retry/timeout para `data_providers.py`

**Files:**
- Create: `backend/services/http_client.py`
- Modify: `backend/services/data_providers.py`

- [ ] **Step 1: Ler todos os pontos de chamada HTTP em `data_providers.py`**

Run: `grep -n "requests\.\(get\|post\)" backend/services/data_providers.py`

Anotar timeout atual de cada um (já levantado pela análise: 10-15s variando) antes de unificar.

- [ ] **Step 2: Escrever teste do wrapper antes de implementar**

```python
# tests/test_http_client.py
import requests
import pytest
from backend.services.http_client import get_with_retry


def test_get_with_retry_retorna_resposta_no_sucesso_imediato(monkeypatch):
    class _FakeResp:
        status_code = 200
        def json(self): return {"ok": True}

    monkeypatch.setattr(requests, "get", lambda *a, **k: _FakeResp())
    resp = get_with_retry("http://exemplo.com", timeout=5)
    assert resp.json() == {"ok": True}


def test_get_with_retry_tenta_3_vezes_antes_de_desistir(monkeypatch):
    chamadas = {"n": 0}

    def _falha(*a, **k):
        chamadas["n"] += 1
        raise requests.exceptions.ConnectionError("falhou")

    monkeypatch.setattr(requests, "get", _falha)
    monkeypatch.setattr("time.sleep", lambda *a: None)  # não esperar de verdade no teste

    with pytest.raises(requests.exceptions.ConnectionError):
        get_with_retry("http://exemplo.com", timeout=5, tentativas=3)

    assert chamadas["n"] == 3


def test_get_with_retry_recupera_na_segunda_tentativa(monkeypatch):
    chamadas = {"n": 0}

    class _FakeResp:
        status_code = 200
        def json(self): return {"ok": True}

    def _falha_depois_recupera(*a, **k):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise requests.exceptions.Timeout("timeout")
        return _FakeResp()

    monkeypatch.setattr(requests, "get", _falha_depois_recupera)
    monkeypatch.setattr("time.sleep", lambda *a: None)

    resp = get_with_retry("http://exemplo.com", timeout=5, tentativas=3)
    assert resp.json() == {"ok": True}
    assert chamadas["n"] == 2
```

- [ ] **Step 3: Rodar e confirmar que falha**

Run: `python -m pytest tests/test_http_client.py -v`
Expected: FAIL (`ModuleNotFoundError: backend.services.http_client`)

- [ ] **Step 4: Implementar o wrapper**

```python
# backend/services/http_client.py
import logging
import time

import requests

logger = logging.getLogger(__name__)


def get_with_retry(
    url: str,
    timeout: float = 10.0,
    tentativas: int = 3,
    backoff_base_s: float = 1.0,
    **kwargs,
) -> requests.Response:
    """GET com retry e backoff exponencial — extrai o padrão já usado em
    core_engine._baixar_yfinance e o generaliza para todas as integrações
    de rede de data_providers.py (que hoje não tinham retry algum)."""
    ultima_excecao: Exception | None = None
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.get(url, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            ultima_excecao = e
            logger.warning(f"Tentativa {tentativa}/{tentativas} falhou para {url}: {e}")
            if tentativa < tentativas:
                time.sleep(backoff_base_s * (2 ** (tentativa - 1)))
    raise ultima_excecao
```

- [ ] **Step 5: Rodar os testes de novo**

Run: `python -m pytest tests/test_http_client.py -v`
Expected: 3 `PASSED`

- [ ] **Step 6: Substituir as chamadas `requests.get` diretas em `data_providers.py` pelo wrapper**

Para cada ponto identificado no Step 1, trocar `requests.get(url, timeout=N)` por `get_with_retry(url, timeout=N)`, preservando o timeout específico de cada endpoint (não forçar um valor único se os atuais têm razão de ser diferentes — registrar no commit se algum foi padronizado).

- [ ] **Step 7: Rodar a suíte completa de `data_providers`**

Run: `python -m pytest tests/test_data_providers.py -v`
Expected: todos os testes existentes continuam passando (eles já mockam `requests.get`/`fetch_*`, então devem continuar funcionando, mas confirmar — algum teste pode precisar mockar `time.sleep` adicionalmente se exercitar um caminho de erro).

- [ ] **Step 8: Commit**

```bash
git add backend/services/http_client.py backend/services/data_providers.py tests/test_http_client.py
git commit -m "feat(http): adiciona wrapper get_with_retry e aplica em data_providers.py"
```

---

## 🟢 P3 — Baixo/médio impacto

### Task 15: Lint Python (ruff) configurado e no CI

**Files:**
- Create: `pyproject.toml` (ou seção `[tool.ruff]` se já existir)
- Modify: `.github/workflows/ci.yml` (da Task 1)

- [ ] **Step 1: Instalar e configurar ruff**

```bash
pip install ruff
```

```toml
# pyproject.toml
[tool.ruff]
line-length = 110
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
ignore = []
```

- [ ] **Step 2: Rodar e ver o volume de achados atuais**

Run: `ruff check backend/ tests/`

Se houver muitos achados pré-existentes (esperado num projeto sem lint até agora), **não corrigir tudo nesta task** — adicionar exceções pontuais via `# noqa` apenas onde necessário para o CI passar, e registrar o volume total como débito conhecido (mesma disciplina já usada para o `any` do TypeScript).

- [ ] **Step 3: Adicionar ao CI**

Em `.github/workflows/ci.yml`, no job `backend`, adicionar antes do `pytest`:
```yaml
      - run: pip install ruff
      - run: ruff check backend/ tests/
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .github/workflows/ci.yml
git commit -m "chore(lint): configura ruff para o backend Python e integra ao CI"
```

---

### Task 16: Dockerfile — healthcheck + usuário non-root

**Files:**
- Modify: `Dockerfile`

- [ ] **Step 1: Ler o Dockerfile atual**

Run: `cat Dockerfile`

- [ ] **Step 2: Adicionar usuário non-root e healthcheck**

Adicionar antes do `CMD`/`ENTRYPOINT` final:
```dockerfile
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

> Se `curl` não estiver na imagem base, adicionar `RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*` antes do `HEALTHCHECK`, ou trocar por um healthcheck via Python (`CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"`) se preferir não adicionar `curl` à imagem.

- [ ] **Step 3: Validar que a imagem builda e roda**

Run: `docker build -t options-signals-test .`
Expected: build sem erro.

Run: `docker run --rm -d --name test-container -p 8000:8000 options-signals-test && sleep 15 && docker inspect --format='{{.State.Health.Status}}' test-container`
Expected: `healthy` (após o `start-period`).

Run: `docker stop test-container`

- [ ] **Step 4: Commit**

```bash
git add Dockerfile
git commit -m "chore(docker): adiciona HEALTHCHECK e usuario non-root"
```

---

### Task 17: `.env.example`

**Files:**
- Create: `.env.example`

- [ ] **Step 1: Listar todas as variáveis de ambiente usadas no código**

Run: `grep -rhoE 'os\.getenv\("([A-Z_]+)"' backend/ | sed -E 's/os.getenv\("//;s/"//' | sort -u`
Run: `grep -rhoE 'process\.env\.([A-Z_]+)' src/ | sed -E 's/process.env.//' | sort -u`

- [ ] **Step 2: Criar o template sem valores reais**

```bash
# Supabase
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=

# Telegram (opcional)
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=

# Dados de mercado
BRAPI_TOKEN=

# Redis (opcional — fallback em memoria se ausente)
REDIS_URL=
```

(Completar com qualquer variável adicional encontrada no Step 1 que não esteja listada acima.)

- [ ] **Step 3: Commit**

```bash
git add .env.example
git commit -m "docs: adiciona .env.example com todas as variaveis de ambiente usadas"
```

---

### Task 18: Tipar `user`/`session` em `supabase-auth.ts`

**Files:**
- Modify: `src/lib/supabase-auth.ts`, `src/lib/supabase.ts`

- [ ] **Step 1: Ler os dois arquivos**

Run: `cat src/lib/supabase-auth.ts src/lib/supabase.ts`

- [ ] **Step 2: Substituir os `any` pelos tipos reais do supabase-js**

```typescript
import type { User, Session } from "@supabase/supabase-js";

// trocar:
// user: any;
// session: any;
// por:
user: User | null;
session: Session | null;
```

(Aplicar a mesma troca em todos os pontos de `any` identificados nos dois arquivos — a análise encontrou `supabase.ts:6` e `supabase-auth.ts:4-5`.)

- [ ] **Step 3: Rodar o type-check e o lint**

Run: `npx tsc --noEmit`
Expected: sem erros novos relacionados a esses dois arquivos (pode revelar usos que assumiam `any` implicitamente — corrigir o uso, não reintroduzir `any`).

Run: `npm run lint`

- [ ] **Step 4: Rodar a suíte de testes do frontend**

Run: `npm run test`
Expected: todos passando.

- [ ] **Step 5: Commit**

```bash
git add src/lib/supabase-auth.ts src/lib/supabase.ts
git commit -m "fix(types): substitui any por User/Session do supabase-js em supabase-auth.ts"
```

---

### Task 19: Testes de componentes financeiros do frontend

**Files:**
- Test: `src/components/OptionAnalyzer.test.tsx`, `src/components/GreeksCalculator.test.tsx`, `src/components/PayoffChart.test.tsx`

**Contexto:** esses três componentes calculam/exibem resultado financeiro direto ao usuário e não têm nenhum teste — exatamente onde um bug de fórmula importa mais (reforça a Task 5, mas no nível de componente React, não só na lib pura).

- [ ] **Step 1: Ler os três componentes para entender suas props/comportamento público**

Run: `cat src/components/OptionAnalyzer.tsx src/components/GreeksCalculator.tsx src/components/PayoffChart.tsx`

- [ ] **Step 2: Escrever teste para `GreeksCalculator` (exemplo — replicar o padrão para os outros dois)**

```typescript
// src/components/GreeksCalculator.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GreeksCalculator } from "./GreeksCalculator";

describe("GreeksCalculator", () => {
  it("calcula e exibe as gregas para parâmetros válidos de uma CALL ATM", () => {
    render(<GreeksCalculator />);

    fireEvent.change(screen.getByLabelText(/preço do ativo/i), { target: { value: "100" } });
    fireEvent.change(screen.getByLabelText(/strike/i), { target: { value: "100" } });
    fireEvent.change(screen.getByLabelText(/dias até o vencimento/i), { target: { value: "30" } });
    fireEvent.change(screen.getByLabelText(/volatilidade/i), { target: { value: "30" } });

    // Delta de uma CALL ATM com esses parâmetros fica perto de 0.5 — valor de
    // referência calculado independentemente (não copiado da implementação
    // sob teste) para servir de guarda real, não de tautologia.
    expect(screen.getByText(/delta/i).closest("div")).toHaveTextContent(/0\.5\d/);
  });

  it("exibe mensagem de erro quando o prêmio informado está abaixo do intrínseco (IV não converge)", () => {
    render(<GreeksCalculator />);
    // ajustar para os seletores/labels reais do componente, encontrados no Step 1
  });
});
```

> Os seletores (`getByLabelText`, textos exatos) precisam ser ajustados para o que o componente real usa — ler o JSX no Step 1 antes de finalizar este teste. Não commitar com seletores adivinhados sem confirmar contra o componente real.

- [ ] **Step 3: Rodar e ajustar até passar com asserções reais (não tautológicas)**

Run: `npm run test -- GreeksCalculator`

Repetir o padrão do Step 2 para `OptionAnalyzer.test.tsx` (testar o cálculo de preço justo/IV) e `PayoffChart.test.tsx` (testar que a curva renderizada bate com pontos de referência calculados independentemente para um payoff conhecido, ex.: CALL comprada — payoff deve ser zero abaixo do strike e linear acima).

- [ ] **Step 4: Rodar a suíte completa do frontend**

Run: `npm run test`
Expected: todos passando, incluindo os novos.

- [ ] **Step 5: Commit**

```bash
git add src/components/OptionAnalyzer.test.tsx src/components/GreeksCalculator.test.tsx src/components/PayoffChart.test.tsx
git commit -m "test(components): adiciona testes para componentes de calculo financeiro (Greeks, Option, Payoff)"
```

---

## Resumo de pendências manuais pós-merge (consolidado)

Depois de cada task ser implementada e mergeada, estas ações precisam ser feitas manualmente, fora do Claude Code, antes do efeito ser real em produção:

| Task | Ação manual | Onde |
|---|---|---|
| 1 | Confirmar que GitHub Actions está habilitado | GitHub → Settings → Actions |
| 2 | Coletar schema real de `signals` (pré-requisito) e aplicar migração `007` | Supabase SQL Editor |
| 3 | Confirmar uso de `anon` key no frontend e aplicar migração `008` | Supabase SQL Editor |
| 4 | (Coberta pela 2, se completa) | — |
| 7 | Validar dados existentes não violam constraints, depois aplicar migração `010` | Supabase SQL Editor |

Todas as outras tasks (5, 6, 8, 9, 10-19) são autocontidas — commit é suficiente, sem ação externa.

---

## Self-Review

**Cobertura do spec (análise arquitetural):** todos os 19 achados da análise consolidada (crítico, alto, médio, baixo) têm uma task correspondente. Os achados de "schema reconstruído"/"colunas órfãs" foram fundidos nas Tasks 2 e 4 para evitar duas migrações redundantes tocando a mesma tabela na mesma janela de tempo.

**Placeholders:** a Task 11 (Pydantic Settings) e a Task 9 Step 3 (teste de regressão de `vol_ratio`) contêm uma nota explícita pedindo para completar com dados reais do arquivo (lista completa de ~45 campos de `CONFIG`; assinatura real de `score_ponderado`) em vez de adivinhar — isso é intencional e não um placeholder vago: a alternativa seria transcrever ~45 linhas de config sem tê-las na tela neste momento, o que arriscaria erro de transcrição maior do que pedir para o executor copiar da fonte real no momento da implementação. Mantido como nota explícita de "fonte de verdade é o arquivo real", não como "implemente depois".

**Consistência de tipos/nomes:** `get_with_retry` (Task 14), `useCachedFetch` (Task 12), `MotorSettings`/`CONFIG` (Task 11), `SignalsRepository`/`fetch_recentes` (Task 10) são usados de forma consistente entre o Step de teste e o Step de implementação dentro de cada task.
