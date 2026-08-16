"""Gatilho (trigger) evaluation service."""
import logging
from typing import Optional

import pandas as pd

from backend.core.constants import (
    ADX_GATILHO_MIN,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    STOCH_OVERBOUGHT,
    STOCH_OVERSOLD,
)

logger = logging.getLogger("gatilho_evaluator")


class GatilhoEvaluator:
    """Evaluate technical triggers for trading signals."""

    def evaluate(
        self,
        df: pd.DataFrame,
        ultimo: dict,
        penult: dict,
        preco: float,
        vol_med: float,
        volume: float,
    ) -> dict:
        """Evaluate all triggers (ALTA/BAIXA).

        Returns dict with:
        - sinais_alta, sinais_baixa: trigger lists
        - ids_alta, ids_baixa: trigger IDs
        - score_alta, score_baixa: scores
        - stoch_k, rsi, vol_ratio: scalars for downstream
        """
        sinais_alta = sinais_baixa = []
        ids_alta = ids_baixa = []
        score_alta = score_baixa = 0

        # Extract indicators
        stoch_k = float(ultimo.get("stoch_k", 50))
        stoch_k_prev = float(penult.get("stoch_k", 50))
        rsi = float(ultimo.get("rsi", 50))
        ema9 = float(ultimo.get("ema9", preco))
        ema21 = float(ultimo.get("ema21", preco))
        ema9_prev = float(penult.get("ema9", ema9))
        ema21_prev = float(penult.get("ema21", ema21))
        macd_d = float(ultimo.get("macd_diff", 0))
        macd_d_prev = float(penult.get("macd_diff", 0))
        atr = float(ultimo.get("atr", preco * 0.02))
        sup20 = float(penult.get("suporte_20", preco))
        res20 = float(penult.get("resistencia_20", preco))
        vol_ratio = volume / vol_med if vol_med > 0 else 1.0
        adx = float(ultimo.get("adx", 0))

        # ALTA triggers (Buy)
        if rsi < RSI_OVERSOLD:
            sinais_alta.append("RSI Oversold")
            ids_alta.append("G1")
            score_alta += 15

        if stoch_k < STOCH_OVERSOLD and stoch_k > stoch_k_prev:
            sinais_alta.append("Stoch Oversold + cross")
            ids_alta.append("G2")
            score_alta += 15

        if preco < sup20:
            sinais_alta.append("Price < Support20")
            ids_alta.append("G3")
            score_alta += 10

        if ema9 > ema21 and ema9_prev <= ema21_prev:
            sinais_alta.append("EMA9 > EMA21 crossover")
            ids_alta.append("G4")
            score_alta += 15

        if macd_d > 0 and macd_d_prev <= 0:
            sinais_alta.append("MACD positive cross")
            ids_alta.append("G5")
            score_alta += 10

        if vol_ratio > 1.5:
            sinais_alta.append("Volume spike")
            ids_alta.append("G6")
            score_alta += 5

        if adx >= ADX_GATILHO_MIN:
            sinais_alta.append(f"ADX strong ({adx:.1f})")
            ids_alta.append("G7")
            score_alta += 10

        # BAIXA triggers (Sell)
        if rsi > RSI_OVERBOUGHT:
            sinais_baixa.append("RSI Overbought")
            ids_baixa.append("B1")
            score_baixa += 15

        if stoch_k > STOCH_OVERBOUGHT and stoch_k < stoch_k_prev:
            sinais_baixa.append("Stoch Overbought + cross")
            ids_baixa.append("B2")
            score_baixa += 15

        if preco > res20:
            sinais_baixa.append("Price > Resistance20")
            ids_baixa.append("B3")
            score_baixa += 10

        if ema9 < ema21 and ema9_prev >= ema21_prev:
            sinais_baixa.append("EMA9 < EMA21 crossover")
            ids_baixa.append("B4")
            score_baixa += 15

        if macd_d < 0 and macd_d_prev >= 0:
            sinais_baixa.append("MACD negative cross")
            ids_baixa.append("B5")
            score_baixa += 10

        if vol_ratio > 1.5:
            sinais_baixa.append("Volume spike")
            ids_baixa.append("B6")
            score_baixa += 5

        if adx >= ADX_GATILHO_MIN:
            sinais_baixa.append(f"ADX strong ({adx:.1f})")
            ids_baixa.append("B7")
            score_baixa += 10

        return {
            "sinais_alta": sinais_alta,
            "sinais_baixa": sinais_baixa,
            "ids_alta": ids_alta,
            "ids_baixa": ids_baixa,
            "score_alta": min(score_alta, 100),
            "score_baixa": min(score_baixa, 100),
            "stoch_k": stoch_k,
            "rsi": rsi,
            "vol_ratio": vol_ratio,
        }

    def evaluate_v2(self, df: pd.DataFrame, ultimo: dict, stoch_k: float, rsi: float, preco: float) -> dict:
        """V2 trigger evaluation (simplified)."""
        # Placeholder for V2 logic
        return {
            "gatilhos_v2": [],
            "gatilhos_v2_ids": [],
            "score_v2": 0,
        }
