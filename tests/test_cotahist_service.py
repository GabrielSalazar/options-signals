"""Loader de prêmios reais de opções via COTAHIST. Usa DataFrame injetado (sem rede)."""
import pandas as pd

from backend.services.cotahist_service import filtrar_opcoes_do_ativo


def _df_cotahist():
    return pd.DataFrame({
        "cod_negociacao": ["PETRG100", "PETRG100", "VALEG60"],
        "tipo_mercado":   [70, 70, 70],   # 70 = opção de compra na B3
        "preco_ultimo":   [1.50, 1.55, 2.10],
        "data_referencia": pd.to_datetime(["2026-06-30", "2026-07-01", "2026-07-01"]),
    })


def test_filtra_series_do_ativo():
    out = filtrar_opcoes_do_ativo(_df_cotahist(), ativo_base="PETR")
    assert set(out["cod_negociacao"]) == {"PETRG100"}
    assert len(out) == 2  # duas datas da mesma série


def test_ativo_inexistente_retorna_vazio():
    out = filtrar_opcoes_do_ativo(_df_cotahist(), ativo_base="ITUB")
    assert out.empty
