"""Testes de coleta de liquidez: OI (PR), bid/ask (COTAHIST) e tratamento diário."""
from datetime import date, datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock
from zipfile import ZipFile

import backend.services.liquidity_service as ls
from backend.services.liquidity_service import (
    _dia_util_anterior,
    _parse_cotahist_zip,
    _parse_pr_zip,
    coletar_liquidity_diaria,
)


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


# ── Tratamento diário: retrocesso de dias úteis, skip-if-exists ──────────────

def test_dia_util_anterior_pula_fim_de_semana():
    """De segunda-feira volta para sexta; de domingo volta para sexta."""
    assert _dia_util_anterior(date(2026, 7, 6)) == date(2026, 7, 3)   # seg → sex
    assert _dia_util_anterior(date(2026, 7, 5)) == date(2026, 7, 3)   # dom → sex
    assert _dia_util_anterior(date(2026, 7, 2)) == date(2026, 7, 1)   # qui → qua


def _mock_supabase_coleta(ja_coletado: bool):
    """Mock do Supabase para coletar_liquidity_diaria (check + upsert)."""
    mock = MagicMock()
    (mock.table.return_value
     .select.return_value
     .eq.return_value
     .limit.return_value
     .execute.return_value) = MagicMock(data=[{"id": 1}] if ja_coletado else [])
    return mock


def test_coleta_skip_se_ja_coletado(monkeypatch):
    """Se a data candidata já tem linhas, não baixa nada e retorna 0."""
    mock_supabase = _mock_supabase_coleta(ja_coletado=True)
    monkeypatch.setattr(ls, "get_supabase", lambda: mock_supabase)
    downloads = []
    monkeypatch.setattr(ls, "_baixar_arquivo_b3",
                        lambda url, desc: downloads.append(url))

    persistidos = coletar_liquidity_diaria(tickers={"PETR4.SA": "Petrobras"}, vxbr=20.0)

    assert persistidos == 0
    assert downloads == []  # nenhum download disparado


def test_coleta_retrocede_ate_achar_arquivo(monkeypatch):
    """Se o arquivo de hoje não existe (feriado/atraso), recua dias úteis e
    persiste sob a data do pregão do arquivo encontrado."""
    mock_supabase = _mock_supabase_coleta(ja_coletado=False)
    monkeypatch.setattr(ls, "get_supabase", lambda: mock_supabase)

    pr_ok = _criar_pr_zip_mock({"PETRG360": 1000})
    chamadas = []

    def fake_download(url, desc):
        chamadas.append(url)
        # falha nas 2 primeiras tentativas (hoje: PR e COTAHIST), acha na 3ª
        return pr_ok if len(chamadas) >= 3 else None

    monkeypatch.setattr(ls, "_baixar_arquivo_b3", fake_download)

    persistidos = coletar_liquidity_diaria(tickers={"PETR4.SA": "Petrobras"}, vxbr=20.0)

    assert persistidos == 1
    upsert_payload = mock_supabase.table.return_value.upsert.call_args[0][0]
    # persistido sob a data do pregão do arquivo (dia útil anterior), não hoje
    hoje = datetime.now(timezone.utc).date()
    data_esperada = _dia_util_anterior(hoje) if hoje.weekday() < 5 else _dia_util_anterior(_dia_util_anterior(hoje))
    assert upsert_payload["data"] == data_esperada.isoformat()
    assert upsert_payload["oi"] == 1000


def test_coleta_sem_arquivo_em_nenhum_dia_retorna_zero(monkeypatch):
    """Se nenhum candidato tem arquivo, retorna 0 sem persistir."""
    mock_supabase = _mock_supabase_coleta(ja_coletado=False)
    monkeypatch.setattr(ls, "get_supabase", lambda: mock_supabase)
    monkeypatch.setattr(ls, "_baixar_arquivo_b3", lambda url, desc: None)

    persistidos = coletar_liquidity_diaria(tickers={"PETR4.SA": "Petrobras"},
                                           vxbr=20.0, max_retrocesso_dias=2)

    assert persistidos == 0
    mock_supabase.table.return_value.upsert.assert_not_called()
