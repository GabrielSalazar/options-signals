"""Tests for DataLoader service."""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from backend.services.data_loader import DataLoader


class TestDataLoaderInitialization:
    """Test DataLoader initialization."""

    def test_init_default(self):
        """Initialize with defaults."""
        loader = DataLoader()
        assert loader.max_retries == 3
        assert loader.backoff_factor == 2.0

    def test_init_custom(self):
        """Initialize with custom values."""
        loader = DataLoader(max_retries=5, backoff_factor=1.5)
        assert loader.max_retries == 5
        assert loader.backoff_factor == 1.5


class TestDataLoaderUsesProvidedData:
    """Test using pre-loaded dataframe."""

    def test_returns_provided_dataframe(self):
        """Should return provided dataframe without fetching."""
        loader = DataLoader()
        df_input = pd.DataFrame({
            "Open": [10.0, 11.0],
            "High": [11.0, 12.0],
            "Low": [9.0, 10.0],
            "Close": [10.5, 11.5],
            "Volume": [1000, 1100],
        })

        result = loader.load_ohlcv("PETR4", df_provided=df_input)

        assert result is df_input
        assert len(result) == 2


class TestDataLoaderCaching:
    """Test caching behavior."""

    @patch("backend.services.data_loader.cache_get_df")
    @patch("backend.services.data_loader.cache_set_df")
    @patch("backend.services.data_loader.yf.download")
    def test_cache_hit_returns_cached(self, mock_yf, mock_set, mock_get):
        """Return cached dataframe on cache hit."""
        loader = DataLoader()
        df_cached = pd.DataFrame({
            "Close": [10.0, 11.0],
            "Volume": [1000, 1100],
        })
        mock_get.return_value = df_cached

        result = loader.load_ohlcv("PETR4", "1d")

        assert result is df_cached
        mock_yf.download.assert_not_called()  # Should not fetch

    @patch("backend.services.data_loader.cache_get_df")
    @patch("backend.services.data_loader.cache_set_df")
    @patch("backend.services.data_loader.yf.download")
    def test_cache_miss_fetches_and_caches(self, mock_yf, mock_set, mock_get):
        """Fetch and cache on cache miss."""
        loader = DataLoader()
        mock_get.return_value = None  # Cache miss
        df_fetched = pd.DataFrame({
            "Close": [10.0, 11.0],
            "Volume": [1000, 1100],
        })
        mock_yf.return_value = df_fetched

        result = loader.load_ohlcv("PETR4", "1d")

        assert result is df_fetched
        mock_yf.assert_called_once()
        mock_set.assert_called_once()  # Should cache


class TestDataLoaderYFinance:
    """Test yfinance fetching."""

    @patch("backend.services.data_loader.yf.download")
    def test_fetch_success(self, mock_yf):
        """Successfully fetch from yfinance."""
        loader = DataLoader()
        df_expected = pd.DataFrame({
            "Close": [10.0, 11.0, 12.0],
            "Volume": [1000, 1100, 1200],
        })
        mock_yf.return_value = df_expected

        with patch("backend.services.data_loader.cache_get_df", return_value=None):
            with patch("backend.services.data_loader.cache_set_df"):
                result = loader.load_ohlcv("PETR4", "1d", verbose=False)

        assert result is df_expected
        mock_yf.assert_called_once()

    @patch("backend.services.data_loader.yf.download")
    def test_fetch_empty_dataframe(self, mock_yf):
        """Return None for empty dataframe."""
        loader = DataLoader()
        mock_yf.return_value = pd.DataFrame()  # Empty

        with patch("backend.services.data_loader.cache_get_df", return_value=None):
            with patch("backend.services.data_loader.cache_set_df"):
                result = loader.load_ohlcv("INVALID", "1d", verbose=False)

        assert result is None

    @patch("backend.services.data_loader.yf.download")
    def test_fetch_with_retry(self, mock_yf):
        """Retry on failure."""
        loader = DataLoader(max_retries=3)
        df_success = pd.DataFrame({"Close": [10.0]})

        # Fail twice, succeed third time
        mock_yf.side_effect = [
            Exception("Network error"),
            pd.DataFrame(),  # Empty
            df_success,  # Success
        ]

        with patch("backend.services.data_loader.cache_get_df", return_value=None):
            with patch("backend.services.data_loader.cache_set_df"):
                result = loader.load_ohlcv("PETR4", "1d", verbose=False)

        assert result is df_success
        assert mock_yf.call_count == 3  # Retried 3 times

    @patch("backend.services.data_loader.yf.download")
    def test_max_retries_exhausted(self, mock_yf):
        """Return None after max retries exhausted."""
        loader = DataLoader(max_retries=2)
        mock_yf.side_effect = Exception("Network error")

        with patch("backend.services.data_loader.cache_get_df", return_value=None):
            with patch("backend.services.data_loader.cache_set_df"):
                result = loader.load_ohlcv("PETR4", "1d", verbose=False)

        assert result is None
        assert mock_yf.call_count == 2


class TestDataLoaderTicker:
    """Test ticker format handling."""

    @patch("backend.services.data_loader.yf.download")
    def test_ticker_with_sa_suffix(self, mock_yf):
        """Handle ticker with .SA suffix."""
        loader = DataLoader()
        mock_yf.return_value = pd.DataFrame({"Close": [10.0]})

        with patch("backend.services.data_loader.cache_get_df", return_value=None):
            with patch("backend.services.data_loader.cache_set_df"):
                loader.load_ohlcv("PETR4.SA", "1d", verbose=False)

        # Check first positional argument (ticker)
        call_args = mock_yf.call_args[0]
        assert "PETR4.SA" in call_args[0]

    @patch("backend.services.data_loader.yf.download")
    def test_ticker_without_sa_suffix(self, mock_yf):
        """Add .SA suffix to ticker."""
        loader = DataLoader()
        mock_yf.return_value = pd.DataFrame({"Close": [10.0]})

        with patch("backend.services.data_loader.cache_get_df", return_value=None):
            with patch("backend.services.data_loader.cache_set_df"):
                loader.load_ohlcv("PETR4", "1d", verbose=False)

        # Check first positional argument (ticker)
        call_args = mock_yf.call_args[0]
        assert "PETR4.SA" in call_args[0]


class TestDataLoaderIntervals:
    """Test interval to period conversion."""

    @patch("backend.services.data_loader.yf.download")
    def test_interval_1d(self, mock_yf):
        """1d interval uses 2y period."""
        loader = DataLoader()
        mock_yf.return_value = pd.DataFrame({"Close": [10.0]})

        with patch("backend.services.data_loader.cache_get_df", return_value=None):
            with patch("backend.services.data_loader.cache_set_df"):
                loader.load_ohlcv("PETR4", "1d", verbose=False)

        call_args = mock_yf.call_args
        assert call_args[1]["period"] == "2y"

    @patch("backend.services.data_loader.yf.download")
    def test_interval_1h(self, mock_yf):
        """1h interval uses 1y period."""
        loader = DataLoader()
        mock_yf.return_value = pd.DataFrame({"Close": [10.0]})

        with patch("backend.services.data_loader.cache_get_df", return_value=None):
            with patch("backend.services.data_loader.cache_set_df"):
                loader.load_ohlcv("PETR4", "1h", verbose=False)

        call_args = mock_yf.call_args
        assert call_args[1]["period"] == "1y"

    @patch("backend.services.data_loader.yf.download")
    def test_interval_5m(self, mock_yf):
        """5m interval uses 60d period."""
        loader = DataLoader()
        mock_yf.return_value = pd.DataFrame({"Close": [10.0]})

        with patch("backend.services.data_loader.cache_get_df", return_value=None):
            with patch("backend.services.data_loader.cache_set_df"):
                loader.load_ohlcv("PETR4", "5m", verbose=False)

        call_args = mock_yf.call_args
        assert call_args[1]["period"] == "60d"
