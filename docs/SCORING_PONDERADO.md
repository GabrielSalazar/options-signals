# Score Ponderado 0–100 — Passo a Passo

> Algoritmo alternativo ao score clássico de [core_engine.py](../core_engine.py).
> Ativável via `CONFIG["scoring_mode"] = "ponderado"`.

## 1. Por que duas modalidades?

| Modo | Característica | Onde vive |
|---|---|---|
| **Clássico** (default) | Score por contagem de gatilhos (+1/+2/+3). Inclui divergências, zonas de demanda/oferta, canal linear. Limiar 5. | [core_engine.py:94-187](../core_engine.py#L94-L187) |
| **Ponderado** (novo) | Pesos fixos por indicador, normalizado 0–100. Inspirado em 31 sinais reais. Limiar 60. | [scoring.py](../scoring.py) |

A coexistência permite A/B testing sem perder a lógica histórica.

## 2. Tabela de pesos (teto 100)

| # | Critério | Peso | Quando pontua |
|---|---|---|---|
| 1 | Preço da opção na faixa R$ 0,10–3,00 | **12** | Dentro da faixa |
| 2 | DTE entre 10 e 60 dias | **8** | Dentro do intervalo |
| 3 | `|Delta|` 0,15–0,45 (OTM ideal) | **10** | 5 se ATM/ITM, 0 se deep-OTM |
| 4 | Tendência (preço vs EMA9/EMA21/EMA200) | **20** | 0/8/16/20 conforme 0–3 mças favoráveis |
| 5 | MACD | **18** | 18 cruzamento • 12 favor+aceleração • 7 favor estável |
| 6 | RSI na zona da direção | **14** | Zona ideal; 10 sobrevendido/sobrecomprado; 6 esticando |
| 7 | Estocástico | **9** | Sobre-zona OU cruzamento K×D |
| 8 | ADX ≥ 25 | **5** | Tendência forte |
| 9 | Volume relativo | **8** | 8 se ≥1,5x • 4 se ≥1,0x |
| 10 | Bônus Bollinger | **4** | Preço junto à banda a favor (reversão) |
| | **Teto** | **100** | |
| | **Limiar (CONFIG["min_score_ponderado"])** | **60** | gera sinal |

## 3. Simetria CALL/PUT

O motor inverte automaticamente as direções:
- CALL: quer `trend_up` alto, RSI em recuperação (35–60), Estocástico em sobrevenda ou cruzando para cima, Bollinger junto à banda inferior.
- PUT: quer `trend_down` alto, RSI esticado (40–65), Estocástico em sobrecompra ou cruzando para baixo, Bollinger junto à banda superior.

## 4. Calibração empírica dos alvos (31 sinais reais)

| Métrica | Mediana | Faixa | Adotado em [config.py](../config.py) |
|---|---|---|---|
| Alvo 1 | +25,0% | +10% a +39% | `alvo1_pct = 0.25` |
| Alvo 2 | +254% | +97% a +449% | `alvo2_pct = 2.50` |
| Alvo final | +760% | +336% a +1128% | `alvo_final_pct = 7.00` |
| Stop | −43% | −28% a −46% | `stop_pct = -0.43` |
| Faixa de compra | ±3,5% | — | `buy_band_pct = 0.035` |

## 5. Como ativar

```python
# config.py
CONFIG["scoring_mode"] = "ponderado"
CONFIG["min_score_ponderado"] = 60
```

E em [core_engine.py](../core_engine.py), o caminho de decisão consulta o modo
(implementação futura — hoje o módulo está disponível mas o switch ainda usa
o clássico; veja `scoring.score_ponderado()` para integrar).

## 6. Diferenças de comportamento esperadas

- **Menos sinais, mais seletivos:** o limiar 60 + filtro |Δ| corta sinais
  fracos que passam no clássico.
- **Mais simetria:** PUTs e CALLs têm o mesmo "esforço" para passar.
- **Mais Greeks-aware:** o filtro de delta evita opções deep-OTM sem
  liquidez prática.
