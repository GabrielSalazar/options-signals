# Camada 2 — Redesenho do Motor de Score — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classificar os 20 gatilhos do motor clássico em famílias com teto de contribuição, calcular a "largura de consenso", separar o setup Reversão×Continuação, documentar a assimetria CALL/PUT e gravar telemetria por gatilho — tudo em modo shadow (campos informativos, sem alterar a decisão de emissão ou os parâmetros reais da estrutura de opção).

**Architecture:** `backend/domain/scoring.py` ganha um registro `GATILHOS` (ID→família+pontos) e as funções puras `calcular_familias`, `classificar_setup` e `parametros_setup_shadow`. `backend/services/core_engine.py` é atualizado para que `_avaliar_gatilhos` retorne os IDs disparados e `analisar_ativo`/`_montar_sinal` persistam os campos shadow no sinal. `backend/services/signal_service.py` propaga esses campos ao Supabase. Uma nova migração (`006`) adiciona as colunas e a tabela `trigger_outcomes`; `backend/services/outcome_service.py` explode o desfecho de cada sinal resolvido em uma linha por gatilho (idempotente via upsert).

**Tech Stack:** Python 3 / FastAPI, pandas, Supabase (Postgres), pytest.

**Spec:** `docs/superpowers/specs/2026-06-29-camada-2-motor-de-score-design.md`

**Refinamentos feitos durante o planejamento (não estavam explícitos no spec, mas são necessários para corretude):**
- `trigger_outcomes` ganha `UNIQUE (signal_id, gatilho_id)` e a explosão usa `upsert` — sem isso, cada chamada de `avaliar_sinais` (endpoint usado sob demanda) duplicaria as linhas do mesmo sinal.
- Só sinais com desfecho **terminal** (`alvo1`/`alvo2`/`alvo_final`/`stop`/`expirou`) geram linhas em `trigger_outcomes` — `aberto`/`indeterminado` são pulados (ainda não há resultado definitivo).
- Não foram criadas as flags `consenso_filter_mode`/`setup_filter_mode` em `CONFIG` — como esta camada não implementa nenhum modo "ativo" para essas decisões (fica para a Camada 5, após validação), uma flag sem nenhum consumidor seria código morto. As decisões ficam puramente informativas nos campos do sinal.

**Pendência manual após o merge:** aplicar a migração `006_camada2_motor_score.sql` no Supabase ANTES do deploy (mesmo fluxo das pendentes anteriores).

---

### Task 1: Registro de gatilhos por família e teto de contribuição

**Files:**
- Modify: `backend/domain/scoring.py`, `backend/core/config.py`
- Test: `tests/test_scoring.py`

- [ ] **Step 1: Escrever os testes que falham**

Adicionar a `tests/test_scoring.py` (no topo do arquivo, junto dos demais imports de `backend.domain.scoring`):

```python
from backend.domain.scoring import GATILHOS, calcular_familias
```

E os testes (em qualquer ponto do arquivo, próximo aos testes de `avaliar_filtro_iv`):

```python
def test_gatilhos_alta_somam_23_pontos():
    soma = sum(v["pontos"] for k, v in GATILHOS.items() if k.startswith("G"))
    assert soma == 23


def test_gatilhos_baixa_somam_21_pontos():
    soma = sum(v["pontos"] for k, v in GATILHOS.items() if k.startswith("B"))
    assert soma == 21


def test_calcular_familias_sem_teto_quando_dentro_do_cap():
    r = calcular_familias(["G2", "G3", "G7", "G10"])
    assert r["breakdown"] == {"OSCILADOR": 2, "ESTRUTURA": 2, "TENDENCIA": 2, "LIQUIDEZ": 3}
    assert r["score_capped"] == 9
    assert r["familias_ativas"] == 4


def test_calcular_familias_aplica_teto_quando_familia_excede_cap():
    # G1(+3) + G2(+2) = 5 pts em OSCILADOR, mas o cap é 4
    r = calcular_familias(["G1", "G2"])
    assert r["breakdown"] == {"OSCILADOR": 4}
    assert r["score_capped"] == 4
    assert r["familias_ativas"] == 1


def test_calcular_familias_ignora_ids_desconhecidos():
    r = calcular_familias(["G1", "ZZZ"])
    assert r["breakdown"] == {"OSCILADOR": 3}


def test_calcular_familias_lista_vazia():
    r = calcular_familias([])
    assert r == {"score_capped": 0, "familias_ativas": 0, "breakdown": {}}
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `pytest tests/test_scoring.py -v -k "gatilhos or calcular_familias"`
Expected: FAIL com `ImportError: cannot import name 'GATILHOS'`

- [ ] **Step 3: Adicionar os caps por família ao CONFIG**

Em `backend/core/config.py`, logo após a linha `"iv_filter_mode": "shadow", ...`, adicionar:

```python
    "familia_cap_oscilador":   4,   # teto de contribuicao por familia (Camada 2.1)
    "familia_cap_tendencia":   4,
    "familia_cap_estrutura":   3,
    "familia_cap_divergencia": 3,
    "familia_cap_liquidez":    4,
```

- [ ] **Step 4: Implementar o registro `GATILHOS` e `calcular_familias`**

Em `backend/domain/scoring.py`, adicionar ao final do arquivo:

```python
# ── Camada 2.1 — famílias de gatilhos e teto de contribuição ──────────────

GATILHOS: dict[str, dict] = {
    # Gatilhos de alta (G1-G11, docs/ESTRATEGIAS_OPCOES_B3.md)
    "G1":  {"familia": "OSCILADOR",   "pontos": 3},
    "G2":  {"familia": "OSCILADOR",   "pontos": 2},
    "G3":  {"familia": "ESTRUTURA",   "pontos": 2},
    "G4":  {"familia": "TENDENCIA",   "pontos": 2},
    "G5":  {"familia": "LIQUIDEZ",    "pontos": 1},
    "G6":  {"familia": "OSCILADOR",   "pontos": 2},
    "G7":  {"familia": "TENDENCIA",   "pontos": 2},
    "G8":  {"familia": "ESTRUTURA",   "pontos": 1},
    "G9":  {"familia": "DIVERGENCIA", "pontos": 3},
    "G10": {"familia": "LIQUIDEZ",    "pontos": 3},
    "G11": {"familia": "TENDENCIA",   "pontos": 2},
    # Gatilhos de baixa (B1-B9)
    "B1": {"familia": "OSCILADOR",   "pontos": 3},
    "B2": {"familia": "OSCILADOR",   "pontos": 2},
    "B3": {"familia": "ESTRUTURA",   "pontos": 2},
    "B4": {"familia": "TENDENCIA",   "pontos": 2},
    "B5": {"familia": "TENDENCIA",   "pontos": 2},
    "B6": {"familia": "OSCILADOR",   "pontos": 2},
    "B7": {"familia": "DIVERGENCIA", "pontos": 3},
    "B8": {"familia": "LIQUIDEZ",    "pontos": 3},
    "B9": {"familia": "TENDENCIA",   "pontos": 2},
}


def calcular_familias(gatilhos_ids: list[str]) -> dict:
    """
    Aplica o teto de contribuição por família (Camada 2.1) sobre os gatilhos
    que dispararam. Cada família contribui no máximo `familia_cap_<nome>`
    (CONFIG) ao score, mesmo que a soma bruta dos gatilhos da família exceda
    o teto. `familias_ativas` conta famílias distintas com pelo menos 1
    gatilho disparado (antes do cap) — é a "largura de consenso".
    IDs fora do registro `GATILHOS` são ignorados (não derruba o cálculo).
    Retorna {"score_capped": int, "familias_ativas": int, "breakdown": dict}.
    """
    caps = {
        "OSCILADOR":   CONFIG.get("familia_cap_oscilador", 4),
        "TENDENCIA":   CONFIG.get("familia_cap_tendencia", 4),
        "ESTRUTURA":   CONFIG.get("familia_cap_estrutura", 3),
        "DIVERGENCIA": CONFIG.get("familia_cap_divergencia", 3),
        "LIQUIDEZ":    CONFIG.get("familia_cap_liquidez", 4),
    }
    bruto: dict[str, int] = {}
    for gid in gatilhos_ids:
        info = GATILHOS.get(gid)
        if not info:
            continue
        bruto[info["familia"]] = bruto.get(info["familia"], 0) + info["pontos"]

    breakdown = {fam: min(pts, caps.get(fam, pts)) for fam, pts in bruto.items()}
    return {
        "score_capped": sum(breakdown.values()),
        "familias_ativas": len(bruto),
        "breakdown": breakdown,
    }
```

- [ ] **Step 5: Rodar os testes e confirmar que passam**

Run: `pytest tests/test_scoring.py -v -k "gatilhos or calcular_familias"`
Expected: PASS (7 testes)

- [ ] **Step 6: Commit**

```bash
git add backend/domain/scoring.py backend/core/config.py tests/test_scoring.py
git commit -m "feat(score): adiciona registro de gatilhos por familia e teto de contribuicao"
```

---

### Task 2: Classificação de setup (Reversão × Continuação) e parâmetros shadow

**Files:**
- Modify: `backend/domain/scoring.py`
- Test: `tests/test_scoring.py`

- [ ] **Step 1: Escrever os testes que falham**

Adicionar ao import de `backend.domain.scoring` em `tests/test_scoring.py`:

```python
from backend.domain.scoring import classificar_setup, parametros_setup_shadow
```

E os testes:

```python
def test_classificar_setup_reversao_quando_familias_de_reversao_dominam():
    breakdown = {"OSCILADOR": 2, "ESTRUTURA": 2, "TENDENCIA": 2, "LIQUIDEZ": 3}
    assert classificar_setup(breakdown) == "REVERSAO"


def test_classificar_setup_continuacao_quando_tendencia_domina():
    breakdown = {"TENDENCIA": 6}
    assert classificar_setup(breakdown) == "CONTINUACAO"


def test_classificar_setup_hibrido_em_empate():
    assert classificar_setup({"OSCILADOR": 2, "TENDENCIA": 2}) == "HIBRIDO"


def test_classificar_setup_hibrido_sem_nenhuma_familia():
    assert classificar_setup({}) == "HIBRIDO"


def test_parametros_setup_shadow_reversao():
    p = parametros_setup_shadow("REVERSAO")
    assert p == {"otm_mult": 0.7, "dte_min": 10, "dte_max": 25,
                 "alvo2_pct": 1.50, "stop_pct": -0.35}


def test_parametros_setup_shadow_continuacao():
    p = parametros_setup_shadow("CONTINUACAO")
    assert p == {"otm_mult": 1.0, "dte_min": 5, "dte_max": 20,
                 "alvo2_pct": 2.50, "stop_pct": -0.43}


def test_parametros_setup_shadow_hibrido_usa_valores_de_continuacao():
    assert parametros_setup_shadow("HIBRIDO") == parametros_setup_shadow("CONTINUACAO")
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `pytest tests/test_scoring.py -v -k "classificar_setup or parametros_setup_shadow"`
Expected: FAIL com `ImportError: cannot import name 'classificar_setup'`

- [ ] **Step 3: Implementar as funções**

Em `backend/domain/scoring.py`, adicionar ao final do arquivo (depois de `calcular_familias`):

```python
def classificar_setup(breakdown: dict) -> str:
    """
    Classifica o sinal por família dominante (Camada 2.2):
      REVERSAO    se OSCILADOR+DIVERGENCIA+ESTRUTURA > TENDENCIA
      CONTINUACAO se TENDENCIA > OSCILADOR+DIVERGENCIA+ESTRUTURA
      HIBRIDO     em caso de empate (inclusive 0 a 0)
    `breakdown` é o dict {familia: pontos} retornado por `calcular_familias`
    (já com os tetos aplicados).
    """
    reversao = (breakdown.get("OSCILADOR", 0) + breakdown.get("DIVERGENCIA", 0)
                + breakdown.get("ESTRUTURA", 0))
    continuacao = breakdown.get("TENDENCIA", 0)
    if reversao > continuacao:
        return "REVERSAO"
    if continuacao > reversao:
        return "CONTINUACAO"
    return "HIBRIDO"


def parametros_setup_shadow(setup: str) -> dict:
    """
    Parâmetros de estrutura de opção que SERIAM usados por setup (Camada 2.2).
    Shadow apenas — não afeta a estrutura real da opção, que continua usando
    os parâmetros únicos atuais de CONFIG. Valores da tabela do plano,
    hipóteses a validar na Camada 5. HIBRIDO usa os mesmos valores da
    Continuação (que já coincidem com os defaults atuais de produção:
    alvo2_pct=2.50, stop_pct=-0.43), por não haver família dominante que
    justifique desviar.
    """
    if setup == "REVERSAO":
        return {"otm_mult": 0.7, "dte_min": 10, "dte_max": 25,
                "alvo2_pct": 1.50, "stop_pct": -0.35}
    return {"otm_mult": 1.0, "dte_min": 5, "dte_max": 20,
            "alvo2_pct": 2.50, "stop_pct": -0.43}
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `pytest tests/test_scoring.py -v -k "classificar_setup or parametros_setup_shadow"`
Expected: PASS (7 testes)

- [ ] **Step 5: Commit**

```bash
git add backend/domain/scoring.py tests/test_scoring.py
git commit -m "feat(score): adiciona classificacao de setup reversao x continuacao (shadow)"
```

---

### Task 3: `_avaliar_gatilhos` retorna os IDs dos gatilhos disparados

**Files:**
- Modify: `backend/services/core_engine.py:93-213` (`_avaliar_gatilhos`)
- Test: `tests/test_core_engine.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicionar a `tests/test_core_engine.py` (reaproveitando `_make_df` já definido no topo do arquivo):

```python
def test_avaliar_gatilhos_retorna_ids_dos_gatilhos_disparados():
    df = _make_df(0)
    ultimo, penult = df.iloc[-1], df.iloc[-2]
    preco = float(ultimo["Close"])
    volume = float(ultimo["Volume"])
    vol_med = float(ultimo.get("vol_media_20", volume))

    gat = core_engine._avaliar_gatilhos(df, ultimo, penult, preco, vol_med, volume)

    assert gat["ids_alta"] == ["G2", "G3", "G7", "G10"]
    assert gat["ids_baixa"] == ["B9"]
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `pytest tests/test_core_engine.py -v -k ids_dos_gatilhos`
Expected: FAIL com `KeyError: 'ids_alta'`

- [ ] **Step 3: Implementar — anotar cada disparo com seu ID**

Em `backend/services/core_engine.py`, substituir a função `_avaliar_gatilhos` inteira (linhas 93-213):

```python
def _avaliar_gatilhos(df: pd.DataFrame, ultimo, penult, preco: float,
                      vol_med: float, volume: float) -> dict:
    """Avalia os gatilhos técnicos (alta/baixa) sobre o df e retorna os scores,
    as listas de sinais (texto, p/ exibição) e de IDs (Camada 2.1, ex.: "G1"),
    e os escalares usados a jusante (stoch_k, rsi, vol_ratio).
    Não inclui o bônus de horário (somado pelo orquestrador)."""
    sinais_alta, sinais_baixa = [], []
    ids_alta, ids_baixa = [], []
    score_alta = score_baixa = 0

    stoch_k      = float(ultimo.get("stoch_k",     50))
    stoch_d      = float(ultimo.get("stoch_d",     50))
    stoch_k_prev = float(penult.get("stoch_k",     50))
    stoch_d_prev = float(penult.get("stoch_d",     50))
    rsi          = float(ultimo.get("rsi",         50))
    ema9         = float(ultimo.get("ema9",     preco))
    ema21        = float(ultimo.get("ema21",    preco))
    ema9_prev    = float(penult.get("ema9",     ema9))
    ema21_prev   = float(penult.get("ema21",    ema21))
    macd_d       = float(ultimo.get("macd_diff",    0))
    macd_d_prev  = float(penult.get("macd_diff",    0))
    atr          = float(ultimo.get("atr",  preco*0.02))
    sup20        = float(ultimo.get("suporte_20",   preco))
    res20        = float(ultimo.get("resistencia_20",preco))
    vol_ratio    = volume / vol_med if vol_med > 0 else 1.0
    bb_lo        = float(ultimo.get("bb_lower",     0))

    ordem = CONFIG["pivot_ordem"]
    ultimos_fundos, ultimos_topos = ultimos_pivots_confirmados(df, ordem, n=3)

    # ── GATILHOS DE ALTA ─────────────────────────────────────────────
    if (stoch_k < CONFIG["stoch_oversold"] + 10 and stoch_k > stoch_d and stoch_k_prev <= stoch_d_prev):
        sinais_alta.append("📈 Estocástico: cruzamento altista em sobrevenda")
        ids_alta.append("G1")
        score_alta += 3

    if rsi < CONFIG["rsi_oversold"]:
        sinais_alta.append(f"📈 RSI sobrevenda: {rsi:.1f}")
        ids_alta.append("G2")
        score_alta += 2

    if preco <= sup20 + atr:
        sinais_alta.append(f"📈 Preço em suporte 20D: R${sup20:.2f}")
        ids_alta.append("G3")
        score_alta += 2

    if ema9 > ema21 and ema9_prev <= ema21_prev:
        sinais_alta.append("📈 EMA9 cruzou acima EMA21")
        ids_alta.append("G4")
        score_alta += 2

    if vol_ratio >= CONFIG["volume_mult"]:
        sinais_alta.append(f"📈 Volume {vol_ratio:.1f}x acima da média")
        ids_alta.append("G5")
        score_alta += 1

    if macd_d > 0 and macd_d_prev <= 0:
        sinais_alta.append("📈 MACD cruzou zero (momentum altista)")
        ids_alta.append("G6")
        score_alta += 2

    if (len(ultimos_fundos) >= 3 and all(ultimos_fundos[i] < ultimos_fundos[i+1] for i in range(2))):
        sinais_alta.append("📈 Fundos ascendentes (reversão)")
        ids_alta.append("G7")
        score_alta += 2

    if bb_lo > 0 and preco <= bb_lo * 1.01:
        sinais_alta.append(f"📈 Preço na Bollinger inferior: R${bb_lo:.2f}")
        ids_alta.append("G8")
        score_alta += 1

    div_alta, _ = detectar_divergencia(df, janela=5)
    if div_alta:
        sinais_alta.append("📈 Divergência altista RSI (preço cai, RSI sobe)")
        ids_alta.append("G9")
        score_alta += 3

    zona_dem, _ = encontrar_zonas_demanda_oferta(df)
    if zona_dem:
        sinais_alta.append("📈 Preço em zona de demanda histórica")
        ids_alta.append("G10")
        score_alta += 3

    canal_alt, _, slope = detectar_canal_linear(df)
    if canal_alt:
        sinais_alta.append(f"📈 Canal altista (slope={slope:.3f})")
        ids_alta.append("G11")
        score_alta += 2

    # ── GATILHOS DE BAIXA ────────────────────────────────────────────
    if (stoch_k > CONFIG["stoch_overbought"] - 10 and stoch_k < stoch_d and stoch_k_prev >= stoch_d_prev):
        sinais_baixa.append("📉 Estocástico: cruzamento baixista em sobrecompra")
        ids_baixa.append("B1")
        score_baixa += 3

    if rsi > CONFIG["rsi_overbought"]:
        sinais_baixa.append(f"📉 RSI sobrecompra: {rsi:.1f}")
        ids_baixa.append("B2")
        score_baixa += 2

    if preco >= res20 - atr:
        sinais_baixa.append(f"📉 Preço em resistência 20D: R${res20:.2f}")
        ids_baixa.append("B3")
        score_baixa += 2

    if ema9 < ema21 and ema9_prev >= ema21_prev:
        sinais_baixa.append("📉 EMA9 cruzou abaixo EMA21")
        ids_baixa.append("B4")
        score_baixa += 2

    if (len(ultimos_topos) >= 3 and all(ultimos_topos[i] > ultimos_topos[i+1] for i in range(2))):
        sinais_baixa.append("📉 Topos descendentes (tendência de baixa)")
        ids_baixa.append("B5")
        score_baixa += 2

    if macd_d < 0 and macd_d_prev >= 0:
        sinais_baixa.append("📉 MACD cruzou zero negativamente")
        ids_baixa.append("B6")
        score_baixa += 2

    _, div_baixa = detectar_divergencia(df, janela=5)
    if div_baixa:
        sinais_baixa.append("📉 Divergência baixista RSI (preço sobe, RSI cai)")
        ids_baixa.append("B7")
        score_baixa += 3

    _, zona_ofe = encontrar_zonas_demanda_oferta(df)
    if zona_ofe:
        sinais_baixa.append("📉 Preço em zona de oferta histórica")
        ids_baixa.append("B8")
        score_baixa += 3

    _, canal_bx, slope_bx = detectar_canal_linear(df)
    if canal_bx:
        sinais_baixa.append(f"📉 Canal baixista (slope={slope_bx:.3f})")
        ids_baixa.append("B9")
        score_baixa += 2

    return {
        "score_alta": score_alta, "score_baixa": score_baixa,
        "sinais_alta": sinais_alta, "sinais_baixa": sinais_baixa,
        "ids_alta": ids_alta, "ids_baixa": ids_baixa,
        "stoch_k": stoch_k, "rsi": rsi, "vol_ratio": vol_ratio,
    }
```

- [ ] **Step 4: Rodar o teste novo e confirmar que passa**

Run: `pytest tests/test_core_engine.py -v -k ids_dos_gatilhos`
Expected: PASS

- [ ] **Step 5: Rodar a suíte completa de core_engine (garantir que nada quebrou)**

Run: `pytest tests/test_core_engine.py -v`
Expected: PASS em todos os testes (a mudança é puramente aditiva — `sinais_alta`/`sinais_baixa`/`score_alta`/`score_baixa` continuam idênticos)

- [ ] **Step 6: Commit**

```bash
git add backend/services/core_engine.py tests/test_core_engine.py
git commit -m "feat(score): _avaliar_gatilhos retorna ids dos gatilhos disparados"
```

---

### Task 4: Wiring em `analisar_ativo`/`_montar_sinal` — campos shadow no sinal

**Files:**
- Modify: `backend/services/core_engine.py:19` (import), `:373-457` (`analisar_ativo`), `:297-370` (`_montar_sinal`)
- Test: `tests/test_core_engine.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicionar a `tests/test_core_engine.py`:

```python
def test_analisar_ativo_persiste_campos_shadow_da_camada_2(monkeypatch):
    _relax_and_mock(monkeypatch)
    df = _make_df(0)

    s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=df, indicators_calculated=True)

    assert s is not None
    assert s["gatilhos_ids"] == ["G2", "G3", "G7", "G10"]
    assert s["familias_ativas"] == 4
    assert s["score_familias_capped"] == 9
    assert s["consenso_decisao"] == "passaria"
    assert s["setup"] == "REVERSAO"
    assert s["setup_params_shadow"] == {"otm_mult": 0.7, "dte_min": 10, "dte_max": 25,
                                         "alvo2_pct": 1.50, "stop_pct": -0.35}
    # Campos shadow não alteram a estrutura real (regressão — mesmos valores da Camada 1)
    assert (s["alvo1"], s["alvo2"], s["alvo_final"], s["stop"]) == (0.12, 0.35, 0.8, 0.06)
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `pytest tests/test_core_engine.py -v -k campos_shadow_da_camada_2`
Expected: FAIL com `KeyError: 'gatilhos_ids'`

- [ ] **Step 3: Atualizar o import**

Em `backend/services/core_engine.py:19`, trocar:

```python
from backend.domain.scoring import score_ponderado, avaliar_filtro_iv
```

por:

```python
from backend.domain.scoring import (
    score_ponderado, avaliar_filtro_iv, calcular_familias, classificar_setup,
    parametros_setup_shadow,
)
```

- [ ] **Step 4: Inserir o bloco de famílias/consenso/setup em `analisar_ativo`**

Em `analisar_ativo`, localizar o trecho (logo após o bloco do filtro de IV):

```python
        elif filtro["decisao"] != "normal" and verbose:
            logger.info(f"ℹ {ticker_base}: filtro IV (shadow) indicaria '{filtro['decisao']}' — {filtro['motivo']}")

        if df_provided is None:
            registrar_sinal(ticker_base, tipo_sinal, score)
```

e substituir por:

```python
        elif filtro["decisao"] != "normal" and verbose:
            logger.info(f"ℹ {ticker_base}: filtro IV (shadow) indicaria '{filtro['decisao']}' — {filtro['motivo']}")

        # ── FAMÍLIAS / CONSENSO / SETUP (Camada 2.1-2.2 — shadow) ─────────
        gatilhos_ids = gat["ids_alta"] if tipo_sinal == "CALL" else gat["ids_baixa"]
        familias = calcular_familias(gatilhos_ids)
        consenso_decisao = ("passaria" if (score >= MIN_SCORE and familias["familias_ativas"] >= 2)
                            else "bloquearia")
        setup = classificar_setup(familias["breakdown"])
        estrutura["gatilhos_ids"] = gatilhos_ids
        estrutura["familias_ativas"] = familias["familias_ativas"]
        estrutura["score_familias_capped"] = familias["score_capped"]
        estrutura["consenso_decisao"] = consenso_decisao
        estrutura["setup"] = setup
        estrutura["setup_params_shadow"] = parametros_setup_shadow(setup)

        if df_provided is None:
            registrar_sinal(ticker_base, tipo_sinal, score)
```

- [ ] **Step 5: Expor os campos novos em `_montar_sinal`**

Em `_montar_sinal`, localizar o final do dict de retorno:

```python
        "vol_ratio":    vol_ratio,
        "gatilhos":     gatilhos,
    }
```

e substituir por:

```python
        "vol_ratio":    vol_ratio,
        "gatilhos":     gatilhos,
        "gatilhos_ids": estrutura.get("gatilhos_ids", []),
        "familias_ativas": estrutura.get("familias_ativas"),
        "score_familias_capped": estrutura.get("score_familias_capped"),
        "consenso_decisao": estrutura.get("consenso_decisao"),
        "setup":        estrutura.get("setup"),
        "setup_params_shadow": estrutura.get("setup_params_shadow"),
    }
```

- [ ] **Step 6: Rodar o teste novo e confirmar que passa**

Run: `pytest tests/test_core_engine.py -v -k campos_shadow_da_camada_2`
Expected: PASS

- [ ] **Step 7: Rodar a suíte completa do projeto**

Run: `pytest tests/ -v`
Expected: PASS em todos os testes (exceto a falha pré-existente e não relacionada `test_market_analysis::test_analysis_dados_insuficientes_retorna_422`)

- [ ] **Step 8: Commit**

```bash
git add backend/services/core_engine.py tests/test_core_engine.py
git commit -m "feat(score): persiste familias_ativas, consenso, setup e parametros shadow no sinal"
```

---

### Task 5: Persistência dos campos novos em `signal_service.py`

**Files:**
- Modify: `backend/services/signal_service.py:120` (dentro de `persist_signals`)
- Test: `tests/test_signal_service.py`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_signal_service.py` já importa o módulo como `from backend.services import signal_service as ss` (mesma convenção usada nos testes existentes do arquivo, ex.: `monkeypatch.setattr(ss, "persist_signals", ...)`). `persist_signals` (linha 74 de `signal_service.py`) faz `supabase.table("signals").insert(rows).execute()`. Adicionar ao final de `tests/test_signal_service.py`:

```python
def test_persist_signals_propaga_campos_da_camada_2(monkeypatch):
    capturado = {}

    class _FakeTable:
        def insert(self, rows):
            capturado["rows"] = rows
            return self
        def execute(self):
            return type("R", (), {"data": capturado["rows"]})()

    class _FakeSupabase:
        def table(self, nome):
            return _FakeTable()

    monkeypatch.setattr(ss, "get_supabase", lambda: _FakeSupabase())

    sinal = {
        "ticker": "TESTE3", "tipo_sinal": "CALL", "score": 9,
        "gatilhos_ids": ["G2", "G3"], "familias_ativas": 2,
        "score_familias_capped": 4, "consenso_decisao": "passaria",
        "setup": "REVERSAO", "setup_params_shadow": {"otm_mult": 0.7},
    }
    ss.persist_signals([sinal])

    row = capturado["rows"][0]
    assert row["gatilhos_ids"] == ["G2", "G3"]
    assert row["familias_ativas"] == 2
    assert row["score_familias_capped"] == 4
    assert row["consenso_decisao"] == "passaria"
    assert row["setup"] == "REVERSAO"
    assert row["setup_params_shadow"] == {"otm_mult": 0.7}
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `pytest tests/test_signal_service.py -v -k camada_2`
Expected: FAIL — `KeyError: 'gatilhos_ids'` (chave ausente no row persistido)

- [ ] **Step 3: Atualizar `persist_signals`**

Em `backend/services/signal_service.py:120`, trocar:

```python
            "gatilhos":      s.get("gatilhos", []),
            "book_until":    s.get("book_until"),
```

por:

```python
            "gatilhos":      s.get("gatilhos", []),
            "gatilhos_ids":  s.get("gatilhos_ids", []),
            "familias_ativas": s.get("familias_ativas"),
            "score_familias_capped": s.get("score_familias_capped"),
            "consenso_decisao": s.get("consenso_decisao"),
            "setup":         s.get("setup"),
            "setup_params_shadow": s.get("setup_params_shadow"),
            "book_until":    s.get("book_until"),
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `pytest tests/test_signal_service.py -v -k camada_2`
Expected: PASS

- [ ] **Step 5: Rodar a suíte completa de signal_service**

Run: `pytest tests/test_signal_service.py -v`
Expected: PASS em todos

- [ ] **Step 6: Commit**

```bash
git add backend/services/signal_service.py tests/test_signal_service.py
git commit -m "feat(score): persiste campos shadow da Camada 2 no Supabase"
```

---

### Task 6: Migration 006 — colunas da Camada 2 e tabela `trigger_outcomes`

**Files:**
- Create: `supabase/migrations/006_camada2_motor_score.sql`

- [ ] **Step 1: Criar o arquivo da migração**

```sql
-- ============================================================
-- Migration 006: Camada 2 (Motor de Score) — familias/consenso/
-- setup em `signals` + telemetria por gatilho (`trigger_outcomes`)
-- Run via: Supabase Dashboard → SQL Editor
-- ============================================================

ALTER TABLE signals
  ADD COLUMN IF NOT EXISTS gatilhos_ids          TEXT[],
  ADD COLUMN IF NOT EXISTS familias_ativas        INTEGER,
  ADD COLUMN IF NOT EXISTS score_familias_capped  INTEGER,
  ADD COLUMN IF NOT EXISTS consenso_decisao       TEXT,
  ADD COLUMN IF NOT EXISTS setup                  TEXT,
  ADD COLUMN IF NOT EXISTS setup_params_shadow     JSONB;

CREATE TABLE IF NOT EXISTS trigger_outcomes (
    id                  BIGSERIAL PRIMARY KEY,
    signal_id           BIGINT NOT NULL,
    gatilho_id          TEXT NOT NULL,
    familia             TEXT,
    pontos              INTEGER,
    setup               TEXT,
    resultado_final     TEXT,
    retorno_pct         NUMERIC,
    dias_ate_resolucao  INTEGER,
    created_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE (signal_id, gatilho_id)
);

CREATE INDEX IF NOT EXISTS idx_trigger_outcomes_gatilho
  ON trigger_outcomes (gatilho_id, resultado_final);
```

> A restrição `UNIQUE (signal_id, gatilho_id)` permite usar `upsert` na explosão por gatilho (Task 8) — chamadas repetidas de `avaliar_sinais` sobre o mesmo sinal resolvido não duplicam linhas.

- [ ] **Step 2: Não aplicar agora — só ao final do plano**

Mesma disciplina das migrações 002-005: aplicar manualmente no Supabase Dashboard depois que todo o código desta Camada 2 estiver mergeado. Sem teste automatizado de schema; a suíte pytest completa (com os fakes de Supabase) é o teste de regressão.

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/006_camada2_motor_score.sql
git commit -m "chore(db): adiciona migration 006 (campos da Camada 2 + tabela trigger_outcomes)"
```

---

### Task 7: `retorno_pct_do_desfecho` em `outcome.py`

**Files:**
- Modify: `backend/domain/outcome.py`
- Test: `tests/test_outcome.py`

- [ ] **Step 1: Escrever os testes que falham**

Em `tests/test_outcome.py:7`, trocar:

```python
from backend.domain.outcome import avaliar_desfecho, comparar_por_desfecho, eh_ganho
```

por:

```python
from backend.domain.outcome import (
    avaliar_desfecho, comparar_por_desfecho, eh_ganho, retorno_pct_do_desfecho,
)
```

E adicionar ao final do arquivo:

```python
# ── retorno_pct_do_desfecho ────────────────────────────────────────────────

def test_retorno_pct_do_desfecho_alvo1():
    assert retorno_pct_do_desfecho("alvo1") == 25.0


def test_retorno_pct_do_desfecho_alvo2():
    assert retorno_pct_do_desfecho("alvo2") == 250.0


def test_retorno_pct_do_desfecho_alvo_final():
    assert retorno_pct_do_desfecho("alvo_final") == 700.0


def test_retorno_pct_do_desfecho_stop():
    assert retorno_pct_do_desfecho("stop") == -43.0


def test_retorno_pct_do_desfecho_expirou_retorna_none():
    assert retorno_pct_do_desfecho("expirou") is None


def test_retorno_pct_do_desfecho_aberto_retorna_none():
    assert retorno_pct_do_desfecho("aberto") is None
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `pytest tests/test_outcome.py -v -k retorno_pct_do_desfecho`
Expected: FAIL com `ImportError: cannot import name 'retorno_pct_do_desfecho'`

- [ ] **Step 3: Implementar a função**

Em `backend/domain/outcome.py:11`, trocar:

```python
from backend.domain.greeks import bs_call_price, bs_put_price
```

por:

```python
from backend.core.config import CONFIG
from backend.domain.greeks import bs_call_price, bs_put_price
```

E adicionar ao final do arquivo:

```python
_RETORNO_PCT_POR_DESFECHO = {
    "alvo1": "alvo1_pct", "alvo2": "alvo2_pct",
    "alvo_final": "alvo_final_pct", "stop": "stop_pct",
}


def retorno_pct_do_desfecho(desfecho: str) -> float | None:
    """Retorno percentual nominal associado ao desfecho (Camada 2.4 —
    telemetria por gatilho). Usa os percentuais de CONFIG que definem
    alvos/stop (mesma fonte que gera os valores absolutos do sinal), não o
    caminho de preço real — é uma categorização, não uma medição exata do
    retorno realizado. `expirou`/`aberto`/`indeterminado` não têm percentual
    associado de forma confiável -> None."""
    campo = _RETORNO_PCT_POR_DESFECHO.get(desfecho)
    if campo is None:
        return None
    return round(CONFIG[campo] * 100, 1)
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `pytest tests/test_outcome.py -v`
Expected: PASS em todos os testes

- [ ] **Step 5: Commit**

```bash
git add backend/domain/outcome.py tests/test_outcome.py
git commit -m "feat(score): adiciona retorno_pct_do_desfecho para telemetria por gatilho"
```

---

### Task 8: Explosão por gatilho em `trigger_outcomes` (`outcome_service.py`)

**Files:**
- Modify: `backend/services/outcome_service.py`
- Test: `tests/test_outcome_service.py`

- [ ] **Step 1: Escrever os testes que falham**

Substituir o conteúdo de `tests/test_outcome_service.py` por:

```python
"""Teste de wiring do outcome_service (Supabase + preços mockados)."""
from backend.services import outcome_service as osvc


class _FakeQuery:
    def __init__(self, store, table_name, data=None):
        self._store = store
        self._table = table_name
        self._data = data

    def select(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def upsert(self, rows, on_conflict=None):
        self._store.setdefault(self._table, []).extend(rows)
        return self

    def execute(self):
        if self._table == "signals":
            return type("R", (), {"data": self._data})()
        return type("R", (), {"data": []})()


class _FakeSupabase:
    def __init__(self, data):
        self._data = data
        self.store = {}

    def table(self, nome):
        return _FakeQuery(self.store, nome, self._data)


def _row(**over):
    r = {
        "id": 1, "ticker": "TESTE3", "tipo_sinal": "CALL", "strike_ref": 110.0,
        "premio_est": 1.0, "preco_tela": None,
        "alvo1": 1.25, "alvo2": 3.50, "alvo_final": 8.0, "stop": 0.57,
        "hv_20d": 40.0, "iv_mercado": None, "dte": 20, "preco_acao": 100.0,
        "score": 9, "score_ponderado": 72, "ponderado_passou": True,
        "timestamp": "2026-05-20T13:00:00+00:00",
    }
    r.update(over)
    return r


def test_avaliar_sinais_sem_supabase_retorna_erro(monkeypatch):
    monkeypatch.setattr(osvc, "get_supabase", lambda: None)
    rep = osvc.avaliar_sinais(dias=30)
    assert rep["resolvidos"] == 0
    assert "erro" in rep


def test_avaliar_sinais_avalia_e_agrega(monkeypatch):
    monkeypatch.setattr(osvc, "get_supabase", lambda: _FakeSupabase([_row()]))
    # ação subindo → CALL ganha
    monkeypatch.setattr(osvc, "_precos_desde", lambda t, d: [100, 104, 108, 113, 118, 122])
    rep = osvc.avaliar_sinais(dias=30)
    assert rep["sinais_avaliados"] == 1
    assert rep["ganhos"] == 1
    assert rep["win_rate_classico"] == 100.0
    assert "distribuicao" in rep


def test_avaliar_sinais_pula_sem_precos(monkeypatch):
    monkeypatch.setattr(osvc, "get_supabase", lambda: _FakeSupabase([_row()]))
    monkeypatch.setattr(osvc, "_precos_desde", lambda t, d: [])  # sem dados
    rep = osvc.avaliar_sinais(dias=30)
    assert rep["sinais_avaliados"] == 0


def test_avaliar_sinais_persiste_trigger_outcomes_para_desfecho_terminal(monkeypatch):
    fake = _FakeSupabase([_row(gatilhos_ids=["G2", "G3"], setup="REVERSAO")])
    monkeypatch.setattr(osvc, "get_supabase", lambda: fake)
    monkeypatch.setattr(osvc, "_precos_desde", lambda t, d: [100, 104, 108, 113, 118, 122])

    osvc.avaliar_sinais(dias=30)

    linhas = fake.store.get("trigger_outcomes", [])
    assert len(linhas) == 2
    assert {l["gatilho_id"] for l in linhas} == {"G2", "G3"}
    assert all(l["signal_id"] == 1 for l in linhas)
    assert all(l["resultado_final"] == "alvo_final" for l in linhas)
    assert all(l["retorno_pct"] == 700.0 for l in linhas)
    assert all(l["dias_ate_resolucao"] == 5 for l in linhas)
    assert {l["familia"] for l in linhas} == {"OSCILADOR", "ESTRUTURA"}


def test_avaliar_sinais_pula_trigger_outcomes_sem_gatilhos_ids(monkeypatch):
    fake = _FakeSupabase([_row()])  # sinal legado, sem gatilhos_ids
    monkeypatch.setattr(osvc, "get_supabase", lambda: fake)
    monkeypatch.setattr(osvc, "_precos_desde", lambda t, d: [100, 104, 108, 113, 118, 122])

    osvc.avaliar_sinais(dias=30)

    assert fake.store.get("trigger_outcomes", []) == []
```

- [ ] **Step 2: Rodar os testes e confirmar que os 2 novos falham**

Run: `pytest tests/test_outcome_service.py -v`
Expected: os 3 testes antigos PASSAM (a troca dos fakes preserva o comportamento); os 2 novos testes de `trigger_outcomes` FALHAM (`fake.store` fica vazio — a explosão ainda não existe)

- [ ] **Step 3: Implementar a explosão por gatilho**

Em `backend/services/outcome_service.py:14-22`, trocar:

```python
from backend.services.supabase_client import get_supabase
from backend.services.core_engine import _baixar_ohlcv
from backend.domain.outcome import avaliar_desfecho, comparar_por_desfecho

logger = logging.getLogger("b3_api")

_CAMPOS = ("ticker, tipo_sinal, strike_ref, premio_est, preco_tela, alvo1, alvo2, "
           "alvo_final, stop, hv_20d, iv_mercado, dte, preco_acao, score, "
           "score_ponderado, ponderado_passou, timestamp")
```

por:

```python
from backend.services.supabase_client import get_supabase
from backend.services.core_engine import _baixar_ohlcv
from backend.domain.outcome import avaliar_desfecho, comparar_por_desfecho, retorno_pct_do_desfecho
from backend.domain.scoring import GATILHOS

logger = logging.getLogger("b3_api")

_CAMPOS = ("id, ticker, tipo_sinal, strike_ref, premio_est, preco_tela, alvo1, alvo2, "
           "alvo_final, stop, hv_20d, iv_mercado, dte, preco_acao, score, "
           "score_ponderado, ponderado_passou, gatilhos_ids, setup, timestamp")

_DESFECHOS_TERMINAIS = ("alvo1", "alvo2", "alvo_final", "stop", "expirou")


def _persistir_trigger_outcomes(supabase, sinal: dict, resultado: dict) -> None:
    """Explode o desfecho do sinal em uma linha por gatilho disparado
    (Camada 2.4). Só persiste desfechos terminais (ignora aberto/indeterminado,
    que ainda não têm resultado definitivo); idempotente via upsert em
    (signal_id, gatilho_id) — chamadas repetidas de `avaliar_sinais` sobre o
    mesmo sinal não duplicam linhas. Sinais sem `gatilhos_ids` (legados,
    anteriores a esta camada) são pulados. Falha de persistência não impede
    a avaliação do sinal (apenas loga)."""
    if resultado["desfecho"] not in _DESFECHOS_TERMINAIS:
        return
    ids = sinal.get("gatilhos_ids") or []
    if not ids:
        return

    retorno_pct = retorno_pct_do_desfecho(resultado["desfecho"])
    linhas = [{
        "signal_id":          sinal["id"],
        "gatilho_id":         gid,
        "familia":            GATILHOS.get(gid, {}).get("familia"),
        "pontos":             GATILHOS.get(gid, {}).get("pontos"),
        "setup":              sinal.get("setup"),
        "resultado_final":    resultado["desfecho"],
        "retorno_pct":        retorno_pct,
        "dias_ate_resolucao": resultado["dias_ate"],
    } for gid in ids]

    try:
        supabase.table("trigger_outcomes").upsert(linhas, on_conflict="signal_id,gatilho_id").execute()
    except Exception as e:
        logger.warning(f"Erro ao persistir trigger_outcomes do sinal {sinal.get('id')}: {e}")
```

Em seguida, dentro de `avaliar_sinais`, localizar:

```python
        r = avaliar_desfecho(s, precos)
        avaliados.append({
```

e substituir por:

```python
        r = avaliar_desfecho(s, precos)
        _persistir_trigger_outcomes(supabase, s, r)
        avaliados.append({
```

- [ ] **Step 4: Rodar os testes e confirmar que todos passam**

Run: `pytest tests/test_outcome_service.py -v`
Expected: PASS (5 testes)

- [ ] **Step 5: Rodar a suíte completa do projeto**

Run: `pytest tests/ -v`
Expected: PASS em todos (exceto a falha pré-existente e não relacionada já documentada)

- [ ] **Step 6: Commit**

```bash
git add backend/services/outcome_service.py tests/test_outcome_service.py
git commit -m "feat(score): explode desfecho do sinal em trigger_outcomes por gatilho"
```

---

### Task 9: Documentar a assimetria CALL/PUT (Camada 2.3)

**Files:**
- Modify: `docs/ESTRATEGIAS_OPCOES_B3.md`

- [ ] **Step 1: Adicionar a seção de documentação**

Ao final de `docs/ESTRATEGIAS_OPCOES_B3.md` (depois do bloco `> [!WARNING]` final), adicionar:

```markdown

---

## Famílias de gatilhos e a assimetria CALL × PUT (Camada 2)

Os 20 gatilhos são agrupados em 5 famílias (Camada 2.1 — `backend/domain/scoring.py::GATILHOS`):

| Família | Gatilhos de alta | Gatilhos de baixa |
|---|---|---|
| OSCILADOR | G1, G2, G6 | B1, B2, B6 |
| TENDENCIA | G4, G7, G11 | B4, B5, B9 |
| ESTRUTURA | G3, G8 | B3 |
| DIVERGENCIA | G9 | B7 |
| LIQUIDEZ | G5, G10 | B8 |

O lado de alta tem 11 gatilhos (máx. 23 pts); o de baixa tem 9 (máx. 21 pts). Isso é uma
**decisão atual, não uma lacuna não examinada**: faltam dois gatilhos espelho do lado
baixista —

1. **Espelho de G8** (Bollinger inferior → família ESTRUTURA): um gatilho de preço na
   banda superior de Bollinger para o lado de baixa.
2. **Espelho de G5** (volume relativo → família LIQUIDEZ): um gatilho de volume em
   distribuição (alta em queda de preço) para o lado de baixa.

Ambos ficam para uma iteração futura, com seu próprio ciclo de validação (Camada 5) —
adicionar gatilhos novos muda a distribuição de pontos por família e exige
recalibração, o que está fora do escopo da Camada 2 (que reorganiza os gatilhos
*existentes*, não adiciona novos). Até essa iteração, o viés estrutural de 2 pontos a
mais no lado de alta é aceito conscientemente.
```

- [ ] **Step 2: Commit**

```bash
git add docs/ESTRATEGIAS_OPCOES_B3.md
git commit -m "docs(estrategias): documenta familias de gatilhos e assimetria CALL/PUT (Camada 2.3)"
```

---

## Pendência manual final (antes do deploy)

- [ ] Aplicar `supabase/migrations/006_camada2_motor_score.sql` no Supabase Dashboard.
- [ ] Atualizar `docs/CHANGELOG.md` registrando a Camada 2 (seguir o padrão das entradas das Camadas 0 e 1).
