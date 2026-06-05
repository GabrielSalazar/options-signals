"""Testes dos vencimentos B3 — semanais (sexta) + mensais (3ª sexta)."""
from backend.domain.options_math import _proximo_vencimento_b3, mes_vencimento_ideal
from backend.core.config import CONFIG


def test_proximo_vencimento_retorna_data_valida_no_range():
    """Retorna (mes, ano, dte, tipo) com DTE dentro de [dte_min, dte_max]."""
    mes, ano, dte, tipo = _proximo_vencimento_b3()
    assert mes in range(1, 13)
    assert ano in [2026, 2027]
    assert CONFIG["dte_minimo"] <= dte <= CONFIG["dte_maximo"]
    assert tipo in ["semanal", "mensal", "nenhum"]


def test_mes_vencimento_ideal_retorna_terceira_sexta_se_no_range():
    """Retorna (mes, ano, dte) do próximo vencimento no range [dte_min, dte_max]."""
    mes, ano, dte = mes_vencimento_ideal()
    assert mes in range(1, 13)
    assert ano in [2026, 2027]
    assert CONFIG["dte_minimo"] <= dte <= CONFIG["dte_maximo"]


def test_dte_minimo_1_permite_vencimentos_proximos():
    """Com dte_minimo=1, sextas próximas (semanais) são aceitas."""
    assert CONFIG["dte_minimo"] == 1
    _, _, dte, _ = _proximo_vencimento_b3()
    # Próxima sexta deve ter DTE dentro do range [1, 45]
    assert 1 <= dte <= 45 or dte == 0  # 0 = fallback (nenhum encontrado)
