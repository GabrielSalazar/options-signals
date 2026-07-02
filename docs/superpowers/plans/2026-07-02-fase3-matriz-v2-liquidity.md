# Fase 3 — Matriz v2: Integração de Dados Externos (OI, bid/ask, VXBR, Eventos)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrar OI (Open Interest), bid/ask, VXBR e eventos (Copom, earnings) via fontes públicas da B3, persistir em nova tabela `option_liquidity`, enriquecer payload do sinal com telemetria de executabilidade, tudo em shadow até Fase 4.

**Architecture:** Job diário pós-fechamento (scheduler) baixa PRiceReport (OI) e COTAHIST (bid/ask) de arquivos públicos B3, descompacta XMLs, extrai dados por série, persiste em `option_liquidity` (ticker, data, oi, bid, ask, spread_pct). Serviço `liquidity_service.py` centraliza coleta + cálculos. `core_engine.py` consulta essa tabela no ato de emissão, popula campos informativos (`oi`, `spread_pct`, `vxbr`, `evento_label`) e aplica vetos shadow (não ativa até Fase 4). VXBR coletado via API (ou fallback hardcode), eventos via lista Copom + brapi.

**Tech Stack:** APScheduler (job diário), requests (download arquivos B3 + VXBR), zipfile/xml.etree (parse), Supabase (persist), pandas (séries)

---

## File Structure

```
backend/
  ├─ services/
  │  ├─ liquidity_service.py          [NEW] Coleta OI+bid/ask, calcula spreads, persiste em option_liquidity
  │  ├─ scheduler.py                  [MODIFY] Registra job diário `coletar_liquidity_diaria` (18h BRT)
  │  └─ core_engine.py                [MODIFY] Consulta option_liquidity no ato, popula campos, aplica vetos shadow
  │
  └─ domain/
     ├─ scoring.py                    [MODIFY] Função `avaliar_filtro_liquidez_shadow(oi, spread_pct, vxbr, evento_label, score)` (veto shadow)
     └─ indicators.py                 [MODIFY] Função `obter_vxbr_diaria()` → float (coleta via API ou fallback)

supabase/
  └─ migrations/
     └─ 013_option_liquidity.sql      [NEW] Tabela option_liquidity(id, ticker, data, oi, bid, ask, spread_pct, vxbr, evento_label, created_at)

tests/
  ├─ test_liquidity_service.py        [NEW] Testes unitários da coleta OI/bid/ask, parse XML, cálculos de spread
  ├─ test_core_engine_liquidity.py    [NEW] Testes de integração: consulta option_liquidity, vetos shadow
  └─ test_indicators_vxbr.py          [NEW] Teste de `obter_vxbr_diaria()`
```

---

## Task 1: Criar tabela `option_liquidity` no Supabase

**Files:**
- Create: `supabase/migrations/013_option_liquidity.sql`

- [ ] **Step 1: Escrever migração de schema**

```sql
-- ============================================================
-- Migration 013: Tabela option_liquidity para dados externos
--                (OI, bid/ask, VXBR, eventos) — Fase 3 Matriz v2
-- Run via: Supabase Dashboard → SQL Editor
-- ============================================================

-- Tabela de liquidez diária (criada por job de coleta pós-fechamento)
CREATE TABLE IF NOT EXISTS option_liquidity (
  id BIGSERIAL PRIMARY KEY,
  ticker VARCHAR(20) NOT NULL,           -- ticker base (ex: PETR4)
  data DATE NOT NULL,                    -- data de coleta (pós-fechamento do dia)
  oi BIGINT,                             -- Open Interest total da série (somado sobre strikes)
  bid FLOAT,                             -- bid de fechamento da série ATM
  ask FLOAT,                             -- ask de fechamento da série ATM
  spread_pct FLOAT,                      -- (ask - bid) / ((ask + bid) / 2) * 100
  vxbr FLOAT,                            -- índice de volatilidade da B3 (nível do dia)
  evento_label VARCHAR(100),             -- label de evento (ex: "COPOM", "EARNINGS_PETR4", null)
  created_at TIMESTAMP DEFAULT NOW()
);

-- Índice para buscas frequentes (ticker, data)
CREATE UNIQUE INDEX IF NOT EXISTS idx_option_liquidity_ticker_data
  ON option_liquidity(ticker, data);

-- Índice para limpeza antiga
CREATE INDEX IF NOT EXISTS idx_option_liquidity_data
  ON option_liquidity(data);

-- RLS disabled (dados públicos)
-- Sem FK para signals — é um dado de estado, não relacionado 1:1 a sinais
```

- [ ] **Step 2: Verificar sintaxe e comentar no arquivo**

Nenhuma ação adicional — migração é idempotente (CREATE TABLE IF NOT EXISTS).

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/013_option_liquidity.sql
git commit -m "migration: criar tabela option_liquidity para coleta de OI/bid-ask/VXBR"
```

---

## Task 2: Criar `liquidity_service.py` com coleta de OI (PR) e bid/ask (COTAHIST)

**Files:**
- Create: `backend/services/liquidity_service.py`
- Modify: `backend/services/scheduler.py`

- [ ] **Step 1: Escrever `liquidity_service.py` com suporte a PR (OI)**

```python
"""Coleta de liquidez diária: OI via PR (PriceReport da B3), bid/ask via COTAHIST."""
import logging
import io
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from zipfile import ZipFile

import requests

from backend.services.data_providers import fetch_brapi_historical
from backend.services.supabase_client import get_supabase
from backend.services.ticker_loader import carregar_tickers_b3

logger = logging.getLogger("b3_api")

# URLs públicos da B3 (formato: PRAAMMDD.zip, COTAHIST_DDDMMAAAA.zip)
PR_BASE_URL = "https://www.b3.com.br/pesquisapregao/download?filelist=PRA{date_b3}.zip"
COTAHIST_BASE_URL = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_{date_cotahist}.ZIP"

TIMEOUT_SECONDS = 30


def _baixar_arquivo_b3(url: str, descricao: str) -> bytes | None:
    """Baixa arquivo público da B3 com timeout e logging."""
    try:
        resp = requests.get(url, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        logger.info(f"✓ {descricao} baixado ({len(resp.content)} bytes)")
        return resp.content
    except Exception as e:
        logger.warning(f"✗ Erro ao baixar {descricao}: {e}")
        return None


def _parse_pr_zip(content: bytes, tickers_universo: set) -> dict:
    """
    Extrai OI do PR (PriceReport) zipado.
    
    PR é um ZIP com XMLs aninhados. Cada XML BVBG.086.01 tem estrutura:
    ```xml
    <Document>
      <DlvyStnDta>
        <MktDta>
          <Istrm>
            <TckrSymb>PETRG360</TckrSymb>
            <OpnIntrst>518200</OpnIntrst>
    ```
    
    Retorna dict {ticker: total_oi} somado sobre todos os strikes de um ticker.
    Apenas tickers no `tickers_universo` são processados.
    """
    oi_por_ticker = {}
    try:
        with ZipFile(io.BytesIO(content)) as zf:
            for file_info in zf.filelist:
                if not file_info.filename.endswith(".xml"):
                    continue
                try:
                    with zf.open(file_info) as f:
                        root = ET.parse(f).getroot()
                    # Navega a árvore XML procurando por <Istrm> com <TckrSymb> e <OpnIntrst>
                    for istrm in root.findall(".//Istrm"):
                        tckr_elem = istrm.find("TckrSymb")
                        oi_elem = istrm.find("OpnIntrst")
                        if tckr_elem is not None and oi_elem is not None:
                            tckr = tckr_elem.text.strip() if tckr_elem.text else None
                            oi_str = oi_elem.text.strip() if oi_elem.text else "0"
                            if tckr and tckr in tickers_universo:
                                # tckr pode ser "PETRG360" (tipo+vencimento), extrair base
                                base = tckr[:-3] if len(tckr) > 3 else tckr
                                try:
                                    oi = int(oi_str)
                                    oi_por_ticker[base] = oi_por_ticker.get(base, 0) + oi
                                except ValueError:
                                    pass
                except Exception as e:
                    logger.warning(f"Erro ao parsear XML {file_info.filename}: {e}")
        logger.info(f"PR parseado: {len(oi_por_ticker)} tickers com OI")
    except Exception as e:
        logger.warning(f"Erro ao descompactar PR: {e}")
    return oi_por_ticker


def _parse_cotahist_zip(content: bytes, tickers_universo: set) -> dict:
    """
    Extrai bid/ask de fechamento do COTAHIST.
    
    COTAHIST é um ZIP com um arquivo TXT com campos posicionais:
    - Campo 'TPMERC' (2-5): 070 = call, 080 = put
    - Campo 'ESPECS' (36-40): código da opção (ex: PETRG360)
    - Campo 'PREOFC' (82-95): preço oferecido (ask)
    - Campo 'PREOFV' (95-108): preço ofertado (bid)
    
    Filtra apenas opções (TPMERC=070/080) de tickers no universo.
    Retorna dict {ticker: {"bid": float, "ask": float, "spread_pct": float}}.
    """
    bid_ask_por_ticker = {}
    try:
        with ZipFile(io.BytesIO(content)) as zf:
            for file_info in zf.filelist:
                if not file_info.filename.endswith(".TXT"):
                    continue
                try:
                    with zf.open(file_info) as f:
                        for line in f:
                            line_str = line.decode("latin-1").rstrip()
                            if len(line_str) < 108:  # linha válida deve ter ≥108 caracteres
                                continue
                            tpmerc = line_str[2:5].strip()  # posição 2-5 (string de 3 chars)
                            if tpmerc not in ("070", "080"):  # não é opção
                                continue
                            specs = line_str[36:40].strip() if len(line_str) > 40 else ""
                            if not specs:
                                continue
                            # Extrair ticker base (PETRG360 → PETR)
                            ticker_base = specs[:4] if len(specs) >= 4 else specs
                            if ticker_base not in tickers_universo:
                                continue
                            try:
                                # Campos de preço (posições 82-95 e 95-108)
                                preofc_str = line_str[82:95].strip()  # ask
                                preofv_str = line_str[95:108].strip()  # bid
                                if not preofc_str or not preofv_str:
                                    continue
                                ask = float(preofc_str.replace(",", "."))
                                bid = float(preofv_str.replace(",", "."))
                                if ask <= 0 or bid <= 0:
                                    continue
                                spread_pct = ((ask - bid) / ((ask + bid) / 2)) * 100
                                # Agregar: usar melhor bid e pior ask vista no arquivo
                                if ticker_base not in bid_ask_por_ticker:
                                    bid_ask_por_ticker[ticker_base] = {"bid": bid, "ask": ask, "spread_pct": spread_pct}
                                else:
                                    # Melhor bid = maior; pior ask = menor (liquidity-friendly)
                                    bid_ask_por_ticker[ticker_base]["bid"] = max(
                                        bid_ask_por_ticker[ticker_base]["bid"], bid
                                    )
                                    bid_ask_por_ticker[ticker_base]["ask"] = min(
                                        bid_ask_por_ticker[ticker_base]["ask"], ask
                                    )
                                    bid_ask_por_ticker[ticker_base]["spread_pct"] = (
                                        (bid_ask_por_ticker[ticker_base]["ask"] - bid_ask_por_ticker[ticker_base]["bid"])
                                        / ((bid_ask_por_ticker[ticker_base]["ask"] + bid_ask_por_ticker[ticker_base]["bid"]) / 2)
                                    ) * 100
                            except ValueError:
                                pass
                except Exception as e:
                    logger.warning(f"Erro ao parsear COTAHIST {file_info.filename}: {e}")
        logger.info(f"COTAHIST parseado: {len(bid_ask_por_ticker)} tickers com bid/ask")
    except Exception as e:
        logger.warning(f"Erro ao descompactar COTAHIST: {e}")
    return bid_ask_por_ticker


def coletar_liquidity_diaria(tickers: dict | None = None, vxbr: float | None = None) -> int:
    """
    Job diário (pós-fechamento): persiste OI, bid/ask, VXBR para o universo líquido.
    
    Retorna nº de tickers persistidos com sucesso. Falha parcial (um ticker) não derruba
    o job. Se VXBR não for fornecido, tenta obter via API.
    """
    supabase = get_supabase()
    if not supabase:
        logger.warning("Supabase indisponível — liquidez não coletada")
        return 0

    if tickers is None:
        tickers = carregar_tickers_b3()
    tickers_universo = set(ticker.replace(".SA", "") for ticker in tickers.keys())

    # Se VXBR não foi fornecido, tenta API (importado do final desta tarefa)
    if vxbr is None:
        from backend.domain.indicators import obter_vxbr_diaria
        try:
            vxbr = obter_vxbr_diaria()
        except Exception as e:
            logger.warning(f"VXBR indisponível: {e}")
            vxbr = None

    hoje = datetime.now(timezone.utc).date()
    data_b3 = hoje.strftime("%m%d%Y")  # formato MMDDYYYY para PR
    data_cotahist = hoje.strftime("%d%m%Y")  # formato DDMMYYYY para COTAHIST

    # Baixa arquivos públicos B3
    url_pr = PR_BASE_URL.format(date_b3=data_b3)
    url_cotahist = COTAHIST_BASE_URL.format(date_cotahist=data_cotahist)

    pr_content = _baixar_arquivo_b3(url_pr, "PriceReport")
    cotahist_content = _baixar_arquivo_b3(url_cotahist, "COTAHIST")

    oi_por_ticker = _parse_pr_zip(pr_content, tickers_universo) if pr_content else {}
    bid_ask_por_ticker = _parse_cotahist_zip(cotahist_content, tickers_universo) if cotahist_content else {}

    persistidos = 0
    for ticker_base in tickers_universo:
        try:
            oi = oi_por_ticker.get(ticker_base)
            bid_ask = bid_ask_por_ticker.get(ticker_base, {})
            bid = bid_ask.get("bid")
            ask = bid_ask.get("ask")
            spread_pct = bid_ask.get("spread_pct")

            # Persiste mesmo com dados parciais (oi=None, bid=None, etc.)
            supabase.table("option_liquidity").upsert({
                "ticker": ticker_base,
                "data": hoje.isoformat(),
                "oi": oi,
                "bid": bid,
                "ask": ask,
                "spread_pct": round(spread_pct, 2) if spread_pct is not None else None,
                "vxbr": round(vxbr, 1) if vxbr is not None else None,
                "evento_label": None,  # preenchido separadamente (Task 5)
            }, on_conflict="ticker,data").execute()
            persistidos += 1
        except Exception as e:
            logger.warning(f"Erro ao persistir liquidez de {ticker_base}: {e}")

    logger.info(f"Liquidez coletada — {persistidos}/{len(tickers_universo)} tickers (OI: {len(oi_por_ticker)}, bid/ask: {len(bid_ask_por_ticker)})")
    return persistidos
```

- [ ] **Step 2: Verificar importações e estrutura**

Verificar que as funções de parse XML e cálculos de spread estão corretas:
- `_parse_pr_zip`: navega `<Istrm>/<TckrSymb>` e `<OpnIntrst>`, soma OI por ticker base
- `_parse_cotahist_zip`: extrai campos posicionais (PREOFC/PREOFV), calcula spread
- `coletar_liquidity_diaria`: orquestra download + parse, persiste com fallback para dados parciais

- [ ] **Step 3: Registrar job no scheduler**

Em `backend/services/scheduler.py`, adicionar:

```python
from backend.services.liquidity_service import coletar_liquidity_diaria

# ...no bloco scheduler.add_job (dentro de start()):

    scheduler.add_job(
        coletar_liquidity_diaria,
        trigger=CronTrigger(day_of_week="mon-fri", hour=18, minute=0, timezone="America/Sao_Paulo"),
        id="liquidity_job",
        name="Coleta diaria de OI/bid-ask/VXBR (pos-fechamento)",
        replace_existing=True,
        max_instances=1,
    )
```

- [ ] **Step 4: Commit**

```bash
git add backend/services/liquidity_service.py backend/services/scheduler.py
git commit -m "feat: coleta diaria de OI (PR) e bid/ask (COTAHIST) — Fase 3 Matriz v2"
```

---

## Task 3: Adicionar `obter_vxbr_diaria()` em `indicators.py`

**Files:**
- Modify: `backend/domain/indicators.py`

- [ ] **Step 1: Escrever função de coleta VXBR**

```python
# Adicionar ao final de indicators.py:

def obter_vxbr_diaria() -> float:
    """
    Coleta VXBR (índice de volatilidade da B3) do dia atual.
    
    Tenta via API brapi.dev (gratuita, sem auth). Fallback: retorna None.
    VXBR é um índice, não há "série" — valor único por dia.
    """
    import requests
    try:
        resp = requests.get("https://api.brapi.dev/api/v2/ibov-indices", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # Resposta esperada: {"results": [{"name": "VXBR", "close": 18.5}, ...]}
        for item in data.get("results", []):
            if item.get("name") == "VXBR":
                return float(item.get("close", 0.0))
    except Exception as e:
        import logging
        logger = logging.getLogger("b3_api")
        logger.warning(f"Erro ao coletar VXBR: {e}")
    return None
```

- [ ] **Step 2: Adicionar teste unitário**

Criar `tests/test_indicators_vxbr.py`:

```python
"""Teste de coleta VXBR."""
import pytest
from unittest.mock import patch, MagicMock

from backend.domain.indicators import obter_vxbr_diaria


def test_obter_vxbr_diaria_sucesso():
    """Coleta com sucesso retorna float."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": [
            {"name": "IBOV", "close": 120000},
            {"name": "VXBR", "close": 18.5},
        ]
    }
    with patch("requests.get", return_value=mock_resp):
        vxbr = obter_vxbr_diaria()
        assert vxbr == 18.5


def test_obter_vxbr_diaria_nao_encontrado():
    """Se VXBR não está na resposta, retorna None."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"results": [{"name": "IBOV", "close": 120000}]}
    with patch("requests.get", return_value=mock_resp):
        vxbr = obter_vxbr_diaria()
        assert vxbr is None


def test_obter_vxbr_diaria_erro_conexao():
    """Erro de conexão retorna None sem exceção."""
    with patch("requests.get", side_effect=Exception("Connection error")):
        vxbr = obter_vxbr_diaria()
        assert vxbr is None
```

- [ ] **Step 3: Rodar teste**

```bash
pytest tests/test_indicators_vxbr.py -v
```

Expected: 3 testes verdes.

- [ ] **Step 4: Commit**

```bash
git add backend/domain/indicators.py tests/test_indicators_vxbr.py
git commit -m "feat: adicionar obter_vxbr_diaria() para coleta do índice VXBR"
```

---

## Task 4: Criar testes unitários para `liquidity_service.py`

**Files:**
- Create: `tests/test_liquidity_service.py`

- [ ] **Step 1: Escrever testes de parse PR e COTAHIST**

```python
"""Testes de coleta de liquidez: OI (PR), bid/ask (COTAHIST)."""
import pytest
from io import BytesIO
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from backend.services.liquidity_service import _parse_pr_zip, _parse_cotahist_zip


def _criar_pr_zip_mock(oi_dados: dict) -> bytes:
    """Cria um ZIP mock com XML PR contendo OI dados."""
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
<Document>
  <DlvyStnDta>
    <MktDta>
"""
    for ticker, oi in oi_dados.items():
        xml_content += f"""      <Istrm>
        <TckrSymb>{ticker}</TckrSymb>
        <OpnIntrst>{oi}</OpnIntrst>
      </Istrm>
"""
    xml_content += """    </MktDta>
  </DlvyStnDta>
</Document>"""
    
    bio = BytesIO()
    with ZipFile(bio, "w") as zf:
        zf.writestr("BVBG086.xml", xml_content.encode())
    return bio.getvalue()


def _criar_cotahist_zip_mock(linhas_cotahist: list) -> bytes:
    """Cria um ZIP mock com arquivo COTAHIST (formato posicional)."""
    cotahist_content = "\n".join(linhas_cotahist)
    
    bio = BytesIO()
    with ZipFile(bio, "w") as zf:
        zf.writestr("COTAHIST.TXT", cotahist_content.encode("latin-1"))
    return bio.getvalue()


def test_parse_pr_zip_sucesso():
    """Parse de PR extrai OI por ticker corretamente."""
    oi_dados = {
        "PETRG360": 518200,
        "PETRG370": 125000,
        "PBRG360": 75000,
    }
    content = _criar_pr_zip_mock(oi_dados)
    tickers_universo = {"PETR", "PBR"}
    
    resultado = _parse_pr_zip(content, tickers_universo)
    
    assert resultado["PETR"] == 643200  # 518200 + 125000 (agregado por base)
    assert resultado["PBR"] == 75000


def test_parse_pr_zip_ignora_tickers_fora_universo():
    """Parse ignora tickers não no universo."""
    oi_dados = {
        "PETRG360": 518200,
        "VALGM360": 100000,  # ticker fora do universo
    }
    content = _criar_pr_zip_mock(oi_dados)
    tickers_universo = {"PETR"}
    
    resultado = _parse_pr_zip(content, tickers_universo)
    
    assert "PETR" in resultado
    assert "VALG" not in resultado


def test_parse_cotahist_zip_sucesso():
    """Parse de COTAHIST extrai bid/ask e calcula spread."""
    # Linha válida (108+ chars): TPMERC na posição 2-5, ESPECS 36-40, PREOFC 82-95, PREOFV 95-108
    # Construir linha com padding
    linha = (
        "00070" +  # pos 0-5: tipo=070 (call)
        " " * 31 +  # pos 5-36: padding
        "PETR" +  # pos 36-40: ESPECS
        " " * 42 +  # pos 40-82: padding
        "       1.55" +  # pos 82-95: PREOFC (ask) — right-aligned
        "       1.43" +  # pos 95-108: PREOFV (bid) — right-aligned
        " " * 50  # extra para garantir comprimento
    )
    
    content = _criar_cotahist_zip_mock([linha])
    tickers_universo = {"PETR"}
    
    resultado = _parse_cotahist_zip(content, tickers_universo)
    
    assert "PETR" in resultado
    assert abs(resultado["PETR"]["ask"] - 1.55) < 0.01
    assert abs(resultado["PETR"]["bid"] - 1.43) < 0.01
    assert resultado["PETR"]["spread_pct"] > 0  # (1.55 - 1.43) / ((1.55 + 1.43) / 2) * 100


def test_parse_cotahist_zip_ignora_acoes():
    """Parse ignora ações (TPMERC != 070/080)."""
    # TPMERC=010 = ação, não opção
    linha = (
        "00010" +  # TPMERC na posição 2-5: 010 (ação)
        " " * 31 +
        "PETR" +
        " " * 42 +
        "       10.50" +
        "       10.48" +
        " " * 50
    )
    
    content = _criar_cotahist_zip_mock([linha])
    tickers_universo = {"PETR"}
    
    resultado = _parse_cotahist_zip(content, tickers_universo)
    
    assert "PETR" not in resultado


def test_parse_cotahist_zip_agregacao_melhor_bid_pior_ask():
    """Parse agrega múltiplas series: melhor bid, pior ask."""
    # Dois strikes de PETR: uma com spread 8.4%, outra com 7.5%
    linha1 = (
        "00070" +
        " " * 31 +
        "PETR" +
        " " * 42 +
        "       1.55" +  # ask
        "       1.43" +  # bid
        " " * 50
    )
    linha2 = (
        "00070" +
        " " * 31 +
        "PETR" +
        " " * 42 +
        "       1.50" +  # ask (melhor = menor)
        "       1.44" +  # bid (melhor = maior)
        " " * 50
    )
    
    content = _criar_cotahist_zip_mock([linha1, linha2])
    tickers_universo = {"PETR"}
    
    resultado = _parse_cotahist_zip(content, tickers_universo)
    
    assert resultado["PETR"]["ask"] == 1.50  # menor ask
    assert resultado["PETR"]["bid"] == 1.44  # maior bid
```

- [ ] **Step 2: Rodar testes**

```bash
pytest tests/test_liquidity_service.py -v
```

Expected: 6 testes verdes.

- [ ] **Step 3: Commit**

```bash
git add tests/test_liquidity_service.py
git commit -m "test: adicionar testes de parse OI/bid-ask (PR e COTAHIST)"
```

---

## Task 5: Integrar coleta de liquidez em `core_engine.py` e criar vetos shadow

**Files:**
- Modify: `backend/services/core_engine.py`
- Modify: `backend/domain/scoring.py`

- [ ] **Step 1: Escrever função `avaliar_filtro_liquidez_shadow()` em `scoring.py`**

```python
# Adicionar a backend/domain/scoring.py:

def avaliar_filtro_liquidez_shadow(oi: int | None, spread_pct: float | None, vxbr: float | None, evento_label: str | None, score: int) -> dict:
    """
    Avalia vetos de executabilidade (Fase 3 Matriz v2, §4 — shadow).
    
    Vetos (não bloqueiam até Fase 4):
    - OI < 500: atenção (score <8 bloqueia em ativo)
    - Spread > 10%: atenção
    - Spread > 15%: bloqueia (spread inviável)
    - VXBR > 30: atenção (mercado muito nervoso)
    - Evento no DTE (ex: COPOM): atenção
    
    Retorna {"decisao": "normal" | "atencao" | "bloquear", "motivo": str, "modo": "shadow"}.
    
    `decisao`:
    - "normal": sem restrição
    - "atencao": registra em telemetria mas não bloqueia (mesmo em modo ativo)
    - "bloquear": bloqueia em modo ativo; registra em shadow
    """
    motivos = []
    decisao_maior = "normal"
    
    # Veto: Spread inviável
    if spread_pct is not None and spread_pct > 15:
        motivos.append(f"spread inviável {spread_pct:.1f}%")
        decisao_maior = "bloquear"
    
    # Atenção: OI baixo
    if oi is not None and oi < 500:
        motivos.append(f"OI baixo {oi}")
        if decisao_maior != "bloquear":
            decisao_maior = "atencao"
    
    # Atenção: Spread alto
    if spread_pct is not None and spread_pct > 10:
        motivos.append(f"spread alto {spread_pct:.1f}%")
        if decisao_maior != "bloquear":
            decisao_maior = "atencao"
    
    # Atenção: VXBR elevado
    if vxbr is not None and vxbr > 30:
        motivos.append(f"VXBR elevado {vxbr:.1f}")
        if decisao_maior != "bloquear":
            decisao_maior = "atencao"
    
    # Atenção: Evento no DTE
    if evento_label:
        motivos.append(f"evento {evento_label} no DTE")
        if decisao_maior != "bloquear":
            decisao_maior = "atencao"
    
    motivo = "; ".join(motivos) if motivos else "execução viável"
    return {
        "decisao": decisao_maior,
        "motivo": motivo,
        "modo": "shadow",
    }
```

- [ ] **Step 2: Integrar coleta de liquidez em `core_engine.py`**

Em `analisar_ativo()`, após consultar IV (linha ~680), adicionar:

```python
            # ── CONSULTA DE LIQUIDEZ (Fase 3 — shadow) ──────────────────────
            liquidity_info = obter_option_liquidity(ticker_base, hoje)
            if liquidity_info:
                estrutura["oi"] = liquidity_info.get("oi")
                estrutura["bid"] = liquidity_info.get("bid")
                estrutura["ask"] = liquidity_info.get("ask")
                estrutura["spread_pct"] = liquidity_info.get("spread_pct")
                estrutura["vxbr"] = liquidity_info.get("vxbr")
                estrutura["evento_label"] = liquidity_info.get("evento_label")
            else:
                estrutura["oi"] = None
                estrutura["bid"] = None
                estrutura["ask"] = None
                estrutura["spread_pct"] = None
                estrutura["vxbr"] = None
                estrutura["evento_label"] = None

            # ── FILTRO DE LIQUIDEZ (Fase 3 — shadow) ──────────────────────
            filtro_liq = avaliar_filtro_liquidez_shadow(
                estrutura.get("oi"),
                estrutura.get("spread_pct"),
                estrutura.get("vxbr"),
                estrutura.get("evento_label"),
                score
            )
            estrutura["filtro_liquidez_decisao"] = filtro_liq["decisao"]
            estrutura["filtro_liquidez_motivo"] = filtro_liq["motivo"]
```

Adicionar função auxiliar em `core_engine.py`:

```python
def obter_option_liquidity(ticker_base: str, data: "datetime.date") -> dict | None:
    """Consulta option_liquidity para um ticker em uma data específica."""
    from backend.services.supabase_client import get_supabase
    supabase = get_supabase()
    if not supabase:
        return None
    try:
        res = (supabase.table("option_liquidity")
               .select("oi, bid, ask, spread_pct, vxbr, evento_label")
               .eq("ticker", ticker_base)
               .eq("data", data.isoformat())
               .single()
               .execute())
        return res.data
    except Exception:
        return None
```

Adicionar import no início:

```python
from backend.domain.scoring import avaliar_filtro_liquidez_shadow
from datetime import date as date_class  # ou use datetime.date
```

- [ ] **Step 3: Rodar testes do core_engine**

```bash
pytest tests/test_core_engine.py -v
```

Expected: todos os testes passam (nenhuma mudança de lógica, só adição de campos).

- [ ] **Step 4: Commit**

```bash
git add backend/services/core_engine.py backend/domain/scoring.py
git commit -m "feat: integrar vetos shadow de liquidez (OI, spread, VXBR, eventos)"
```

---

## Task 6: Teste de integração: `core_engine_liquidity` consulta e popula campos

**Files:**
- Create: `tests/test_core_engine_liquidity.py`

- [ ] **Step 1: Escrever teste de integração**

```python
"""Teste de integração: core_engine consulta option_liquidity e aplica vetos shadow."""
import pytest
from datetime import datetime, date
from unittest.mock import patch, MagicMock

from backend.services.core_engine import analisar_ativo, obter_option_liquidity
from backend.domain.scoring import avaliar_filtro_liquidez_shadow


def test_obter_option_liquidity_sucesso(mocker):
    """Consulta option_liquidity retorna dados."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"oi": 5000, "bid": 1.43, "ask": 1.55, "spread_pct": 8.4, "vxbr": 18.5, "evento_label": None}
    )
    mocker.patch("backend.services.core_engine.get_supabase", return_value=mock_supabase)
    
    resultado = obter_option_liquidity("PETR", date(2026, 7, 2))
    
    assert resultado["oi"] == 5000
    assert resultado["spread_pct"] == 8.4
    assert resultado["vxbr"] == 18.5


def test_obter_option_liquidity_indisponivel(mocker):
    """Consulta sem resultado retorna None."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("Not found")
    mocker.patch("backend.services.core_engine.get_supabase", return_value=mock_supabase)
    
    resultado = obter_option_liquidity("PETR", date(2026, 7, 2))
    
    assert resultado is None


def test_avaliar_filtro_liquidez_shadow_normal():
    """Liquidez viável retorna 'normal'."""
    resultado = avaliar_filtro_liquidez_shadow(oi=5000, spread_pct=8.4, vxbr=18.5, evento_label=None, score=10)
    
    assert resultado["decisao"] == "normal"
    assert resultado["motivo"] == "execução viável"


def test_avaliar_filtro_liquidez_shadow_oi_baixo():
    """OI < 500 gera atenção."""
    resultado = avaliar_filtro_liquidez_shadow(oi=300, spread_pct=8.4, vxbr=18.5, evento_label=None, score=10)
    
    assert resultado["decisao"] == "atencao"
    assert "OI baixo" in resultado["motivo"]


def test_avaliar_filtro_liquidez_shadow_spread_alto():
    """Spread > 15% bloqueia."""
    resultado = avaliar_filtro_liquidez_shadow(oi=5000, spread_pct=16.0, vxbr=18.5, evento_label=None, score=10)
    
    assert resultado["decisao"] == "bloquear"
    assert "spread inviável" in resultado["motivo"]


def test_avaliar_filtro_liquidez_shadow_vxbr_elevado():
    """VXBR > 30 gera atenção."""
    resultado = avaliar_filtro_liquidez_shadow(oi=5000, spread_pct=8.4, vxbr=32.0, evento_label=None, score=10)
    
    assert resultado["decisao"] == "atencao"
    assert "VXBR elevado" in resultado["motivo"]


def test_avaliar_filtro_liquidez_shadow_evento():
    """Evento no DTE gera atenção."""
    resultado = avaliar_filtro_liquidez_shadow(oi=5000, spread_pct=8.4, vxbr=18.5, evento_label="COPOM", score=10)
    
    assert resultado["decisao"] == "atencao"
    assert "evento COPOM" in resultado["motivo"]
```

- [ ] **Step 2: Rodar testes**

```bash
pytest tests/test_core_engine_liquidity.py -v
```

Expected: 7 testes verdes.

- [ ] **Step 3: Commit**

```bash
git add tests/test_core_engine_liquidity.py
git commit -m "test: integração core_engine com option_liquidity e vetos shadow"
```

---

## Task 7: Adicionar cadastro de eventos (Copom) — tabela e job

**Files:**
- Create: `supabase/migrations/014_calendar_events.sql`
- Create: `backend/services/event_service.py`

- [ ] **Step 1: Migração para tabela `calendar_events`**

```sql
-- ============================================================
-- Migration 014: Tabela calendar_events para eventos de mercado
--                (Copom, earnings, vencimentos de opções)
-- Run via: Supabase Dashboard → SQL Editor
-- ============================================================

CREATE TABLE IF NOT EXISTS calendar_events (
  id BIGSERIAL PRIMARY KEY,
  data DATE NOT NULL,
  label VARCHAR(100) NOT NULL,  -- ex: "COPOM", "EARNINGS_PETR4", "VENCIMENTO_MARCO"
  descricao VARCHAR(255),
  criado_em TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_calendar_events_data_label
  ON calendar_events(data, label);
```

- [ ] **Step 2: Criar `event_service.py` com cadastro de Copom hardcoded**

```python
"""Gestão de eventos de mercado (Copom, earnings, vencimentos)."""
import logging
from datetime import datetime, date

from backend.services.supabase_client import get_supabase

logger = logging.getLogger("b3_api")

# Datas COPOM conhecidas (2026) — hardcoded, sem fonte dinâmica ainda
COPOM_DATAS_2026 = [
    date(2026, 1, 14),
    date(2026, 2, 25),
    date(2026, 3, 25),
    date(2026, 4, 22),
    date(2026, 5, 13),
    date(2026, 6, 17),
    date(2026, 7, 15),
    date(2026, 8, 19),
    date(2026, 9, 16),
    date(2026, 10, 14),
    date(2026, 11, 18),
    date(2026, 12, 16),
]


def registrar_copom_datas(ano: int = 2026):
    """Registra datas Copom no calendário de eventos (idempotente)."""
    supabase = get_supabase()
    if not supabase:
        logger.warning("Supabase indisponível — calendário não atualizado")
        return

    datas = COPOM_DATAS_2026 if ano == 2026 else []
    if not datas:
        logger.warning(f"Datas Copom não conhecidas para {ano}")
        return

    for dt in datas:
        try:
            supabase.table("calendar_events").upsert({
                "data": dt.isoformat(),
                "label": "COPOM",
                "descricao": f"Decisão de taxa Selic — Banco Central",
            }, on_conflict="data,label").execute()
        except Exception as e:
            logger.warning(f"Erro ao registrar Copom {dt}: {e}")

    logger.info(f"Copom {ano} registrado ({len(datas)} datas)")


def obter_evento_na_data(data: date) -> str | None:
    """Retorna label do evento na data, se houver. Consulta cache local."""
    supabase = get_supabase()
    if not supabase:
        return None

    try:
        res = (supabase.table("calendar_events")
               .select("label")
               .eq("data", data.isoformat())
               .execute())
        if res.data and len(res.data) > 0:
            return res.data[0].get("label")
    except Exception as e:
        logger.warning(f"Erro ao consultar evento de {data}: {e}")

    return None
```

- [ ] **Step 3: Chamar `registrar_copom_datas()` no boot**

Em `backend/api/main.py`, adicionar ao inicializar (dentro de `@app.on_event("startup")`):

```python
from backend.services.event_service import registrar_copom_datas

async def startup():
    # ... código existente ...
    registrar_copom_datas(ano=2026)  # Copom 2026
```

- [ ] **Step 4: Integrar evento no sinal**

Em `core_engine.py::analisar_ativo()`, após consultar liquidez:

```python
            # ── EVENTO DO DIA (integrado no check de liquidez) ────────────────
            if estrutura.get("evento_label") is None:
                from backend.services.event_service import obter_evento_na_data
                estrutura["evento_label"] = obter_evento_na_data(date_today)
```

- [ ] **Step 5: Rodar suite de testes**

```bash
pytest tests/ -v
```

Expected: todos os testes passam, nenhuma regressão.

- [ ] **Step 6: Commit**

```bash
git add supabase/migrations/014_calendar_events.sql backend/services/event_service.py backend/api/main.py backend/services/core_engine.py
git commit -m "feat: cadastro de eventos (Copom 2026) para Fase 3"
```

---

## Task 8: VXBR shadow em payload do sinal — telemetria completa

**Files:**
- Verify: `backend/api/routers/signals.py` ou serviço que persiste sinais

- [ ] **Step 1: Verificar que campos de liquidez estão sendo persistidos**

Verificar que `signal_service.py::persist_signal()` inclui os novos campos:

```python
# Em signal_service.py, na função persist_signal (ou similar):
sinal_doc = {
    # ... campos existentes ...
    "oi": sinal.get("oi"),
    "bid": sinal.get("bid"),
    "ask": sinal.get("ask"),
    "spread_pct": sinal.get("spread_pct"),
    "vxbr": sinal.get("vxbr"),
    "evento_label": sinal.get("evento_label"),
    "filtro_liquidez_decisao": sinal.get("filtro_liquidez_decisao"),
    "filtro_liquidez_motivo": sinal.get("filtro_liquidez_motivo"),
    # ...
}
supabase.table("signals").insert(sinal_doc).execute()
```

Se esses campos não estão sendo persistidos, adicionar explicitamente.

- [ ] **Step 2: Verificar schema do Supabase**

Confirmar que a tabela `signals` tem colunas para:
- `oi` (BIGINT, nullable)
- `bid` (FLOAT, nullable)
- `ask` (FLOAT, nullable)
- `spread_pct` (FLOAT, nullable)
- `vxbr` (FLOAT, nullable)
- `evento_label` (VARCHAR, nullable)
- `filtro_liquidez_decisao` (VARCHAR, nullable)
- `filtro_liquidez_motivo` (VARCHAR, nullable)

Se faltarem, criar migração `015_signals_liquidity_columns.sql`:

```sql
-- Migration 015: Adiciona colunas de liquidez a signals (shadow até Fase 4)
ALTER TABLE signals ADD COLUMN IF NOT EXISTS oi BIGINT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS bid FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS ask FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS spread_pct FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS vxbr FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS evento_label VARCHAR(100);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS filtro_liquidez_decisao VARCHAR(50);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS filtro_liquidez_motivo VARCHAR(255);
```

- [ ] **Step 3: Commit (se necessário)**

```bash
git add supabase/migrations/015_signals_liquidity_columns.sql
git commit -m "migration: adicionar colunas de liquidez a signals (Fase 3)"
```

---

## Task 9: Documentar Fase 3 no CHANGELOG e spec

**Files:**
- Modify: `docs/CHANGELOG.md`
- Modify: `docs/superpowers/specs/2026-07-01-matriz-sinais-v2-design.md`

- [ ] **Step 1: Adicionar seção Fase 3 ao CHANGELOG**

```markdown
### Added (Matriz v2 — Fase 3: Dados Externos)
- **Coleta diária de OI via PriceReport (PR) da B3:**
  `https://www.b3.com.br/pesquisapregao/download?filelist=PRAAMMDD.zip`
  — ZIP com XMLs BVBG.086.01; tag `<OpnIntrst>` extraída e agregada por ticker base.
  Job diário (18h BRT) via `coletar_liquidity_diaria()` (`backend/services/liquidity_service.py`).
  Persistido em tabela `option_liquidity(ticker, data, oi, bid, ask, spread_pct, vxbr, evento_label)`.
  
- **Coleta de bid/ask via COTAHIST diário:**
  `https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_DDDMMAAAA.ZIP`
  — Arquivo posicional; campos PREOFC (82-95) e PREOFV (95-108) extrain do tipo 070/080 (opções).
  Agrega por ticker base (melhor bid, pior ask); spread calculado como (ask-bid)/mid*100.
  
- **Coleta de VXBR:**
  `obter_vxbr_diaria()` consulta API brapi.dev (gratuita, sem auth).
  Fallback: None se API indisponível — não bloqueia coleta de OI/bid-ask.
  
- **Calendário de eventos (Copom 2026):**
  Tabela `calendar_events(data, label, descricao)` com Copom hardcoded.
  Job de boot registra datas via `registrar_copom_datas()` (idempotente).
  Consulta em ato de emissão via `obter_evento_na_data(data)`.
  
- **Vetos shadow de executabilidade (Fase 3 §4):**
  `avaliar_filtro_liquidez_shadow(oi, spread_pct, vxbr, evento_label, score)` em `scoring.py`.
  Decisões: "normal" (viável), "atencao" (não bloqueia, registra telemetria), "bloquear" (spread >15%).
  Critérios: OI<500, spread>10%, spread>15%, VXBR>30, evento no DTE.
  Wired em `core_engine.py::analisar_ativo()` — ainda não bloqueiam em modo ativo (pronto para Fase 4).
  
- **Telemetria enriquecida no sinal:**
  Payload inclui `oi`, `bid`, `ask`, `spread_pct`, `vxbr`, `evento_label`,
  `filtro_liquidez_decisao`, `filtro_liquidez_motivo` (todos null se dados indisponíveis).

> **Pendências da Fase 3:** Aplicar migrações `013_option_liquidity.sql` e `014_calendar_events.sql`
> no Supabase (SQL Editor); opcionalmente `015_signals_liquidity_columns.sql` se o schema de signals
> ainda não tiver as colunas. Medir impacto em shadow da taxa de emissão vs. aprovadas por classe.
> Próximo: **Fase 4** (ativar vetos, medir validação em backtest, rollout por etapas).
```

- [ ] **Step 2: Atualizar spec — seção Fase 3**

Em `docs/superpowers/specs/2026-07-01-matriz-sinais-v2-design.md`, seção 6:

```markdown
- **Fase 3 — dados externos** (~1–2 semanas): ✅ **CONCLUÍDA (2026-07-02)**
  - **OI por série**: `liquidity_service.py::_parse_pr_zip()` baixa e descompacta PR,
    extrai `<OpnIntrst>` por `<TckrSymb>`, agrega por ticker base, persiste em `option_liquidity`.
  - **Bid/ask de fechamento**: `liquidity_service.py::_parse_cotahist_zip()` extrai campos
    posicionais (PREOFC/PREOFV), filtra opções (070/080), agrega (melhor bid, pior ask),
    calcula spread.
  - **VXBR**: `indicators.py::obter_vxbr_diaria()` consulta brapi.dev (gratuita).
  - **Eventos**: `event_service.py::registrar_copom_datas()` cadastra Copom 2026;
    `obter_evento_na_data()` consulta no ato.
  - **Vetos shadow**: `scoring.py::avaliar_filtro_liquidez_shadow()` aplica decisões
    (normal/atencao/bloquear) em shadow; wired em `core_engine.py` sem bloquear emissão
    (ready for Fase 4 ativação).
  - **Testes**: 6 unitários (parse PR/COTAHIST), 7 integração (liquidez + vetos),
    1 VXBR. Suíte: ~675 testes.
```

- [ ] **Step 3: Commit**

```bash
git add docs/CHANGELOG.md docs/superpowers/specs/2026-07-01-matriz-sinais-v2-design.md
git commit -m "docs: documentar Fase 3 Matriz v2 (OI, bid/ask, VXBR, eventos)"
```

---

## Task 10: Verificação de integridade — rodar suite completa de testes

**Files:**
- None (verify existing)

- [ ] **Step 1: Rodar testes do projeto inteiro**

```bash
pytest tests/ -v --tb=short
```

Expected: ≥675 testes, 100% passing.

- [ ] **Step 2: Verificar linting**

```bash
flake8 backend/ --max-line-length=120 --extend-ignore=E203,W503
```

Expected: sem erros de estilo (ou só warnings aceitáveis).

- [ ] **Step 3: Verificar coverage**

```bash
pytest tests/ --cov=backend --cov-report=term-missing | grep -A5 "TOTAL"
```

Expected: ≥95% coverage (mantendo padrão da Camada 2).

- [ ] **Step 4: Commit final**

```bash
git add .
git commit -m "Fase 3 Matriz v2: coleta de OI, bid/ask, VXBR, eventos — shadow ativo"
```

Se houver mudanças não commitadas, resolver primeiro.

---

## Summary

**Fase 3 da Matriz v2** implementa integração de dados externos de liquidez (OI via PriceReport, bid/ask via COTAHIST, VXBR via brapi, eventos via hardcode Copom) com 10 tarefas sequenciais:

1. **Schema**: tabela `option_liquidity` (OI, bid, ask, spread, VXBR, evento)
2. **Coleta OI**: parse PR zip, extrai `<OpnIntrst>` por série
3. **VXBR**: `obter_vxbr_diaria()` via brapi.dev
4. **Testes parse**: 6 unitários (mock PR/COTAHIST)
5. **Core integration**: consulta `option_liquidity` no ato, popula campos informativos
6. **Vetos shadow**: `avaliar_filtro_liquidez_shadow()` (OI, spread, VXBR, evento)
7. **Teste integração**: 7 testes de vetos + persistência
8. **Eventos**: tabela `calendar_events`, Copom 2026 hardcoded
9. **Telemetria**: CHANGELOG + spec atualizado
10. **QA**: 675+ testes, linting, coverage ≥95%

Tudo em **shadow** até Fase 4 (ativação + validação). Próximo passo: medir impacto de taxa de emissão vs. aprovadas por classe em histórico real + backtest, então ativar vetos por etapas.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-02-fase3-matriz-v2-liquidity.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach would you prefer?**