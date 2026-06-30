"""
Testes unitários para o módulo config.py.

Cobre:
  - CONFIG defaults
  - ATIVOS_B3 e OTM_POR_ATIVO
  - score_horario
  - is_reentrada_valida / registrar_sinal
  - dentro_horario_pregao
"""
import copy
from datetime import datetime, timedelta

import pytest

from backend.core.config import (
    ATIVOS_B3,
    CONFIG,
    OTM_DEFAULT,
    OTM_POR_ATIVO,
    _historico_sinais,
    is_reentrada_valida,
    registrar_sinal,
    score_horario,
    validar_config,
)


class TestValidarConfig:
    """validar_config() trava invariantes críticos no boot (fail-fast). [P2-7]"""

    def test_config_atual_e_valido(self):
        validar_config()  # não deve levantar

    def test_rejeita_dte_invalido(self):
        c = copy.deepcopy(CONFIG); c["dte_minimo"] = 50  # > dte_maximo
        with pytest.raises(ValueError, match="DTE"):
            validar_config(c)

    def test_rejeita_delta_invalido(self):
        c = copy.deepcopy(CONFIG); c["delta_min"] = 0.6  # > delta_max
        with pytest.raises(ValueError, match="delta"):
            validar_config(c)

    def test_rejeita_stop_positivo(self):
        c = copy.deepcopy(CONFIG); c["stop_pct"] = 0.43
        with pytest.raises(ValueError, match="stop_pct"):
            validar_config(c)

    def test_rejeita_alvos_nao_crescentes(self):
        c = copy.deepcopy(CONFIG); c["alvo2_pct"] = 0.1  # < alvo1
        with pytest.raises(ValueError, match="alvo"):
            validar_config(c)


class TestConfigDefaults:
    """Verifica que CONFIG tem todos os parâmetros necessários."""

    REQUIRED_KEYS = [
        "stoch_k_period", "stoch_d_period", "rsi_period",
        "ema_fast", "ema_slow", "volume_mult",
        "stop_pct", "alvo1_pct", "alvo2_pct", "alvo_final_pct",
        "min_volume_acoes", "min_score",
        "delta_min", "delta_max", "dte_minimo", "dte_maximo",
        "reentrada_min_dias", "scoring_mode", "min_score_ponderado",
    ]

    @pytest.mark.parametrize("key", REQUIRED_KEYS)
    def test_key_exists(self, key):
        assert key in CONFIG, f"CONFIG missing key: {key}"

    def test_stop_negative(self):
        assert CONFIG["stop_pct"] < 0, "stop_pct deve ser negativo"

    def test_alvo1_positive(self):
        assert CONFIG["alvo1_pct"] > 0

    def test_delta_range_valid(self):
        assert 0 < CONFIG["delta_min"] < CONFIG["delta_max"] <= 1.0

    def test_dte_range_valid(self):
        assert 0 < CONFIG["dte_minimo"] < CONFIG["dte_maximo"]

    def test_pivot_ordem_existe_e_valido(self):
        assert "pivot_ordem" in CONFIG
        assert isinstance(CONFIG["pivot_ordem"], int)
        assert CONFIG["pivot_ordem"] >= 1

    def test_reentrada_direcional_knobs(self):
        assert CONFIG["reentrada_mesma_direcao_dias"] >= 1
        assert CONFIG["reentrada_direcao_oposta_delta_score"] >= 0


class TestAtivosB3:
    """Verifica integridade da lista de ativos."""

    def test_has_major_tickers(self):
        for t in ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBAS3.SA", "WEGE3.SA"]:
            assert t in ATIVOS_B3, f"{t} ausente de ATIVOS_B3"

    def test_all_keys_end_with_sa(self):
        for t in ATIVOS_B3:
            assert t.endswith(".SA"), f"Ticker {t} não termina com .SA"

    def test_all_values_non_empty(self):
        for t, name in ATIVOS_B3.items():
            assert len(name) > 0, f"Nome vazio para {t}"


class TestOTM:
    """Verifica OTM_POR_ATIVO."""

    def test_default_exists(self):
        assert OTM_DEFAULT > 0

    def test_all_otm_positive(self):
        for t, v in OTM_POR_ATIVO.items():
            assert 0 < v < 1, f"OTM inválido para {t}: {v}"


class TestScoreHorario:
    """Testes para score_horario — bonificação por horário de mercado."""

    def test_abertura(self):
        """10:00–11:30 → score 2."""
        assert score_horario("10:30") == 2

    def test_melhor_janela(self):
        """13:00–15:00 → score 3."""
        assert score_horario("14:00") == 3

    def test_final_pregao(self):
        """15:00–16:30 → score 1."""
        assert score_horario("16:00") == 1

    def test_fora_pregao(self):
        """Fora do horário → score 0."""
        assert score_horario("08:00") == 0
        assert score_horario("18:00") == 0

    def test_invalid_format(self):
        """Formato inválido → score 0."""
        assert score_horario("abc") == 0

    def test_usa_timezone_brt_nao_naive(self, monkeypatch):
        """score_horario() sem argumento deve avaliar a hora em BRT, não no fuso
        do servidor. Simulamos um servidor em UTC: 16:30 UTC = 13:30 BRT → bônus 3."""
        from datetime import datetime as real_dt
        from zoneinfo import ZoneInfo

        import backend.core.config as cfg

        class _FakeDateTime(real_dt):
            @classmethod
            def now(cls, tz=None):
                base = real_dt(2026, 6, 15, 16, 30, tzinfo=ZoneInfo("UTC"))
                return base.astimezone(tz) if tz else base.replace(tzinfo=None)

        monkeypatch.setattr(cfg, "datetime", _FakeDateTime)
        assert cfg.score_horario() == 3  # 13:30 BRT


class TestReentrada:
    """Testes de reentrada de sinais."""

    def setup_method(self):
        """Limpa o histórico antes de cada teste."""
        _historico_sinais.clear()

    def test_first_entry_valid(self):
        assert is_reentrada_valida("PETR4") is True

    def test_recent_entry_blocked(self):
        registrar_sinal("VALE3")
        assert is_reentrada_valida("VALE3") is False

    def test_old_entry_valid(self):
        from backend.core.config import _historico_sinais
        _historico_sinais["ITUB4"] = [{
            "ts": datetime.now() - timedelta(days=CONFIG["reentrada_mesma_direcao_dias"] + 1),
            "tipo": "CALL", "score": 8,
        }]
        assert is_reentrada_valida("ITUB4", "CALL", 8) is True

    def test_mesma_direcao_recente_bloqueia(self):
        registrar_sinal("PETR4", "CALL", 9)
        assert is_reentrada_valida("PETR4", "CALL", 12) is False

    def test_direcao_oposta_fraca_bloqueia(self):
        registrar_sinal("PETR4", "CALL", 11)
        assert is_reentrada_valida("PETR4", "PUT", 12) is False

    def test_direcao_oposta_forte_emite(self):
        registrar_sinal("PETR4", "CALL", 11)
        assert is_reentrada_valida("PETR4", "PUT", 13) is True

    def test_different_tickers_independent(self):
        registrar_sinal("PETR4")
        assert is_reentrada_valida("VALE3") is True


class TestLoaderKnobs:
    """Knobs do carregador de tickers e dos pontos expostos (A2/A3)."""

    @pytest.mark.parametrize("key", [
        "min_volume_rs", "ticker_top_n", "ticker_cache_segundos",
        "scan_max_workers", "telegram_throttle_s",
    ])
    def test_knob_exists(self, key):
        assert key in CONFIG, f"CONFIG missing key: {key}"

    def test_min_volume_rs_positive(self):
        assert CONFIG["min_volume_rs"] > 0

    def test_scan_max_workers_reasonable(self):
        assert 1 <= CONFIG["scan_max_workers"] <= 32
