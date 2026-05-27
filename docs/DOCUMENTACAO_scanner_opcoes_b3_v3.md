# DOCUMENTAÇÃO TÉCNICA — SCANNER DE OPÇÕES OTM B3 v3.0

## 1. VISÃO GERAL

**Arquivos core:** 
- `core_engine.py` — Motor de análise de ativos e geração de sinais
- `scanner_opcoes_b3_v3.py` — CLI com interface Telegram e tabelas
- `config.py` — Configuração centralizada de parâmetros
- `indicators.py` — Cálculo de indicadores técnicos (RSI, MACD, Estocástico, Bollinger, ATR, EMA)
- `options_math.py` — Matemática de opções (Black-Scholes, DTE, IV histórica, decodificação B3)
- `backtest.py` — Motor de backtesting histórico

**Estratégia base:** Swing Trade com Opções OTM (fora do dinheiro)  
**Período validado:** Março 2026 — maio 2026 (22+ operações confirmadas)  
**Linguagem:** Python 3.8+  
**Dependências:** yfinance, pandas, numpy, ta, scipy, colorama, tabulate, requests

### Objetivo
Identificar setups de swing trade explosivos (1–5 dias úteis) em opções OTM da B3 usando um **motor de score multifatorial** com 11 gatilhos de alta e 8 gatilhos de baixa, acoplado a precificação matemática (Black-Scholes).

### Performance histórica
**Base de dados:** 22 operações confirmadas (Mar–Mai/2026)
| Métrica | Valor |
|---|---|
| Taxa de acerto (Alvo 1+) | 82% (18 wins / 4 stops) |
| Ganho médio (wins) | +82,7% |
| Perda média (stops) | -39,5% |
| Expectância líquida | +60,4% por operação |
| Maior resultado | MGLUQ833 +455% (Alvo 2) |
| 2° maior | RADLP225 +257% (Alvo 2) |
| 3° maior | WEGED510 +191% (Alvo 2) |
| Operações com R/R ≥ 1.0 | 91% (20 sinais) |

---

## 2. ARQUITETURA

### Fluxo de Execução

```
scanner_opcoes_b3_v3.py: main()
 │
 ├─ [modo interativo] analisar_ativo(ticker, nome, df_provided=None)
 │   ou
 ├─ [modo produção] varrer_ativos(ATIVOS_B3, interval='1d')
 │
 └─ Para cada ativo:
     ├─ Validação de reentrada (últimos 3 dias)
     ├─ yf.download() → 6 meses OHLCV (ou df_provided para backtest)
     ├─ Filtro volume (min 1M diário)
     ├─ calcular_indicadores(df) [indicators.py]
     │   ├─ Estocástico (K, D)
     │   ├─ RSI, MACD, ATR, EMA (9, 21, 200)
     │   ├─ Bollinger Bands
     │   ├─ Máximos/Mínimos locais
     │   └─ Suporte/Resistência 20D
     │
     ├─ Motor de Score (11 gatilhos ALTA + 8 gatilhos BAIXA)
     │   ├─ Detecção de divergência (G9/B7)
     │   ├─ Zonas de demanda/oferta (G10/B8)
     │   ├─ Canal linear (G11/B9)
     │   └─ Score de horário (+1 a +3 conforme pregão)
     │
     ├─ Decisão direcional (CALL se score_alta > score_baixa)
     ├─ Seleção de strike OTM (dinâmico por volatilidade)
     ├─ Cálculo DTE e IV histórica
     ├─ Black-Scholes para prêmio estimado
     ├─ Definição de alvos e stops (R/R ≥ 0.8)
     │
     └─ Retorna dict(sinal) se score >= 5 e R/R >= 0.8
         ├─ Registra reentrada
         ├─ Envia Telegram (se configurado)
         └─ Exibe no terminal com cores
```

### Estrutura de Módulos

| Módulo | Função | Dependências |
|--------|--------|--------------|
| `core_engine.py` | `analisar_ativo()` — motor central | indicators, options_math, config |
| `config.py` | Parâmetros globais, histórico de sinais | — |
| `indicators.py` | 6 funções de cálculo de indicadores + 3 funções avançadas | numpy, pandas, ta (opcional) |
| `options_math.py` | Black-Scholes, DTE, IV, decodificação B3 | numpy, pandas, scipy, datetime, calendar |
| `scanner_opcoes_b3_v3.py` | CLI, Telegram, tabelas, backtest | core_engine, backtest, requests, colorama |
| `backtest.py` | Motor de backtesting histórico | core_engine, indicators |

---

## 3. CONFIGURAÇÃO (CONFIG dict)

| Parâmetro | Valor padrão | Origem na planilha |
|---|---|---|
| stoch_oversold | 25 | ITUB4, B3SAQ180 — cruzamento sobrevenda |
| stoch_overbought | 75 | Gatilho PUT em sobrecompra |
| rsi_oversold | 35 | ABEV3, GGBR4 — divergência RSI |
| rsi_overbought | 65 | Zona de oferta RSI alto |
| ema_fast | 9 | SUZBE450 — cruzamento médias +27,9% |
| ema_slow | 21 | Tendência curto prazo |
| volume_mult | 1.5x | MGLUQ833 — captura liquidez +455% |
| stop_pct | -42% | Média observada: -39,5% (4 stops) |
| alvo1_pct | +25% | Alvo 1 real varia: +10% a +71% |
| alvo2_pct | +150% | Alvos parciais intermediários |
| alvo_final_pct | +400% | Posição especulativa remanescente |
| min_volume_diario | 1.000.000 | Garantia liquidez na opção |

---

## 4. DECODIFICADOR DE OPÇÕES B3

**Formato:** `[4 letras ação][1 letra tipo/mês][3 dígitos strike]`

**Tabela de meses CALL (A–L) / PUT (M–X):**
```
CALL: A=Jan B=Fev C=Mar D=Abr E=Mai F=Jun G=Jul H=Ago I=Set J=Out K=Nov L=Dez
PUT:  M=Jan N=Fev O=Mar P=Abr Q=Mai R=Jun S=Jul T=Ago U=Set V=Out W=Nov X=Dez
```

**Heurística de strike (com bug identificado na v2):**
```python
# Regras corretas:
# BOVA11: strike = strike_raw diretamente (ex: BOVAR169 → R$169)
# Ações > R$10 com 3 dígitos: dividir por 100 (ex: PETRQ440 → R$44,00)
# Ações < R$10 com 3-4 dígitos: dividir por 1000 (ex: MGLUQ833 → R$8,33)
```

**Exemplos validados pela planilha:**
| Código | Ativo | Tipo | Venc | Strike | Resultado |
|---|---|---|---|---|---|
| BBSER376 | BBSE3 | PUT | Jun/26 | R$37,60 | +26,41% Alvo 1 |
| MGLUF672 | MGLU3 | CALL | Jun/26 | R$6,72 | +28,94% Alvo 1 |
| LRENQ146 | LREN3 | PUT | Mai/26 | R$14,60 | +71,42% Alvo 1 |
| MGLUQ833 | MGLU3 | PUT | Mai/26 | R$8,33 | +455% Alvo 2 |
| WEGED510 | WEGE3 | CALL | Abr/26 | R$51,00 | +191% Alvo 2 |
| RADLP225 | RADL3 | PUT | Abr/26 | R$22,50 | +257% Alvo 2 |

---

## 5. MOTOR DE SINAIS — GATILHOS DETALHADOS (core_engine.py)

Todos os gatilhos abaixo são verificados no função `analisar_ativo()`, linhas 88–176. O sistema é **aditivo**: cada gatilho identificado soma pontos ao respectivo lado (alta ou baixa). A direção vencedora emite o sinal se score ≥ MIN_SCORE (5 pontos).

### 5.1 Gatilhos de ALTA → Sinal CALL (11 critérios)

| ID | Critério | Score | Código [core_engine.py] |
|---|---|---|---|
| **G1** | Estocástico: %K cruza acima %D **em sobrevenda** (%K < 35) | +3 | linha 89–91 |
| **G2** | RSI < 35 (sobrevenda) | +2 | linha 93–95 |
| **G3** | Preço ≤ suporte_20D + 1×ATR (suporte dinâmico) | +2 | linha 97–99 |
| **G4** | EMA9 cruzou **acima** EMA21 (reversão bullish) | +2 | linha 101–103 |
| **G5** | Volume ≥ 1,5× média_20D (liquidez demanda) | +1 | linha 105–107 |
| **G6** | MACD diff cruzou zero **para cima** (momentum altista) | +2 | linha 109–111 |
| **G7** | 3 fundos locais **ascendentes** (estrutura de alta) | +2 | linha 113–116 |
| **G8** | Preço ≤ Bollinger inferior × 1,01 (compressão volatilidade) | +1 | linha 118–120 |
| **G9** | Divergência altista: preço cai, RSI sobe | +3 | linha 122–125 |
| **G10** | Preço em zona de demanda histórica (±1 ATR de swing low) | +3 | linha 127–130 |
| **G11** | Canal linear altista (slope topos & fundos > 0) | +2 | linha 132–135 |

### 5.2 Gatilhos de BAIXA → Sinal PUT (8 critérios)

| ID | Critério | Score | Código [core_engine.py] |
|---|---|---|---|
| **B1** | Estocástico: %K cruza abaixo %D **em sobrecompra** (%K > 75) | +3 | linha 138–140 |
| **B2** | RSI > 65 (sobrecompra) | +2 | linha 142–144 |
| **B3** | Preço ≥ resistência_20D − 1×ATR (resistência dinâmica) | +2 | linha 146–148 |
| **B4** | EMA9 cruzou **abaixo** EMA21 (reversão bearish) | +2 | linha 150–152 |
| **B5** | 3 topos locais **descendentes** (estrutura de baixa) | +2 | linha 154–157 |
| **B6** | MACD diff cruzou zero **para baixo** (momentum baixista) | +2 | linha 159–161 |
| **B7** | Divergência baixista: preço sobe, RSI cai | +3 | linha 163–166 |
| **B8** | Preço em zona de oferta histórica (±1 ATR de swing high) | +3 | linha 168–171 |
| **B9** | Canal linear baixista (slope topos & fundos < 0) | +2 | linha 173–176 |

### 5.3 Bônus de Horário (score_horario)

Aplicado a **ambos** os lados (alta e baixa):
- **10:00–11:30:** +2 pontos (abertura, alta volatilidade)
- **13:00–15:00:** +3 pontos (pico pós-almoço)
- **15:00–16:30:** +1 ponto (fechamento, liquidez decrescente)
- **Outros horários:** 0 pontos

**Decisão final (linha 184–199):**
- Se `score_alta >= score_baixa`: sinal **CALL**
- Se `score_baixa > score_alta`: sinal **PUT**
- Se ambos < MIN_SCORE (5): **sem sinal**

---

## 6. IMPLEMENTAÇÃO ATUAL (v3.0+) — Especificação Técnica

### 6.1 ✅ Cálculo Real de Risk/Reward (core_engine.py, linhas 218–226)

```python
risco = premio_est - stop
rr_alvo1 = round((alvo1 - premio_est) / risco, 2) if risco > 0 else 0
rr_alvo2 = round((alvo2 - premio_est) / risco, 2) if risco > 0 else 0
rr_final = round((alvo_final - premio_est) / risco, 2) if risco > 0 else 0

# FILTRO CRÍTICO: só emitir sinal se rr_alvo1 >= CONFIG["rr_minimo"] (0.8)
if rr_alvo1 < CONFIG["rr_minimo"]:
    return None  # Sinal descartado
```

**Observado:** R/R Alvo 1 típico = 0.8x–1.5x | Alvo Final = 5x–15x

### 6.2 ✅ Detecção Formal de Divergência (indicators.py, linhas 80–89)

```python
def detectar_divergencia(df: pd.DataFrame, janela: int = 5) -> tuple:
    precos = df["Close"].tail(janela).values
    rsi    = df["rsi"].tail(janela).values
    # Alta: preço faz fundo mais baixo, RSI faz fundo mais alto
    div_alta  = (precos[-1] < precos[0]) and (rsi[-1] > rsi[0])
    # Baixa: preço faz topo mais alto, RSI faz topo mais baixo
    div_baixa = (precos[-1] > precos[0]) and (rsi[-1] < rsi[0])
    return div_alta, div_baixa  # Mapeados como G9 (+3) e B7 (+3)
```

**Status:** ✅ Implementado e testado

### 6.3 ✅ Zonas de Demanda e Oferta (indicators.py, linhas 91–105)

```python
def encontrar_zonas_demanda_oferta(df: pd.DataFrame, lookback: int = 60,
                                   tolerancia_atr: float = 1.0) -> tuple:
    preco  = float(df["Close"].iloc[-1])
    atr    = float(df["atr"].iloc[-1])
    fundos = df[df["is_fundo_local"]]["Low"].tail(lookback).values
    topos  = df[df["is_topo_local"]]["High"].tail(lookback).values
    
    zona_demanda = any(abs(preco - f) <= atr * tolerancia_atr for f in fundos)
    zona_oferta  = any(abs(preco - t) <= atr * tolerancia_atr for t in topos)
    
    return zona_demanda, zona_oferta  # Mapeados como G10 (+3) e B8 (+3)
```

**Status:** ✅ Implementado (core_engine.py, linhas 127–130 e 168–171)

### 6.4 ✅ Detecção de Canal Linear (indicators.py, linhas 107–124)

```python
def detectar_canal_linear(df: pd.DataFrame, janela: int = 20) -> tuple:
    idx = np.arange(janela)
    h   = df["High"].tail(janela).values
    l   = df["Low"].tail(janela).values
    
    slope_topos  = np.polyfit(idx, h, 1)[0]
    slope_fundos = np.polyfit(idx, l, 1)[0]
    
    canal_altista  = (slope_topos > 0) and (slope_fundos > 0)
    canal_baixista = (slope_topos < 0) and (slope_fundos < 0)
    return canal_altista, canal_baixista, slope_medio  # G11 (+2) e B9 (+2)
```

**Status:** ✅ Implementado (core_engine.py, linhas 132–135 e 173–176)

### 6.5 ✅ OTM Dinâmico por Volatilidade (config.py, linhas 75–84)

```python
OTM_POR_ATIVO = {
    "MGLU3": 0.12, "BRKM5": 0.10, "USIM5": 0.10,  # Alta volatilidade (±12%)
    "BEEF3": 0.12, "MRVE3": 0.10, "BRAV3": 0.10,  
    "VALE3": 0.07, "SUZB5": 0.07, "LREN3": 0.07,  # Média volatilidade (±7%)
    "ITUB4": 0.05, "BBDC4": 0.05, "ABEV3": 0.05,  # Baixa volatilidade (±5%)
    "BOVA11": 0.04,  # ETF ultra-líquido (±4%)
}

# Uso em core_engine.py, linha 202
dist_otm = OTM_POR_ATIVO.get(ticker_base, 0.07)  # default 7%
```

**Status:** ✅ Implementado e em produção

### 6.6 ✅ Rastreio de Reentradas (config.py, linhas 86–95)

```python
_historico_sinais = {}  # ticker → [datetime, datetime, ...]

def registrar_sinal(ticker: str):
    _historico_sinais.setdefault(ticker, []).append(datetime.now())

def is_reentrada_valida(ticker: str) -> bool:
    if ticker not in _historico_sinais:
        return True
    dias_desde_ultimo = (datetime.now() - _historico_sinais[ticker][-1]).days
    return dias_desde_ultimo >= CONFIG["reentrada_min_dias"]  # default 3 dias
```

**Status:** ✅ Implementado (core_engine.py, linhas 22–25)

### 6.7 ✅ Filtro de DTE (options_math.py, linhas 60–79)

```python
def calcular_dte(mes_venc: int, ano_venc: int = None) -> int:
    cal = calendar.monthcalendar(ano_venc, mes_venc)
    sextas = [semana[4] for semana in cal if semana[4] != 0]
    venc = date(ano_venc, mes_venc, sextas[2])  # 3ª sexta-feira
    dias_corridos = (venc - date.today()).days
    return max(0, round(dias_corridos * 5 / 7))  # conversão para dias úteis

# Filtro crítico em mes_vencimento_ideal():
if CONFIG["dte_minimo"] <= dte <= CONFIG["dte_maximo"]:  # 10–45 dias úteis
    return mes, ano, dte
```

**Status:** ✅ Implementado (core_engine.py, linha 207)

### 6.8 ✅ Integração Score de Horário (core_engine.py, linhas 178–181)

```python
bonus_horario = score_horario()  # Função em config.py, linhas 97–108
score_alta  += bonus_horario
score_baixa += bonus_horario
```

**Status:** ✅ Implementado e em produção

### 6.9 ✅ Notificação Telegram (scanner_opcoes_b3_v3.py, linhas 35–60)

```python
def enviar_telegram(sinal: dict):
    token   = CONFIG.get("telegram_token", "")
    chat_id = CONFIG.get("telegram_chat_id", "")
    
    msg = (
        f"🎯 *SINAL B3 — {sinal['ticker']}*\n"
        f"*Tipo:* {sinal['tipo_sinal']} | *Venc:* {mes_str}/{sinal['ano_venc']}\n"
        f"*Entrada:* R$ {sinal['entrada_min']:.2f} – {sinal['entrada_max']:.2f}\n"
        f"*Alvo 1:* R$ {sinal['alvo1']:.2f} | R/R: {sinal['rr_alvo1']:.1f}×\n"
        f"*Stop:* R$ {sinal['stop']:.2f}\n"
        f"*Score:* {sinal['score']}/10"
    )
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                  data={'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'})
```

**Status:** ✅ Implementado (requer `TELEGRAM_TOKEN` e `TELEGRAM_CHAT_ID` em env ou config.py)

---

## 7. HISTÓRICO DE BUGS CORRIGIDOS

| Versão | Descrição | Impacto | Correção |
|--------|-----------|--------|----------|
| v2.0 | Heurística strike incorreta para BOVA11 (BOVAR169 → R$18,10 em vez de R$169) | Alto | ✅ Corrigido em options_math.py (linhas 34–48) com case ETF |
| v2.0 | CONFIG e ATIVOS_B3 declarados com indentação errada | Crítico | ✅ Separado em config.py (dicts no nível de módulo) |
| v2.0 | Prêmio estimado 1,8% — muito impreciso | Médio | ✅ Black-Scholes implementado + IV histórica (options_math.py) |
| v2.5 | Score de horário não integrado ao motor | Médio | ✅ Integrado em core_engine.py (linhas 178–181) |

---

## 8. ATIVOS B3 — UNIVERSO COMPLETO MAPEADO DA PLANILHA

| Ativo | Nome | Setor | Ocorrências planilha | Maior resultado |
|---|---|---|---|---|
| MGLU3 | Magazine Luiza | Varejo | 5 sinais | +455% (MGLUQ833) |
| VALE3 | Vale | Mineração | 4 sinais | +28% Alvo 1 |
| BRKM5 | Braskem | Petroquímica | 3 sinais | STOP -40% |
| LREN3 | Lojas Renner | Varejo | 3 sinais | +71,42% (LRENQ146) |
| SUZB5 | Suzano | Papel/Celulose | 3 sinais | +27,9% (SUZBE450) |
| WEGE3 | WEG | Industrial | 2 sinais | +191% (WEGED510) |
| ABEV3 | Ambev | Bebidas | 2 sinais | +138% (ABEVP161) |
| ITUB4 | Itaú Unibanco | Financeiro | 2 sinais | Em aberto |
| BOVA11 | ETF IBOVESPA | ETF/Hedge | 4 sinais | +17,85% (BOVAQ183) |
| RADL3 | RD Saúde | Farmácias | 2 sinais | +257% (RADLP225) |
| USIM5 | Usiminas | Siderurgia | 2 sinais | +21,74% |
| B3SA3 | B3 S.A. | Financeiro | 3 sinais | +32,55% (B3SAQ187) |
| BBSE3 | BB Seguridade | Seguros | 2 sinais | +26,41% (BBSER376) |
| CSNA3 | CSN | Siderurgia | 2 sinais | Em aberto |
| BBAS3 | Banco do Brasil | Financeiro | 2 sinais | Em aberto |
| BBDC4 | Bradesco | Financeiro | 2 sinais | Em aberto |
| GGBR4 | Gerdau | Siderurgia | 2 sinais | Em aberto |
| SANB11 | Santander | Financeiro | 1 sinal | +18,91% |
| PETR4 | Petrobras PN | Petróleo | 1 sinal | Em aberto |
| BPAC11 | BTG Pactual | Financeiro | 1 sinal | +10% |
| GOAU4 | Gerdau Metalúrg. | Siderurgia | 1 sinal | +37,5% |
| BEEF3 | Minerva Foods | Alimentos | 1 sinal | Em aberto |
| BRAV3 | Brava Energia | Petróleo | 1 sinal | Em aberto |
| ASAI3 | Assaí Atacadista | Varejo | 1 sinal | STOP -38% |
| MRVE3 | MRV Engenharia | Construção | 1 sinal | Em aberto |

---

## 9. ROADMAP DE EVOLUÇÃO

**Fase 1 — Correções críticas (v3.0) ✅ CONCLUÍDA:**
- [x] Corrigir heurística strike BOVA11
- [x] Separar CONFIG e ATIVOS_B3
- [x] Elevar MIN_SCORE para 5
- [x] Implementar cálculo R/R (Melhoria 6.1)
- [x] Integração Score de Horário

**Fase 2 — Novos indicadores (v3.1) ✅ CONCLUÍDA:**
- [x] Divergência RSI/Stoch (G9/B7) — +3 score (indicators.py)
- [x] Zonas de demanda/oferta via swings (G10/B8) — +3 score (indicators.py)
- [x] Detecção de canal linear (G11/B9) — +2 score (indicators.py)
- [x] Score de horário integrado ao motor (core_engine.py)

**Fase 3 — Prêmio e estrutura de opção (v3.2) ✅ CONCLUÍDA:**
- [x] OTM dinâmico por volatilidade do ativo (config.py)
- [x] Filtro DTE 10–45 dias úteis (options_math.py)
- [x] Estimativa prêmio por IV histórica (options_math.py)
- [x] Black-Scholes simplificado (options_math.py)

**Fase 4 — Automação e produção (v4.0) ✅ CONCLUÍDA:**
- [x] Dados intraday H1 (yfinance interval='1h' em scanner_opcoes_b3_v3.py)
- [x] Notificação Telegram (scanner_opcoes_b3_v3.py)
- [x] Rastreio de reentradas (config.py)
- [x] Backtest integrado (backtest.py)
- [x] CLI com argumentos (scanner_opcoes_b3_v3.py)

**Fase 5 — Próximas otimizações (v4.1 roadmap):**
- [ ] Dados intraday H4 (análise de múltiplos timeframes)
- [ ] Integração com broker API (execução automática)
- [ ] Dashboard em tempo real (Streamlit/Plotly)
- [ ] Otimização de parâmetros via bagging/walk-forward
- [ ] Análise de drawdown e Sharpe ratio

---

## 10. AVISO LEGAL

> Este script é **exclusivamente educacional e analítico**.  
> Os prêmios exibidos são **estimativas** — dados reais de opções requerem acesso à chain da B3.  
> Para operar: InfoMoney, OpLab, Nelogica, Profit.  
> **Opções podem perder 100% do capital investido.** Consulte assessor habilitado CVM/CNPI.