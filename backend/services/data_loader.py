"""Data loading service — OHLCV fetching, caching, and preparation."""
import logging
import time
from typing import Optional

import pandas as pd
import yfinance as yf

from backend.core.cache import cache_get_df, cache_set_df

logger = logging.getLogger("data_loader")


class DataLoader:
    """Load and cache OHLCV data from multiple sources."""

    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        """Initialize DataLoader.

        Args:
            max_retries: Maximum retry attempts for yfinance
            backoff_factor: Exponential backoff multiplier
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def load_ohlcv(
        self,
        ticker: str,
        interval: str = "1d",
        df_provided: Optional[pd.DataFrame] = None,
        indicators_calculated: bool = False,
        verbose: bool = False,
    ) -> Optional[pd.DataFrame]:
        """Load OHLCV data with caching.

        Args:
            ticker: Stock ticker (PETR4.SA format)
            interval: Candle interval (1d, 1h, 5m, etc)
            df_provided: Pre-loaded dataframe (skip fetching)
            indicators_calculated: Whether indicators already computed
            verbose: Log debug info

        Returns:
            OHLCV dataframe or None if fetch failed
        """
        if df_provided is not None:
            if verbose:
                logger.info(f"Using provided dataframe for {ticker}")
            return df_provided

        # Try cache first
        cache_key = f"{ticker}_{interval}"
        cached_df = cache_get_df(cache_key)

        if cached_df is not None and len(cached_df) > 0:
            if verbose:
                logger.info(f"Cache hit for {ticker}_{interval}: {len(cached_df)} rows")
            return cached_df

        # Fetch fresh data
        if verbose:
            logger.info(f"Fetching {ticker} {interval} from yfinance")

        df = self._fetch_yfinance_with_retry(ticker, interval, verbose)

        if df is None or len(df) == 0:
            logger.warning(f"Failed to fetch {ticker} after {self.max_retries} retries")
            return None

        # Cache result
        cache_set_df(cache_key, df)

        return df

    def _fetch_yfinance_with_retry(
        self, ticker: str, interval: str, verbose: bool
    ) -> Optional[pd.DataFrame]:
        """Fetch from yfinance with exponential backoff retry.

        Args:
            ticker: Stock ticker
            interval: Candle interval
            verbose: Log debug info

        Returns:
            OHLCV dataframe or None if all retries failed
        """
        yf_ticker = ticker if ticker.endswith(".SA") else f"{ticker}.SA"
        period = self._interval_to_period(interval)

        for attempt in range(self.max_retries):
            try:
                if verbose:
                    logger.debug(
                        f"yfinance attempt {attempt + 1}/{self.max_retries} for {ticker}"
                    )

                df = yf.download(
                    yf_ticker,
                    period=period,
                    interval=interval,
                    auto_adjust=True,
                    progress=False,
                )

                if df is not None and not df.empty:
                    if verbose:
                        logger.info(f"Successfully fetched {len(df)} rows for {ticker}")
                    return df

                if verbose:
                    logger.warning(f"Empty dataframe for {ticker} on attempt {attempt + 1}")

                # Exponential backoff before retry
                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_factor ** attempt
                    time.sleep(wait_time)

            except Exception as e:
                logger.warning(
                    f"yfinance error for {ticker} attempt {attempt + 1}: {e}"
                )

                # Backoff before retry
                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_factor ** attempt
                    time.sleep(wait_time)

        return None

    @staticmethod
    def _interval_to_period(interval: str) -> str:
        """Convert interval to yfinance period.

        Args:
            interval: Candle interval (1d, 1h, 5m, etc)

        Returns:
            Period string for yfinance
        """
        mapping = {
            "1d": "2y",  # 2 years of daily data
            "1h": "1y",  # 1 year of hourly data
            "5m": "60d",  # 60 days of 5min data
            "15m": "60d",
            "1mo": "5y",  # 5 years monthly
        }
        return mapping.get(interval, "1y")
