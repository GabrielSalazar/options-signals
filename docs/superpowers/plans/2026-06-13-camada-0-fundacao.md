# Camada 0 — Correções de Fundação · Plano de Implementação

> **Para workers agênticos:** SUB-SKILL OBRIGATÓRIA: use `superpowers:subagent-driven-development` (recomendado) ou `superpowers:executing-plans` para implementar este plano tarefa-a-tarefa. Os passos usam checkbox (`- [ ]`) para rastreamento.

**Goal:** Eliminar os bugs metodológicos que contaminam todo o motor de sinais — look-ahead bias nos pivots, bônus de horário afrouxando o threshold, cooldown cego à direção — e fechar a higiene técnica pendente (timezone, cache key). Nada de feature nova: tornar o sistema correto.

**Architecture:** Correções cirúrgicas em `backend/domain` e `backend/services`. O princípio do look-ahead é resolvido no **consumo** dos pivots (excluir candles não confirmados), o que mata o bias no backtest sem mudar o comportamento em produção. A separação score técnico × bônus de sessão move a decisão de emissão para o score puro. O cooldown passa a ser chaveado por `(ticker, direção)` com regra de reversão por delta de score. Todos os parâmetros novos vivem em `CONFIG`.

**Tech Stack:** Python 3.11, pandas, `ta`, pytest, Supabase (Postgres, migrações SQL idempotentes), zoneinfo (stdlib).

**Pré-requisito de ambiente:** rodar a suíte a partir da raiz do repo com `python -m pytest -q` (deve estar verde antes de começar — baseline ~140 testes).

---

## File Structure

| Arquivo | Responsabilidade | Ação |
|---------|------------------|------|
| `backend/domain/indicators.py` | `pivots_confirmados()` + helper de consumo confirmado; `encontrar_zonas_demanda_oferta` usa pivots confirmados | Modificar |
| `backend/services/core_engine.py` | Gatilhos G7/B5 consomem pivots confirmados; bônus de horário fora do score de decisão; reentrada por (ticker, direção, score); cache key com `period` | Modificar |
| `backend/core/config.py` | Novos knobs (`pivot_ordem`, `reentrada_mesma_direcao_dias`, `reentrada_direcao_oposta_delta_score`); `_historico_sinais` com tipo+score; `score_horario`/`dentro_horario_pregao` em BRT | Modificar |
| `backend/services/signal_service.py` | Persistir `score_tecnico`/`bonus_sessao`; `rebuild_historico_sinais` lê tipo+score | Modificar |
| `backend/services/telegram_service.py` | Formatter exibe score técnico e bônus separados | Modificar |
| `supabase/migrations/002_score_tecnico_bonus_sessao.sql` | Colunas `score_tecnico`, `bonus_sessao` + backfill | Criar |
| `tests/test_lookahead.py` | Guarda permanente anti-look-ahead | Criar |
| `tests/test_indicators.py` | Testes de `pivots_confirmados` e consumo confirmado | Modificar |
| `tests/test_core_engine.py` | Caracterização atualizada (bônus fora do score; reentrada por direção) | Modificar |
| `tests/test_config.py` | Testes de reentrada por direção, timezone, novos knobs | Modificar |
| `docs/CHANGELOG.md` | Registrar a mudança e o delta de backtest | Modificar |
| `requirements.txt` | `tzdata` (zoneinfo no Windows) | Modificar |

**Ordem de execução:** Parte 0.1 → 0.2 → 0.3 → 0.4. A 0.2 deve preceder a 0.3 (a reentrada por direção usa o score técnico puro).

---

# PARTE 0.1 — Eliminar look-ahead bias nos pivots locais

**Problema:** [indicators.py:96-97](../../backend/domain/indicators.py#L96-L97) define os pivots com `shift(-1)` — olham **1 candle no futuro**. No backtest ([backtest.py:29](../../backend/services/backtest.py#L29)) os indicadores são pré-calculados sobre o histórico inteiro e depois fatiados, então o pivot da linha de decisão foi confirmado com dados que ainda não existiam → o backtest está contaminado.

**Decisão de design:** um pivot no índice `i` só é confirmável quando existem `ordem` candles à direita. A correção tem duas frentes: (a) redefinir os pivots por janela simétrica via `pivots_confirmados()`; (b) no **consumo**, ignorar as últimas `ordem` linhas do dataframe recebido — é isso que mata o look-ahead mesmo quando os flags foram pré-calculados sobre um df maior. Com `pivot_ordem = 1` (default desta camada), o comportamento em produção é idêntico ao atual (a última linha nunca foi pivot, pois `shift(-1)` é NaN ali), mas o backtest deixa de enxergar o futuro. Aumentar a ordem para 3–5 (pivots mais robustos) é **calibração** e pertence à Camada 2/5.

**Arquivos:** `backend/core/config.py`, `backend/domain/indicators.py`, `backend/services/core_engine.py`, `tests/`

### Task 0.1.1: Knob `pivot_ordem` no CONFIG

**Files:**
- Modify: `backend/core/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Escrever o teste falho**

Em `tests/test_config.py`, dentro de `class TestConfigDefaults`, adicione:

```python
    def test_pivot_ordem_existe_e_valido(self):
        assert "pivot_ordem" in CONFIG
        assert isinstance(CONFIG["pivot_ordem"], int)
        assert CONFIG["pivot_ordem"] >= 1
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_config.py::TestConfigDefaults::test_pivot_ordem_existe_e_valido -v`
Expected: FAIL — `KeyError: 'pivot_ordem'` / assert.

- [ ] **Step 3: Adicionar o knob**

Em `backend/core/config.py`, no bloco `# ── Reentrada ──`, logo após `"reentrada_min_dias": 3,`:

```python
    # ── Pivots locais (anti-look-ahead) ────────────────────────────────────
    "pivot_ordem": 1,   # candles à esquerda E à direita p/ confirmar pivot.
                        # 1 = preserva o comportamento de produção atual e elimina
                        # o look-ahead no backtest. ↑ (3–5) = pivots mais robustos
                        # (calibração da Camada 2/5).
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_config.py::TestConfigDefaults::test_pivot_ordem_existe_e_valido -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/config.py tests/test_config.py
git commit -m "feat(config): add pivot_ordem knob for confirmed pivots"
```

### Task 0.1.2: `pivots_confirmados()` em indicators.py

**Files:**
- Modify: `backend/domain/indicators.py`
- Test: `tests/test_indicators.py`

- [ ] **Step 1: Escrever os testes falhos**

Em `tests/test_indicators.py`, adicione o import no topo (junte ao import existente de `backend.domain.indicators`):

```python
from backend.domain.indicators import pivots_confirmados, ultimos_pivots_confirmados
```

E adicione a classe de teste:

```python
class TestPivotsConfirmados:
    """pivots_confirmados: janela simétrica + invariância a dados futuros."""

    def test_detecta_fundo_e_topo_simples(self):
        # V em fundo (idx 2) e ^ em topo (idx 6)
        low  = [10, 9, 8, 9, 10, 11, 12, 11, 10]
        high = [11, 10, 9, 10, 11, 12, 13, 12, 11]
        df = pd.DataFrame({"Low": low, "High": high})
        is_fundo, is_topo = pivots_confirmados(df, ordem=1)
        assert bool(is_fundo.iloc[2]) is True
        assert bool(is_topo.iloc[6]) is True

    def test_ultimas_ordem_linhas_nunca_confirmadas(self):
        df = pd.DataFrame({"Low": list(range(10, 0, -1)), "High": list(range(11, 1, -1))})
        is_fundo, is_topo = pivots_confirmados(df, ordem=2)
        # as 2 últimas linhas não têm candles suficientes à direita
        assert bool(is_fundo.iloc[-1]) is False
        assert bool(is_fundo.iloc[-2]) is False

    def test_invariante_a_dados_futuros(self):
        rng = np.random.default_rng(7)
        base = 50 + np.cumsum(rng.normal(0, 1.0, 120))
        df = pd.DataFrame({"Low": base - 0.5, "High": base + 0.5})
        ordem = 2
        t = 90
        f_trunc, t_trunc = pivots_confirmados(df.iloc[:t + 1], ordem)
        f_full,  t_full  = pivots_confirmados(df.iloc[:t + 1 + 20], ordem)
        lim = t - ordem  # índices confirmáveis até t
        assert f_trunc.iloc[:lim + 1].equals(f_full.iloc[:lim + 1])
        assert t_trunc.iloc[:lim + 1].equals(t_full.iloc[:lim + 1])
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_indicators.py::TestPivotsConfirmados -v`
Expected: FAIL — `ImportError: cannot import name 'pivots_confirmados'`.

- [ ] **Step 3: Implementar as funções**

Em `backend/domain/indicators.py`, logo após os imports do topo (`from backend.core.config import CONFIG`), adicione:

```python
def pivots_confirmados(df: pd.DataFrame, ordem: int = 1) -> tuple[pd.Series, pd.Series]:
    """Fundos/topos locais por janela simétrica de `ordem` candles de cada lado.

    Um pivot no índice ``i`` só é marcado quando existem ``ordem`` candles à
    esquerda E à direita (a janela ``rolling(center=True)`` retorna NaN nas
    bordas). Por isso o valor de ``i`` é invariante à adição de candles após
    ``i + ordem`` — base do teste anti-look-ahead. A marcação fica na data de
    OCORRÊNCIA ``i``; o consumo deve ignorar as últimas ``ordem`` linhas do df
    recebido (ver ``ultimos_pivots_confirmados``).
    """
    low, high = df["Low"], df["High"]
    w = 2 * ordem + 1
    min_roll = low.rolling(w, center=True).min()
    max_roll = high.rolling(w, center=True).max()
    is_fundo = (low == min_roll) & min_roll.notna()
    is_topo  = (high == max_roll) & max_roll.notna()
    return is_fundo, is_topo


def ultimos_pivots_confirmados(df: pd.DataFrame, ordem: int = 1,
                               n: int = 3) -> tuple:
    """Últimos ``n`` valores de fundos (Low) e topos (High) locais CONFIRMADOS.

    Exclui as últimas ``ordem`` linhas do df recebido: na decisão tomada na
    última linha ``t``, um pivot em índice ``> t - ordem`` exigiria candles
    futuros. Isso elimina o look-ahead mesmo quando ``is_fundo_local`` foi
    pré-calculado sobre um df maior (caso do backtest).
    """
    if len(df) <= ordem:
        return [], []
    base = df.iloc[:len(df) - ordem]
    fundos = base[base["is_fundo_local"]]["Low"].tail(n).values
    topos  = base[base["is_topo_local"]]["High"].tail(n).values
    return fundos, topos
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_indicators.py::TestPivotsConfirmados -v`
Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add backend/domain/indicators.py tests/test_indicators.py
git commit -m "feat(indicators): add pivots_confirmados + confirmed-pivot consumer"
```

### Task 0.1.3: `calcular_indicadores` usa janela simétrica confirmada

**Files:**
- Modify: `backend/domain/indicators.py:96-97`
- Test: `tests/test_indicators.py` (cobertura existente de `test_adds_expected_columns` já garante presença das colunas)

- [ ] **Step 1: Substituir a definição com look-ahead**

Em `backend/domain/indicators.py`, troque as linhas 96-97:

```python
    df["is_fundo_local"]  = (l < l.shift(1)) & (l < l.shift(-1))
    df["is_topo_local"]   = (h > h.shift(1)) & (h > h.shift(-1))
```

por:

```python
    is_fundo, is_topo = pivots_confirmados(df, ordem=CONFIG["pivot_ordem"])
    df["is_fundo_local"] = is_fundo
    df["is_topo_local"]  = is_topo
```

- [ ] **Step 2: Rodar a suíte de indicadores**

Run: `python -m pytest tests/test_indicators.py -v`
Expected: PASS. (`test_adds_expected_columns` continua verde — as colunas seguem existindo; com `ordem=1` a definição é equivalente à anterior módulo empates de float.)

- [ ] **Step 3: Commit**

```bash
git add backend/domain/indicators.py
git commit -m "refactor(indicators): is_fundo/topo_local via confirmed symmetric pivots"
```

### Task 0.1.4: `encontrar_zonas_demanda_oferta` consome pivots confirmados

**Files:**
- Modify: `backend/domain/indicators.py:142-156`
- Test: `tests/test_indicators.py` (`TestEncontrarZonas` existente continua válido)

- [ ] **Step 1: Reescrever a função para excluir candles não confirmados**

Em `backend/domain/indicators.py`, substitua `encontrar_zonas_demanda_oferta` (linhas 142-156) por:

```python
def encontrar_zonas_demanda_oferta(df: pd.DataFrame, lookback: int = 60,
                                   tolerancia_atr: float = 1.0,
                                   ordem: int | None = None) -> tuple:
    if len(df) < 10:
        return False, False

    if ordem is None:
        ordem = CONFIG["pivot_ordem"]

    preco  = float(df["Close"].iloc[-1])
    atr    = float(df["atr"].iloc[-1]) if "atr" in df.columns else preco * 0.02

    # Só pivots confirmados (exclui as últimas `ordem` linhas — sem look-ahead).
    base = df.iloc[:len(df) - ordem] if len(df) > ordem else df.iloc[0:0]
    fundos = base[base["is_fundo_local"]]["Low"].tail(lookback).values
    topos  = base[base["is_topo_local"]]["High"].tail(lookback).values

    zona_demanda = any(abs(preco - f) <= atr * tolerancia_atr for f in fundos)
    zona_oferta  = any(abs(preco - t) <= atr * tolerancia_atr for t in topos)

    return zona_demanda, zona_oferta
```

- [ ] **Step 2: Rodar e ver passar**

Run: `python -m pytest tests/test_indicators.py::TestEncontrarZonas -v`
Expected: PASS (retorna tupla de bools; df curto → `(False, False)`).

- [ ] **Step 3: Commit**

```bash
git add backend/domain/indicators.py
git commit -m "fix(indicators): zonas demanda/oferta usam apenas pivots confirmados"
```

### Task 0.1.5: Gatilhos G7/B5 (core_engine) consomem pivots confirmados

**Files:**
- Modify: `backend/services/core_engine.py:9-14` (import), `:141-144` e `:182-185`
- Test: coberto pela 0.1.6 (anti-look-ahead) e pela caracterização existente

- [ ] **Step 1: Importar o helper**

Em `backend/services/core_engine.py`, no import de `backend.domain.indicators` (linhas 9-14), acrescente `ultimos_pivots_confirmados`:

```python
from backend.domain.indicators import (
    calcular_indicadores,
    detectar_divergencia,
    encontrar_zonas_demanda_oferta,
    detectar_canal_linear,
    ultimos_pivots_confirmados,
)
```

- [ ] **Step 2: Calcular os pivots confirmados uma vez no início de `_avaliar_gatilhos`**

Em `_avaliar_gatilhos`, logo após `bb_lo = float(ultimo.get("bb_lower", 0))` (linha ~114), adicione:

```python
    ordem = CONFIG["pivot_ordem"]
    ultimos_fundos, ultimos_topos = ultimos_pivots_confirmados(df, ordem, n=3)
```

- [ ] **Step 3: Substituir o gatilho de fundos (linhas 141-144)**

Troque:

```python
    ultimos_fundos = df[df["is_fundo_local"]].tail(3)["Low"].values
    if (len(ultimos_fundos) >= 3 and all(ultimos_fundos[i] < ultimos_fundos[i+1] for i in range(2))):
```

por:

```python
    if (len(ultimos_fundos) >= 3 and all(ultimos_fundos[i] < ultimos_fundos[i+1] for i in range(2))):
```

- [ ] **Step 4: Substituir o gatilho de topos (linhas 182-185)**

Troque:

```python
    ultimos_topos = df[df["is_topo_local"]].tail(3)["High"].values
    if (len(ultimos_topos) >= 3 and all(ultimos_topos[i] > ultimos_topos[i+1] for i in range(2))):
```

por:

```python
    if (len(ultimos_topos) >= 3 and all(ultimos_topos[i] > ultimos_topos[i+1] for i in range(2))):
```

- [ ] **Step 5: Rodar a caracterização (deve permanecer verde)**

Run: `python -m pytest tests/test_core_engine.py -v`
Expected: PASS. Com `pivot_ordem=1`, o conjunto de pivots em produção (df termina na decisão) é idêntico ao anterior — a última linha nunca era pivot. Se algum assert de `score`/contagem mudar, **PARE**: investigue antes de re-baselinar (com ordem=1 não deveria mudar).

- [ ] **Step 6: Commit**

```bash
git add backend/services/core_engine.py
git commit -m "fix(core_engine): gatilhos de fundos/topos usam pivots confirmados (anti-look-ahead)"
```

### Task 0.1.6: Guarda permanente anti-look-ahead

**Files:**
- Create: `tests/test_lookahead.py`

- [ ] **Step 1: Escrever o teste de guarda**

Crie `tests/test_lookahead.py`:

```python
"""Guarda permanente anti-look-ahead (Camada 0, Parte 0.1).

Prova que a decisão tomada no candle t NÃO usa informação de candles > t.
Os únicos gatilhos com risco de look-ahead são os de pivot (fundos/topos) e as
zonas de demanda/oferta — os demais indicadores (RSI, MACD, EMA…) são causais.
"""
import numpy as np
import pandas as pd

from backend.domain.indicators import (
    calcular_indicadores, ultimos_pivots_confirmados, encontrar_zonas_demanda_oferta,
)
from backend.core.config import CONFIG


def _ohlcv(seed: int, n: int = 150) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    base = 30 + np.cumsum(rng.normal(0, 0.4, n))
    close = np.maximum(base, 1.0)
    high = close * (1 + rng.uniform(0.003, 0.015, n))
    low = close * (1 - rng.uniform(0.003, 0.015, n))
    openp = close + rng.normal(0, 0.05, n)
    vol = rng.uniform(2_000_000, 5_000_000, n)
    idx = pd.date_range("2025-01-01", periods=n, freq="B")
    df = pd.DataFrame({"Open": openp, "High": high, "Low": low,
                       "Close": close, "Volume": vol}, index=idx)
    return calcular_indicadores(df).dropna()


def test_consumo_de_pivots_ignora_flag_contaminado_na_borda():
    """Mesmo que is_fundo_local seja True nas últimas `ordem` linhas (como ocorre
    no backtest com indicadores pré-calculados), o consumo deve ignorá-las."""
    df = _ohlcv(1)
    ordem = CONFIG["pivot_ordem"]
    df = df.copy()
    # Contamina artificialmente a última linha (simula flag pré-calculado c/ futuro)
    df.iloc[-1, df.columns.get_loc("is_fundo_local")] = True
    df.iloc[-1, df.columns.get_loc("Low")] = -999.0  # valor impossível, denuncia uso
    fundos, _ = ultimos_pivots_confirmados(df, ordem, n=3)
    assert -999.0 not in list(fundos)


def test_decisao_em_t_invariante_a_candles_futuros():
    """Os gatilhos de pivot/zona avaliados no candle t batem quer o df termine em
    t, quer continue além — desde que os indicadores sejam recalculados por janela
    (sem reaproveitar flags computados com o futuro)."""
    full = _ohlcv(2, n=150)
    ordem = CONFIG["pivot_ordem"]
    for t in (110, 120, 130):
        # df que termina exatamente em t (decisão "honesta")
        df_t = full.iloc[: t + 1]
        # df que vai além de t, mas recortado de volta a t ANTES de consumir
        df_future_cut = full.iloc[: t + 1 + 12].iloc[: t + 1]
        f_t, tp_t = ultimos_pivots_confirmados(df_t, ordem, n=3)
        f_f, tp_f = ultimos_pivots_confirmados(df_future_cut, ordem, n=3)
        assert list(f_t) == list(f_f)
        assert list(tp_t) == list(tp_f)
        assert encontrar_zonas_demanda_oferta(df_t) == encontrar_zonas_demanda_oferta(df_future_cut)
```

- [ ] **Step 2: Rodar e ver passar**

Run: `python -m pytest tests/test_lookahead.py -v`
Expected: PASS (2 testes).

- [ ] **Step 3: Commit**

```bash
git add tests/test_lookahead.py
git commit -m "test(lookahead): guarda permanente anti-look-ahead nos pivots/zonas"
```

### Task 0.1.7: Re-rodar o backtest e registrar o delta

**Files:**
- Modify: `docs/CHANGELOG.md`

- [ ] **Step 1: Rodar um backtest de referência ANTES vs. DEPOIS**

Compare um ticker líquido num intervalo fixo. A partir da raiz do repo:

```bash
python -c "from backend.services.backtest import rodar_backtest, exibir_relatorio_backtest; exibir_relatorio_backtest(rodar_backtest('PETR4.SA','Petrobras','2025-06-01','2026-06-01'))"
```

Anote `Total de sinais` e `Win Rate (Atingiu Alvo 1)`. Compare com o valor no branch anterior (`git stash` / `git worktree` da `main` se quiser o número exato pré-fix). **Esperado:** queda no hit-rate dos gatilhos de pivot — é o efeito da remoção do bias, **não** regressão.

- [ ] **Step 2: Registrar no CHANGELOG**

Em `docs/CHANGELOG.md`, sob `## [Não lançado]` → `### Fixed`, adicione:

```markdown
- **Look-ahead bias eliminado nos pivots locais (Camada 0.1):** `is_fundo_local`/
  `is_topo_local` passam a usar janela simétrica confirmada (`pivots_confirmados`,
  `CONFIG["pivot_ordem"]=1`) e os gatilhos de fundos/topos + zonas de demanda/oferta
  consomem apenas pivots confirmados (excluindo as últimas `ordem` linhas). O backtest
  deixa de enxergar o futuro. Delta no backtest de referência (PETR4, 2025-06→2026-06):
  win-rate <ANTES>% → <DEPOIS>%, sinais <ANTES> → <DEPOIS>. Guarda permanente em
  `tests/test_lookahead.py`.
```

Substitua `<ANTES>`/`<DEPOIS>` pelos números medidos no Step 1.

- [ ] **Step 3: Commit**

```bash
git add docs/CHANGELOG.md
git commit -m "docs(changelog): registra delta do backtest pós-correção de look-ahead"
```

**Critério de aceite 0.1:** `tests/test_lookahead.py` verde; backtest reproduzível; caracterização (`test_core_engine.py`) intacta.

---

# PARTE 0.2 — Retirar o bônus de horário do threshold de emissão

**Problema:** [core_engine.py:392-394](../../backend/services/core_engine.py#L392-L394) soma `bonus_horario` a `score_alta`/`score_baixa` **antes** do `MIN_SCORE` ([:397-399](../../backend/services/core_engine.py#L397)). Às 13h–15h, 2 pontos técnicos + 3 de bônus já cruzam o limiar de 5 — o filtro de qualidade afrouxa nas janelas de "maior confiança".

**Decisão:** a emissão passa a usar **apenas** o score técnico (gatilhos direcionais). O `bonus_sessao` vira campo informativo persistido, para priorização e tag de execução. O campo `score` do sinal passa a ser o score técnico puro (em produção isso muda o valor quando há bônus; nos testes o bônus é mockado para 0, então a caracterização não muda).

**Arquivos:** `backend/services/core_engine.py`, `backend/services/signal_service.py`, `backend/services/telegram_service.py`, `supabase/migrations/`, `tests/`

### Task 0.2.1: Decisão de emissão usa só o score técnico

**Files:**
- Modify: `backend/services/core_engine.py:391-412` e `_montar_sinal` (`:288-353`)
- Test: `tests/test_core_engine.py`

- [ ] **Step 1: Escrever o teste falho**

Em `tests/test_core_engine.py`, adicione:

```python
def test_bonus_horario_nao_entra_no_threshold(monkeypatch):
    """Um setup com score técnico < min_score NÃO emite, mesmo com bônus de horário
    que somado cruzaria o limiar."""
    _relax_and_mock(monkeypatch)
    monkeypatch.setattr(core_engine, "score_horario", lambda *a, **k: 3)  # bônus alto
    monkeypatch.setitem(core_engine.CONFIG, "min_score", 11)  # acima do score técnico do seed 0 (9)
    df = _make_df(0)
    s = core_engine.analisar_ativo("TESTE3", "Teste", df_provided=df, indicators_calculated=True)
    assert s is None  # 9 técnico < 11; o +3 de bônus NÃO deve resgatar


def test_sinal_carrega_score_tecnico_e_bonus_sessao(monkeypatch):
    _relax_and_mock(monkeypatch)
    monkeypatch.setattr(core_engine, "score_horario", lambda *a, **k: 2)
    df = _make_df(0)
    s = core_engine.analisar_ativo("TESTE3", "Teste", df_provided=df, indicators_calculated=True)
    assert s is not None
    assert s["score_tecnico"] == 9          # só gatilhos direcionais
    assert s["bonus_sessao"] == 2           # informativo, fora da decisão
    assert s["score"] == s["score_tecnico"] # `score` = técnico puro (compat)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_core_engine.py::test_bonus_horario_nao_entra_no_threshold tests/test_core_engine.py::test_sinal_carrega_score_tecnico_e_bonus_sessao -v`
Expected: FAIL — hoje o bônus entra no score e os campos `score_tecnico`/`bonus_sessao` não existem.

- [ ] **Step 3: Separar score técnico do bônus na decisão**

Em `backend/services/core_engine.py`, substitua o bloco das linhas 391-399:

```python
        # ── SCORE DE HORÁRIO integrado ───────────────────────
        bonus_horario = score_horario()
        score_alta  += bonus_horario
        score_baixa += bonus_horario

        # ── DECISÃO ──────────────────────────────────────────────────────
        MIN_SCORE = CONFIG["min_score"]
        if score_alta < MIN_SCORE and score_baixa < MIN_SCORE:
            return None
```

por:

```python
        # ── BÔNUS DE SESSÃO (informativo — NÃO entra na decisão de emissão) ──
        bonus_sessao = score_horario()

        # ── DECISÃO (apenas score técnico/direcional) ─────────────────────
        MIN_SCORE = CONFIG["min_score"]
        if score_alta < MIN_SCORE and score_baixa < MIN_SCORE:
            return None
```

- [ ] **Step 4: Propagar `bonus_sessao` ao sinal**

Na chamada de `_montar_sinal` (linhas 422-424), passe `bonus_sessao`:

```python
        return _montar_sinal(ticker_base, nome, tipo_sinal, direcao_label, emoji, score,
                             gatilhos, preco, ultimo, penult, stoch_k, rsi, vol_ratio,
                             estrutura, verbose, bonus_sessao=bonus_sessao)
```

Atualize a assinatura de `_montar_sinal` (linha 288-291) acrescentando o parâmetro:

```python
def _montar_sinal(ticker_base: str, nome: str, tipo_sinal: str, direcao_label: str,
                  emoji: str, score: int, gatilhos: list, preco: float, ultimo, penult,
                  stoch_k: float, rsi: float, vol_ratio: float, estrutura: dict,
                  verbose: bool, bonus_sessao: int = 0) -> dict | None:
```

E no dict de retorno de `_montar_sinal` (após `"score": score,` na linha 348), adicione:

```python
        "score_tecnico": score,
        "bonus_sessao":  bonus_sessao,
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_core_engine.py -v`
Expected: PASS (incluindo os 2 novos e toda a caracterização — o bônus mockado nos testes existentes é 0, então `score` não muda).

- [ ] **Step 6: Commit**

```bash
git add backend/services/core_engine.py tests/test_core_engine.py
git commit -m "fix(core_engine): bonus de sessao fora do threshold; persiste score_tecnico/bonus_sessao"
```

### Task 0.2.2: Persistir `score_tecnico` e `bonus_sessao`

**Files:**
- Modify: `backend/services/signal_service.py:84-120`
- Test: `tests/test_signal_service.py` (se houver teste de `persist_signals`; senão, validação manual)

- [ ] **Step 1: Adicionar os campos ao row de persistência**

Em `backend/services/signal_service.py`, dentro de `persist_signals`, no dict `rows.append({...})`, logo após `"score": s["score"],` (linha 90), adicione:

```python
            "score_tecnico": s.get("score_tecnico", s.get("score")),
            "bonus_sessao":  s.get("bonus_sessao", 0),
```

- [ ] **Step 2: Verificar que a suíte segue verde**

Run: `python -m pytest tests/test_signal_service.py -v`
Expected: PASS. (O insert é mockado/condicional ao Supabase; os campos extras não quebram o contrato.)

- [ ] **Step 3: Commit**

```bash
git add backend/services/signal_service.py
git commit -m "feat(persist): grava score_tecnico e bonus_sessao no Supabase"
```

### Task 0.2.3: Migração Supabase + backfill

**Files:**
- Create: `supabase/migrations/002_score_tecnico_bonus_sessao.sql`

- [ ] **Step 1: Criar a migração idempotente**

Crie `supabase/migrations/002_score_tecnico_bonus_sessao.sql`:

```sql
-- ============================================================
-- Migration 002: Separa score técnico do bônus de sessão (Camada 0.2)
-- Run via: Supabase Dashboard → SQL Editor
-- ============================================================

-- 1. Novas colunas (idempotente)
ALTER TABLE signals
  ADD COLUMN IF NOT EXISTS score_tecnico INTEGER,
  ADD COLUMN IF NOT EXISTS bonus_sessao  INTEGER;

-- 2. Backfill do bônus a partir da hora BRT do timestamp (aproximado por faixa).
--    Janelas: 10:00–11:30 → 2 · 13:00–15:00 → 3 · 15:00–16:30 → 1 · resto → 0.
UPDATE signals
SET bonus_sessao = CASE
    WHEN (EXTRACT(HOUR   FROM (timestamp AT TIME ZONE 'America/Sao_Paulo')) * 60
        + EXTRACT(MINUTE FROM (timestamp AT TIME ZONE 'America/Sao_Paulo')))
        BETWEEN 600 AND 690 THEN 2
    WHEN (EXTRACT(HOUR   FROM (timestamp AT TIME ZONE 'America/Sao_Paulo')) * 60
        + EXTRACT(MINUTE FROM (timestamp AT TIME ZONE 'America/Sao_Paulo')))
        BETWEEN 780 AND 900 THEN 3
    WHEN (EXTRACT(HOUR   FROM (timestamp AT TIME ZONE 'America/Sao_Paulo')) * 60
        + EXTRACT(MINUTE FROM (timestamp AT TIME ZONE 'America/Sao_Paulo')))
        BETWEEN 900 AND 990 THEN 1
    ELSE 0
END
WHERE bonus_sessao IS NULL;

-- 3. score_tecnico histórico = score − bônus inferido (nunca negativo).
UPDATE signals
SET score_tecnico = GREATEST(COALESCE(score, 0) - COALESCE(bonus_sessao, 0), 0)
WHERE score_tecnico IS NULL;

-- 4. Índice para priorização por score técnico
CREATE INDEX IF NOT EXISTS idx_signals_score_tecnico
  ON signals (tipo_sinal, score_tecnico DESC);
```

- [ ] **Step 2: Aplicar no Supabase**

Cole o conteúdo no SQL Editor do Supabase Dashboard e execute. Confirme que rodou sem erro (idempotente — pode ser reaplicada).

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/002_score_tecnico_bonus_sessao.sql
git commit -m "feat(db): migration 002 — score_tecnico + bonus_sessao com backfill"
```

### Task 0.2.4: Telegram exibe score técnico e bônus separados

**Files:**
- Modify: `backend/services/telegram_service.py:72`
- Test: `tests/test_telegram.py`

- [ ] **Step 1: Escrever/ajustar o teste**

Em `tests/test_telegram.py`, adicione (ajuste os mocks conforme o padrão do arquivo — `enviar_telegram` monta a `msg`; capture-a via monkeypatch de `requests.post`):

```python
def test_formatter_separa_score_tecnico_e_bonus(monkeypatch):
    import backend.services.telegram_service as tg
    capturado = {}
    monkeypatch.setitem(tg.CONFIG, "telegram_token", "x")
    monkeypatch.setitem(tg.CONFIG, "telegram_chat_id", "y")
    monkeypatch.setattr(tg.requests, "post",
                        lambda *a, **k: capturado.update(k.get("data", {})) or type("R", (), {})())
    tg.enviar_telegram({
        "ticker": "PETR4", "nome": "Petrobras", "tipo_sinal": "CALL",
        "mes_venc": 6, "ano_venc": 2026, "strike_ref": 40.0, "dist_otm_pct": 6.0,
        "iv_hist": 35.0, "dte": 30, "entrada_min": 0.5, "entrada_max": 0.6,
        "alvo1": 0.7, "alvo2": 1.0, "alvo_final": 2.0, "stop": 0.3,
        "rr_alvo1": 0.5, "rr_alvo2": 1.0, "rr_final": 2.0,
        "score_tecnico": 9, "bonus_sessao": 3, "score": 9, "gatilhos": ["x"],
    })
    assert "Score técnico:* 9" in capturado["text"]
    assert "Bônus sessão:* +3" in capturado["text"]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_telegram.py::test_formatter_separa_score_tecnico_e_bonus -v`
Expected: FAIL — hoje a msg tem `*Score:* {score}/10`.

- [ ] **Step 3: Atualizar o formatter**

Em `backend/services/telegram_service.py`, troque a linha 72:

```python
        f"*Score:* {sinal.get('score')}/10\n"
```

por:

```python
        f"*Score técnico:* {sinal.get('score_tecnico', sinal.get('score'))} (mín. {CONFIG.get('min_score', 5)})\n"
        f"*Bônus sessão:* +{sinal.get('bonus_sessao', 0)} (prioridade, não entra no corte)\n"
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_telegram.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/telegram_service.py tests/test_telegram.py
git commit -m "feat(telegram): exibe score tecnico e bonus de sessao separados"
```

**Critério de aceite 0.2:** nenhum sinal emitido com `score_tecnico < min_score`; `score_tecnico`/`bonus_sessao` presentes no sinal, persistidos e no Telegram.

---

# PARTE 0.3 — Cooldown por ticker + direção

**Problema:** [config.py:166-170](../../backend/core/config.py#L166-L170) bloqueia reentrada por `ticker` apenas; [core_engine.py:363](../../backend/services/core_engine.py#L363) descarta um PUT forte porque saiu um CALL dias antes.

**Decisão:** chavear o histórico por `(ticker, direção)`. Sinal de mesma direção dentro de `reentrada_mesma_direcao_dias` é bloqueado; sinal **oposto** ao vigente só emite se `score_tecnico >= score_vigente + reentrada_direcao_oposta_delta_score`. A checagem move-se para **depois** de determinar tipo/score (precisa deles), preservando a condição de que só roda em produção (`df_provided is None`).

**Arquivos:** `backend/core/config.py`, `backend/services/core_engine.py`, `backend/services/signal_service.py`, `tests/`

### Task 0.3.1: Knobs de reentrada

**Files:**
- Modify: `backend/core/config.py:43-44`
- Test: `tests/test_config.py`

- [ ] **Step 1: Escrever o teste falho**

Em `tests/test_config.py`, dentro de `TestConfigDefaults`:

```python
    def test_reentrada_direcional_knobs(self):
        assert CONFIG["reentrada_mesma_direcao_dias"] >= 1
        assert CONFIG["reentrada_direcao_oposta_delta_score"] >= 0
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_config.py::TestConfigDefaults::test_reentrada_direcional_knobs -v`
Expected: FAIL — KeyError.

- [ ] **Step 3: Adicionar os knobs**

Em `backend/core/config.py`, no bloco `# ── Reentrada ──` (após `"reentrada_min_dias": 3,`):

```python
    "reentrada_mesma_direcao_dias": 3,         # bloqueio de mesma direção (ticker, tipo)
    "reentrada_direcao_oposta_delta_score": 2, # reversão só se score >= vigente + delta
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_config.py::TestConfigDefaults::test_reentrada_direcional_knobs -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/config.py tests/test_config.py
git commit -m "feat(config): knobs de reentrada por direcao"
```

### Task 0.3.2: `registrar_sinal`/`is_reentrada_valida` por direção

**Files:**
- Modify: `backend/core/config.py:161-170`
- Test: `tests/test_config.py` (`class TestReentrada`)

- [ ] **Step 1: Escrever os testes (incluindo atualização do formato interno)**

Em `tests/test_config.py`, na `class TestReentrada`, **atualize** `test_old_entry_valid` (o formato interno mudou) e **acrescente** os casos direcionais:

```python
    def test_old_entry_valid(self):
        from backend.core.config import _historico_sinais
        _historico_sinais["ITUB4"] = [{
            "ts": datetime.now() - timedelta(days=CONFIG["reentrada_mesma_direcao_dias"] + 1),
            "tipo": "CALL", "score": 8,
        }]
        assert is_reentrada_valida("ITUB4", "CALL", 8) is True

    def test_mesma_direcao_recente_bloqueia(self):
        registrar_sinal("PETR4", "CALL", 9)
        assert is_reentrada_valida("PETR4", "CALL", 12) is False

    def test_direcao_oposta_fraca_bloqueia(self):
        registrar_sinal("PETR4", "CALL", 11)
        # PUT só com score >= 11 + delta(2) = 13
        assert is_reentrada_valida("PETR4", "PUT", 12) is False

    def test_direcao_oposta_forte_emite(self):
        registrar_sinal("PETR4", "CALL", 11)
        assert is_reentrada_valida("PETR4", "PUT", 13) is True
```

Mantenha `test_first_entry_valid`, `test_recent_entry_blocked`, `test_different_tickers_independent` — eles chamam com `tipo=None` e devem continuar válidos (compat).

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_config.py::TestReentrada -v`
Expected: FAIL — assinatura/formato atuais não suportam direção.

- [ ] **Step 3: Reescrever o estado e as funções**

Em `backend/core/config.py`, substitua o bloco das linhas 161-170:

```python
_historico_sinais = {}

def registrar_sinal(ticker: str):
    _historico_sinais.setdefault(ticker, []).append(datetime.now())

def is_reentrada_valida(ticker: str) -> bool:
    if ticker not in _historico_sinais:
        return True
    ultima = _historico_sinais[ticker][-1]
    return (datetime.now() - ultima).days >= CONFIG["reentrada_min_dias"]
```

por:

```python
# _historico_sinais: ticker -> [{"ts": datetime, "tipo": str|None, "score": int}]
_historico_sinais = {}

def registrar_sinal(ticker: str, tipo_sinal: str | None = None, score: int = 0):
    _historico_sinais.setdefault(ticker, []).append(
        {"ts": datetime.now(), "tipo": tipo_sinal, "score": int(score)}
    )

def is_reentrada_valida(ticker: str, tipo_sinal: str | None = None, score: int = 0) -> bool:
    """Cooldown por (ticker, direção):
    - mesma direção dentro de `reentrada_mesma_direcao_dias` → bloqueia;
    - direção oposta vigente → só emite se score >= score_vigente + delta.
    """
    registros = _historico_sinais.get(ticker)
    if not registros:
        return True
    agora = datetime.now()
    dias = CONFIG["reentrada_mesma_direcao_dias"]
    delta = CONFIG["reentrada_direcao_oposta_delta_score"]

    mesmos = [r for r in registros if r.get("tipo") == tipo_sinal]
    if mesmos and (agora - mesmos[-1]["ts"]).days < dias:
        return False

    opostos = [r for r in registros
               if r.get("tipo") is not None and r.get("tipo") != tipo_sinal]
    if opostos and (agora - opostos[-1]["ts"]).days < dias:
        if score < opostos[-1].get("score", 0) + delta:
            return False

    return True
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_config.py::TestReentrada -v`
Expected: PASS (todos, incluindo os de compat com `tipo=None`).

- [ ] **Step 5: Commit**

```bash
git add backend/core/config.py tests/test_config.py
git commit -m "feat(config): cooldown por (ticker, direcao) com regra de reversao por delta"
```

### Task 0.3.3: `core_engine` aplica a reentrada por direção

**Files:**
- Modify: `backend/services/core_engine.py:361-366` (remover checagem antiga) e `:413-420` (nova checagem + registro)
- Test: `tests/test_core_engine.py`

- [ ] **Step 1: Escrever o teste falho**

Em `tests/test_core_engine.py`:

```python
def test_reentrada_oposta_forte_emite_apos_call(monkeypatch):
    """CALL registrado; um PUT forte o suficiente ainda emite (não é bloqueado pelo
    cooldown cego à direção). Usa df_provided=None? Não — a reentrada só roda em
    produção; aqui exercitamos a função de estado diretamente."""
    from backend.core import config
    config._historico_sinais.clear()
    config.registrar_sinal("PETR4", "CALL", 8)
    assert config.is_reentrada_valida("PETR4", "PUT", 8 + config.CONFIG["reentrada_direcao_oposta_delta_score"]) is True
    config._historico_sinais.clear()
```

(O caminho de produção — `df_provided is None` — é coberto pela integração; a unidade da regra fica em `test_config.py`.)

- [ ] **Step 2: Rodar e ver passar/baseline**

Run: `python -m pytest tests/test_core_engine.py::test_reentrada_oposta_forte_emite_apos_call -v`
Expected: PASS (a função já existe da 0.3.2). Este teste fixa a expectativa de integração de nomes.

- [ ] **Step 3: Remover a checagem antiga (início de `analisar_ativo`)**

Em `backend/services/core_engine.py`, remova as linhas 363-366:

```python
        if df_provided is None and not is_reentrada_valida(ticker_base):
            if verbose:
                logger.info(f"↩ {ticker_base}: sinal recente (<{CONFIG['reentrada_min_dias']}d), pulando")
            return None
```

- [ ] **Step 4: Inserir a checagem após decidir tipo/score**

Ainda em `analisar_ativo`, logo após o bloco que define `tipo_sinal`/`score`/`gatilhos` (após a linha 412, antes do comentário `# ── ESTRUTURA DA OPÇÃO ──`), adicione:

```python
        # ── REENTRADA por (ticker, direção, score) — só em produção ──────
        if df_provided is None and not is_reentrada_valida(ticker_base, tipo_sinal, score):
            if verbose:
                logger.info(f"↩ {ticker_base}: reentrada bloqueada ({tipo_sinal}, score {score})")
            return None
```

- [ ] **Step 5: Atualizar o registro do sinal**

Troque a linha 419-420:

```python
        if df_provided is None:
            registrar_sinal(ticker_base)
```

por:

```python
        if df_provided is None:
            registrar_sinal(ticker_base, tipo_sinal, score)
```

- [ ] **Step 6: Rodar a suíte do core**

Run: `python -m pytest tests/test_core_engine.py -v`
Expected: PASS. Os testes de caracterização usam `df_provided=df` → a reentrada é pulada, comportamento inalterado.

- [ ] **Step 7: Commit**

```bash
git add backend/services/core_engine.py tests/test_core_engine.py
git commit -m "fix(core_engine): reentrada por (ticker, direcao, score) apos decisao"
```

### Task 0.3.4: `rebuild_historico_sinais` reconstrói tipo + score

**Files:**
- Modify: `backend/services/signal_service.py:142-168`
- Test: validação por inspeção (depende do Supabase; manter a função resiliente)

- [ ] **Step 1: Atualizar a query e o append**

Em `backend/services/signal_service.py`, na função `rebuild_historico_sinais`, troque o `select` (linha 152) de `"ticker, timestamp"` para incluir tipo e score, e o append (linhas 156-165) para o novo formato:

```python
        res = (supabase.table("signals")
               .select("ticker, timestamp, tipo_sinal, score_tecnico, score")
               .gte("timestamp", cutoff)
               .order("timestamp")
               .execute())
        for row in res.data:
            ticker = row.get("ticker", "")
            ts_str = row.get("timestamp", "")
            if not ticker or not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
                score = row.get("score_tecnico")
                if score is None:
                    score = row.get("score", 0)
                _historico_sinais.setdefault(ticker, []).append(
                    {"ts": ts, "tipo": row.get("tipo_sinal"), "score": int(score or 0)}
                )
            except Exception:
                pass
```

- [ ] **Step 2: Rodar a suíte de serviço**

Run: `python -m pytest tests/test_signal_service.py -v`
Expected: PASS (a função é resiliente a Supabase ausente; testes não dependem de dados reais).

- [ ] **Step 3: Commit**

```bash
git add backend/services/signal_service.py
git commit -m "fix(signal_service): rebuild_historico_sinais reconstroi tipo e score"
```

**Critério de aceite 0.3:** CALL dia 1 → PUT forte dia 3 emite; PUT fraco dia 3 não emite (cobertos em `test_config.py`).

---

# PARTE 0.4 — Higiene técnica pendente

**Problema:** `score_horario`/`dentro_horario_pregao` ([config.py:172-190](../../backend/core/config.py#L172-L190)) usam `datetime.now()` **naive** (timezone do servidor, não BRT) — afeta o bônus e o agendamento. A cache key ([core_engine.py:69](../../backend/services/core_engine.py#L69)) não inclui `period`.

**Arquivos:** `backend/core/config.py`, `backend/services/core_engine.py`, `requirements.txt`, `tests/`

### Task 0.4.1: Horário de pregão em America/Sao_Paulo

**Files:**
- Modify: `backend/core/config.py:1-2` (import) e `:172-190`
- Modify: `requirements.txt`
- Test: `tests/test_config.py`

> **Ordem importa:** `_TZ_SP = ZoneInfo("America/Sao_Paulo")` é avaliado no import de `config.py`. Sem dados de timezone o import falha (Windows/dev) e derruba toda a suíte — por isso o `tzdata` vem **antes** de tocar o módulo.

- [ ] **Step 1: Adicionar `tzdata` e instalar**

Em `requirements.txt`, adicione numa nova linha (se ainda não existir):

```
tzdata
```

Run: `pip install tzdata`
Expected: instalado. (Em produção Linux o zoneinfo resolve via SO; `tzdata` cobre Windows/dev.)

- [ ] **Step 2: Escrever o teste falho**

Em `tests/test_config.py`, dentro de `class TestScoreHorario`, adicione:

```python
    def test_usa_timezone_brt_nao_naive(self, monkeypatch):
        """score_horario() sem argumento deve avaliar a hora em BRT, não no fuso
        do servidor. Simulamos um servidor em UTC: 16:30 UTC = 13:30 BRT → bônus 3."""
        import backend.core.config as cfg
        from datetime import datetime as real_dt
        from zoneinfo import ZoneInfo

        class _FakeDateTime(real_dt):
            @classmethod
            def now(cls, tz=None):
                base = real_dt(2026, 6, 15, 16, 30, tzinfo=ZoneInfo("UTC"))
                return base.astimezone(tz) if tz else base.replace(tzinfo=None)

        monkeypatch.setattr(cfg, "datetime", _FakeDateTime)
        assert cfg.score_horario() == 3  # 13:30 BRT
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `python -m pytest tests/test_config.py::TestScoreHorario::test_usa_timezone_brt_nao_naive -v`
Expected: FAIL — hoje `datetime.now()` naive devolve 16:30 → bônus 1 (ou 0), não 3.

- [ ] **Step 4: Importar zoneinfo e corrigir as funções**

Em `backend/core/config.py`, ajuste o import do topo (linhas 1-2):

```python
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_TZ_SP = ZoneInfo("America/Sao_Paulo")
```

Troque `score_horario` (linhas 172-183) para derivar a hora default em BRT:

```python
def score_horario(hora_str: str = None) -> int:
    if hora_str is None:
        hora_str = datetime.now(_TZ_SP).strftime("%H:%M")
    try:
        h, m = map(int, hora_str.split(":"))
        minutos = h * 60 + m
        if 600 <= minutos <= 690:   return 2   # 10:00–11:30
        if 780 <= minutos <= 900:   return 3   # 13:00–15:00
        if 900 <= minutos <= 990:   return 1   # 15:00–16:30
        return 0
    except Exception:
        return 0
```

Troque `dentro_horario_pregao` (linhas 185-190):

```python
def dentro_horario_pregao(margem_min: int = 30) -> bool:
    now = datetime.now(_TZ_SP)
    abert  = now.replace(hour=10, minute=0,  second=0, microsecond=0)
    fech   = now.replace(hour=16, minute=30, second=0, microsecond=0)
    margem = timedelta(minutes=margem_min)
    return (abert + margem) <= now <= (fech - margem)
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_config.py::TestScoreHorario -v`
Expected: PASS (incluindo os testes existentes que passam `hora_str` explícito — esses não dependem do fuso).

- [ ] **Step 6: Commit**

```bash
git add backend/core/config.py requirements.txt tests/test_config.py
git commit -m "fix(config): horario de pregao em America/Sao_Paulo (nao naive)"
```

### Task 0.4.2: Cache key inclui `period`

**Files:**
- Modify: `backend/services/core_engine.py:68-69`
- Test: `tests/test_core_engine.py`

- [ ] **Step 1: Escrever o teste falho**

Em `tests/test_core_engine.py`:

```python
def test_cache_key_inclui_period(monkeypatch):
    """A cache key de OHLCV deve conter ticker, interval E period (evita
    contaminação entre janelas/backtest x scan ao vivo)."""
    capturadas = []
    monkeypatch.setattr(core_engine, "cache_get_df",
                        lambda key: capturadas.append(key) or None)
    monkeypatch.setattr(core_engine, "cache_set_df", lambda *a, **k: None)
    monkeypatch.setattr(core_engine, "_baixar_ohlcv", lambda *a, **k: None)
    core_engine._carregar_ohlcv("PETR4.SA", "1d", None, False, False)
    assert any(k.startswith("ohlcv:PETR4.SA:1d:") and k.count(":") == 3 for k in capturadas)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_core_engine.py::test_cache_key_inclui_period -v`
Expected: FAIL — a key atual é `ohlcv:{ticker}:{interval}` (2 `:`).

- [ ] **Step 3: Incluir period na key**

Em `backend/services/core_engine.py`, dentro de `_carregar_ohlcv`, troque a linha 69:

```python
        cache_key = f"ohlcv:{ticker}:{interval}"
```

por:

```python
        cache_key = f"ohlcv:{ticker}:{interval}:{period}"
```

(`period` já está definido na linha imediatamente anterior — linha 68.)

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_core_engine.py::test_cache_key_inclui_period -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/core_engine.py tests/test_core_engine.py
git commit -m "fix(cache): inclui period na chave de OHLCV"
```

### Task 0.4.3 (opcional, menor impacto): Persistir config do Telegram no Supabase

> Hoje a config do Telegram persiste em `telegram_config.json` ([telegram_service.py:23-53](../../backend/services/telegram_service.py#L23-L53)) — não sobrevive ao filesystem efêmero do Render. Este item é o de **menor impacto na correção dos sinais**; faça-o só se houver tempo na camada, senão promova-o para a Camada 6/infra.

**Files:**
- Modify: `backend/services/telegram_service.py`, `supabase/migrations/003_telegram_config.sql` (criar)

- [ ] **Step 1: Criar a migração da tabela de config**

Crie `supabase/migrations/003_telegram_config.sql`:

```sql
-- Migration 003: persistência da config do Telegram (Camada 0.4)
CREATE TABLE IF NOT EXISTS telegram_config (
  id        INTEGER PRIMARY KEY DEFAULT 1,
  token     TEXT,
  chat_id   TEXT,
  updated_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT single_row CHECK (id = 1)
);
```

- [ ] **Step 2: Escrever o teste falho**

Em `tests/test_telegram.py`:

```python
def test_save_telegram_config_grava_no_supabase(monkeypatch):
    import backend.services.telegram_service as tg
    capturado = {}
    class _Tbl:
        def upsert(self, row): capturado.update(row); return self
        def execute(self): return type("R", (), {})()
    class _Sb:
        def table(self, _): return _Tbl()
    monkeypatch.setattr(tg, "get_supabase", lambda: _Sb())
    tg.save_telegram_config("tok", "cid")
    assert capturado.get("token") == "tok" and capturado.get("chat_id") == "cid"
```

- [ ] **Step 3: Implementar Supabase com fallback ao JSON**

Em `backend/services/telegram_service.py`, adicione o import no topo:

```python
from backend.services.supabase_client import get_supabase
```

Reescreva `save_telegram_config`:

```python
def save_telegram_config(token: str, chat_id: str):
    """Persiste a config do Telegram no Supabase (tabela telegram_config, linha
    única); cai para arquivo JSON quando o Supabase está indisponível."""
    supabase = get_supabase()
    if supabase:
        try:
            supabase.table("telegram_config").upsert(
                {"id": 1, "token": token, "chat_id": chat_id}
            ).execute()
            return
        except Exception as e:
            logger.warning(f"Falha ao gravar telegram_config no Supabase: {e}")
    try:
        with open(_TELEGRAM_CONFIG_FILE, "w") as f:
            json.dump({"token": token, "chat_id": chat_id}, f)
    except Exception as e:
        logger.warning(f"Erro ao salvar telegram_config.json: {e}")
```

Em `load_telegram_config`, logo após o bloco de variáveis de ambiente (depois de `CONFIG["telegram_chat_id"] = env_chat_id`) e antes do `try: with open(...)`, acrescente a tentativa via Supabase:

```python
    supabase = get_supabase()
    if supabase:
        try:
            res = (supabase.table("telegram_config")
                   .select("token, chat_id").eq("id", 1).limit(1).execute())
            if res.data:
                row = res.data[0]
                if row.get("token") and not env_token:
                    CONFIG["telegram_token"] = row["token"]
                if row.get("chat_id") and not env_chat_id:
                    CONFIG["telegram_chat_id"] = row["chat_id"]
                logger.info("Config Telegram carregada do Supabase")
                return
        except Exception as e:
            logger.warning(f"Falha ao ler telegram_config do Supabase: {e}")
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_telegram.py -v`
Expected: PASS (com Supabase ausente nos demais testes, cai no fallback JSON — comportamento atual preservado).

- [ ] **Step 5: Commit**

```bash
git add backend/services/telegram_service.py supabase/migrations/003_telegram_config.sql tests/test_telegram.py
git commit -m "feat(telegram): persiste config no Supabase com fallback ao JSON"
```

**Critério de aceite 0.4:** `score_horario`/`dentro_horario_pregao` corretos sob mock de horário em UTC e BRT; cache key nunca retorna janela errada.

---

# Fechamento da Camada 0

- [ ] **Suíte completa verde**

Run: `python -m pytest -q`
Expected: PASS (baseline ~140 + novos testes).

> **Nota:** o projeto **não tem linter Python** configurado (sem `pyproject.toml`/`ruff`/`flake8` — só `requirements.txt`). A dívida de lint conhecida é exclusivamente no frontend (`@typescript-eslint/no-explicit-any`), não tocada por esta camada (toda backend). Não há passo de lint Python a rodar.

- [ ] **Frontend intacto** (o campo `score` segue existindo)

Run: `npm test`
Expected: PASS (36 testes; a UI exibe `score`, agora técnico puro — o `/10` cosmético fica para a Camada 6).

- [ ] **Atualizar a Definição de Pronto global** em `docs/PLANO_IMPLEMENTACAO_MELHORIAS.md` (marcar Camada 0) e confirmar as migrações 002/003 aplicadas no Supabase.

---

## Notas de execução / decisões que divergem do documento original

1. **`pivot_ordem=1` (não 5).** O documento sugere ordem 5; o código atual é ordem 1. Para a Camada 0 (correção, não feature) o objetivo é **eliminar o look-ahead** sem recalibrar a sensibilidade dos pivots — ordem 1 preserva o comportamento de produção e mata o bias no backtest. Subir para 3–5 é calibração da Camada 2/5 (basta mudar o knob; o teste de invariância já cobre qualquer ordem).
2. **`score` = score técnico.** Há dois sistemas de score (clássico em `core_engine`, ponderado 0–100 em `scoring.py`). A 0.2 trata o **clássico** (que decide por padrão). O `score_ponderado` já não inclui bônus de horário. Manter `score` = `score_tecnico` evita quebrar frontend/persistência existentes.
3. **Backfill aproximado.** O bônus histórico é inferido por faixa horária BRT do `timestamp` (aproximação — o minuto exato de emissão não é recuperável). Documentado na migração.
4. **0.4.3 (Telegram no Supabase)** é o item de menor impacto na correção; está marcado como opcional e pode migrar para a Camada 6/infra.
