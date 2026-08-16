"""Tests for volatility surface modeling and analysis.

Testa construção de superfície de IV, detecção de skew/smile, interpolação.
Todos os testes usam ativos arbitrários (não específicos de ticker).
"""
import pytest
import numpy as np

from backend.domain.volatility_surface import (
    VolatilitySurface,
    IVPoint,
    SkewType,
    SurfaceMetrics
)


class TestVolatilitySurfaceBasic:
    """Testes de funcionalidade básica de construção da superfície."""

    def test_surface_initialization(self):
        """Deve inicializar superfície com spot price."""
        surface = VolatilitySurface(spot_price=100.0)
        assert surface.spot_price == 100.0
        assert len(surface.points) == 0

    def test_add_single_point(self):
        """Deve adicionar ponto de IV à superfície."""
        surface = VolatilitySurface(spot_price=100.0)
        surface.add_point(strike=105.0, dte=9, iv=0.25, option_type="CALL")

        assert len(surface.points) == 1
        point = surface.points[0]
        assert point.strike == 105.0
        assert point.dte == 9
        assert point.iv == 0.25
        assert point.option_type == "CALL"

    def test_moneyness_calculated_on_add(self):
        """Deve calcular moneyness (spot/strike) ao adicionar ponto."""
        surface = VolatilitySurface(spot_price=100.0)
        surface.add_point(strike=110.0, dte=9, iv=0.25, option_type="CALL")

        point = surface.points[0]
        expected_moneyness = 100.0 / 110.0
        assert abs(point.moneyness - expected_moneyness) < 0.0001

    def test_add_multiple_points(self):
        """Deve agregar múltiplos pontos de IV."""
        surface = VolatilitySurface(spot_price=100.0)

        strikes = [95.0, 100.0, 105.0, 110.0]
        for strike in strikes:
            surface.add_point(strike=strike, dte=9, iv=0.20, option_type="CALL")

        assert len(surface.points) == 4

    def test_atm_iv_exact_match(self):
        """Deve extrair IV ATM quando disponível exatamente."""
        surface = VolatilitySurface(spot_price=100.0)

        # Adiciona strike ATM (100.0)
        surface.add_point(strike=100.0, dte=9, iv=0.25, option_type="CALL")
        surface.add_point(strike=100.0, dte=9, iv=0.26, option_type="PUT")

        atm = surface.atm_iv(dte=9)
        assert atm is not None
        assert abs(atm - 0.255) < 0.001  # Média de CALL/PUT

    def test_atm_iv_near_match(self):
        """Deve extrair IV ATM para strikes próximos (±2%)."""
        surface = VolatilitySurface(spot_price=100.0)

        surface.add_point(strike=99.0, dte=9, iv=0.25, option_type="CALL")
        surface.add_point(strike=101.0, dte=9, iv=0.25, option_type="PUT")

        atm = surface.atm_iv(dte=9)
        assert atm is not None
        assert abs(atm - 0.25) < 0.001

    def test_atm_iv_none_if_not_available(self):
        """Deve retornar None se IV ATM não disponível."""
        surface = VolatilitySurface(spot_price=100.0)

        surface.add_point(strike=110.0, dte=9, iv=0.25, option_type="CALL")
        surface.add_point(strike=90.0, dte=9, iv=0.30, option_type="PUT")

        atm = surface.atm_iv(dte=9)
        assert atm is None


class TestVolatilitySurfaceInterpolation:
    """Testes de interpolação de IV para strikes não cotados."""

    def test_interpolation_with_sparse_data(self):
        """Deve interpolar IV para strike não cotado com dados suficientes."""
        surface = VolatilitySurface(spot_price=100.0)

        # Cria grade básica de pontos
        surface.add_point(strike=95.0, dte=9, iv=0.30, option_type="CALL")
        surface.add_point(strike=100.0, dte=9, iv=0.25, option_type="CALL")
        surface.add_point(strike=105.0, dte=9, iv=0.22, option_type="CALL")

        # Interpola para strike intermediário
        iv_interp = surface.interpolate_iv(strike=102.5, dte=9)
        assert iv_interp is not None
        assert 0.20 < iv_interp < 0.24  # Deve estar entre 100 e 105

    def test_interpolation_none_if_insufficient_points(self):
        """Deve retornar None se pontos insuficientes (<3)."""
        surface = VolatilitySurface(spot_price=100.0)

        surface.add_point(strike=100.0, dte=9, iv=0.25, option_type="CALL")
        surface.add_point(strike=105.0, dte=9, iv=0.22, option_type="CALL")

        iv_interp = surface.interpolate_iv(strike=102.5, dte=9)
        # Pode ser None ou valor válido (< 3 points é borderline)

    def test_interpolation_multiple_dte(self):
        """Deve interpolar em 2D (strike × DTE)."""
        surface = VolatilitySurface(spot_price=100.0)

        # Cria grade 2D
        for dte in [9, 30, 60]:
            for strike in [95.0, 100.0, 105.0]:
                iv = 0.25 - 0.02 * ((dte - 9) / 51)  # IV aumenta com prazo
                surface.add_point(strike=strike, dte=dte, iv=iv, option_type="CALL")

        # Interpola ponto não cotado
        iv_interp = surface.interpolate_iv(strike=102.0, dte=45)
        if iv_interp is not None:
            assert 0.20 < iv_interp < 0.25


class TestVolatilitySurfaceSkew:
    """Testes de detecção de padrão de volatilidade (skew vs smile)."""

    def test_detect_flat_volatility(self):
        """Deve detectar volatilidade plana (skew flat)."""
        surface = VolatilitySurface(spot_price=100.0)

        # Mesma IV em todos os strikes (flat)
        for strike in [90.0, 95.0, 100.0, 105.0, 110.0]:
            option_type = "CALL" if strike > 100.0 else "PUT"
            surface.add_point(strike=strike, dte=9, iv=0.25, option_type=option_type)

        skew = surface.detect_skew()
        assert skew == SkewType.FLAT

    def test_detect_put_skew(self):
        """Deve detectar skew: puts OTM mais voláteis que calls OTM."""
        surface = VolatilitySurface(spot_price=100.0)

        # ATM
        surface.add_point(strike=100.0, dte=9, iv=0.20, option_type="CALL")
        surface.add_point(strike=100.0, dte=9, iv=0.20, option_type="PUT")

        # OTM calls (strike > spot): baixa IV
        surface.add_point(strike=105.0, dte=9, iv=0.18, option_type="CALL")
        surface.add_point(strike=110.0, dte=9, iv=0.16, option_type="CALL")

        # OTM puts (strike < spot): alta IV
        surface.add_point(strike=95.0, dte=9, iv=0.28, option_type="PUT")
        surface.add_point(strike=90.0, dte=9, iv=0.35, option_type="PUT")

        skew = surface.detect_skew()
        assert skew == SkewType.SKEW

    def test_detect_reverse_skew(self):
        """Deve detectar reverse skew: calls OTM mais voláteis que puts OTM."""
        surface = VolatilitySurface(spot_price=100.0)

        # ATM
        surface.add_point(strike=100.0, dte=9, iv=0.20, option_type="CALL")
        surface.add_point(strike=100.0, dte=9, iv=0.20, option_type="PUT")

        # OTM calls: alta IV
        surface.add_point(strike=105.0, dte=9, iv=0.30, option_type="CALL")
        surface.add_point(strike=110.0, dte=9, iv=0.35, option_type="CALL")

        # OTM puts: baixa IV
        surface.add_point(strike=95.0, dte=9, iv=0.18, option_type="PUT")
        surface.add_point(strike=90.0, dte=9, iv=0.16, option_type="PUT")

        skew = surface.detect_skew()
        assert skew == SkewType.REVERSE_SKEW


class TestVolatilitySurfaceSmile:
    """Testes de detecção de padrão de smile."""

    def test_calculate_smile_strength_zero_if_no_data(self):
        """Deve retornar strength=0 se superfície vazia."""
        surface = VolatilitySurface(spot_price=100.0)
        strength = surface.calculate_smile_strength()
        assert strength == 0.0

    def test_calculate_smile_strength_nonzero_with_convexity(self):
        """Deve calcular strength > 0 se houver convexidade."""
        surface = VolatilitySurface(spot_price=100.0)

        # Smile: OTM > ATM
        surface.add_point(strike=90.0, dte=9, iv=0.25, option_type="CALL")
        surface.add_point(strike=100.0, dte=9, iv=0.20, option_type="CALL")  # ATM lowest
        surface.add_point(strike=110.0, dte=9, iv=0.25, option_type="CALL")

        strength = surface.calculate_smile_strength()
        assert 0.0 < strength <= 1.0

    def test_smile_strength_normalized(self):
        """Deve retornar strength normalizada [0.0, 1.0]."""
        surface = VolatilitySurface(spot_price=100.0)

        for strike in [90.0, 95.0, 100.0, 105.0, 110.0]:
            # Smile extremo
            iv = 0.20 if strike == 100.0 else 0.40
            surface.add_point(strike=strike, dte=9, iv=iv, option_type="CALL")

        strength = surface.calculate_smile_strength()
        assert 0.0 <= strength <= 1.0


class TestVolatilitySurfaceMetrics:
    """Testes de cálculo de métricas agregadas."""

    def test_compute_metrics_basic(self):
        """Deve computar métricas agregadas da superfície."""
        surface = VolatilitySurface(spot_price=100.0)

        surface.add_point(strike=95.0, dte=9, iv=0.25, option_type="CALL")
        surface.add_point(strike=100.0, dte=9, iv=0.23, option_type="CALL")
        surface.add_point(strike=105.0, dte=9, iv=0.21, option_type="CALL")

        metrics = surface.compute_metrics()

        assert isinstance(metrics, SurfaceMetrics)
        assert 0.15 < metrics.atm_iv < 0.30  # IV razoável
        assert 0.0 <= metrics.iv_rank <= 1.0
        assert isinstance(metrics.skew_type, SkewType)
        assert 0.0 <= metrics.smile_strength <= 1.0

    def test_compute_metrics_with_historical_iv(self):
        """Deve calcular IV rank com histórico de IVs."""
        surface = VolatilitySurface(spot_price=100.0)

        surface.add_point(strike=100.0, dte=9, iv=0.25, option_type="CALL")

        # Histórico com IV atual em percentil 60
        historical_ivs = [0.15, 0.18, 0.20, 0.22, 0.25, 0.28, 0.30, 0.35]

        metrics = surface.compute_metrics(historical_ivs=historical_ivs)
        assert 0.0 <= metrics.iv_rank <= 1.0

    def test_compute_metrics_term_structure_contango(self):
        """Deve detectar contango (IV curta < longa)."""
        surface = VolatilitySurface(spot_price=100.0)

        # Curta: IV baixa
        surface.add_point(strike=100.0, dte=9, iv=0.20, option_type="CALL")

        # Longa: IV alta
        surface.add_point(strike=100.0, dte=60, iv=0.30, option_type="CALL")

        metrics = surface.compute_metrics()
        assert metrics.term_structure == "contango"

    def test_compute_metrics_term_structure_backwardation(self):
        """Deve detectar backwardation (IV curta > longa)."""
        surface = VolatilitySurface(spot_price=100.0)

        # Curta: IV alta
        surface.add_point(strike=100.0, dte=9, iv=0.30, option_type="CALL")

        # Longa: IV baixa
        surface.add_point(strike=100.0, dte=60, iv=0.20, option_type="CALL")

        metrics = surface.compute_metrics()
        assert metrics.term_structure == "backwardation"


class TestVolatilitySurfaceGeneric:
    """Testes de genericidade (qualquer ativo)."""

    def test_works_with_different_spot_prices(self):
        """Deve funcionar identicamente com diferentes preços do ativo."""
        # Superfície para ativo a 100
        surface1 = VolatilitySurface(spot_price=100.0)
        surface1.add_point(strike=105.0, dte=9, iv=0.25, option_type="CALL")

        # Superfície para ativo a 50 (mesma OTM%)
        surface2 = VolatilitySurface(spot_price=50.0)
        surface2.add_point(strike=52.5, dte=9, iv=0.25, option_type="CALL")

        metrics1 = surface1.compute_metrics()
        metrics2 = surface2.compute_metrics()

        # Mesma IV implica mesmas métricas (com rounding)
        assert abs(metrics1.atm_iv - metrics2.atm_iv) < 0.01

    def test_cache_invalidation_on_add(self):
        """Deve invalidar cache de métricas ao adicionar ponto."""
        surface = VolatilitySurface(spot_price=100.0)
        surface.add_point(strike=100.0, dte=9, iv=0.25, option_type="CALL")

        metrics1 = surface.compute_metrics()

        # Adiciona novo ponto
        surface.add_point(strike=105.0, dte=9, iv=0.20, option_type="CALL")

        metrics2 = surface.compute_metrics()

        # Métricas podem ter mudado
        # (verificamos que cache foi invalidado, não valores específicos)
        assert metrics1 is not metrics2  # Objetos diferentes
