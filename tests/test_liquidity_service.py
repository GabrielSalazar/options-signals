"""Testes de coleta de liquidez: OI (PR), bid/ask (COTAHIST)."""
from io import BytesIO
from zipfile import ZipFile

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


def _linha_cotahist(tpmerc: str, ticker: str, ask: str, bid: str) -> str:
    """Monta linha posicional COTAHIST com os campos que a implementação lê:
    TPMERC em [2:5], ticker em [36:40], PREOFC (ask) em [82:95], PREOFV (bid) em [95:108].
    """
    linha = "00" + tpmerc                     # [0:2] registro, [2:5] TPMERC
    linha += " " * (36 - len(linha))          # padding até 36
    linha += ticker.ljust(4)                  # [36:40] ticker base
    linha += " " * (82 - len(linha))          # padding até 82
    linha += f"{ask:>13}"                     # [82:95] PREOFC (ask), right-aligned
    linha += f"{bid:>13}"                     # [95:108] PREOFV (bid), right-aligned
    assert len(linha) == 108
    return linha


def test_parse_pr_zip_sucesso():
    """Parse de PR extrai OI por ticker base, somando strikes."""
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
    assert list(resultado.keys()) == ["PETR"]


def test_parse_cotahist_zip_sucesso():
    """Parse de COTAHIST extrai bid/ask e calcula spread."""
    linha = _linha_cotahist("070", "PETR", "1.55", "1.43")

    content = _criar_cotahist_zip_mock([linha])
    tickers_universo = {"PETR"}

    resultado = _parse_cotahist_zip(content, tickers_universo)

    assert "PETR" in resultado
    assert abs(resultado["PETR"]["ask"] - 1.55) < 0.01
    assert abs(resultado["PETR"]["bid"] - 1.43) < 0.01
    # spread = (1.55 - 1.43) / ((1.55 + 1.43) / 2) * 100 ≈ 8.05%
    assert abs(resultado["PETR"]["spread_pct"] - 8.05) < 0.1


def test_parse_cotahist_zip_ignora_acoes():
    """Parse ignora ações (TPMERC != 070/080)."""
    linha = _linha_cotahist("010", "PETR", "10.50", "10.48")  # 010 = ação

    content = _criar_cotahist_zip_mock([linha])
    tickers_universo = {"PETR"}

    resultado = _parse_cotahist_zip(content, tickers_universo)

    assert "PETR" not in resultado


def test_parse_cotahist_zip_ignora_ticker_fora_universo():
    """Parse ignora opções de tickers fora do universo."""
    linha = _linha_cotahist("070", "VALE", "1.55", "1.43")

    content = _criar_cotahist_zip_mock([linha])
    tickers_universo = {"PETR"}

    resultado = _parse_cotahist_zip(content, tickers_universo)

    assert resultado == {}


def test_parse_cotahist_zip_agregacao_melhor_bid_pior_ask():
    """Parse agrega múltiplas séries: melhor bid (maior), pior ask (menor)."""
    linha1 = _linha_cotahist("070", "PETR", "1.55", "1.43")
    linha2 = _linha_cotahist("070", "PETR", "1.50", "1.44")

    content = _criar_cotahist_zip_mock([linha1, linha2])
    tickers_universo = {"PETR"}

    resultado = _parse_cotahist_zip(content, tickers_universo)

    assert resultado["PETR"]["ask"] == 1.50  # menor ask
    assert resultado["PETR"]["bid"] == 1.44  # maior bid
    # spread recalculado sobre bid/ask agregados
    esperado = ((1.50 - 1.44) / ((1.50 + 1.44) / 2)) * 100
    assert abs(resultado["PETR"]["spread_pct"] - esperado) < 0.01
