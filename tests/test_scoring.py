"""
Testes unitários para o módulo scoring.py — score ponderado de sinais.

Cobre:
  - Score perfeito (todos os indicadores favoráveis)
  - Score mínimo (tudo contra)
  - Componentes individuais (preço, DTE, delta, tendência, MACD, RSI, etc.)
  - Limite do score em [0, 100]
  - Sinal passando ou não com base no limiar
"""
import pytest
from unittest.mock import patch
from backend.domain.scoring import score_ponderado


def _make_row(**overrides):
    """Cria um dict simulando uma linha de indicadores (último candle)."""
    defaults = {
        "Close": 100.0,
        "Volume": 5_000_000,
        "stoch_k": 50.0,
        "stoch_d": 50.0,
        "rsi": 50.0,
        "ema9": 100.0,
        "ema21": 99.0,
        "ema200": 95.0,
        "macd_diff": 0.5,
        "atr": 2.0,
        "bb_lower": 96.0,
        "bb_upper": 104.0,
        "bb_mid": 100.0,
        "bb_pct": 0.5,
        "bb_width": 0.08,
        "vol_ratio": 1.0,
        "vol_media_20": 5_000_000,
        "suporte_20": 95.0,
        "resistencia_20": 105.0,
        "trend_up": 3,
        "trend_down": 0,
        "adx": 30.0,
        "williams_r": -50.0,
        "cci": 0.0,
    }
    defaults.update(overrides)

    class Row:
        def __init__(self, d):
            self._d = d
        def get(self, key, default=None):
            return self._d.get(key, default)
        def __getitem__(self, key):
            return self._d[key]

    return Row(defaults)


class TestScorePonderadoCall:
    """Testes do score ponderado para CALL."""

    def _call_score(self, last_kw=None, prev_kw=None, price=1.00, dte=30, greeks=None):
        last = _make_row(**(last_kw or {}))
        prev = _make_row(**(prev_kw or {}))
        greeks = greeks or {"delta": 0.30}
        return score_ponderado(last, prev, price, dte, greeks, "CALL")

    def test_score_returns_dict_with_keys(self):
        result = self._call_score()
        assert "score" in result
        assert "signal" in result
        assert "reasons" in result
        assert isinstance(result["reasons"], list)

    def test_score_capped_at_100(self):
        """Score nunca deve ultrapassar 100."""
        result = self._call_score()
        assert result["score"] <= 100

    def test_score_non_negative(self):
        result = self._call_score()
        assert result["score"] >= 0

    def test_price_in_range_gives_12(self):
        """Preço na faixa [0.10, 3.00] → +12 pontos."""
        result = self._call_score(price=1.50)
        assert any("Preço" in r and "✅" in r for r in result["reasons"])

    def test_price_out_of_range(self):
        """Preço fora da faixa → 0 pontos para preço."""
        result = self._call_score(price=10.00)
        assert any("Preço fora" in r for r in result["reasons"])

    def test_dte_in_range_gives_8(self):
        """DTE entre 10 e 60 → +8 pontos."""
        result = self._call_score(dte=30)
        assert any("Vencimento" in r and "✅" in r for r in result["reasons"])

    def test_dte_out_of_range(self):
        result = self._call_score(dte=90)
        assert any("DTE fora" in r for r in result["reasons"])

    def test_delta_otm_ideal(self):
        """Delta |0.30| na faixa [0.15, 0.45] → +10."""
        result = self._call_score(greeks={"delta": 0.30})
        assert any("Delta" in r and "OTM ideal" in r for r in result["reasons"])

    def test_delta_too_otm(self):
        result = self._call_score(greeks={"delta": 0.05})
        assert any("muito OTM" in r for r in result["reasons"])

    def test_strong_trend_gives_20(self):
        """Tendência 3/3 → +20 pontos."""
        result = self._call_score(last_kw={"trend_up": 3})
        assert any("Tendência" in r and "✅" in r for r in result["reasons"])

    def test_weak_trend(self):
        result = self._call_score(last_kw={"trend_up": 1})
        assert any("fraca" in r for r in result["reasons"])

    def test_macd_cross_bullish(self):
        """MACD cruzamento bullish → +18."""
        result = self._call_score(
            last_kw={"macd_diff": 0.5},
            prev_kw={"macd_diff": -0.1},
        )
        assert any("cruzamento" in r and "bullish" in r for r in result["reasons"])

    def test_rsi_recovery_zone(self):
        """RSI entre 35-60 para CALL → +14."""
        result = self._call_score(last_kw={"rsi": 45.0})
        assert any("RSI" in r and "recuperação" in r for r in result["reasons"])

    def test_rsi_overbought_penalizes(self):
        """RSI > 68 para CALL → 0 pontos."""
        result = self._call_score(last_kw={"rsi": 80.0})
        assert any("RSI" in r and "sobrecomprado" in r for r in result["reasons"])

    def test_stoch_oversold_gives_9(self):
        """Estocástico K < 25 → +9."""
        result = self._call_score(last_kw={"stoch_k": 15.0, "stoch_d": 20.0})
        assert any("sobrevendido" in r for r in result["reasons"])

    def test_adx_strong(self):
        """ADX >= 25 → +5."""
        result = self._call_score(last_kw={"adx": 30.0})
        assert any("ADX forte" in r for r in result["reasons"])

    def test_adx_weak(self):
        result = self._call_score(last_kw={"adx": 15.0})
        assert any("ADX fraco" in r for r in result["reasons"])

    def test_volume_high(self):
        """Volume >= 1.5x → +8."""
        result = self._call_score(last_kw={"vol_ratio": 2.0})
        assert any("Volume" in r and "✅" in r for r in result["reasons"])

    def test_bollinger_lower_bonus(self):
        """bb_pct < 0.25 para CALL → +4 bônus."""
        result = self._call_score(last_kw={"bb_pct": 0.10})
        assert any("Bollinger" in r and "inferior" in r for r in result["reasons"])

    def test_vwap_bonus_call(self):
        """Preço acima do VWAP para CALL → +5."""
        result = self._call_score(last_kw={"Close": 105.0, "vwap": 100.0})
        assert any("VWAP" in r for r in result["reasons"])

    def test_volatility_squeeze_bonus(self):
        """Bollinger dentro de Keltner → +5 (Volatility Squeeze)."""
        result = self._call_score(last_kw={
            "bb_upper": 102.0, "bb_lower": 98.0,
            "kc_upper": 105.0, "kc_lower": 95.0
        })
        assert any("Squeeze" in r for r in result["reasons"])


class TestScorePonderadoPut:
    """Testes do score ponderado para PUT."""

    def _put_score(self, last_kw=None, prev_kw=None, price=1.00, dte=30, greeks=None):
        last = _make_row(**(last_kw or {}))
        prev = _make_row(**(prev_kw or {}))
        greeks = greeks or {"delta": -0.30}
        return score_ponderado(last, prev, price, dte, greeks, "PUT")

    def test_rsi_losing_force(self):
        """RSI entre 40-65 para PUT → +14."""
        result = self._put_score(last_kw={"rsi": 55.0})
        assert any("RSI" in r and "perdendo força" in r for r in result["reasons"])

    def test_stoch_overbought_for_put(self):
        """Estocástico K > 75 → +9."""
        result = self._put_score(last_kw={"stoch_k": 85.0, "stoch_d": 80.0})
        assert any("sobrecomprado" in r for r in result["reasons"])

    def test_bollinger_upper_bonus(self):
        """bb_pct > 0.75 para PUT → +4."""
        result = self._put_score(last_kw={"bb_pct": 0.90})
        assert any("Bollinger" in r and "superior" in r for r in result["reasons"])

    def test_macd_cross_bearish(self):
        result = self._put_score(
            last_kw={"macd_diff": -0.5},
            prev_kw={"macd_diff": 0.1},
        )
        assert any("cruzamento" in r and "bearish" in r for r in result["reasons"])


class TestScoreSignalThreshold:
    """Testes do limiar de sinal (min_score_ponderado)."""

    def test_high_score_passes(self):
        """Score alto com todos os indicadores favoráveis deve gerar signal=True."""
        last = _make_row(
            trend_up=3, rsi=45.0, stoch_k=15.0, stoch_d=20.0,
            adx=30.0, vol_ratio=2.0, bb_pct=0.10, macd_diff=0.5,
        )
        prev = _make_row(macd_diff=-0.1, stoch_k=22.0, stoch_d=21.0)
        result = score_ponderado(last, prev, 1.00, 30, {"delta": 0.30}, "CALL")
        assert result["signal"] is True, f"Score={result['score']} deveria passar"

    def test_low_score_fails(self):
        """Score baixo deve gerar signal=False."""
        last = _make_row(
            trend_up=0, rsi=80.0, stoch_k=80.0, stoch_d=75.0,
            adx=15.0, vol_ratio=0.5, bb_pct=0.90, macd_diff=-0.5,
        )
        prev = _make_row(macd_diff=-0.3)
        result = score_ponderado(last, prev, 10.00, 90, {"delta": 0.05}, "CALL")
        assert result["signal"] is False, f"Score={result['score']} não deveria passar"
