"""Tests for Prometheus metrics."""
import pytest
from unittest.mock import patch, MagicMock

from backend.core import metrics


class TestMetricsRecording:
    """Test metrics recording functions."""

    def test_record_signal_generated(self):
        """Should increment signals_generated_total counter."""
        with patch.object(
            metrics.signals_generated_total, "labels"
        ) as mock_labels:
            mock_labels.return_value.inc = MagicMock()
            metrics.record_signal_generated("PETR4", "CALL_ALTA")
            mock_labels.assert_called_once_with(
                ticker="PETR4", tipo_sinal="CALL_ALTA"
            )

    def test_record_scan_error(self):
        """Should increment scan_errors_total counter."""
        with patch.object(metrics.scan_errors_total, "labels") as mock_labels:
            mock_labels.return_value.inc = MagicMock()
            metrics.record_scan_error("yfinance_timeout")
            mock_labels.assert_called_once_with(error_type="yfinance_timeout")

    def test_set_cache_hit_ratio_valid_range(self):
        """Cache hit ratio should accept valid 0.0-1.0 range."""
        with patch.object(metrics.cache_hit_ratio, "set") as mock_set:
            metrics.set_cache_hit_ratio(0.75)
            mock_set.assert_called_once_with(0.75)

    def test_set_cache_hit_ratio_clamps_negative(self):
        """Negative cache hit ratio should clamp to 0.0."""
        with patch.object(metrics.cache_hit_ratio, "set") as mock_set:
            metrics.set_cache_hit_ratio(-0.5)
            mock_set.assert_called_once_with(0.0)

    def test_set_cache_hit_ratio_clamps_over_one(self):
        """Cache hit ratio > 1.0 should clamp to 1.0."""
        with patch.object(metrics.cache_hit_ratio, "set") as mock_set:
            metrics.set_cache_hit_ratio(1.5)
            mock_set.assert_called_once_with(1.0)

    def test_set_cooldown_count(self):
        """Should set cooldown_active_count gauge."""
        with patch.object(metrics.cooldown_active_count, "set") as mock_set:
            metrics.set_cooldown_count(5)
            mock_set.assert_called_once_with(5)

    def test_set_cooldown_count_negative_clamps_to_zero(self):
        """Negative cooldown count should clamp to 0."""
        with patch.object(metrics.cooldown_active_count, "set") as mock_set:
            metrics.set_cooldown_count(-1)
            mock_set.assert_called_once_with(0)

    def test_set_connection_pool_size(self):
        """Should set db_connection_pool_size gauge."""
        with patch.object(metrics.db_connection_pool_size, "set") as mock_set:
            metrics.set_connection_pool_size(10)
            mock_set.assert_called_once_with(10)


class TestMetricsExist:
    """Test that metric objects are properly defined."""

    def test_counters_exist(self):
        """Should have counter metrics."""
        assert metrics.signals_generated_total is not None
        assert metrics.scan_errors_total is not None

    def test_histograms_exist(self):
        """Should have histogram metrics."""
        assert metrics.scan_latency_seconds is not None
        assert metrics.analytics_latency_seconds is not None
        assert metrics.backtest_latency_seconds is not None

    def test_gauges_exist(self):
        """Should have gauge metrics."""
        assert metrics.cache_hit_ratio is not None
        assert metrics.cooldown_active_count is not None
        assert metrics.db_connection_pool_size is not None
