"""Generic volatility surface modeling and analysis.

Constructs and analyzes IV surface across strikes and DTEs.
Detects skew/smile patterns, performs IV interpolation, and calculates IV rank.
Works with ANY underlying asset (ticker-agnostic).
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np
from scipy.interpolate import griddata


class SkewType(Enum):
    """Classificação de padrão de volatilidade."""
    FLAT = "flat"  # Volatilidade uniforme entre strikes
    SMILE = "smile"  # Volatilidade maior em OTM puts e calls
    SKEW = "skew"  # Assimétria: puts OTM mais voláteis que calls
    REVERSE_SKEW = "reverse_skew"  # Inverso: calls OTM mais voláteis


@dataclass
class IVPoint:
    """Ponto individual de volatilidade implícita na superfície."""
    strike: float  # Preço de strike
    dte: int  # Dias até expiração
    iv: float  # Volatilidade implícita (0.20 = 20%)
    moneyness: float  # Razão spot/strike
    option_type: str  # "CALL" ou "PUT"


@dataclass
class SurfaceMetrics:
    """Métricas agregadas da superfície de volatilidade."""
    atm_iv: float  # IV no dinheiro (ATM)
    iv_rank: float  # Percentil de IV histórica (0.0-1.0)
    skew_type: SkewType  # Tipo de padrão detectado
    smile_strength: float  # Força do smile (0.0-1.0)
    term_structure: str  # "contango" ou "backwardation"


class VolatilitySurface:
    """Construtor e analisador de superfície de volatilidade.

    Agrupa pontos de IV de uma corrente de opções, detecta padrões de skew/smile,
    e fornece interpolação de IV para strikes/DTEs não cotados.
    """

    def __init__(self, spot_price: float):
        """Inicializa superfície para um ativo subjacente.

        Args:
            spot_price: Preço current do ativo subjacente
        """
        self.spot_price = spot_price
        self.points: list[IVPoint] = []
        self._cached_metrics: Optional[SurfaceMetrics] = None

    def add_point(
        self,
        strike: float,
        dte: int,
        iv: float,
        option_type: str
    ) -> None:
        """Adiciona um ponto de IV à superfície.

        Args:
            strike: Preço de strike
            dte: Dias até expiração
            iv: Volatilidade implícita (0.20 = 20%)
            option_type: "CALL" ou "PUT"
        """
        moneyness = self.spot_price / strike
        point = IVPoint(
            strike=strike,
            dte=dte,
            iv=iv,
            moneyness=moneyness,
            option_type=option_type
        )
        self.points.append(point)
        self._cached_metrics = None  # Invalidate cache

    def atm_iv(self, dte: int) -> Optional[float]:
        """Extrai IV no dinheiro (ATM) para um vencimento específico.

        Args:
            dte: Dias até expiração

        Returns:
            Volatilidade implícita ATM ou None se não disponível
        """
        # Busca pontos no vencimento com moneyness perto de 1.0
        atm_candidates = [
            p for p in self.points
            if p.dte == dte and 0.98 < p.moneyness < 1.02
        ]

        if not atm_candidates:
            return None

        # Retorna IV médio entre CALL/PUT ATM
        return np.mean([p.iv for p in atm_candidates])

    def interpolate_iv(
        self,
        strike: float,
        dte: int
    ) -> Optional[float]:
        """Interpola IV para strike/DTE não cotados.

        Args:
            strike: Strike desejado
            dte: DTE desejado

        Returns:
            IV interpolada ou None se dados insuficientes
        """
        if len(self.points) < 3:
            return None  # Precisa mínimo 3 pontos

        strikes_arr = np.array([p.strike for p in self.points])
        dtes_arr = np.array([p.dte for p in self.points])
        ivs_arr = np.array([p.iv for p in self.points])

        # Verificar se todos os DTEs são iguais (interpolação 1D)
        if np.std(dtes_arr) < 0.1:
            # Todos no mesmo DTE, interpola só por strike
            if abs(np.max(strikes_arr) - np.min(strikes_arr)) < 1e-6:
                return None  # Todos strikes iguais também

            try:
                # Interpola 1D por strike
                iv_interp = np.interp(strike, np.sort(strikes_arr), ivs_arr[np.argsort(strikes_arr)])
                return float(iv_interp) if not np.isnan(iv_interp) else None
            except (ValueError, IndexError):
                return None

        # Interpolação 2D (strike × DTE)
        try:
            points = np.column_stack([strikes_arr, dtes_arr])
            iv_interp = griddata(
                points,
                ivs_arr,
                ([strike], [dte]),
                method='cubic'
            )
            return float(iv_interp[0]) if not np.isnan(iv_interp[0]) else None
        except (ValueError, IndexError):
            return None

    def detect_skew(self) -> SkewType:
        """Detecta padrão de volatilidade (skew ou smile).

        Returns:
            SkewType indicando o padrão detectado
        """
        # Agrupa por DTE
        by_dte = {}
        for p in self.points:
            if p.dte not in by_dte:
                by_dte[p.dte] = []
            by_dte[p.dte].append(p)

        # Analisa a DTE mais curta/próxima
        if not by_dte:
            return SkewType.FLAT

        closest_dte = min(by_dte.keys())
        points_at_dte = by_dte[closest_dte]

        # Coleta todos os IV por moneyness (ignora tipo, compara padrão geral)
        # moneyness = spot / strike, então:
        # moneyness > 1: strike < spot (OTM puts = strikes baixos)
        # moneyness < 1: strike > spot (OTM calls = strikes altos)
        otm_low = []  # strikes < spot (OTM puts, moneyness > 1.02)
        atm = []      # strikes perto de spot
        otm_high = []  # strikes > spot (OTM calls, moneyness < 0.98)

        for p in points_at_dte:
            if p.moneyness > 1.02:  # Strike < spot = OTM put
                otm_low.append(p.iv)
            elif p.moneyness < 0.98:  # Strike > spot = OTM call
                otm_high.append(p.iv)
            else:  # Perto de ATM
                atm.append(p.iv)

        if not otm_low or not otm_high:
            return SkewType.FLAT

        avg_otm_low = np.mean(otm_low)
        avg_otm_high = np.mean(otm_high)

        # Detecta padrão
        diff_pct = abs(avg_otm_high - avg_otm_low) / np.mean([avg_otm_high, avg_otm_low])

        if diff_pct < 0.05:  # Diferença <5%
            return SkewType.FLAT
        elif avg_otm_low > avg_otm_high:
            # Puts OTM têm IV mais alta que calls OTM = SKEW (padrão típico)
            return SkewType.SKEW
        else:
            # Calls OTM têm IV mais alta que puts OTM = REVERSE_SKEW
            return SkewType.REVERSE_SKEW

    def calculate_smile_strength(self) -> float:
        """Calcula força do padrão de smile.

        Smile: máxima convexidade de IV vs moneyness (OTM > ATM).

        Returns:
            Força normalizada (0.0-1.0)
        """
        # Agrupa por DTE
        by_dte = {}
        for p in self.points:
            if p.dte not in by_dte:
                by_dte[p.dte] = []
            by_dte[p.dte].append(p)

        if not by_dte:
            return 0.0

        # Usa DTE mais próxima
        closest_dte = min(by_dte.keys())
        points_at_dte = by_dte[closest_dte]

        # Separa por moneyness
        moneyness_vals = np.array([p.moneyness for p in points_at_dte])
        iv_vals = np.array([p.iv for p in points_at_dte])

        if len(moneyness_vals) < 3:
            return 0.0

        # Ordena por moneyness
        sorted_idx = np.argsort(moneyness_vals)
        moneyness_sorted = moneyness_vals[sorted_idx]
        iv_sorted = iv_vals[sorted_idx]

        # Calcula segunda derivada (convexidade)
        try:
            diffs = np.diff(iv_sorted, n=2)
            convexity = np.mean(np.abs(diffs)) / (np.mean(iv_sorted) or 1.0)
            # Normaliza a [0, 1]
            return min(convexity / 0.5, 1.0)
        except (IndexError, ZeroDivisionError):
            return 0.0

    def compute_metrics(
        self,
        historical_ivs: Optional[list[float]] = None
    ) -> SurfaceMetrics:
        """Computa métricas agregadas da superfície.

        Args:
            historical_ivs: Lista de IVs históricas (para cálculo de IV rank)

        Returns:
            SurfaceMetrics com análise completa
        """
        if self._cached_metrics:
            return self._cached_metrics

        # IV ATM
        atm = self.atm_iv(min([p.dte for p in self.points], default=30))
        atm_iv = atm or (np.mean([p.iv for p in self.points]) if self.points else 0.20)

        # IV Rank: percentil de IV atual em relação ao histórico
        if historical_ivs and len(historical_ivs) > 1:
            current_iv = np.mean([p.iv for p in self.points])
            # Calcula em que percentil a IV atual fica no histórico
            rank_pct = (sum(1 for iv in historical_ivs if iv <= current_iv) / len(historical_ivs))
            iv_rank = np.clip(rank_pct, 0.0, 1.0)
        else:
            iv_rank = 0.5  # Padrão se não houver histórico

        # Padrão e força de smile
        skew_type = self.detect_skew()
        smile_strength = self.calculate_smile_strength()

        # Term structure: compara IV curta vs longa
        short_term = self.atm_iv(min([p.dte for p in self.points if p.dte <= 30], default=30))
        long_term = self.atm_iv(max([p.dte for p in self.points if p.dte >= 60], default=60))

        if short_term and long_term:
            term_structure = "backwardation" if short_term > long_term else "contango"
        else:
            term_structure = "unknown"

        metrics = SurfaceMetrics(
            atm_iv=atm_iv,
            iv_rank=iv_rank,
            skew_type=skew_type,
            smile_strength=smile_strength,
            term_structure=term_structure
        )

        self._cached_metrics = metrics
        return metrics
