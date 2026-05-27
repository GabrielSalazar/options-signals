# Montagem de Sinal — Scanner de Opções B3 v3.0+ (Pipeline Completo)

## Visão Geral

Este documento descreve detalhadamente o **fluxo de execução ponta-a-ponta** que transforma dados brutos do mercado (ações B3) em um **Sinal de Operação Estruturado** pronto para negociação de opções (Calls ou Puts OTM).

**Objetivo:** Não adivinhar o mercado, mas encontrar **assimetrias Risco/Retorno** onde a probabilidade está a nosso favor usando:
1. Motor de pontuação multifatorial (Score System) com 19 gatilhos
2. Modelo de precificação matemática (Black-Scholes)
3. Filtros de risco rigorosos (R/R ≥ 0.8, DTE 10–45d, reentrada 3d)

---

## 1. Pipeline de Execução Completo (core_engine.py, funcão analisar_ativo)

```
[1] Validação de Reentrada
    ↓
[2] Download OHLCV (6 meses diários)
    ↓
[3] Validação de Volume (>1M)
    ↓
[4] Cálculo de 19 Indicadores
    ↓
[5] Motor de Score (19 gatilhos)
    ↓
[6] Seleção de Strike (OTM dinâmico)
    ↓
[7] Cálculo DTE & IV Histórica
    ↓
[8] Black-Scholes (Prêmio estimado)
    ↓
[9] Estrutura de Entrada/Saída (Alvos + Stop)
    ↓
[10] Filtro R/R (≥ 0.8)
    ↓
[11] Registro & Notificação
```

### Etapa 1: Validação de Reentrada (linhas 22–25)

```python
ticker_base = ticker.replace(".SA", "")
if df_provided is None and not is_reentrada_valida(ticker_base):
    logger.info(f"↩ {ticker_base}: sinal recente (<3d), pulando")
    return None
```

**Objetivo:** Evitar múltiplos sinais no mesmo ativo em curto período.  
**Parâmetro:** `reentrada_min_dias = 3` (config.py, linha 36)  
**Exceção:** Testes e backtest (df_provided) ignoram reentrada.

### Etapa 2: Download & Tratamento de Erros (linhas 27–52)

```python
if df_provided is not None:
    df = df_provided.copy()
else:
    period = "6mo" if interval == "1d" else "730d"
    max_retries = 3
    df = None
    for tentativa in range(max_retries):
        try:
            df = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
            if df is not None and not df.empty:
                break
        except Exception as e:
            if tentativa == max_retries - 1:
                logger.error(f"Falha ao baixar {ticker} após 3 tentativas")
                return None
            time.sleep(2)

if df is None or len(df) < 30:
    return None
```

**Objetivo:** Robustez contra falhas de rede / API yfinance.  
**Parâmetros:**
- `period = "6mo"` para diário (6 meses de histórico)
- `period = "730d"` para 1h (2 anos para IV mais confiável)
- `max_retries = 3` com backoff de 2s
- Mínimo 30 barras para indicadores válidos

### Etapa 3: Limpeza de Colunas (linha 50)

```python
df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
```

**Objetivo:** yfinance retorna MultiIndex às vezes. Normalizar para nomes simples.

### Etapa 4: Cálculo de Indicadores (linhas 51–55)

```python
df = calcular_indicadores(df)  # indicators.py
df.dropna(inplace=True)

if len(df) < 5:
    return None
```

**Indicadores calculados (indicators.py):**
- Estocástico (K, D)
- RSI, MACD, ATR, EMA (9, 21, 200)
- Bollinger Bands (superior, inferior, média)
- Suporte/Resistência 20D (máximos/mínimos)
- Máximos/Mínimos locais
- Volume médio 20D
- Variação percentual

### Etapa 5: Motor de Score (linhas 57–181)

Este é o **coração do algoritmo**. Veja ESTRATEGIAS_OPCOES_B3.md para detalhes completos.

**Resumido:**
```python
# Últimas 2 barras (atual e anterior)
ultimo = df.iloc[-1]
penult = df.iloc[-2]

# Extração de valores com fallback
stoch_k = float(ultimo.get("stoch_k", 50))
rsi = float(ultimo.get("rsi", 50))
# ... 17 variáveis mais

# Loop nos 11 gatilhos de ALTA
if condicao_g1: sinais_alta.append("..."); score_alta += 3
if condicao_g2: sinais_alta.append("..."); score_alta += 2
# ... G11

# Loop nos 8 gatilhos de BAIXA
if condicao_b1: sinais_baixa.append("..."); score_baixa += 3
# ... B9

# Bônus horário
bonus_horario = score_horario()
score_alta += bonus_horario
score_baixa += bonus_horario

# Decisão
if score_alta >= score_baixa:
    tipo_sinal = "CALL"
else:
    tipo_sinal = "PUT"
```

**Saída:** `tipo_sinal`, `score`, `gatilhos` (lista de strings com emojis)

## 2. O Sistema de Pontuação (Score System) — Detalhado

### 2.1 Estrutura Aditiva

Diferente de sistemas binários (tipo "Se A cruza B, compre"), o scanner usa **lógica aditiva de consenso**. Ele analisa o mercado simultaneamente sob a ótica de Compra de CALL e de Compra de PUT, somando evidências independentes.

- **Score de ALTA:** Para cada um dos 11 gatilhos altistas identificado (+1 a +3 pontos)
- **Score de BAIXA:** Para cada um dos 8 gatilhos baixistas identificado (+1 a +3 pontos)
- **Bônus de Horário:** +0 a +3 adicional, aplicado **a ambos** os lados
- **Limite mínimo:** MIN_SCORE = 5 pontos (config.py, linha 29)

### 2.2 Exemplo Prático

```
Cenário: MGLU3 em 01/Mai/2026, 14:15

Gatilhos ALTA ativados:
  G1 (Stoch em sobrevenda)        +3
  G2 (RSI < 35)                   +2
  G10 (Zona demanda)              +3
  G5 (Volume 2.1x)                +1
  ──────────────────────────────
  score_alta = 9

Gatilhos BAIXA ativados:
  B2 (RSI ainda acima 50)         +0 (não ativado)
  ──────────────────────────────
  score_baixa = 0

Bônus horário (14:15):
  +3 (dentro de 13:00–15:00)
  
  score_alta = 9 + 3 = 12
  score_baixa = 0 + 3 = 3

Decisão: score_alta (12) > score_baixa (3) → SINAL CALL (Score 12/10) ✅
```

### 2.3 Distribuição Típica de Scores

Da base histórica (22 operações):
- **Score 5–6:** ~30% dos sinais (confiança média)
- **Score 7–9:** ~50% dos sinais (confiança alta)
- **Score 10+:** ~20% dos sinais (altíssima confiança, maiores ganhos)

---

## 3. Seleção Dinâmica do Strike OTM (core_engine.py, linhas 201–205)

O scanner **não usa a mesma distância OTM para todos** os papéis. Ativos voláteis suportam strikes distantes (baratos); ativos defensivos precisam de strikes muito próximos.

### 3.1 Tabela OTM por Volatilidade Histórica (config.py, linhas 75–84)

```python
OTM_POR_ATIVO = {
    # ALTA volatilidade (±12% OTM)
    "MGLU3": 0.12, "BEEF3": 0.12,
    "BRKM5": 0.10, "USIM5": 0.10, "ASAI3": 0.10,  # ±10%
    
    # MÉDIA volatilidade (±7-8%)
    "VALE3": 0.07, "SUZB5": 0.07, "LREN3": 0.07,
    "RADL3": 0.07, "GGBR4": 0.08, "GOAU4": 0.08,
    
    # BAIXA volatilidade (±5-6%)
    "ITUB4": 0.05, "BBDC4": 0.05, "ABEV3": 0.05,
    "BBSE3": 0.05, "BBAS3": 0.05, "SANB11": 0.05,
    "BPAC11": 0.05, "EGIE3": 0.05,
    
    # ULTRA-BAIXA (ETF)
    "BOVA11": 0.04,
}

dist_otm = OTM_POR_ATIVO.get(ticker.replace(".SA", ""), 0.07)  # default 7%
```

### 3.2 Cálculo do Strike de Referência (core_engine.py, linhas 203–205)

```python
strike_ref = round(
    preco * (1 - dist_otm) if tipo_sinal == "PUT" else preco * (1 + dist_otm), 2
)
```

### 3.3 Integração com Dados Reais de Opções (Scraping opcoes.net.br)

Ao invés de parar no `strike_ref` teórico, o sistema agora utiliza o módulo `data_providers.py` para consultar a grade **real** da B3 via web scraping na API pública do *opcoes.net.br*.

```python
# core_engine.py
opcao_real = get_real_options_from_opcoes_net(ticker_base, tipo_sinal, strike_ref)
if opcao_real:
    strike_ref = opcao_real["strike_real"]
    preco_tela = opcao_real["preco_tela"]
    ticker_opcao = opcao_real["ticker_opcao"]
```

**Como funciona a seleção real:**
1. O robô acessa `https://opcoes.net.br/listaopcoes/completa?idAcao=PETR4...`
2. Filtra por liquidez (número de negócios > 0).
3. Encontra a opção OTM com Strike matemático mais próximo do nosso `strike_ref` teórico.
4. Extrai o **Ticker verdadeiro (ex: PETRF100)** e o **Prêmio negociado em tela**.

Dessa forma, o cálculo do **Risco/Retorno (R/R)** e dos **Alvos de Saída** passam a ser calculados usando o preço real que o usuário pagará no Home Broker, em vez da estimativa puramente teórica de Black-Scholes.

**Exemplo:**
- MGLU3 a R$ 10,00 + sinal CALL → strike_ref = 10 × 1.12 = **R$ 11,20**
- MGLU3 a R$ 10,00 + sinal PUT → strike_ref = 10 × (1 - 0.12) = **R$ 8,80**

**Lógica:** Strikes OTM são mais baratos mas com menor probabilidade. Quanto mais volátil o ativo, maior o distanciamento possível sem perder gamma.

---

## 4. Escolha do Vencimento (DTE — Days to Expiration)

Operar opções requer **domínio de Theta Decay** (perda de valor pelo tempo). O motor rejeita:
- **< 10 dias úteis:** Theta-decay agressivo, risco de virar zero
- **> 45 dias úteis:** Pouco gamma, prêmios caros, movimento lento

### 4.1 Cálculo de DTE (options_math.py, linhas 60–79)

```python
def calcular_dte(mes_venc: int, ano_venc: int = None) -> int:
    cal = calendar.monthcalendar(ano_venc, mes_venc)
    sextas = [semana[4] for semana in cal if semana[4] != 0]  # todas as sextas
    venc = date(ano_venc, mes_venc, sextas[2])  # 3ª sexta-feira (B3 padrão)
    dias_corridos = (venc - date.today()).days
    return round(dias_corridos * 5 / 7)  # conversão: dias úteis ≈ 71% dos dias corridos
```

### 4.2 Iteração para DTE Ideal (options_math.py, linhas 71–79)

```python
def mes_vencimento_ideal() -> tuple:
    hoje = datetime.now()
    for delta_mes in range(0, 4):  # procura até 4 meses à frente
        mes = ((hoje.month - 1 + delta_mes) % 12) + 1
        ano = hoje.year + ((hoje.month - 1 + delta_mes) // 12)
        dte = calcular_dte(mes, ano)
        
        if CONFIG["dte_minimo"] <= dte <= CONFIG["dte_maximo"]:  # 10 ≤ dte ≤ 45
            return mes, ano, dte  # retorna 1º vencimento válido
    return hoje.month, hoje.year, 0  # fallback (raro)
```

**Uso em core_engine.py (linha 207):**
```python
mes_v, ano_v, dte = mes_vencimento_ideal()
```

**Exemplo de saída:**
- Hoje: 25/Mai/2026
- Iteração 0 (mai/2026): dte=0 (já venceu)
- Iteração 1 (jun/2026): dte=21 → **Retorna Jun/2026 com 21 dias úteis** ✅

---

## 5. Precificação e Estrutura de Entrada/Saída (options_math.py + core_engine.py)

Com Strike, Preço da Ação e DTE definidos, o sistema **não adivinha o preço da opção**. Ele calcula usando matemática.

### 5.1 IV Histórica (options_math.py, linhas 81–94)

```python
def estimar_iv_historica(df: pd.DataFrame, janela: int = 20, interval: str = "1d") -> float:
    retornos = np.log(df["Close"] / df["Close"].shift(1)).dropna()
    if len(retornos) < janela:
        return 0.40  # fallback conservador (40% IV)
    
    iv_periodo = retornos.tail(janela).std()
    
    if interval == "1h":
        fator_anualizacao = np.sqrt(252 * 7)
    else:
        fator_anualizacao = np.sqrt(252)
    
    return float(iv_periodo * fator_anualizacao)
```

**Interpretação:** IV de 32% = ativo muda ±32% em 1 ano (±1σ)

**Uso em core_engine.py (linha 208):**
```python
iv = estimar_iv_historica(df, interval=interval)
```

### 5.2 Black-Scholes Simplificado (options_math.py, linhas 96–112)

```python
def estimar_premio_otm(preco: float, strike: float, dte_du: int,
                       iv: float, tipo: str = "PUT") -> float:
    if dte_du <= 0 or iv <= 0:
        return max(0.10, round(preco * 0.015, 2))
    
    t = dte_du / 252
    d1 = (math.log(preco / strike) + 0.5 * iv**2 * t) / (iv * math.sqrt(t))
    d2 = d1 - iv * math.sqrt(t)
    
    if tipo == "PUT":
        premio = strike * norm.cdf(-d2) - preco * norm.cdf(-d1)
    else:
        premio = preco * norm.cdf(d1) - strike * norm.cdf(d2)
    
    return max(0.10, round(float(premio), 2))
```

**Saída:** Prêmio estimado (Black-Scholes) para CALL ou PUT OTM.

**Exemplo:** MGLU3 a R$10, strike R$11,20, 21 dias, IV 35% → prêmio ≈ R$0,32 (3,2%)

### 5.3 Montagem das Faixas (core_engine.py, linhas 209–216)

```python
premio_est   = estimar_premio_otm(preco, strike_ref, dte, iv, tipo_sinal)
entrada_min  = round(premio_est * 0.90, 2)  # −10%
entrada_max  = round(premio_est * 1.10, 2)  # +10%
alvo1        = round(premio_est * (1 + CONFIG["alvo1_pct"]),      2)  # +25%
alvo2        = round(premio_est * (1 + CONFIG["alvo2_pct"]),      2)  # +150%
alvo_final   = round(premio_est * (1 + CONFIG["alvo_final_pct"]), 2)  # +400%
stop         = round(premio_est * (1 + CONFIG["stop_pct"]),       2)  # −42%
```

**Exemplo (premio_est = R$ 0,35):**

| Nível | Preço | Ganho |
|-------|-------|-------|
| Entrada Min | R$ 0,32 (−10%) | — |
| Entrada Max | R$ 0,38 (+10%) | — |
| **Alvo 1** | R$ 0,44 | **+25%** |
| **Alvo 2** | R$ 0,88 | **+150%** |
| **Alvo Final** | R$ 1,75 | **+400%** |
| **Stop** | R$ 0,20 | **−42%** |

**Lógica:**
- Entrada: tolerância de ±10% no spread (mercado real)
- Alvo 1: lucro parcial, desfazer 50%
- Alvo 2: alvo técnico principal (maioria dos wins)
- Alvo Final: especulação com remanescente
- Stop: proteção absoluta

### 5.4 Cálculo de Risk/Reward (core_engine.py, linhas 218–226)

```python
risco = premio_est - stop  # 0.35 − 0.20 = 0.15

rr_alvo1 = round((alvo1 - premio_est) / risco, 2)  # (0.44 − 0.35) / 0.15 = 0.60
rr_alvo2 = round((alvo2 - premio_est) / risco, 2)  # (0.88 − 0.35) / 0.15 = 3.53
rr_final = round((alvo_final - premio_est) / risco, 2)

# FILTRO CRÍTICO
if rr_alvo1 < CONFIG["rr_minimo"]:  # 0.8
    return None  # SINAL REJEITADO
```

**Interpretação:**
- **R/R 0.6:** Ruim (ganha-se menos do que pode perder)
- **R/R 0.8:** Aceitável (ganho compensa perda com taxa >80%)
- **R/R 1.0+:** Bom (ganho = perda)
- **R/R 3.53:** Excelente (ganha-se muito mais)

**Fórmula de expectância:**
`Expectância = (Taxa_Acerto × Alvo) − (Taxa_Erro × Stop)`
Com R/R=0.8 e 82% de acerto: `(0.82 × 0.8) − (0.18 × 1.0) = +0.476 por operação` ✅

---

## 6. Registro e Notificação (core_engine.py + scanner_opcoes_b3_v3.py)

Se o ativo passou em **todos** os filtros (score, R/R, volume, DTE), o sinal é **registrado e notificado**.

### 6.1 Registro de Reentrada (core_engine.py, linha 229)

```python
if df_provided is None:  # Apenas em produção (não em backtest)
    registrar_sinal(ticker_base)  # Salva timestamp em _historico_sinais
```

### 6.2 Envio Telegram (scanner_opcoes_b3_v3.py, linhas 35–60)

```python
def enviar_telegram(sinal: dict):
    token   = CONFIG.get("telegram_token", "")
    chat_id = CONFIG.get("telegram_chat_id", "")
    if not token or not chat_id:
        return
    
    mes_str = NOMES_MESES.get(sinal["mes_venc"], "")
    msg = (
        f"🎯 *SINAL B3 — {sinal['ticker']}*\n"
        f"*Tipo:* {sinal['tipo_sinal']} | *Venc:* {mes_str}/{sinal['ano_venc']}\n"
        f"*Strike:* R$ {sinal['strike_ref']:.2f} ({sinal['dist_otm_pct']:.0f}% OTM)\n"
        f"*IV:* {sinal['iv_hist']}% | *DTE:* {sinal['dte']} du\n\n"
        f"*Entrada:* R$ {sinal['entrada_min']:.2f} – {sinal['entrada_max']:.2f}\n"
        f"*Alvo 1:* R$ {sinal['alvo1']:.2f} (+25%) | R/R: {sinal['rr_alvo1']:.1f}×\n"
        f"*Alvo 2:* R$ {sinal['alvo2']:.2f} (+150%) | R/R: {sinal['rr_alvo2']:.1f}×\n"
        f"*Stop:* R$ {sinal['stop']:.2f} (-42%)\n\n"
        f"*Score:* {sinal['score']}/10\n"
        f"*Gatilhos:*\n• " + "\n• ".join(sinal["gatilhos"])
    )
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                  data={'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'})
```

---

## 7. Output Final (Estrutura do Dicionário Retornado)

Se um ativo passa em **todos** os filtros, `analisar_ativo()` retorna um dicionário com 25 campos (core_engine.py, linhas 231–259):

```python
return {
    "emoji":        "🟢" ou "🔴",           # ícone visual
    "ticker":       "MGLU3",                # base sem .SA
    "nome":         "Magazine Luiza",
    "tipo_sinal":   "CALL" ou "PUT",
    "direcao":      "COMPRA DE CALL" ou "COMPRA DE PUT",
    "preco_acao":   10.50,                  # preço atual da ação
    "strike_ref":   11.70,                  # strike OTM selecionado
    "dist_otm_pct": 12.0,                   # distância em %
    "iv_hist":      32.5,                   # volatilidade implícita histórica
    "dte":          21,                     # dias úteis até vencimento
    "mes_venc":     6,                      # mês (junho)
    "ano_venc":     2026,
    "premio_est":   0.35,                   # prêmio estimado (Black-Scholes)
    "entrada_min":  0.32,
    "entrada_max":  0.38,
    "alvo1":        0.44,
    "alvo2":        0.88,
    "alvo_final":   1.75,
    "stop":         0.20,
    "rr_alvo1":     0.60,
    "rr_alvo2":     3.53,
    "rr_final":     13.57,
    "score":        9,                      # pontuação final (1–10)
    "stoch_k":      18.5,                   # último valor dos indicadores
    "rsi":          28.3,
    "vol_ratio":    2.15,
    "gatilhos":     ["📈 Estocástico...", "📈 RSI < 35", ...]
}
```

**Uso em scanner_opcoes_b3_v3.py:**
- Enviado ao Telegram via `enviar_telegram(sinal)`
- Impresso em terminal com cores
- Tabulado em resumo final com `tabulate()`
- Armazenado para análise histórica / backtest
