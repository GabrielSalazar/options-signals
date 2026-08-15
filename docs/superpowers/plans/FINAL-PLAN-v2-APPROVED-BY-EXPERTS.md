# PLANO DE REFATORAÇÃO FINAL — v2 Aprovado por Especialistas

**Data:** 2026-08-15  
**Status:** ✅ APROVADO por 5 especialistas (DevOps, Backend, DBA, Security, Code Quality)  
**Timeline:** 33 dias úteis (vs. 34 original) + PRÉ-F0 hardening

---

## 🎯 RESUMO EXECUTIVO

Plano original F0-F8 é **arquiteturalmente sólido**, mas requer **3 fases de preparação PRÉ-F0** e **ajustes em F0-F8**:

```
PRÉ-F0 Hardening (8 dias) ← NOVO
├─ 0-S: Segurança (3 dias): deps pinadas + secrets + scanning
├─ 0-D: Dados (2 dias): migrations tooling + backups + índices
└─ 0-I: Infraestrutura (3 dias): Render free → Railway + graceful shutdown

F0-F8 Refactoring (28 dias) ← REVISADO
├─ F0 (Rede de Proteção): 3 dias + ajustes
├─ F1-F8: 25 dias (plano original)
└─ Checkpoints: após cada fase

TOTAL: ~41 dias úteis (vs. 28 original)
```

---

## 🔴 ACHADOS CRÍTICOS POR ESPECIALISTA

### 1️⃣ DevOps: Infrastructure Hardening (3 dias PRÉ-F0)

| Achado | Severidade | Ação |
|--------|-----------|------|
| Render free hiberna (50s boot) | 🔴 CRÍTICO | Migrar Railway/Fly.io |
| Keep-alive via cron-job.org | 🔴 CRÍTICO | Internal keep-alive loop |
| Zero deployment safety | 🔴 CRÍTICO | Graceful shutdown + readiness probes |
| Sem observabilidade | 🔴 CRÍTICO | Minimal observabilidade F0, full F7 |
| Cobertura de testes não medida | 🔴 CRÍTICO | CI gates (começar com baseline) |

**Recomendação:** PRÉ-F0 Fase 0-I (Infrastructure) — 3 dias

```
0-I.1: Migrar Render free → Railway ($7/mo)        [2 dias]
0-I.2: Add graceful shutdown + readiness probes    [1 dia]
```

---

### 2️⃣ Backend Architecture: 5 Mudanças Críticas

| Mudança | Impacto | Fase |
|---------|--------|------|
| **Move CooldownRepository para F2** | Quebra ciclo core_engine ↔ config | F2 (não F4) |
| **Adiciona contract tests a F0** | Complementa golden master | F0.3 |
| **Lazy-load options.net em F2** | 10-15% speedup em rejeições | F2 |
| **Signal Pydantic com validators** | Manuseio de NaN/numpy types | F1 |
| **Import cycle detection test** | CI detecta circularidade | F2 |

**Nota:** Validators customizados para NaN → None (Pydantic rejeita por default)

---

### 3️⃣ DBA: 3 Críticos (+ PRÉ-F0 Fase 0-D)

| Gap | Severidade | PRÉ-F0 ou F0? |
|-----|-----------|--------------|
| Reversão de migrations insuficiente | 🔴 | PRÉ-F0 (0-D.1) |
| Falta índice trigger_outcomes.signal_id | 🔴 | PRÉ-F0 (0-D.2) |
| Sem backup externo | 🔴 | PRÉ-F0 (0-D.3) |
| Performance sem baseline | 🟠 | F0 (EXPLAIN ANALYZE) |
| Data retention indefinida | 🟠 | F8 |

**Recomendação:** PRÉ-F0 Fase 0-D (Dados) — 2 dias

```
0-D.1: Migrations tooling (versionamento + rollback seguro)    [1 dia]
0-D.2: Índices críticos + backup pg_dump → S3 + restore test  [1 dia]
```

---

### 4️⃣ Security: Simplified (Auth + Telegram OUT OF SCOPE)

| Item | Severidade | Escopo? | Ação |
|------|-----------|---------|------|
| Dependencies não pinadas | 🔴 | ✅ | F0: pip freeze + pip-audit CI |
| Secrets commitadas | 🔴 | ✅ | F0: detect-secrets CI |
| Error exposure | 🟠 | ✅ | F1: Sanitizar detail |
| Input validation | 🟠 | ✅ | F1: Pydantic whitelisting |
| Audit logging | 🟠 | ✅ | F7+F8 |
| Autenticação | ❌ | **OUT OF SCOPE** | — |
| Telegram | ❌ | **OUT OF SCOPE** | — |

**Recomendação:** PRÉ-F0 Fase 0-S (Segurança) — 3 dias

```
0-S.1: Pin requirements.txt + pip-audit CI        [1 dia]
0-S.2: Secrets (unificar + detect-secrets CI)     [1.5 dias]
0-S.3: Config imutável + sanitizar erros          [0.5 dias]
```

---

### 5️⃣ Code Quality: Cobertura Baseline + TDD

| Achado | Severidade | Ação |
|--------|-----------|------|
| Cobertura não medida | 🔴 | F0.2: Medir + aceitar baseline |
| Golden master snapshots = null | 🔴 | F0: Investigar indicadores |
| Sem testes E2E | 🔴 | F1.5: 3 fluxos críticos (novo) |
| Contract testing frágil | 🟠 | F1: Pydantic + gerador TS |
| Sem performance baseline | 🟠 | F7: Benchmarks + Prometheus |

**Recomendação:** Ajustar F0 + Adicionar TDD obrigatório F1-F8

```
F0.2: Medir baseline (não tentar 80% agora)
F1.5: 3 testes E2E (motor→API, API→frontend, full flow)
F1-F8: TDD padrão (RED → GREEN → COVERAGE)
```

---

## 📋 PLANO REVISADO FINAL

### PRÉ-F0: Hardening (8 dias) — NOVO

```
0-S: Segurança (3 dias)
├─ 0-S.1: Pin requirements.txt + pip-audit CI (1d)
├─ 0-S.2: Secrets management (1.5d)
└─ 0-S.3: Config imutável + error sanitization (0.5d)

0-D: Dados (2 dias)
├─ 0-D.1: Migrations tooling + rollback seguro (1d)
└─ 0-D.2: Índices + backup externo + restore test (1d)

0-I: Infraestrutura (3 dias)
├─ 0-I.1: Migrar Render free → Railway (2d)
└─ 0-I.2: Graceful shutdown + readiness probes (1d)

CHECKPOINT PRÉ-F0:
✅ Dependências pinadas + pipeline segura
✅ Backup funcional em S3 + restore testado
✅ Backend pronto para escalar (não hiberna)
✅ Deployment seguro (graceful shutdown)
```

### F0-F8: Refactoring (28 dias) — REVISADO

```
F0: Rede de Proteção (3 dias) [AJUSTADO]
├─ F0.1: Golden Master + 12 fixtures (✅ feito, 33%)
├─ F0.2: Medir cobertura baseline + aceitar como meta (NÃO 80%)
├─ F0.3: Pin deps + tsc no CI (+ contract tests)
└─ F0.4: EXPLAIN ANALYZE (performance baseline)

F1: Contrato Tipado (6-7 dias) [COM TDD + E2E]
├─ F1.1a: Pydantic Signal model + validators (1.5d)
├─ F1.1b: Motor adapter (1d)
├─ F1.2: Gerador TS automático + CI (1d)
├─ F1.3: Contract testing (Pydantic-based, não regex) (0.5d)
└─ F1.5: 3 testes E2E críticos (novo!) (1.5d)

F2: Decomposição Core (5-6 dias) [COM IMPORT CYCLES TEST]
├─ F2.1: ohlcv_loader + triggers_v1 (1d)
├─ F2.2: signal_builder + redução core_engine (1.5d)
├─ F2.3: CooldownRepository abstrato (0.5d) ← MOVED FROM F4
├─ F2.4: Import cycles detection test + lazy-load (1.5d)
└─ F2.5: Reduzir de 959 → ~280 linhas (1d)

F3: Roteadores Magros (2-3 dias) [PARALELO COM F2]
├─ F3.1: market.py decomposição (1d)
└─ F3.2: Reduzir para ~120 linhas (1d)

F4: Estado Global (4-5 dias) [REVISADO]
├─ F4.1: CooldownRepository Redis (agora temos abstrato de F2)
├─ F4.2: CONFIG imutável (já em 0-S.3, confirmar)
└─ F4.3: Redis TTL + fallback (1.5d)

F5: Camada Dados Frontend (3-4 dias)
├─ F5.1: SWR fetcher (1d)
├─ F5.2: Remover 4 caminhos de dados (1.5d)
└─ F5.3: Remove console.log (0.5d)

F6: Decomposição UI (6-7 dias)
├─ F6.1: Lazy-load Plotly (1d)
└─ F6.2: Quebrar 8 arquivos > 400 linhas (2d)

F7: Observabilidade (3 dias) [EXPANDIDO]
├─ F7.1: Prometheus metrics (2d)
├─ F7.2: Structured logging + error sanitization (1d)
└─ F7.3: Alertas (0.5d)

F8: Higiene (2 dias)
├─ F8.1: Remove código morto (0.5d)
├─ F8.2: Data retention policy (0.5d)
└─ F8.3: Cleanup schema (1d)

CHECKPOINTS F0-F8:
✅ Semana 1 (Ago 15-22): F0 + F1.1a completo
✅ Semana 2 (Ago 22-26): F2 ~50% + F3/F4 iniciadas
✅ Semana 3: F2-F4 80% + F5 pronto
✅ Semana 4+: F6-F8 + validação
```

---

## 🎯 Matriz de Alterações ao Plano

| Item | Tipo | Impacto | Fase |
|------|------|--------|------|
| Move CooldownRepository → F2 | Arquitetura | Alto | F2 (não F4) |
| Adiciona testes E2E | Qualidade | Alto | F1.5 (novo) |
| PRÉ-F0 Hardening (8d) | Timeline | +8 dias | Antes de F0 |
| Migrar Render → Railway | Infraestrutura | Alto | 0-I |
| Índices DB + backups | Dados | Alto | 0-D |
| Dependencies + scanning | Segurança | Alto | 0-S |
| TDD obrigatório F1-F8 | Qualidade | Alto | Todas |
| Cobertura baseline (não 80%) | Qualidade | Alto | F0.2 |
| Golden master snapshots reais | Qualidade | Médio | F0 |
| Lazy-load options.net | Performance | Médio | F2 |

---

## ✅ Timeline Final

```
PRÉ-F0 (8d): 0-S, 0-D, 0-I
F0 (3d): Golden Master + Cobertura baseline
F1 (6-7d): Tipos + E2E
F2-F4 (11-14d): Decomposição + Estado
F5-F8 (13-14d): Frontend + Obs + Higiene

TOTAL: ~41-42 dias úteis (vs. 28-34 original)

Razão +13 dias:
- PRÉ-F0 hardening: +8 dias (infra + dados + segurança)
- Ajustes F0-F8: +3 dias (cobertura, E2E, TDD)
- Tamponagem de risco: +2 dias (validações extras)
```

---

## 🎯 Próximas Ações (TODAY)

### Immediate (2-4h)
1. ✅ Medir cobertura baseline (pytest + vitest)
2. ✅ Documentar em `docs/QUALITY_BASELINE.md`
3. ✅ Completar F0 Passo 3 (deps, tsc)

### This Week
4. ✅ Começar PRÉ-F0.0-S (pin deps + detect-secrets)
5. ✅ Começar PRÉ-F0.0-D (migrations tooling)
6. ✅ Começar PRÉ-F0.0-I (Railway migration)

### Aprovação
7. ✅ **Aprovação deste plano (v2) pelo usuário**
8. ✅ Começar execução Semana 1 (Ago 15-22)

---

## 📌 Referências de Documentos Gerados

1. **REFACTORING-PLAN-REVIEW.md** — Revisão detalhada do plano original
2. **ARCHITECTURE-DECISIONS.md** — 5 ADRs (arquitetura)
3. **ROADMAP-NEXT-2-WEEKS.md** — Roadmap executivo Sem 1-2
4. **SECURITY-REVISED-SCOPE.md** — Segurança (sem Auth + Telegram)
5. **SPECIALIST-REVIEWS-CONSOLIDATION.md** — Consolidação de 5 especialistas
6. **FINAL-PLAN-v2-APPROVED-BY-EXPERTS.md** — Este documento

---

**Status:** ✅ PRONTO PARA APROVAÇÃO  
**Próxima ação:** Você aprova este plano v2?

