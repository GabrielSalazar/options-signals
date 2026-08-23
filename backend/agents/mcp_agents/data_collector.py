"""Agent 1: Data Collector — Coleta OHLC + indicadores.

Orquestração de fetch de dados históricos, cálculo de indicadores técnicos,
validação de qualidade, e formatação de saída.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any

import pandas as pd
import pandas_ta
import yfinance as yf

from backend.core.cache import cache_get, cache_set
from backend.agents.mcp_agents.base import MCPAgent
from backend.domain.mcp_models import DataCollectorInput

logger = logging.getLogger("data_collector")


class DataCollectorAgent(MCPAgent):
    """Agent 1: Coleta dados OHLC + indicadores para B3.

    Pipeline:
    1. Fetch OHLC via yfinance (com cache 1h)
    2. Calcula indicadores (RSI, MACD, ATR, Bollinger Bands)
    3. Valida qualidade
    4. Retorna DataCollectorOutput
    """

    def __init__(self):
        """Inicializa agente com cache e timeout."""
        self.logger = logger
        self.cache_ttl_success = 3600  # 1 hora para histórico
        self.cache_ttl_error = 60  # 1 min para erros
        self.timeout = 10  # segundos

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa entrada e retorna dados OHLC + indicadores.

        Args:
            input_data: Dict com strategy, asset, date_range, indicators

        Returns:
            Dict com ohlc, indicators, meta
        """
        # Validar entrada
        try:
            cfg = DataCollectorInput(**input_data)
        except Exception as e:
            self.logger.error(f"Input validation error: {e}")
            raise ValueError(f"Invalid input: {e}")

        self.logger.info(
            f"Processing {cfg.asset} for {cfg.strategy} "
            f"({cfg.date_range['start']} to {cfg.date_range['end']})"
        )

        loop = asyncio.get_event_loop()

        # 1. Fetch OHLC (async via executor)
        try:
            df_ohlc = await loop.run_in_executor(
                None,
                self._fetch_ohlc_sync,
                cfg.asset,
                cfg.date_range["start"],
                cfg.date_range["end"],
                cfg.data_source,
            )
        except Exception as e:
            self.logger.error(f"Fetch OHLC failed: {e}")
            raise

        if df_ohlc is None or df_ohlc.empty:
            self.logger.warning(f"No OHLC data for {cfg.asset}")
            raise ValueError(f"No data available for {cfg.asset}")

        # 2. Calcular indicadores
        try:
            indicators_dict = await loop.run_in_executor(
                None,
                self._calculate_indicators_sync,
                df_ohlc,
                cfg.indicators,
            )
        except Exception as e:
            self.logger.error(f"Indicator calculation failed: {e}")
            raise

        # 3. Validar qualidade
        quality_score = self._validate_quality(df_ohlc, indicators_dict)
        self.logger.info(f"Data quality score: {quality_score:.2%}")

        # 4. Converter para DTOs
        ohlc_list = [
            {
                "date": idx.strftime("%Y-%m-%d"),
                "o": float(row["Open"]),
                "h": float(row["High"]),
                "l": float(row["Low"]),
                "c": float(row["Close"]),
                "v": int(row["Volume"]),
            }
            for idx, row in df_ohlc.iterrows()
        ]

        # 5. Retornar output
        output = {
            "ohlc": ohlc_list,
            "indicators": indicators_dict,
            "meta": {
                "asset": cfg.asset,
                "source": cfg.data_source,
                "records_count": len(df_ohlc),
                "gaps_detected": self._count_gaps(df_ohlc),
                "data_quality_score": quality_score,
                "timestamp": datetime.now().isoformat(),
            },
        }

        self.logger.info(f"✅ Collected {len(ohlc_list)} candles for {cfg.asset}")
        return output

    # ─────────────────────────────────────────────────────────────────────────
    # SYNC METHODS (for executor)
    # ─────────────────────────────────────────────────────────────────────────

    def _fetch_ohlc_sync(
        self, asset: str, start: str, end: str, source: str
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLC com cache.

        Args:
            asset: Ticker (ex: PETR4)
            start: Data inicial (YYYY-MM-DD)
            end: Data final (YYYY-MM-DD)
            source: Fonte (yfinance ou brapi)

        Returns:
            DataFrame com OHLC ou None
        """
        cache_key = f"ohlc:{asset}:{start}:{end}"

        # Try cache
        cached = cache_get(cache_key)
        if cached is not None:
            self.logger.debug(f"Cache hit for {asset} OHLC")
            if cached:
                df = pd.DataFrame(cached)
                if "Date" in df.columns:
                    df["Date"] = pd.to_datetime(df["Date"])
                    df.set_index("Date", inplace=True)
                return df
            return None

        try:
            # Fetch via yfinance
            self.logger.debug(f"Fetching {asset} from yfinance ({start} to {end})")
            ticker = yf.Ticker(f"{asset}.SA")
            df = ticker.history(start=start, end=end)

            if df is None or df.empty:
                self.logger.warning(f"No data from yfinance for {asset}")
                cache_set(cache_key, None, ttl=self.cache_ttl_error)
                return None

            # Normalize columns
            df = df[["Open", "High", "Low", "Close", "Volume"]]
            df = df.astype({"Volume": int})
            df = df.dropna()

            if df.empty:
                self.logger.warning(f"DataFrame empty after cleanup for {asset}")
                cache_set(cache_key, None, ttl=self.cache_ttl_error)
                return None

            # Cache success
            cache_set(
                cache_key,
                df.reset_index().to_dict(orient="records"),
                ttl=self.cache_ttl_success,
            )

            self.logger.info(f"Fetched {len(df)} candles for {asset}")
            return df

        except Exception as e:
            self.logger.error(f"yfinance error for {asset}: {e}")
            cache_set(cache_key, None, ttl=self.cache_ttl_error)
            return None

    def _calculate_indicators_sync(
        self, df: pd.DataFrame, indicators: List[str]
    ) -> Dict[str, Any]:
        """Calcula indicadores com pandas_ta.

        Args:
            df: DataFrame com OHLC
            indicators: Lista de indicadores (rsi, macd, atr, bb)

        Returns:
            Dict com indicadores calculados
        """
        indicators_dict = {}

        try:
            # RSI
            if "rsi" in indicators:
                rsi = df.ta.rsi(length=14, close="Close")
                indicators_dict["rsi"] = rsi.dropna().tolist()

            # MACD
            if "macd" in indicators:
                macd = df.ta.macd(fast=12, slow=26, signal=9, close="Close")
                if macd is not None and not macd.empty:
                    indicators_dict["macd"] = {
                        "line": macd.iloc[:, 0].dropna().tolist(),
                        "signal": macd.iloc[:, 1].dropna().tolist(),
                        "histogram": macd.iloc[:, 2].dropna().tolist(),
                    }

            # ATR
            if "atr" in indicators:
                atr = df.ta.atr(high="High", low="Low", close="Close", length=14)
                if atr is not None:
                    indicators_dict["atr"] = atr.dropna().tolist()

            # Bollinger Bands
            if "bb" in indicators:
                bb = df.ta.bbands(close="Close", length=20, std=2.0)
                if bb is not None and not bb.empty:
                    indicators_dict["bb"] = {
                        "upper": bb.iloc[:, 0].dropna().tolist(),
                        "middle": bb.iloc[:, 1].dropna().tolist(),
                        "lower": bb.iloc[:, 2].dropna().tolist(),
                    }

            self.logger.debug(
                f"Calculated indicators: {list(indicators_dict.keys())}"
            )
            return indicators_dict

        except Exception as e:
            self.logger.error(f"Indicator calculation error: {e}")
            self.logger.debug(f"df columns: {df.columns.tolist()}, df shape: {df.shape}")
            return {}

    # ─────────────────────────────────────────────────────────────────────────
    # VALIDATION
    # ─────────────────────────────────────────────────────────────────────────

    def _validate_quality(self, df: pd.DataFrame, indicators: Dict) -> float:
        """Valida qualidade dos dados (0.0-1.0).

        Args:
            df: DataFrame com OHLC
            indicators: Dict com indicadores

        Returns:
            Score de qualidade (0.0-1.0)
        """
        score = 1.0

        # Verificar gaps
        expected_days = (df.index[-1] - df.index[0]).days
        actual_days = len(df)
        gaps = expected_days - actual_days

        if gaps > 0 and expected_days > 0:
            gap_ratio = gaps / expected_days
            score -= gap_ratio * 0.2  # até -20% por gaps

        # Verificar NaNs em indicadores
        total_indicators = len(indicators)
        if total_indicators > 0:
            valid_indicators = sum(
                1
                for v in indicators.values()
                if v is not None
                and (
                    (isinstance(v, list) and len(v) > 0)
                    or (isinstance(v, dict) and len(v) > 0)
                )
            )
            if valid_indicators < total_indicators:
                score -= (total_indicators - valid_indicators) * 0.1

        # Garantir 0.0-1.0
        return max(0.0, min(1.0, score))

    def _count_gaps(self, df: pd.DataFrame) -> int:
        """Conta gaps (dias faltando) no histórico.

        Args:
            df: DataFrame com OHLC

        Returns:
            Número de gaps encontrados
        """
        if len(df) < 2:
            return 0
        expected = (df.index[-1] - df.index[0]).days
        actual = len(df)
        return expected - actual
