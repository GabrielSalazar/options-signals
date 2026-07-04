"""Testes do serviço de taxa livre de risco (SELIC via BCB) com cache e fallback."""
from unittest.mock import patch

import pandas as pd

from backend.domain.greeks import RISK_FREE_RATE_DEFAULT
from backend.services import risk_free_service


def _fake_sgs_df(valor_percent: float):
    # python-bcb.sgs.get retorna DataFrame indexado por data, coluna = série
    return pd.DataFrame({"selic": [valor_percent]},
                        index=pd.to_datetime(["2026-07-01"]))


def test_selic_convertida_para_decimal():
    risk_free_service._invalidate_cache()
    with patch("backend.services.risk_free_service.sgs.get",
               return_value=_fake_sgs_df(15.0)) as mock_get:
        taxa = risk_free_service.get_selic_anual()
    assert abs(taxa - 0.15) < 1e-9
    mock_get.assert_called_once()


def test_fallback_quando_bcb_falha():
    risk_free_service._invalidate_cache()
    with patch("backend.services.risk_free_service.sgs.get",
               side_effect=RuntimeError("bcb offline")):
        taxa = risk_free_service.get_selic_anual()
    assert taxa == RISK_FREE_RATE_DEFAULT


def test_cache_evita_segunda_chamada():
    risk_free_service._invalidate_cache()
    with patch("backend.services.risk_free_service.sgs.get",
               return_value=_fake_sgs_df(12.5)) as mock_get:
        primeira = risk_free_service.get_selic_anual()
        segunda = risk_free_service.get_selic_anual()
    assert primeira == segunda == 0.125
    mock_get.assert_called_once()
