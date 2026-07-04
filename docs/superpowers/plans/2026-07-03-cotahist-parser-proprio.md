# Parser Próprio COTAHIST B3 (Prêmios Reais de Opções) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o stub `carregar_cotahist_diario` por um parser fixed-width próprio do COTAHIST oficial da B3 (prêmios EOD reais de opções, TPMERC 070/080), e corrigir o parser/URL quebrados do `liquidity_service` descobertos durante a verificação.

**Architecture:** Parser puro (`parsear_cotahist_txt`) separado do download (`carregar_cotahist_diario`), no `cotahist_service.py` existente. O download reusa `_baixar_arquivo_b3` do `liquidity_service`. Offsets verificados contra arquivo real (`COTAHIST_D02072026.ZIP`, baixado e inspecionado em 03/07/2026 — 5.643 calls + 5.934 puts parseados com valores sanos).

**Tech Stack:** Python, pandas, requests (já presente), pytest. **Zero dependências novas.**

---

## Contexto crítico — verificação de 03/07/2026 (leia antes de executar)

O leiaute oficial do COTAHIST foi validado contra um arquivo real baixado da B3. Registros tipo "01" têm 245 chars. Offsets Python (0-indexed) **confirmados em arquivo real**:

| Campo | Slice | Exemplo real (call PETRF18) | Significado |
|---|---|---|---|
| TIPREG | `[0:2]` | `"01"` | tipo de registro (só "01" interessa) |
| DATA_PREGAO | `[2:10]` | `"20260702"` | YYYYMMDD |
| CODBDI | `[10:12]` | `"78"` | código BDI |
| CODNEG | `[12:24]` | `"PETRF18     "` | código de negociação (série) |
| TPMERC | `[24:27]` | `"070"` | 070=call, 080=put, 010=ação vista |
| PREULT | `[108:121]` | `"0000000000807"` → 8.07 | último preço (prêmio EOD) |
| PREOFC | `[121:134]` | melhor oferta de **compra** (bid) | pode ser zero no fechamento |
| PREOFV | `[134:147]` | melhor oferta de **venda** (ask) | pode ser zero no fechamento |
| TOTNEG | `[147:152]` | `"00011"` | nº de negócios |
| PREEXE | `[188:201]` | `"0000000004242"` → 42.42 | strike |
| DATVEN | `[202:210]` | `"20280616"` | vencimento YYYYMMDD |

Preços são **inteiros com 2 decimais implícitos** (`int(campo)/100`) — NÃO há vírgula decimal. Encoding latin-1 (ISO-8859-1).

**Bugs reais descobertos no `liquidity_service.py` (Task 3 corrige):**
1. **URL 404:** o código monta `COTAHIST_{DDMMYYYY}.ZIP` — essa URL retorna **404** (verificado). O arquivo diário real é `COTAHIST_D{DDMMYYYY}.ZIP` (com prefixo `D` — retornou 200 com 503 KB).
2. **Offsets errados:** `_parse_cotahist_zip` lê TPMERC em `[2:5]` — que é o meio da DATA (`"202"` para anos 202x), **nunca** igual a `"070"/"080"`. Nenhuma linha real jamais casa. O fixture do teste é sintético, construído para casar com o código errado, não extraído de arquivo real.
3. **Decimal errado:** o código faz `replace(",", ".")` — arquivos reais não têm vírgula; o valor fica 100× maior.

**Efeito em produção hoje:** o download falha (404) e, se não falhasse, o parse retornaria vazio → `bid/ask/spread_pct` são sempre NULL em `option_liquidity`, silenciosamente. A docstring atual do `cotahist_service.py` repete os offsets errados como "verificados" — a Task 2 a reescreve.

**Fora de escopo (backlog):** integração do loader no fluxo de backtest (hit-rate PUCK, Fase 4); suporte ao arquivo anual `COTAHIST_A{YYYY}.ZIP` (o diário resolve a coleta incremental; o anual entra quando o backtest histórico precisar).

---

## File Structure

- **Modify:** `backend/services/cotahist_service.py` — adiciona `parsear_cotahist_txt` (parser puro) e preenche `carregar_cotahist_diario` (download+unzip+parse); reescreve docstring do módulo.
- **Modify:** `tests/test_cotahist_service.py` — testes do parser com linhas reais verbatim.
- **Modify:** `backend/services/liquidity_service.py` — corrige URL (prefixo `D`) e offsets/decimais de `_parse_cotahist_zip`.
- **Modify:** `tests/test_liquidity_service.py` — builder de linha passa a gerar o leiaute real de 245 chars.
- **Modify:** `docs/BACKLOG.md` — marca o item do parser como concluído; registra a correção do liquidity.

---

## Task 1: Parser fixed-width puro (`parsear_cotahist_txt`)

**Files:**
- Modify: `backend/services/cotahist_service.py`
- Test: `tests/test_cotahist_service.py`

- [ ] **Step 1: Escrever os testes que falham**

Adicionar ao final de `tests/test_cotahist_service.py`. As três linhas são **verbatim de arquivo real** da B3 (pregão 2026-07-02) — não editar nem "consertar" espaços:

```python
# ── Task: parser fixed-width próprio (linhas reais do COTAHIST_D02072026) ──
from backend.services.cotahist_service import parsear_cotahist_txt

_LINHA_ACAO = "012026070202PETR4       010PETROBRAS   PN      N2   R$  000000000378900000000038460000000003765000000000379300000000037960000000003793000000000379627351000000000021888800000000083028224600000000000000009999123100000010000000000000BRPETRACNPR6228"
_LINHA_CALL = "012026070278PETRF18     070PETRE       PN      N2000R$  000000000075000000000008120000000000750000000000080700000000008070000000000000000000000000000011000000000000013800000000000011136600000000000424202028061600000010000000000000BRPETRACNPR6226"
_LINHA_PUT = "012026070282PETRS627    080PETRE       PN      N2000R$  000000000235500000000023550000000002350000000000235300000000023550000000000000000000000000000006000000000000000600000000000001412300000000000616102026071700000010000000000000BRPETRACNPR6225"


def _txt_bytes(*linhas):
    return ("\n".join(linhas) + "\n").encode("latin-1")


def test_parsea_call_e_put_ignorando_acao():
    df = parsear_cotahist_txt(_txt_bytes(_LINHA_ACAO, _LINHA_CALL, _LINHA_PUT))
    assert len(df) == 2  # ação (TPMERC 010) fora
    assert set(df["tipo_mercado"]) == {70, 80}
    assert set(df["cod_negociacao"]) == {"PETRF18", "PETRS627"}


def test_converte_precos_e_datas():
    df = parsear_cotahist_txt(_txt_bytes(_LINHA_CALL))
    row = df.iloc[0]
    assert row["preco_ultimo"] == 8.07          # PREULT [108:121] / 100
    assert row["preco_exercicio"] == 42.42      # PREEXE [188:201] / 100
    assert row["data_referencia"] == pd.Timestamp("2026-07-02")
    assert row["data_vencimento"] == pd.Timestamp("2028-06-16")
    assert row["total_negocios"] == 11          # TOTNEG [147:152]


def test_conteudo_invalido_retorna_vazio_com_colunas():
    df = parsear_cotahist_txt(b"lixo\ncurto\n")
    assert df.empty
    assert list(df.columns) == [
        "data_referencia", "cod_negociacao", "tipo_mercado",
        "preco_ultimo", "preco_exercicio", "data_vencimento", "total_negocios",
    ]


def test_parser_compativel_com_filtro_existente():
    df = parsear_cotahist_txt(_txt_bytes(_LINHA_CALL, _LINHA_PUT))
    out = filtrar_opcoes_do_ativo(df, ativo_base="PETR")
    assert len(out) == 2
```

`import pandas as pd` e `filtrar_opcoes_do_ativo` já existem no topo do arquivo de teste — não duplicar.

- [ ] **Step 2: Rodar e verificar que falha**

Run: `pytest tests/test_cotahist_service.py -v`
Expected: FAIL com `ImportError: cannot import name 'parsear_cotahist_txt'` (os 2 testes antigos continuam passando)

- [ ] **Step 3: Implementar o parser**

Em `backend/services/cotahist_service.py`, adicionar após `_TIPOS_OPCAO`:

```python
# Offsets 0-indexed do registro "01" (245 chars) — VERIFICADOS contra arquivo
# real COTAHIST_D02072026.ZIP em 2026-07-03 (5.643 calls + 5.934 puts parseados).
# Preços são inteiros com 2 decimais implícitos (int/100); encoding latin-1.
_SLICE_DATA = slice(2, 10)      # DATA_PREGAO YYYYMMDD
_SLICE_CODNEG = slice(12, 24)   # código da série (ex.: "PETRF18     ")
_SLICE_TPMERC = slice(24, 27)   # "070"=call, "080"=put
_SLICE_PREULT = slice(108, 121)  # último preço (prêmio EOD)
_SLICE_TOTNEG = slice(147, 152)  # nº de negócios
_SLICE_PREEXE = slice(188, 201)  # strike
_SLICE_DATVEN = slice(202, 210)  # vencimento YYYYMMDD

_COLUNAS = [
    "data_referencia", "cod_negociacao", "tipo_mercado",
    "preco_ultimo", "preco_exercicio", "data_vencimento", "total_negocios",
]


def parsear_cotahist_txt(conteudo_txt: bytes) -> pd.DataFrame:
    """Parseia o TXT do COTAHIST (bytes latin-1) para registros de opção.

    Retorna DataFrame com colunas `_COLUNAS`, apenas registros TIPREG=01 com
    TPMERC 070/080. Linhas malformadas são ignoradas (não derrubam o parse).
    """
    registros = []
    for linha in conteudo_txt.decode("latin-1", errors="replace").splitlines():
        if len(linha) < 245 or linha[0:2] != "01":
            continue
        tpmerc = linha[_SLICE_TPMERC]
        if tpmerc not in ("070", "080"):
            continue
        try:
            registros.append({
                "data_referencia": pd.Timestamp(linha[_SLICE_DATA]),
                "cod_negociacao": linha[_SLICE_CODNEG].strip(),
                "tipo_mercado": int(tpmerc),
                "preco_ultimo": int(linha[_SLICE_PREULT]) / 100.0,
                "preco_exercicio": int(linha[_SLICE_PREEXE]) / 100.0,
                "data_vencimento": pd.Timestamp(linha[_SLICE_DATVEN]),
                "total_negocios": int(linha[_SLICE_TOTNEG]),
            })
        except (ValueError, TypeError):
            continue  # linha corrompida não derruba o arquivo inteiro
    return pd.DataFrame(registros, columns=_COLUNAS)
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `pytest tests/test_cotahist_service.py -v`
Expected: PASS (6 passed — 2 antigos + 4 novos)

- [ ] **Step 5: Commit**

```bash
git add backend/services/cotahist_service.py tests/test_cotahist_service.py
git commit -m "feat(cotahist): parser fixed-width proprio de opcoes, offsets verificados em arquivo real"
```

---

## Task 2: Download do ZIP diário e preenchimento do stub

**Files:**
- Modify: `backend/services/cotahist_service.py` (função `carregar_cotahist_diario` + docstring do módulo)
- Test: `tests/test_cotahist_service.py`

- [ ] **Step 1: Escrever os testes que falham**

Adicionar ao final de `tests/test_cotahist_service.py`:

```python
# ── Task: download diário preenchendo o stub ──
import io
from unittest.mock import patch
from zipfile import ZipFile

from backend.services import cotahist_service


def _zip_bytes(*linhas):
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr("COTAHIST_D02072026.TXT", ("\n".join(linhas) + "\n").encode("latin-1"))
    return buf.getvalue()


def test_carregar_diario_baixa_e_parseia():
    with patch("backend.services.cotahist_service._baixar_arquivo_b3",
               return_value=_zip_bytes(_LINHA_CALL, _LINHA_PUT)) as mock_dl:
        df = cotahist_service.carregar_cotahist_diario("2026-07-02")
    assert len(df) == 2
    url_chamada = mock_dl.call_args[0][0]
    assert "COTAHIST_D02072026.ZIP" in url_chamada  # prefixo D obrigatório (sem D = 404)


def test_carregar_diario_download_falhou_retorna_vazio():
    with patch("backend.services.cotahist_service._baixar_arquivo_b3",
               return_value=None):
        df = cotahist_service.carregar_cotahist_diario("2026-07-02")
    assert df.empty
```

O `from unittest.mock import patch` pode já existir no arquivo — não duplicar.

- [ ] **Step 2: Rodar e verificar que falha**

Run: `pytest tests/test_cotahist_service.py -v`
Expected: FAIL — `AttributeError` (`_baixar_arquivo_b3` não existe no namespace de `cotahist_service`) e/ou `df` vazio no primeiro teste

- [ ] **Step 3: Implementar o download**

Em `backend/services/cotahist_service.py`:

1. Adicionar imports no topo (junto aos existentes):

```python
import io
from datetime import datetime
from zipfile import ZipFile

from backend.services.liquidity_service import _baixar_arquivo_b3
```

2. Adicionar a constante da URL (após os slices):

```python
# URL do arquivo DIÁRIO. Atenção ao prefixo "D": COTAHIST_{DDMMYYYY}.ZIP (sem D)
# retorna 404 (verificado em 2026-07-03); COTAHIST_D{DDMMYYYY}.ZIP retorna 200.
COTAHIST_DIARIO_URL = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_D{ddmmyyyy}.ZIP"
```

3. Substituir o corpo de `carregar_cotahist_diario` (removendo o stub):

```python
def carregar_cotahist_diario(data_ref: str) -> pd.DataFrame:
    """Baixa o COTAHIST diário da B3 e retorna as opções parseadas.

    data_ref: 'YYYY-MM-DD'. Falha de rede/arquivo inexistente (feriado) retorna
    DataFrame vazio com as colunas padrão — o chamador decide recuar a data.
    """
    ddmmyyyy = datetime.strptime(data_ref, "%Y-%m-%d").strftime("%d%m%Y")
    url = COTAHIST_DIARIO_URL.format(ddmmyyyy=ddmmyyyy)
    content = _baixar_arquivo_b3(url, f"COTAHIST diário {data_ref}")
    if not content:
        return pd.DataFrame(columns=_COLUNAS)
    try:
        with ZipFile(io.BytesIO(content)) as zf:
            nomes_txt = [n for n in zf.namelist() if n.upper().endswith(".TXT")]
            if not nomes_txt:
                logger.warning(f"COTAHIST {data_ref}: ZIP sem arquivo .TXT")
                return pd.DataFrame(columns=_COLUNAS)
            with zf.open(nomes_txt[0]) as f:
                return parsear_cotahist_txt(f.read())
    except Exception as e:
        logger.warning(f"COTAHIST {data_ref}: erro ao descompactar/parsear: {e}")
        return pd.DataFrame(columns=_COLUNAS)
```

4. **Reescrever a docstring do módulo** (linhas 1–51 atuais) — a versão atual afirma que os offsets `[2:5]`/`[36:40]`/`[82:95]` do `liquidity_service` foram "conferidos em produção", o que a verificação de 03/07 provou falso. Nova docstring:

```python
"""Carrega e filtra prêmios reais de opções do arquivo COTAHIST da B3.

Parser fixed-width próprio (sem dependência externa): não existe pacote PyPI
viável — o "rb3" do PyPI é uma lib de Redis não relacionada; o rb3 real
(wilsonfreitas) é R/CRAN. Offsets verificados contra arquivo real
COTAHIST_D02072026.ZIP em 2026-07-03 (leiaute oficial "Série Histórica",
registro tipo 01, 245 chars, latin-1, preços com 2 decimais implícitos).

Separação: `parsear_cotahist_txt` é puro (bytes → DataFrame, testável sem
rede); `carregar_cotahist_diario` baixa o ZIP diário (COTAHIST_D{DDMMYYYY}.ZIP
— o prefixo "D" é obrigatório; sem ele a B3 retorna 404) e delega ao parser.
`filtrar_opcoes_do_ativo` recorta as séries de um ativo para uso no backtest.
"""
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `pytest tests/test_cotahist_service.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Smoke test real opcional (rede)**

Se houver rede disponível, validar ponta a ponta uma única vez:

Run: `python -c "from backend.services.cotahist_service import carregar_cotahist_diario; df = carregar_cotahist_diario('2026-07-02'); print(len(df), 'opcoes'); print(df.head(3))"`
Expected: ~11.500 opções com preços/strikes/vencimentos sanos. (Se sem rede: pular, os testes com mock cobrem a lógica.)

- [ ] **Step 6: Commit**

```bash
git add backend/services/cotahist_service.py tests/test_cotahist_service.py
git commit -m "feat(cotahist): download do ZIP diario preenche o stub carregar_cotahist_diario"
```

---

## Task 3: Corrigir URL e parser do liquidity_service (bug real em produção)

**Files:**
- Modify: `backend/services/liquidity_service.py:17` (URL) e `:115-193` (`_parse_cotahist_zip`)
- Modify: `tests/test_liquidity_service.py` (builder `_linha_cotahist`, ~linhas 48-60)

Contexto: hoje `bid/ask/spread_pct` ficam NULL em `option_liquidity` porque (a) a URL sem `D` dá 404 e (b) os offsets do parser nunca casam com linha real. A correção usa os mesmos offsets verificados da Task 1. Nota de semântica: PREOFC = melhor oferta de **compra** = bid; PREOFV = melhor oferta de **venda** = ask (o código antigo invertia os rótulos, além de ler os campos errados).

- [ ] **Step 1: Corrigir o builder de fixture nos testes**

Em `tests/test_liquidity_service.py`, substituir a função `_linha_cotahist` inteira (que hoje gera 108 chars com TPMERC em `[2:5]`) por um builder do leiaute real:

```python
def _linha_cotahist(tpmerc: str, ticker: str, ask: str, bid: str) -> str:
    """Monta linha de 245 chars no leiaute REAL do COTAHIST (registro 01).

    Offsets verificados em arquivo real (2026-07-03): TPMERC [24:27],
    CODNEG [12:24], PREOFC(bid) [121:134], PREOFV(ask) [134:147].
    Preços em centavos (2 decimais implícitos), right-aligned com zeros.
    """
    def _preco(valor: str) -> str:
        return str(int(round(float(valor) * 100))).rjust(13, "0")

    linha = "01"                          # [0:2]   TIPREG
    linha += "20260702"                   # [2:10]  DATA_PREGAO
    linha += "78"                         # [10:12] CODBDI
    linha += f"{ticker}G360".ljust(12)    # [12:24] CODNEG (série; base = 4 primeiros)
    linha += tpmerc                       # [24:27] TPMERC ("070"/"080"/"010")
    linha += " " * (121 - len(linha))     # padding até PREOFC
    linha += _preco(bid)                  # [121:134] PREOFC = melhor oferta de compra (bid)
    linha += _preco(ask)                  # [134:147] PREOFV = melhor oferta de venda (ask)
    linha += " " * (245 - len(linha))     # completa 245 chars
    assert len(linha) == 245
    return linha
```

Os testes existentes que usam o builder (`test_parse_cotahist_zip_sucesso`, `test_parse_cotahist_zip_ignora_acoes` etc.) continuam válidos sem mudança de asserts — só o formato da linha muda. Se algum assert usar `"010"` vs `"70"`: o TPMERC de ação no leiaute real é `"010"`, manter como está.

- [ ] **Step 2: Rodar e verificar que os testes de COTAHIST falham**

Run: `pytest tests/test_liquidity_service.py -v`
Expected: testes `test_parse_cotahist_*` FALHAM (parser antigo não casa com linhas reais — exatamente o bug de produção reproduzido); testes de PR continuam passando

- [ ] **Step 3: Corrigir a URL e o parser**

Em `backend/services/liquidity_service.py`:

1. Linha 17 — adicionar o prefixo `D`:

```python
COTAHIST_BASE_URL = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_D{date_cotahist}.ZIP"
```

2. Em `_parse_cotahist_zip`, substituir o miolo do loop de linhas (de `line_str = ...` até o fim do `except ValueError`):

```python
                        for line in f:
                            line_str = line.decode("latin-1").rstrip()
                            if len(line_str) < 245 or line_str[0:2] != "01":
                                continue
                            tpmerc = line_str[24:27]  # leiaute oficial (verificado 2026-07-03)
                            if tpmerc not in ("070", "080"):  # não é opção
                                continue
                            codneg = line_str[12:24].strip()
                            ticker_base = codneg[:4]
                            if ticker_base not in tickers_universo:
                                continue
                            try:
                                # PREOFC = melhor oferta de COMPRA (bid); PREOFV = de VENDA (ask).
                                # Inteiros com 2 decimais implícitos — sem vírgula.
                                bid = int(line_str[121:134]) / 100.0
                                ask = int(line_str[134:147]) / 100.0
                                if ask <= 0 or bid <= 0:
                                    continue  # sem oferta em pé no fechamento
                                spread_pct = ((ask - bid) / ((ask + bid) / 2)) * 100
```

O bloco de agregação (`if ticker_base not in bid_ask_por_ticker: ...`) permanece igual. Atualizar também a docstring de `_parse_cotahist_zip` (posições e a nota bid/ask corretas).

3. Atualizar o comentário da linha 15 (`COTAHIST_DDDMMAAAA.zip` já indicava o `D`; conferir que o texto final diga `COTAHIST_D{DDMMYYYY}.ZIP`).

- [ ] **Step 4: Rodar e verificar que passa**

Run: `pytest tests/test_liquidity_service.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add backend/services/liquidity_service.py tests/test_liquidity_service.py
git commit -m "fix(liquidity): URL do COTAHIST diario (prefixo D) e offsets reais do parser bid/ask"
```

**⚠️ Nota de deploy:** com a correção, `bid/ask/spread_pct` passarão de NULL para valores reais em `option_liquidity` a partir da próxima coleta. Se houver veto de liquidez por spread lendo essas colunas (matriz v2), conferir se a flag correspondente está em shadow antes do deploy — dado que antes era NULL, o comportamento do veto pode mudar de "nunca ativa" para "ativa de verdade".

---

## Task 4: Regressão completa e documentação

**Files:**
- Modify: `docs/BACKLOG.md`

- [ ] **Step 1: Rodar a suíte completa**

Run: `pytest -q`
Expected: PASS (≥739 passed + os novos; sem regressões)

- [ ] **Step 2: Atualizar o BACKLOG**

Em `docs/BACKLOG.md`, seção "Precificação — próximos passos":

1. Marcar como concluído o item do parser:

```markdown
- [x] Implementar parser fixed-width real para `cotahist_service.carregar_cotahist_diario`
  (feito em 2026-07-03: parser próprio com offsets verificados em arquivo real;
  sem dependência nova. Correção junto: URL/offsets do `liquidity_service` estavam
  quebrados — bid/ask eram sempre NULL em produção.)
```

2. O item "Integrar COTAHIST no fluxo de backtest para medir hit-rate PUCK (Fase 4)" permanece aberto (é o próximo passo natural, fora deste plano).

- [ ] **Step 3: Commit**

```bash
git add docs/BACKLOG.md
git commit -m "docs(backlog): parser COTAHIST proprio concluido; registrar fix do liquidity"
```

---

## Self-Review

- **Cobertura:** parser puro (Task 1), download+stub preenchido (Task 2), correção do bug real de produção descoberto na verificação (Task 3), regressão+docs (Task 4). Integração com backtest explicitamente fora de escopo (backlog).
- **Consistência de tipos:** `parsear_cotahist_txt(bytes) -> pd.DataFrame` com colunas `_COLUNAS`; `carregar_cotahist_diario(str) -> pd.DataFrame` mantém a assinatura do stub; colunas `cod_negociacao`/`tipo_mercado` (int) casam com o que `filtrar_opcoes_do_ativo` já espera (teste de compatibilidade incluso na Task 1).
- **Placeholders:** nenhum — todos os steps têm código completo; fixtures são linhas reais verbatim.
- **Riscos:** (a) leiaute da B3 é estável há décadas, risco baixo; offsets ficam em constantes nomeadas num único lugar; (b) `PREOFC/PREOFV` zerados no fechamento são comuns (séries sem oferta em pé) — comportamento de skip preservado; (c) mudança de NULL→real em `option_liquidity` pode ativar vetos de liquidez — flag de deploy anotada na Task 3.
