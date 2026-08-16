"""Prometheus metrics for observability."""
from prometheus_client import Counter, Histogram, Gauge
from typing import Optional

# Counters
signals_generated_total = Counter(
    "signals_generated_total",
    "Total signals generated",
    ["ticker", "tipo_sinal"],
)

scan_errors_total = Counter(
    "scan_errors_total",
    "Total scan errors",
    ["error_type"],
)

# Histograms (latency in seconds)
scan_latency_seconds = Histogram(
    "scan_latency_seconds",
    "Scan endpoint latency",
    buckets=(0.05, 0.1, 0.2, 0.5, 1.0, 2.0),
)

analytics_latency_seconds = Histogram(
    "analytics_latency_seconds",
    "Analytics endpoint latency",
    buckets=(0.05, 0.1, 0.2, 0.5, 1.0),
)

backtest_latency_seconds = Histogram(
    "backtest_latency_seconds",
    "Backtest endpoint latency",
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0),
)

# Gauges
cache_hit_ratio = Gauge(
    "cache_hit_ratio",
    "Cache hit ratio (0.0 to 1.0)",
)

cooldown_active_count = Gauge(
    "cooldown_active_count",
    "Number of active cooldowns",
)

db_connection_pool_size = Gauge(
    "db_connection_pool_size",
    "Database connection pool size",
)


def record_signal_generated(ticker: str, tipo_sinal: str) -> None:
    """Record signal generation event."""
    signals_generated_total.labels(ticker=ticker, tipo_sinal=tipo_sinal).inc()


def record_scan_error(error_type: str) -> None:
    """Record scan error."""
    scan_errors_total.labels(error_type=error_type).inc()


def set_cache_hit_ratio(ratio: float) -> None:
    """Set cache hit ratio (0.0 to 1.0)."""
    cache_hit_ratio.set(max(0.0, min(1.0, ratio)))


def set_cooldown_count(count: int) -> None:
    """Set number of active cooldowns."""
    cooldown_active_count.set(max(0, count))


def set_connection_pool_size(size: int) -> None:
    """Set database connection pool size."""
    db_connection_pool_size.set(max(0, size))
