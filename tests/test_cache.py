"""
Testes unitários para o módulo cache.py.

Cobre:
  - redis_status retorna dict válido
  - cache_get de chave inexistente retorna None
  - cache_get_df de chave inexistente retorna None

Nota: Sem Redis rodando, cache_set/cache_get retornam None.
      Os testes verificam o comportamento graceful nesse cenário.
"""
import pytest
from cache import cache_get, cache_set, cache_get_df, cache_set_df, redis_status


class TestRedisStatus:
    """Testa redis_status (deve funcionar mesmo sem Redis)."""

    def test_returns_dict(self):
        status = redis_status()
        assert isinstance(status, dict)
        assert "status" in status

    def test_status_value_valid(self):
        status = redis_status()
        assert status["status"] in ("connected", "disabled", "error")


class TestCacheGracefulDegradation:
    """Testa que o cache degrada graciosamente sem Redis."""

    def test_get_missing_key_returns_none(self):
        result = cache_get("absolutely_nonexistent_key_123")
        assert result is None

    def test_get_df_missing_key_returns_none(self):
        result = cache_get_df("absolutely_nonexistent_df_key_123")
        assert result is None

    def test_set_does_not_raise(self):
        """cache_set não deve lançar exceção mesmo sem Redis."""
        try:
            cache_set("test_no_crash", {"a": 1}, ttl=60)
        except Exception as e:
            pytest.fail(f"cache_set levantou exceção: {e}")

    def test_set_df_does_not_raise(self):
        """cache_set_df não deve lançar exceção mesmo sem Redis."""
        import pandas as pd
        df = pd.DataFrame({"A": [1, 2, 3]})
        try:
            cache_set_df("test_df_no_crash", df, ttl=60)
        except Exception as e:
            pytest.fail(f"cache_set_df levantou exceção: {e}")
