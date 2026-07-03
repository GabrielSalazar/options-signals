# Adaptação PUCK → Motor de Sinais (Camada PUCK em shadow) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Incorporar ao motor os conceitos viáveis dos indicadores PUCK (v1.4/v3.1/v4.4): zona do High Candle institucional, fluxo normalizado/z-score, gatilhos de breakout e divergência de fluxo, modificadores de classe (absorção/persistência) e níveis ATR no ativo subjacente — tudo em shadow, medido pelo pipeline da Fase 4 antes de qualquer ativação.

**Architecture:** Novos indicadores vetorizados em `indicators.py` (só OHLCV — sem fonte de dados nova). Gatilhos G20/B20 e G21/B21 entram em `_avaliar_gatilhos_v2` com pontos zerados enquanto `puck_gatilhos_mode="shadow"` (telemetria via `trigger_outcomes` como os G12-G19). Modificadores de classe registram razões em `razoes_downgrade_classe` sem alterar a classe até flag ativa. Níveis ATR no subjacente são campos informativos no payload/SignalCard (migração 016), sem tocar os alvos % atuais da opção.

**Tech Stack:** pandas/numpy (indicadores), pydantic-settings (knobs), pytest, Supabase (migração), React/TS + Vitest (SignalCard)

---

## Síntese de viabilidade (decisão registrada)

### ✅ Implementar agora (este plano)

| Conceito (origem) | Ganho / pró | Impacto |
|---|---|---|
| EMA50 + alinhamento Close>EMA21>EMA50 (v3.1 §9) | Filtro de contexto do breakout; reduz falsos rompimentos contra-tendência | Coluna nova; zero efeito no score atual |
| Zona HC institucional `hc_max/hc_min` (v3.1/v4.4 §3-4) | Conceito estrutural ausente no motor (zona do player institucional como S/R) | Coluna nova; loop O(n) desprezível |
| `cmf_norm` + z-score de fluxo `cmf_z` (v3.1 §7 + v4.4 §5) | Fluxo graduado por intensidade e **autocalibrado cross-asset** (elimina threshold fixo por ativo) | Colunas novas; base dos gatilhos abaixo |
| G20/B20 rompimento HC + fluxo + tendência (v3.1/v4.4 §10/§9) | Cobre o estilo breakout que o motor (reversão/pullback) não tem; hipótese medível | **Zero na emissão** (shadow, 0 pontos); +2 entradas no registro GATILHOS (ESTRUTURA) |
| G21/B21 divergência de fluxo CMF×preço (v3.1 §8) | Antecipa reversões (absorção compradora/vendedora) — barato e complementar ao G9 (divergência RSI) | Zero na emissão (shadow); família MOMENTUM |
| Absorção no HC → razão de downgrade (v4.4 §8/§12) | Rebaixa sinais que testaram o rompimento e falharam com fluxo neutro — filtro de qualidade | Só adiciona texto em `razoes_downgrade_classe` (classe_v2 já é shadow); downgrade real atrás de flag |
| Persistência de fluxo → candidato a upgrade C→B (v4.4 §12, sem o critério de lote) | Único mecanismo de upgrade de classe dos PUCK; recupera sinais C com fluxo institucional persistente | Idem: telemetria em shadow, upgrade real atrás de flag |
| Níveis ATR no subjacente + regra de gestão (v3.1/v4.4 §12/§10-11) | **Maior lacuna prática**: hoje stop/alvos são % fixos sobre o prêmio; PUCK ancora a gestão no ativo (stop 1.5×ATR, TP1/TP2, R:R 2:1, parcial 50% + trailing documentado) | Campos informativos novos (payload + migração 016 + SignalCard); **não substitui** os alvos atuais |

### ⏸ Adiar (viável, mas depende de validação prévia)

| Conceito | Por quê adiar |
|---|---|
| Delta/DTE por classe (v3.1 §13: A→ITM 30-45du, B→ATM, C→OTM curto) | Mexe na emissão (strike/vencimento escolhidos); exige classe_v2 validada na Fase 4 + recalibração de `option_price_min/max` e faixa de delta + re-backtest |
| Trailing stop dinâmico no `outcome_service` | Depende dos níveis ATR persistidos (Task 4) e de decidir se o outcome passa a ser medido pelo subjacente — decisão à parte |
| Ativação dos gatilhos/modificadores PUCK (pontos reais) | Igual a tudo na matriz v2: só após 2 semanas de shadow + hit-rate no pipeline da Fase 4 |

### ❌ Não implementar (inviável ou sem sentido)

| Conceito | Motivo |
|---|---|
| Agressão real por tape reading (`AgressionVolBuy/Sell`, `AvgAgrBuySell` — v4.4 §4) | Sem fonte de dados: exige times & trades intraday (Nelogica/B3 pago). O proxy MFV/CLV (que o próprio autor usou no v3.1) já está coberto pelo CMF do motor |
| Lote médio institucional (`LotesMinInst`) | Mesmo bloqueio de dados acima |
| Grid gradiente / averaging automático (v1.4) | Automação de execução com médio de posição (risco martingale); projeto é sinalizador, não executor |
| VWAP de sessão como filtro (v4.4 §8) | Decisão já registrada na spec v2 (§7): proxy rolling-20 ≠ VWAP de sessão; critério reservado a futuro modo intraday |
| PaintBar/Plots/painel NTSL | Específico do ProfitChart; SignalCard + Telegram já cobrem com mais riqueza |

### Impactos globais

- **Emissão atual: zero.** Tudo nasce em shadow (padrão da casa) — gatilhos com 0 pontos, modificadores só registram razões.
- **Schema:** migração `016` (6 colunas nullable em `signals`). Aplicar no Supabase antes do deploy.
- **Telemetria:** G20/B20/G21/B21 fluem pelo mesmo pipeline dos G12-G19 (`ids_*_v2` → `trigger_outcomes`), medíveis pela query `fase4_monitor_shadow.sql` existente.
- **Risco conceitual:** breakout (G20) raramente coexiste com gatilhos de reversão (G3/G8) — esperado; a medição em shadow dirá se vira classe de setup própria ou pontos no score único.
- **Testes:** ~20-25 novos (indicadores, gatilhos, estrutura, SignalCard). Suíte deve ir de 687 → ~710.
- **Performance:** cálculos vetorizados + 1 loop O(n) (HC, mesmo padrão do SuperTrend) — desprezível.

---

## File Structure

```
backend/
  ├─ core/
  │  └─ settings.py                 [MODIFY] Knobs PUCK (hc_fator_volume, cmf_z_*, absorcao_*, fluxo_*, puck_gatilhos_mode)
  ├─ domain/
  │  ├─ indicators.py               [MODIFY] ema50, clv, hc_max/hc_min, cmf_norm, cmf_z, absorcao, fluxo_persist_pos/neg
  │  └─ scoring.py                  [MODIFY] Registro GATILHOS: G20/B20 (ESTRUTURA), G21/B21 (MOMENTUM)
  └─ services/
     ├─ core_engine.py              [MODIFY] Gatilhos PUCK em _avaliar_gatilhos_v2; modificadores de classe; níveis ATR em _montar_estrutura_opcao; payload
     └─ signal_service.py           [MODIFY] Persistir 6 campos novos

supabase/migrations/
  └─ 016_signals_puck_columns.sql   [NEW] ativo_entrada/stop/tp1/tp2, absorcao, fluxo_persistencia_dias

src/
  ├─ types/signals.ts               [MODIFY] Campos novos no tipo Signal
  └─ components/
     ├─ SignalCard.tsx              [MODIFY] Seção "Níveis no ativo" + badge absorção
     └─ SignalCard.test.tsx         [MODIFY] Testes dos campos novos

tests/
  ├─ test_indicators_puck.py        [NEW] HC, clv, cmf_norm, cmf_z, absorção, persistência
  ├─ test_gatilhos_puck.py          [NEW] G20/B20, G21/B21, modo shadow (0 pontos)
  └─ test_estrutura_ativo_niveis.py [NEW] Níveis ATR direcionais no payload

docs/
  └─ CHANGELOG.md                   [MODIFY] Seção "Camada PUCK (shadow)"
```

---

## Task 1: Knobs de configuração PUCK

**Files:**
- Modify: `backend/core/settings.py` (após o bloco matriz v2, linha ~61)

- [ ] **Step 1: Adicionar campos ao MotorSettings**

Em `backend/core/settings.py`, após `cci_extremo: float = 100.0` (linha 61), inserir:

```python
    # ── Camada PUCK (HC institucional, fluxo normalizado, breakout) ──
    # "shadow": gatilhos G20/B20/G21/B21 reportam com 0 pontos; modificadores
    # de classe só registram razões. "ativo": pontos reais e classe alterada.
    puck_gatilhos_mode: str = Field(default="shadow", pattern="^(shadow|ativo)$")
    absorcao_classe_mode: str = Field(default="shadow", pattern="^(shadow|ativo)$")
    fluxo_upgrade_mode: str = Field(default="shadow", pattern="^(shadow|ativo)$")
    hc_fator_volume: float = 1.5        # HC exige volume > fator × média20 (institucional)
    cmf_z_periodo: int = 21             # janela do z-score do CMF (PUCK v4.4 §5)
    cmf_z_gatilho: float = 1.0          # z mínimo p/ G20/B20 (1.0=padrão, 1.5=seletivo)
    absorcao_clv_max: float = 0.1       # |CLV| abaixo disso = fluxo neutro (absorção)
    fluxo_persistencia_clv: float = 0.3 # CLV direcional mínimo p/ contar persistência
    fluxo_persistencia_min: int = 3     # dias consecutivos p/ candidato a upgrade C→B
    atr_mult_stop: float = 1.5          # stop no ativo = entrada ∓ mult × ATR
    atr_mult_tp1: float = 1.5           # TP1 (realizar 50%)
    atr_mult_tp2: float = 3.0           # TP2 (R:R 2:1)
```

- [ ] **Step 2: Rodar a suíte para garantir que nada quebrou**

Run: `python -m pytest tests/ -q --tb=short 2>&1 | tail -5`
Expected: 687 passed (nenhum teste depende dos knobs novos ainda).

- [ ] **Step 3: Commit**

```bash
git add backend/core/settings.py
git commit -m "feat(puck): knobs de configuracao da camada PUCK (HC, z-score, absorcao, ATR)"
```

---

## Task 2: Indicadores PUCK em `indicators.py`

**Files:**
- Modify: `backend/domain/indicators.py` (helpers no fim do módulo; wiring em `calcular_indicadores` após a linha 134 `df["supertrend_dir"] = ...`)
- Test: `tests/test_indicators_puck.py`

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/test_indicators_puck.py`:

```python
"""Indicadores da camada PUCK: HC institucional, CLV, cmf_norm, cmf_z,
absorção e persistência de fluxo."""
import numpy as np
import pandas as pd
import pytest

from backend.domain.indicators import (
    _clv,
    _high_candle_zones,
    calcular_indicadores,
)


def _df_sintetico(n=60, seed=42):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 0.5, n))
    high = close + rng.uniform(0.2, 1.0, n)
    low = close - rng.uniform(0.2, 1.0, n)
    vol = rng.uniform(1e6, 2e6, n)
    return pd.DataFrame({
        "Open": close, "High": high, "Low": low, "Close": close, "Volume": vol,
    })


def test_clv_fechamento_na_maxima():
    """Fechou na máxima → CLV = +1; na mínima → -1; range zero → 0."""
    h = pd.Series([10.0, 10.0, 10.0])
    l = pd.Series([9.0, 9.0, 10.0])
    c = pd.Series([10.0, 9.0, 10.0])
    clv = _clv(h, l, c)
    assert clv.iloc[0] == pytest.approx(1.0)
    assert clv.iloc[1] == pytest.approx(-1.0)
    assert clv.iloc[2] == 0.0  # High == Low → sem pressão


def test_high_candle_atualiza_somente_com_volume_institucional():
    """HC só atualiza com novo máximo de volume E volume > fator × média20."""
    n = 30
    vol = pd.Series([1e6] * n)
    vol.iloc[25] = 2e6   # 2x a média → institucional
    vol.iloc[27] = 1.1e6 # acima da média mas < 1.5x → NÃO vira HC
    high = pd.Series([10.0] * n); high.iloc[25] = 12.0; high.iloc[27] = 15.0
    low = pd.Series([9.0] * n);  low.iloc[25] = 11.0;  low.iloc[27] = 14.0

    hc_max, hc_min = _high_candle_zones(high, low, vol, fator=1.5)

    assert hc_max.iloc[26] == 12.0   # HC definido pela barra 25
    assert hc_min.iloc[26] == 11.0
    assert hc_max.iloc[29] == 12.0   # barra 27 não substituiu o HC


def test_high_candle_sem_lookahead():
    """O HC do dia i não pode usar dados de i+1..n."""
    df = _df_sintetico(60)
    hc_full, _ = _high_candle_zones(df["High"], df["Low"], df["Volume"], 1.5)
    hc_parcial, _ = _high_candle_zones(
        df["High"].iloc[:40], df["Low"].iloc[:40], df["Volume"].iloc[:40], 1.5)
    # Mesmo valor na barra 39 calculado com 40 ou com 60 barras
    assert (hc_full.iloc[39] == hc_parcial.iloc[39]) or (
        np.isnan(hc_full.iloc[39]) and np.isnan(hc_parcial.iloc[39]))


def test_calcular_indicadores_adiciona_colunas_puck():
    df = calcular_indicadores(_df_sintetico(80))
    for col in ("ema50", "clv", "hc_max", "hc_min", "cmf_norm", "cmf_z",
                "absorcao", "fluxo_persist_pos", "fluxo_persist_neg"):
        assert col in df.columns, f"coluna {col} ausente"


def test_cmf_z_escala_de_zscore():
    """cmf_z deve ser ~N(0,1): média próxima de 0 no df sintético."""
    df = calcular_indicadores(_df_sintetico(120))
    z = df["cmf_z"].dropna()
    assert len(z) > 30
    assert abs(z.mean()) < 1.0  # sanity: não explodiu de escala


def test_fluxo_persistencia_conta_dias_consecutivos():
    df = _df_sintetico(60)
    # Força 4 dias consecutivos fechando na máxima (CLV=1) no fim da série
    for i in range(56, 60):
        df.loc[i, "Close"] = df.loc[i, "High"]
    out = calcular_indicadores(df)
    assert out["fluxo_persist_pos"].iloc[-1] >= 4
    assert out["fluxo_persist_neg"].iloc[-1] == 0


def test_absorcao_detectada():
    """High tocou o HC, fechou abaixo, CLV neutro → absorção."""
    df = _df_sintetico(60)
    # Barra 40 vira HC institucional (volume 3x)
    df.loc[40, "Volume"] = df["Volume"].mean() * 3
    df.loc[40, "High"] = 200.0
    df.loc[40, "Low"] = 100.0
    # Última barra: testa o topo do HC e falha com fluxo neutro
    df.loc[59, "High"] = 201.0             # >= hc_max (200)
    df.loc[59, "Low"] = 197.0
    df.loc[59, "Close"] = 199.0            # < hc_max e CLV = (2-2)/4 = 0
    out = calcular_indicadores(df)
    assert bool(out["absorcao"].iloc[-1]) is True
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_indicators_puck.py -v 2>&1 | tail -15`
Expected: FAIL/ERROR — `ImportError: cannot import name '_clv'`.

- [ ] **Step 3: Implementar helpers no fim de `indicators.py`**

Adicionar ao final de `backend/domain/indicators.py` (antes de `detectar_divergencia` ou após os helpers manuais existentes):

```python
def _clv(high, low, close) -> pd.Series:
    """Close Location Value (PUCK §5): +1 fecha na máxima, -1 na mínima.
    Range zero (leilão) → 0 (sem pressão)."""
    rng = (high - low).replace(0, np.nan)
    return (((close - low) - (high - close)) / rng).fillna(0.0)


def _high_candle_zones(high, low, volume, fator: float = 1.5) -> tuple:
    """Zona do High Candle institucional (PUCK §3-4).

    O HC é o candle de maior volume visto até então, desde que o volume seja
    também > fator × média20 (filtro institucional — sem ele qualquer volume
    crescente atualizaria a zona). Retorna (hc_max, hc_min) forward-filled.
    Loop necessário (estado sequencial), mesmo padrão do _supertrend_dir.
    Sem look-ahead: a zona do dia i usa apenas candles 0..i.
    """
    media_vol = volume.rolling(20).mean().values
    vol, hi, lo = volume.values, high.values, low.values
    n = len(vol)
    hc_max = np.full(n, np.nan)
    hc_min = np.full(n, np.nan)
    maior_vol = 0.0
    cur_max = cur_min = np.nan
    for i in range(n):
        limiar = media_vol[i] * fator if media_vol[i] == media_vol[i] else float("inf")
        if vol[i] > maior_vol and vol[i] > limiar:
            maior_vol = vol[i]
            cur_max, cur_min = hi[i], lo[i]
        hc_max[i] = cur_max
        hc_min[i] = cur_min
    return (pd.Series(hc_max, index=high.index),
            pd.Series(hc_min, index=high.index))
```

- [ ] **Step 4: Wiring em `calcular_indicadores`**

Em `backend/domain/indicators.py`, logo após a linha do SuperTrend (`df["supertrend_dir"] = _supertrend_dir(...)`, linha ~134), inserir:

```python
    # ── Camada PUCK: HC institucional, fluxo normalizado, absorção ────────
    df["ema50"] = c.ewm(span=50, adjust=False).mean()
    df["clv"] = _clv(h, l, c)
    df["hc_max"], df["hc_min"] = _high_candle_zones(
        h, l, v, CONFIG.get("hc_fator_volume", 1.5))

    periodo_z = CONFIG.get("cmf_z_periodo", 21)
    mfv = df["clv"] * v
    soma_vol = v.rolling(periodo_z).sum()
    agress_pos = mfv.clip(lower=0).rolling(periodo_z).sum() / (soma_vol + 1e-9)
    agress_neg = (-mfv).clip(lower=0).rolling(periodo_z).sum() / (soma_vol + 1e-9)
    media_pos = agress_pos.ewm(span=periodo_z, adjust=False).mean()
    media_neg = agress_neg.ewm(span=periodo_z, adjust=False).mean()
    # cmf_norm: intensidade do fluxo vs. média histórica do próprio ativo
    # (>1.5 = evento institucional; PUCK v3.1 §7). Sinal segue o CMF.
    df["cmf_norm"] = np.where(
        df["cmf"] > 0, agress_pos / (media_pos + 1e-9),
        np.where(df["cmf"] < 0, -(agress_neg / (media_neg + 1e-9)), 0.0))
    # cmf_z: z-score do CMF (PUCK v4.4 §5) — threshold autocalibrado cross-asset
    df["cmf_z"] = ((df["cmf"] - df["cmf"].rolling(periodo_z).mean())
                   / (df["cmf"].rolling(periodo_z).std() + 1e-9))

    # Absorção (PUCK v4.4 §8): testou o topo do HC, fechou abaixo, fluxo neutro
    df["absorcao"] = ((h >= df["hc_max"]) & (c < df["hc_max"])
                      & (df["clv"].abs() < CONFIG.get("absorcao_clv_max", 0.1)))

    # Persistência de fluxo (PUCK v4.4 §12): dias consecutivos com CLV direcional
    limite_clv = CONFIG.get("fluxo_persistencia_clv", 0.3)
    pos = (df["clv"] > limite_clv).astype(int)
    neg = (df["clv"] < -limite_clv).astype(int)
    df["fluxo_persist_pos"] = pos * (pos.groupby((pos != pos.shift()).cumsum()).cumcount() + 1)
    df["fluxo_persist_neg"] = neg * (neg.groupby((neg != neg.shift()).cumsum()).cumcount() + 1)
```

- [ ] **Step 5: Rodar os testes novos**

Run: `python -m pytest tests/test_indicators_puck.py -v 2>&1 | tail -15`
Expected: 7 passed.

- [ ] **Step 6: Rodar a suíte inteira (regressão)**

Run: `python -m pytest tests/ -q --tb=short 2>&1 | tail -5`
Expected: 694 passed (687 + 7), 0 failed.

- [ ] **Step 7: Commit**

```bash
git add backend/domain/indicators.py tests/test_indicators_puck.py
git commit -m "feat(puck): indicadores HC institucional, CLV, cmf_norm/cmf_z, absorcao e persistencia"
```

---

## Task 3: Gatilhos G20/B20 (rompimento HC) e G21/B21 (divergência de fluxo)

**Files:**
- Modify: `backend/domain/scoring.py` (registro `GATILHOS`, linha ~262 após B19)
- Modify: `backend/services/core_engine.py` (`_avaliar_gatilhos_v2`, após o bloco BW linha ~410, antes dos redutores)
- Test: `tests/test_gatilhos_puck.py`

- [ ] **Step 1: Registrar os gatilhos no registro de famílias**

Em `backend/domain/scoring.py`, dentro do dict `GATILHOS`, após `"B19": {...}` (linha ~262), adicionar:

```python
    # Camada PUCK (shadow até validação — pontos só valem com puck_gatilhos_mode=ativo)
    "G20": {"familia": "ESTRUTURA", "pontos": 3},   # Rompimento do HC institucional
    "G21": {"familia": "MOMENTUM",  "pontos": 2},   # Divergência de fluxo (absorção compradora)
    "B20": {"familia": "ESTRUTURA", "pontos": 3},   # Rompimento baixista do HC
    "B21": {"familia": "MOMENTUM",  "pontos": 2},   # Divergência de fluxo (absorção vendedora)
```

- [ ] **Step 2: Escrever os testes que falham**

Criar `tests/test_gatilhos_puck.py`:

```python
"""Gatilhos PUCK: G20/B20 (rompimento HC) e G21/B21 (divergência de fluxo)."""
import numpy as np
import pandas as pd
import pytest

from backend.core.config import CONFIG
from backend.services.core_engine import _avaliar_gatilhos_v2


def _df_base(n=10):
    return pd.DataFrame({
        "Open": [100.0] * n, "High": [101.0] * n, "Low": [99.0] * n,
        "Close": [100.0] * n, "Volume": [1e6] * n,
    })


def _ultimo(**kwargs):
    """Linha de indicadores com defaults neutros; override por kwargs."""
    base = {
        "cci": None, "mfi": None, "cmf": None, "supertrend_dir": None,
        "ema21": None, "adx": None, "bb_width": None,
        "hc_max": None, "hc_min": None, "ema50": None, "cmf_z": None,
        "Low": 100.0, "High": 100.0,
    }
    base.update(kwargs)
    return pd.Series(base)


def test_g20_rompimento_hc_dispara():
    """Low > hc_max + z-fluxo >= 1 + Close>EMA21>EMA50 → G20 na lista v2."""
    ultimo = _ultimo(hc_max=95.0, Low=96.0, cmf_z=1.5, ema21=94.0, ema50=92.0)
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=96.5)
    assert "G20" in v2["ids_alta_v2"]


def test_g20_nao_dispara_sem_fluxo():
    """Rompimento geométrico sem z-fluxo (cmf_z=0.2) → não dispara (FIX 4 do PUCK)."""
    ultimo = _ultimo(hc_max=95.0, Low=96.0, cmf_z=0.2, ema21=94.0, ema50=92.0)
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=96.5)
    assert "G20" not in v2["ids_alta_v2"]


def test_g20_nao_dispara_contra_tendencia():
    """EMAs desalinhadas (EMA21 < EMA50) → não dispara."""
    ultimo = _ultimo(hc_max=95.0, Low=96.0, cmf_z=1.5, ema21=92.0, ema50=94.0)
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=96.5)
    assert "G20" not in v2["ids_alta_v2"]


def test_b20_rompimento_baixista():
    ultimo = _ultimo(hc_min=105.0, High=104.0, cmf_z=-1.5, ema21=106.0, ema50=108.0)
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=103.5)
    assert "B20" in v2["ids_baixa_v2"]


def test_g21_divergencia_de_fluxo():
    """CMF negativo + preço subiu vs. barra anterior → G21 (venda absorvida)."""
    df = _df_base()
    df.loc[len(df) - 2, "Close"] = 99.0  # penúltimo fechamento abaixo
    ultimo = _ultimo(cmf=-0.15)
    v2 = _avaliar_gatilhos_v2(df, ultimo, stoch_k=50, rsi=50, preco=100.0)
    assert "G21" in v2["ids_alta_v2"]


def test_b21_divergencia_de_fluxo_baixista():
    df = _df_base()
    df.loc[len(df) - 2, "Close"] = 101.0  # penúltimo fechamento acima
    ultimo = _ultimo(cmf=0.15)
    v2 = _avaliar_gatilhos_v2(df, ultimo, stoch_k=50, rsi=50, preco=100.0)
    assert "B21" in v2["ids_baixa_v2"]


def test_puck_shadow_nao_pontua():
    """Em modo shadow (default), G20 aparece na lista mas contribui 0 pontos.

    Atenção: o fixture arma também o G17 (preço > EMA21, +1) — inevitável,
    pois o G20 exige preço > EMA21 > EMA50. Então o score esperado é
    exatamente 1 (só o G17); se o G20 pontuasse, seria 4.
    """
    assert CONFIG.get("puck_gatilhos_mode", "shadow") == "shadow"
    ultimo = _ultimo(hc_max=95.0, Low=96.0, cmf_z=1.5, ema21=94.0, ema50=92.0)
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=96.5)
    assert "G20" in v2["ids_alta_v2"]
    assert v2["score_alta_v2"] == 1  # apenas o G17; G20 em shadow = 0 pontos


def test_indicador_ausente_fail_safe():
    """hc_max/cmf_z None (df antigo) → nunca dispara, sem exceção."""
    ultimo = _ultimo()  # tudo None
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=100.0)
    for gid in ("G20", "B20", "G21", "B21"):
        assert gid not in v2["ids_alta_v2"] + v2["ids_baixa_v2"]
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `python -m pytest tests/test_gatilhos_puck.py -v 2>&1 | tail -15`
Expected: FAIL — G20/G21 não aparecem nas listas (código ainda não existe).

- [ ] **Step 4: Implementar em `_avaliar_gatilhos_v2`**

Em `backend/services/core_engine.py`, dentro de `_avaliar_gatilhos_v2`, após o bloco do BW/G19 (linha ~410) e ANTES do comentário `# Redutores (spec §3)`, inserir:

```python
    # ── Gatilhos PUCK (rompimento HC + divergência de fluxo) ─────────────
    # Em shadow os pontos são 0: o ID entra na telemetria (trigger_outcomes)
    # sem afetar score mesmo se matriz_v2_gatilhos_mode virar "ativo".
    puck_ativo = CONFIG.get("puck_gatilhos_mode") == "ativo"
    hc_max = _val("hc_max"); hc_min = _val("hc_min")
    ema50_v = _val("ema50"); cmf_z = _val("cmf_z")
    low_v = _val("Low"); high_v = _val("High")
    z_min = CONFIG.get("cmf_z_gatilho", 1.0)

    if None not in (hc_max, ema21_v, ema50_v, cmf_z, low_v):
        if low_v > hc_max and cmf_z >= z_min and preco > ema21_v > ema50_v:
            _fire("alta", "G20",
                  f"📈 Rompimento do HC institucional (z-fluxo {cmf_z:.1f})",
                  3 if puck_ativo else 0)
    if None not in (hc_min, ema21_v, ema50_v, cmf_z, high_v):
        if high_v < hc_min and cmf_z <= -z_min and preco < ema21_v < ema50_v:
            _fire("baixa", "B20",
                  f"📉 Rompimento baixista do HC institucional (z-fluxo {cmf_z:.1f})",
                  3 if puck_ativo else 0)

    close_prev = float(df["Close"].iloc[-2]) if len(df) >= 2 else None
    if cmf is not None and close_prev is not None:
        if cmf < 0 and preco > close_prev:
            _fire("alta", "G21",
                  "📈 Divergência de fluxo (venda absorvida, preço subiu)",
                  2 if puck_ativo else 0)
        elif cmf > 0 and preco < close_prev:
            _fire("baixa", "B21",
                  "📉 Divergência de fluxo (compra absorvida, preço caiu)",
                  2 if puck_ativo else 0)
```

Nota: `ema21_v` e `cmf` já existem no escopo da função (linhas ~379 e ~393).

- [ ] **Step 5: Rodar os testes novos**

Run: `python -m pytest tests/test_gatilhos_puck.py -v 2>&1 | tail -15`
Expected: 8 passed.

- [ ] **Step 6: Regressão completa**

Run: `python -m pytest tests/ -q --tb=short 2>&1 | tail -5`
Expected: 702 passed, 0 failed.

- [ ] **Step 7: Commit**

```bash
git add backend/domain/scoring.py backend/services/core_engine.py tests/test_gatilhos_puck.py
git commit -m "feat(puck): gatilhos shadow G20/B20 (rompimento HC) e G21/B21 (divergencia de fluxo)"
```

---

## Task 4: Modificadores de classe (absorção / persistência de fluxo)

**Files:**
- Modify: `backend/services/core_engine.py` (`analisar_ativo`, após o bloco classe v2 linha ~799)
- Test: adicionar casos em `tests/test_gatilhos_puck.py`

- [ ] **Step 1: Escrever os testes que falham**

Adicionar ao final de `tests/test_gatilhos_puck.py`:

```python
from backend.services.core_engine import _aplicar_modificadores_classe_puck


def test_absorcao_registra_razao_sem_mudar_classe_em_shadow():
    classe, razoes = _aplicar_modificadores_classe_puck(
        classe_v2="A", razoes=[], absorcao=True, persist=0, tipo_sinal="CALL")
    assert classe == "A"  # shadow: não rebaixa
    assert any("absorção" in r for r in razoes)


def test_persistencia_registra_candidato_a_upgrade():
    classe, razoes = _aplicar_modificadores_classe_puck(
        classe_v2="C", razoes=[], absorcao=False, persist=4, tipo_sinal="CALL")
    assert classe == "C"  # shadow: não sobe
    assert any("upgrade" in r for r in razoes)


def test_sem_absorcao_nem_persistencia_nao_altera():
    classe, razoes = _aplicar_modificadores_classe_puck(
        classe_v2="B", razoes=["x"], absorcao=False, persist=1, tipo_sinal="CALL")
    assert classe == "B"
    assert razoes == ["x"]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_gatilhos_puck.py -v 2>&1 | tail -8`
Expected: FAIL — `ImportError: cannot import name '_aplicar_modificadores_classe_puck'`.

- [ ] **Step 3: Implementar a função em `core_engine.py`**

Adicionar como função de módulo (logo antes de `_montar_estrutura_opcao`, linha ~435):

```python
def _aplicar_modificadores_classe_puck(classe_v2: str, razoes: list[str],
                                       absorcao: bool, persist: int,
                                       tipo_sinal: str) -> tuple[str, list[str]]:
    """Modificadores PUCK da classe v2 (v4.4 §8/§12), em shadow por default.

    - Absorção no HC (testou o rompimento e falhou com fluxo neutro):
      registra razão; rebaixa uma classe apenas com absorcao_classe_mode=ativo.
    - Persistência de fluxo a favor (>= fluxo_persistencia_min dias):
      registra candidato a upgrade C→B; sobe apenas com fluxo_upgrade_mode=ativo.
    """
    if absorcao:
        razoes = razoes + ["absorção no HC (rompimento testado e rejeitado)"]
        if CONFIG.get("absorcao_classe_mode") == "ativo" and classe_v2 in ("A", "B"):
            classe_v2 = "B" if classe_v2 == "A" else "C"
    elif (persist >= CONFIG.get("fluxo_persistencia_min", 3) and classe_v2 == "C"):
        razoes = razoes + [f"candidato a upgrade C→B: fluxo persistente {persist}d"]
        if CONFIG.get("fluxo_upgrade_mode") == "ativo":
            classe_v2 = "B"
    return classe_v2, razoes
```

- [ ] **Step 4: Wiring em `analisar_ativo`**

Em `backend/services/core_engine.py`, após `estrutura["razoes_downgrade_classe"] = razoes_downgrade` (linha ~799), substituir essas duas linhas de atribuição por:

```python
            # Modificadores PUCK (absorção / persistência) — shadow
            absorcao = bool(ultimo.get("absorcao", False))
            persist_col = "fluxo_persist_pos" if tipo_sinal == "CALL" else "fluxo_persist_neg"
            persist_raw = ultimo.get(persist_col, 0)
            persist = int(persist_raw) if persist_raw == persist_raw else 0  # NaN-safe
            classe_v2, razoes_downgrade = _aplicar_modificadores_classe_puck(
                classe_v2, razoes_downgrade, absorcao, persist, tipo_sinal)
            estrutura["classe_v2"] = classe_v2
            estrutura["razoes_downgrade_classe"] = razoes_downgrade
            estrutura["absorcao"] = absorcao
            estrutura["fluxo_persistencia_dias"] = persist
```

- [ ] **Step 5: Rodar testes e regressão**

Run: `python -m pytest tests/test_gatilhos_puck.py tests/test_core_engine.py -q --tb=short 2>&1 | tail -5`
Expected: todos passam (3 novos + suíte core_engine intacta).

- [ ] **Step 6: Commit**

```bash
git add backend/services/core_engine.py tests/test_gatilhos_puck.py
git commit -m "feat(puck): modificadores shadow de classe (absorcao no HC, persistencia de fluxo)"
```

---

## Task 5: Níveis ATR no ativo subjacente

**Files:**
- Modify: `backend/services/core_engine.py` (`_montar_estrutura_opcao` linha ~505-530; payload builder linha ~611-619)
- Modify: `backend/services/signal_service.py` (dict de persistência, linha ~165)
- Create: `supabase/migrations/016_signals_puck_columns.sql`
- Test: `tests/test_estrutura_ativo_niveis.py`

- [ ] **Step 1: Escrever a migração**

Criar `supabase/migrations/016_signals_puck_columns.sql`:

```sql
-- ============================================================
-- Migration 016: Colunas da camada PUCK em signals (shadow)
--   Níveis ATR no ativo subjacente (gestão pelo ativo, não pela opção)
--   + telemetria de absorção/persistência de fluxo
-- Run via: Supabase Dashboard → SQL Editor
-- ============================================================
ALTER TABLE signals ADD COLUMN IF NOT EXISTS ativo_entrada FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS ativo_stop FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS ativo_tp1 FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS ativo_tp2 FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS absorcao BOOLEAN;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS fluxo_persistencia_dias INTEGER;
```

- [ ] **Step 2: Escrever os testes que falham**

Criar `tests/test_estrutura_ativo_niveis.py`:

```python
"""Níveis ATR no ativo subjacente (PUCK §12): stop 1.5×ATR, TP1 1.5×, TP2 3×."""
import pytest

from backend.services.core_engine import _niveis_ativo_atr


def test_niveis_call():
    n = _niveis_ativo_atr(preco=100.0, atr=2.0, tipo_sinal="CALL")
    assert n["ativo_entrada"] == 100.0
    assert n["ativo_stop"] == 97.0    # 100 - 1.5×2
    assert n["ativo_tp1"] == 103.0    # 100 + 1.5×2
    assert n["ativo_tp2"] == 106.0    # 100 + 3×2 → R:R 2:1


def test_niveis_put_espelhados():
    n = _niveis_ativo_atr(preco=100.0, atr=2.0, tipo_sinal="PUT")
    assert n["ativo_stop"] == 103.0
    assert n["ativo_tp1"] == 97.0
    assert n["ativo_tp2"] == 94.0


def test_atr_invalido_usa_fallback_2pct():
    """ATR NaN/zero → fallback 2% do preço (fail-safe)."""
    n = _niveis_ativo_atr(preco=100.0, atr=0.0, tipo_sinal="CALL")
    assert n["ativo_stop"] == 97.0    # 100 - 1.5×(2% de 100)
    n2 = _niveis_ativo_atr(preco=100.0, atr=float("nan"), tipo_sinal="CALL")
    assert n2["ativo_stop"] == 97.0
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `python -m pytest tests/test_estrutura_ativo_niveis.py -v 2>&1 | tail -8`
Expected: FAIL — `ImportError: cannot import name '_niveis_ativo_atr'`.

- [ ] **Step 4: Implementar `_niveis_ativo_atr` e wiring**

Em `backend/services/core_engine.py`, adicionar função de módulo (junto de `_aplicar_modificadores_classe_puck`):

```python
def _niveis_ativo_atr(preco: float, atr: float, tipo_sinal: str) -> dict:
    """Níveis de gestão no ATIVO subjacente (PUCK §12), informativos:
    stop = entrada ∓ 1.5×ATR | TP1 = ±1.5×ATR (realizar 50%) | TP2 = ±3×ATR.
    Os alvos % sobre o prêmio da opção continuam sendo os oficiais; estes
    campos ancoram a gestão no ativo (invalidação da tese, não da opção)."""
    if atr != atr or atr <= 0:  # NaN ou inválido
        atr = preco * 0.02
    d = 1 if tipo_sinal.upper() == "CALL" else -1
    return {
        "ativo_entrada": round(preco, 2),
        "ativo_stop":    round(preco - d * CONFIG.get("atr_mult_stop", 1.5) * atr, 2),
        "ativo_tp1":     round(preco + d * CONFIG.get("atr_mult_tp1", 1.5) * atr, 2),
        "ativo_tp2":     round(preco + d * CONFIG.get("atr_mult_tp2", 3.0) * atr, 2),
    }
```

Em `_montar_estrutura_opcao`, junto do cálculo de alvos (após a linha do `stop`, ~510), adicionar:

```python
    atr_ativo = float(df["atr"].iloc[-1]) if "atr" in df.columns else preco * 0.02
    niveis_ativo = _niveis_ativo_atr(preco, atr_ativo, tipo_sinal)
```

e espalhar `**niveis_ativo` no dict `estrutura` retornado (linhas ~519-527).

No payload builder (dict das linhas ~611-619), adicionar:

```python
        "ativo_entrada": estrutura.get("ativo_entrada"),
        "ativo_stop":    estrutura.get("ativo_stop"),
        "ativo_tp1":     estrutura.get("ativo_tp1"),
        "ativo_tp2":     estrutura.get("ativo_tp2"),
        "absorcao":      estrutura.get("absorcao"),
        "fluxo_persistencia_dias": estrutura.get("fluxo_persistencia_dias"),
```

- [ ] **Step 5: Persistência em `signal_service.py`**

No dict de persistência (após `"filtro_liquidez_motivo"`, linha ~168), adicionar:

```python
            "ativo_entrada": s.get("ativo_entrada"),
            "ativo_stop":    s.get("ativo_stop"),
            "ativo_tp1":     s.get("ativo_tp1"),
            "ativo_tp2":     s.get("ativo_tp2"),
            "absorcao":      s.get("absorcao"),
            "fluxo_persistencia_dias": s.get("fluxo_persistencia_dias"),
```

- [ ] **Step 6: Rodar testes novos + regressão**

Run: `python -m pytest tests/test_estrutura_ativo_niveis.py tests/ -q --tb=short 2>&1 | tail -5`
Expected: 705+ passed, 0 failed.

- [ ] **Step 7: Commit**

```bash
git add supabase/migrations/016_signals_puck_columns.sql backend/services/core_engine.py backend/services/signal_service.py tests/test_estrutura_ativo_niveis.py
git commit -m "feat(puck): niveis ATR no ativo subjacente (stop/TP1/TP2 informativos) + migration 016"
```

---

## Task 6: SignalCard — Níveis no ativo + badge de absorção

**Files:**
- Modify: `src/types/signals.ts` (interface `Signal`, após `filtro_liquidez_motivo`)
- Modify: `src/components/SignalCard.tsx` (após o bloco "Entrada / Alvos")
- Test: `src/components/SignalCard.test.tsx`

- [ ] **Step 1: Adicionar campos ao tipo**

Em `src/types/signals.ts`, após `filtro_liquidez_motivo` (linha ~58):

```typescript
  // Camada PUCK (níveis no ativo subjacente + telemetria, shadow)
  ativo_entrada?: number | null
  ativo_stop?: number | null
  ativo_tp1?: number | null
  ativo_tp2?: number | null
  absorcao?: boolean | null
  fluxo_persistencia_dias?: number | null
```

- [ ] **Step 2: Escrever os testes que falham**

Adicionar em `src/components/SignalCard.test.tsx` (seguindo o padrão dos testes existentes de Fase 3):

```typescript
it('exibe níveis no ativo quando presentes', () => {
    render(<SignalCard signal={{ ...baseSignal, ativo_entrada: 36.42, ativo_stop: 35.1, ativo_tp1: 37.74, ativo_tp2: 39.06 }} />)
    expect(screen.getByText(/Níveis no ativo/i)).toBeInTheDocument()
    expect(screen.getByText(/35\.10/)).toBeInTheDocument()
    expect(screen.getByText(/39\.06/)).toBeInTheDocument()
})

it('omite níveis no ativo quando null', () => {
    render(<SignalCard signal={{ ...baseSignal, ativo_stop: null }} />)
    expect(screen.queryByText(/Níveis no ativo/i)).not.toBeInTheDocument()
})

it('exibe badge de absorção quando true', () => {
    render(<SignalCard signal={{ ...baseSignal, absorcao: true }} />)
    expect(screen.getByText(/Absorção/i)).toBeInTheDocument()
})
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `npx vitest run src/components/SignalCard.test.tsx 2>&1 | tail -10`
Expected: 3 novos FAIL.

- [ ] **Step 4: Implementar no SignalCard**

Em `src/components/SignalCard.tsx`:

(a) Badge de absorção — dentro do bloco de badges existente (após o badge de liquidez, linha ~98):

```tsx
                    {signal.absorcao && (
                        <span
                            className="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider"
                            style={{ background: '#FFFBEB', color: '#92400E', border: '1px solid var(--dw-yellow)' }}
                            title="Rompimento do HC testado e rejeitado com fluxo neutro (telemetria shadow)"
                        >
                            Absorção HC
                        </span>
                    )}
```

(atualizar a condição do wrapper para `(signal.evento_label || classe || liquidez || signal.absorcao)`)

(b) Seção "Níveis no ativo" — após o bloco "Entrada / Alvos":

```tsx
            {/* Níveis no ativo subjacente (PUCK — gestão pela tese, não pela opção) */}
            {signal.ativo_stop != null && (
                <div className="bg-dw-bg-soft rounded-lg p-3 space-y-1">
                    <p className="label">Níveis no ativo (ATR)</p>
                    <div className="grid grid-cols-3 gap-2 font-mono text-xs">
                        <div>
                            <span className="text-dw-ink-muted">Stop</span>
                            <p className="font-semibold" style={{ color: 'var(--dw-red)' }}>R$ {fmtNum(signal.ativo_stop)}</p>
                        </div>
                        <div>
                            <span className="text-dw-ink-muted">TP1 (50%)</span>
                            <p className="font-semibold text-dw-ink">R$ {fmtNum(signal.ativo_tp1)}</p>
                        </div>
                        <div>
                            <span className="text-dw-ink-muted">TP2 (100%)</span>
                            <p className="font-semibold text-dw-ink">R$ {fmtNum(signal.ativo_tp2)}</p>
                        </div>
                    </div>
                    <p className="text-[10px] text-dw-ink-muted">
                        Gestão pelo ativo: no TP1 realizar 50% e mover o stop para a entrada
                        (R$ {fmtNum(signal.ativo_entrada)}); zerar se o ativo fechar além do stop.
                    </p>
                </div>
            )}
```

- [ ] **Step 5: Rodar os testes do frontend**

Run: `npx vitest run 2>&1 | tail -5`
Expected: todos passam (existentes + 3 novos).

- [ ] **Step 6: Commit**

```bash
git add src/types/signals.ts src/components/SignalCard.tsx src/components/SignalCard.test.tsx
git commit -m "feat(frontend): niveis ATR no ativo e badge de absorcao no SignalCard"
```

---

## Task 7: Documentação e verificação final

**Files:**
- Modify: `docs/CHANGELOG.md` (seção `[Não lançado]`)
- None: verificação

- [ ] **Step 1: CHANGELOG**

Adicionar em `docs/CHANGELOG.md`, no topo da seção `[Não lançado]`:

```markdown
### Added (Camada PUCK — shadow)
- **Indicadores PUCK** ([backend/domain/indicators.py](../backend/domain/indicators.py)):
  `ema50`, `clv` (Close Location Value), zona do High Candle institucional
  (`hc_max`/`hc_min`, volume > 1.5× média20), `cmf_norm` (intensidade de fluxo vs.
  média do próprio ativo), `cmf_z` (z-score do CMF — threshold autocalibrado
  cross-asset, PUCK v4.4), `absorcao` e `fluxo_persist_pos/neg`.
- **Gatilhos shadow G20/B20** (rompimento do HC com fluxo e tendência alinhados,
  família ESTRUTURA) e **G21/B21** (divergência de fluxo CMF×preço, família
  MOMENTUM) — 0 pontos até `puck_gatilhos_mode=ativo`; telemetria via
  `trigger_outcomes` como os demais gatilhos v2.
- **Modificadores shadow de classe**: absorção no HC registra razão de downgrade;
  fluxo persistente ≥3d registra candidato a upgrade C→B (flags
  `absorcao_classe_mode`/`fluxo_upgrade_mode`).
- **Níveis ATR no ativo subjacente** (informativos): `ativo_entrada/stop/tp1/tp2`
  (stop 1.5×ATR, TP1 1.5×, TP2 3× → R:R 2:1) no payload, persistidos (migração
  `016`) e exibidos no SignalCard com a regra de gestão parcial. Os alvos % sobre
  o prêmio da opção permanecem os oficiais.
- **Decisões registradas**: agressão por tape reading e lote institucional são
  inviáveis sem dados intraday pagos (proxy = CLV/CMF); grid gradiente (v1.4) e
  VWAP de sessão ficam fora do escopo (spec v2 §7).

> **Pendências:** aplicar migração `016` no Supabase; medir gatilhos/modificadores
> PUCK na janela shadow da Fase 4 (query `fase4_monitor_shadow.sql`) antes de
> qualquer ativação; delta/DTE por classe adiado para pós-validação.
```

- [ ] **Step 2: Suíte completa + lint**

Run: `python -m pytest tests/ -q --tb=short 2>&1 | tail -3 && python -m ruff check backend/`
Expected: ~710 passed, 0 failed; "All checks passed!".

Run: `npx vitest run 2>&1 | tail -3`
Expected: todos os testes frontend passam.

- [ ] **Step 3: Commit final**

```bash
git add docs/CHANGELOG.md
git commit -m "docs(puck): camada PUCK shadow no CHANGELOG (indicadores, gatilhos, niveis ATR)"
```

---

## Summary

| Task | Entrega | Testes novos |
|---|---|---|
| 1 | Knobs PUCK em `MotorSettings` | 0 (coberto pela suíte) |
| 2 | Indicadores: HC, CLV, cmf_norm/z, absorção, persistência | 7 |
| 3 | Gatilhos shadow G20/B20 + G21/B21 | 8 |
| 4 | Modificadores shadow de classe | 3 |
| 5 | Níveis ATR no subjacente + migração 016 + persistência | 3 |
| 6 | SignalCard (níveis + badge absorção) | 3 (Vitest) |
| 7 | CHANGELOG + verificação final | — |

**Pós-implementação:** aplicar migração 016 no Supabase, deploy, e incluir G20/B20/G21/B21 na janela de medição shadow da Fase 4 (a query `fase4_monitor_shadow.sql` já cobre via `trigger_outcomes`). Ativação de qualquer flag PUCK só após hit-rate medido.

---

## Adendo (2026-07-03) — Task 8: G22/B22 "Teste do HC" + aceleração de fluxo (OPÇÕES B3 v8.2)

Origem: análise do doc `OPCOES_B3_v2_Documentacao.docx` (v8.2 "ZERO NOISE"), que INVERTE o filtro geométrico do v4.4: em vez de rompimento (`Low > maxHC`), exige TOQUE/teste da zona (`Low ≤ maxHC`) — pullback ao nível institucional defendido. Alinha com o DNA de reversão do motor. A aceleração de fluxo (filtro 4 do v8.2: agressão crescente 3 barras) entra como CONDIÇÃO do gatilho, não como gatilho separado.

**Files:**
- Modify: `backend/domain/indicators.py` — colunas `cmf_acel_pos`/`cmf_acel_neg` (cmf estritamente crescente/decrescente por 3 barras; NaN nunca dispara)
- Modify: `backend/domain/scoring.py` — registro `GATILHOS`: G22/B22 (ESTRUTURA, 3)
- Modify: `backend/services/core_engine.py` — G22/B22 em `_avaliar_gatilhos_v2` + incluir "G22"/"B22" em `_PUCK_IDS` (leak-guard)
- Test: `tests/test_indicators_puck.py` (aceleração) e `tests/test_gatilhos_puck.py` (G22/B22)

**Condições (shadow, pontos 0 até `puck_gatilhos_mode=ativo`):**
- G22 (alta): `Low <= hc_max` E `Close > hc_max` (tocou o topo da zona e fechou acima — defesa) E `cmf_z >= cmf_z_gatilho` E `cmf_acel_pos` E `Close > ema21`
- B22 (baixa): espelho — `High >= hc_min` E `Close < hc_min` E `cmf_z <= -z_min` E `cmf_acel_neg` E `Close < ema21`
- Sentinela ±inf segura por construção: `Close > hc_max(+inf)` e `Close < hc_min(-inf)` são False.
- `tests/test_scoring.py`: somas por lado 40→43.

- [x] Implementado via subagente (mesmo pipeline: implementer + spec review + quality review).
