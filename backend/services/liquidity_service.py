"""Coleta de liquidez diária: OI via PR (PriceReport da B3), bid/ask via COTAHIST."""
import logging
import io
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from zipfile import ZipFile

import requests

from backend.services.supabase_client import get_supabase
from backend.services.ticker_loader import carregar_tickers_b3

logger = logging.getLogger("b3_api")

# URLs públicos da B3 (formato: PRAAMMDD.zip, COTAHIST_DDDMMAAAA.zip)
PR_BASE_URL = "https://www.b3.com.br/pesquisapregao/download?filelist=PRA{date_b3}.zip"
COTAHIST_BASE_URL = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_{date_cotahist}.ZIP"

TIMEOUT_SECONDS = 30


def _baixar_arquivo_b3(url: str, descricao: str) -> bytes | None:
    """Baixa arquivo público da B3 com timeout e logging.

    Args:
        url: URL completa do arquivo (contém data já formatada)
        descricao: nome descritivo para logging (ex: "PriceReport", "COTAHIST")

    Returns:
        Conteúdo do arquivo em bytes, ou None se falha.
        Falhas são logadas como WARNING, não criam exceção.
    """
    try:
        resp = requests.get(url, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        logger.info(f"✓ {descricao} baixado ({len(resp.content)} bytes)")
        return resp.content
    except Exception as e:
        logger.warning(f"✗ Erro ao baixar {descricao}: {e}")
        return None


def _parse_pr_zip(content: bytes, tickers_universo: set) -> dict:
    """Extrai OI do PR (PriceReport) zipado.

    PR é um ZIP com XMLs aninhados. Cada XML BVBG.086.01 tem estrutura:
    ```xml
    <Document>
      <DlvyStnDta>
        <MktDta>
          <Istrm>
            <TckrSymb>PETRG360</TckrSymb>
            <OpnIntrst>518200</OpnIntrst>
          </Istrm>
          ...
        </MktDta>
      </DlvyStnDta>
    </Document>
    ```

    O arquivo XML pode conter múltiplas séries de opções (diferentes strikes
    do mesmo ticker base). Esta função soma OI sobre todos os strikes.

    Args:
        content: Conteúdo zipado do PR (bytes)
        tickers_universo: Set de tickers base a processar (ex: {"PETR", "VALE", "BBAS"})
                         Strings são comparadas com os 4 primeiros chars de TckrSymb

    Returns:
        dict {ticker_base: total_oi} — ticker é a chave (agregação por base),
        OI é a soma de todos os strikes dessa base. Se um ticker não aparecer
        no arquivo, ele não aparece no dict (e será None em persistência).
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
    """Extrai bid/ask de fechamento do COTAHIST.

    COTAHIST é um ZIP com um arquivo TXT com campos posicionais (fixed-width).
    Estrutura esperada (baseada em formato oficial B3 para COTAHIST):
    - Campo 'TPMERC' (posição 2-5): "070" = call, "080" = put
                     (ignoramos outros tipos como "010" = ação)
    - Campo 'ESPECS' (posição 36-40): código da opção (ex: PETRG360)
    - Campo 'PREOFC' (posição 82-95): preço oferecido (ask) — right-aligned, vírgula decimal
    - Campo 'PREOFV' (posição 95-108): preço ofertado (bid) — right-aligned, vírgula decimal

    A função filtra apenas opções (TPMERC=070/080) de tickers no universo,
    agrega múltiplos strikes de um mesmo ticker (melhor bid = maior, pior ask = menor),
    e calcula spread como (ask - bid) / mid * 100.

    Args:
        content: Conteúdo zipado do COTAHIST (bytes)
        tickers_universo: Set de tickers base a processar

    Returns:
        dict {ticker_base: {"bid": float, "ask": float, "spread_pct": float}}
        Se um ticker não aparecer no arquivo, ele não aparece no dict.
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
    """Job diário (pós-fechamento): persiste OI, bid/ask, VXBR para o universo líquido.

    Este é um job idempotente: rodar 2x no mesmo dia sobrescreve a entrada anterior
    (via upsert em on_conflict="ticker,data"). Falha parcial (um ticker) não derruba
    o job — cada ticker é encapsulado em try/except, e o job retorna o nº de
    tickers com sucesso. Se Supabase estiver indisponível, retorna 0.

    Dados parciais são persistidos como NULL:
    - Se PR falhar, oi = NULL para todos os tickers
    - Se COTAHIST falhar, bid/ask/spread_pct = NULL para todos
    - Se brapi falhar (VXBR), vxbr = NULL para todos
    - eventos_label preenchido em Task posterior (job de eventos)

    Args:
        tickers: dict {ticker_with_SA: nome} (ex: {"PETR4.SA": "Petrobras"})
                 Se None, carrega universo via carregar_tickers_b3()
        vxbr: float VXBR do dia. Se None, tenta obter via obter_vxbr_diaria() (Task 3)

    Returns:
        int: Número de tickers persistidos com sucesso. (Falhas parciais contam como sucesso
             da persistência, mesmo que bid/ask/oi sejam NULL.)
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
    data_b3 = hoje.strftime("%y%m%d")  # formato AAMMDD (ex: 260702) — nome real do arquivo PR na B3
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
                "evento_label": None,  # preenchido separadamente (Task 7)
            }, on_conflict="ticker,data").execute()
            persistidos += 1
        except Exception as e:
            logger.warning(f"Erro ao persistir liquidez de {ticker_base}: {e}")

    logger.info(f"Liquidez coletada — {persistidos}/{len(tickers_universo)} tickers (OI: {len(oi_por_ticker)}, bid/ask: {len(bid_ask_por_ticker)})")
    return persistidos
