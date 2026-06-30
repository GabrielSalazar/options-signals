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
from backend.core.cache import cache_get, cache_set, cache_get_df, cache_set_df, redis_status


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


class TestInMemoryFallback:
    """Sem Redis, o cache usa um store TTL em memória (não mais no-op). [P0]"""

    def setup_method(self):
        from backend.core import cache
        cache._mem.clear()

    def test_set_get_roundtrip_sem_redis(self, monkeypatch):
        from backend.core import cache
        monkeypatch.setattr(cache, "_get_redis", lambda: None)
        cache.cache_set("k1", {"a": 1}, ttl=60)
        assert cache.cache_get("k1") == {"a": 1}

    def test_df_roundtrip_sem_redis(self, monkeypatch):
        import pandas as pd
        from backend.core import cache
        monkeypatch.setattr(cache, "_get_redis", lambda: None)
        df = pd.DataFrame({"A": [1, 2, 3]})
        cache.cache_set_df("df1", df, ttl=60)
        out = cache.cache_get_df("df1")
        assert out is not None
        pd.testing.assert_frame_equal(out, df)

    def test_ttl_expira(self, monkeypatch):
        from backend.core import cache
        monkeypatch.setattr(cache, "_get_redis", lambda: None)
        t = {"now": 1000.0}
        monkeypatch.setattr(cache.time, "time", lambda: t["now"])
        cache.cache_set("k2", "v", ttl=10)
        assert cache.cache_get("k2") == "v"
        t["now"] = 1011.0  # passou do TTL
        assert cache.cache_get("k2") is None

    def test_df_get_retorna_copia(self, monkeypatch):
        import pandas as pd
        from backend.core import cache
        monkeypatch.setattr(cache, "_get_redis", lambda: None)
        df = pd.DataFrame({"A": [1, 2, 3]})
        cache.cache_set_df("df2", df, ttl=60)
        out = cache.cache_get_df("df2")
        out.loc[0, "A"] = 999
        assert cache.cache_get_df("df2").loc[0, "A"] == 1  # store não mutado

    def test_mem_set_faz_prune_de_expirados_ao_exceder_max(self, monkeypatch):
        """Quando _mem atinge _MEM_MAX, entradas expiradas são removidas antes de inserir a nova."""
        from backend.core import cache
        monkeypatch.setattr(cache, "_get_redis", lambda: None)
        monkeypatch.setattr(cache, "_MEM_MAX", 3)
        t = {"now": 1000.0}
        monkeypatch.setattr(cache.time, "time", lambda: t["now"])

        # Duas chaves com TTL curto (vão expirar) e uma chave viva.
        cache.cache_set("exp1", "v1", ttl=5)
        cache.cache_set("exp2", "v2", ttl=5)
        cache.cache_set("viva", "v3", ttl=1000)
        assert len(cache._mem) == 3

        # Avança o tempo para expirar exp1/exp2, mas não "viva".
        t["now"] = 1010.0
        # Inserir uma 4a chave dispara o prune (len >= _MEM_MAX).
        cache.cache_set("nova", "v4", ttl=1000)

        assert "exp1" not in cache._mem
        assert "exp2" not in cache._mem
        assert "viva" in cache._mem
        assert "nova" in cache._mem


class TestGetRedisConnectFlow:
    """Testa o fluxo de conexão lazy do cliente Redis (_get_redis)."""

    def setup_method(self):
        from backend.core import cache
        cache._client = None
        cache._unavailable = False

    def teardown_method(self):
        from backend.core import cache
        cache._client = None
        cache._unavailable = False

    def test_unavailable_flag_curto_circuita_sem_tentar_conectar(self, monkeypatch):
        from backend.core import cache
        cache._unavailable = True
        chamado = {"sim": False}

        def fake_redis_module():
            chamado["sim"] = True
            raise AssertionError("não deveria tentar importar redis quando _unavailable=True")

        monkeypatch.setattr(cache, "_get_redis", cache._get_redis)  # no-op, mantém função real
        result = cache._get_redis()
        assert result is None
        assert chamado["sim"] is False

    def test_client_ja_conectado_e_reutilizado(self, monkeypatch):
        from backend.core import cache
        fake_client = object()
        cache._client = fake_client
        cache._unavailable = False
        assert cache._get_redis() is fake_client

    def test_conexao_falha_marca_unavailable(self, monkeypatch):
        """Se redis.from_url/ping lançar, _get_redis retorna None e marca _unavailable."""
        from backend.core import cache
        import sys
        import types

        fake_redis_mod = types.ModuleType("redis")

        def from_url(*a, **kw):
            class _R:
                def ping(self):
                    raise ConnectionError("sem conexão")
            return _R()

        fake_redis_mod.from_url = from_url
        monkeypatch.setitem(sys.modules, "redis", fake_redis_mod)

        result = cache._get_redis()
        assert result is None
        assert cache._unavailable is True

    def test_conexao_sucesso_retorna_client_e_armazena(self, monkeypatch):
        """Se ping() funcionar, _get_redis retorna o client e o guarda em _client."""
        from backend.core import cache
        import sys
        import types

        class _FakeClient:
            def ping(self):
                return True

        fake_client = _FakeClient()
        fake_redis_mod = types.ModuleType("redis")
        fake_redis_mod.from_url = lambda *a, **kw: fake_client
        monkeypatch.setitem(sys.modules, "redis", fake_redis_mod)

        result = cache._get_redis()
        assert result is fake_client
        assert cache._client is fake_client
        # Segunda chamada reusa o client cacheado (não invoca from_url de novo).
        monkeypatch.setattr(fake_redis_mod, "from_url",
                             lambda *a, **kw: (_ for _ in ()).throw(AssertionError("não deveria reconectar")))
        assert cache._get_redis() is fake_client


class TestCacheComRedisMockado:
    """Exercita os caminhos de cache_get/cache_set/cache_get_df/cache_set_df quando há um client Redis."""

    def test_cache_get_hit_deserializa_json(self, monkeypatch):
        from backend.core import cache

        class _FakeRedis:
            def get(self, key):
                return '{"x": 1, "y": [1, 2, 3]}'

        monkeypatch.setattr(cache, "_get_redis", lambda: _FakeRedis())
        assert cache.cache_get("qualquer") == {"x": 1, "y": [1, 2, 3]}

    def test_cache_get_miss_redis_retorna_none(self, monkeypatch):
        from backend.core import cache

        class _FakeRedis:
            def get(self, key):
                return None

        monkeypatch.setattr(cache, "_get_redis", lambda: _FakeRedis())
        assert cache.cache_get("qualquer") is None

    def test_cache_get_excecao_no_redis_retorna_none(self, monkeypatch):
        from backend.core import cache

        class _FakeRedis:
            def get(self, key):
                raise TimeoutError("redis lento")

        monkeypatch.setattr(cache, "_get_redis", lambda: _FakeRedis())
        assert cache.cache_get("qualquer") is None

    def test_cache_set_chama_setex_com_json(self, monkeypatch):
        from backend.core import cache
        chamadas = {}

        class _FakeRedis:
            def setex(self, key, ttl, raw):
                chamadas["key"] = key
                chamadas["ttl"] = ttl
                chamadas["raw"] = raw

        monkeypatch.setattr(cache, "_get_redis", lambda: _FakeRedis())
        cache.cache_set("minha_key", {"a": 1}, ttl=42)
        assert chamadas["key"] == "minha_key"
        assert chamadas["ttl"] == 42
        assert '"a": 1' in chamadas["raw"]

    def test_cache_set_excecao_no_redis_nao_propaga(self, monkeypatch):
        from backend.core import cache

        class _FakeRedis:
            def setex(self, key, ttl, raw):
                raise ConnectionError("caiu")

        monkeypatch.setattr(cache, "_get_redis", lambda: _FakeRedis())
        # Não deve lançar.
        cache.cache_set("minha_key", {"a": 1}, ttl=42)

    def test_cache_get_df_hit_deserializa_dataframe(self, monkeypatch):
        import pandas as pd
        from backend.core import cache

        df_original = pd.DataFrame({"A": [1, 2, 3]})
        raw = df_original.to_json()

        class _FakeRedis:
            def get(self, key):
                return raw

        monkeypatch.setattr(cache, "_get_redis", lambda: _FakeRedis())
        out = cache.cache_get_df("df_key")
        assert out is not None
        assert list(out["A"]) == [1, 2, 3]

    def test_cache_get_df_miss_redis_retorna_none(self, monkeypatch):
        from backend.core import cache

        class _FakeRedis:
            def get(self, key):
                return None

        monkeypatch.setattr(cache, "_get_redis", lambda: _FakeRedis())
        assert cache.cache_get_df("df_key") is None

    def test_cache_get_df_excecao_retorna_none(self, monkeypatch):
        from backend.core import cache

        class _FakeRedis:
            def get(self, key):
                raise ValueError("json corrompido")

        monkeypatch.setattr(cache, "_get_redis", lambda: _FakeRedis())
        assert cache.cache_get_df("df_key") is None

    def test_cache_set_df_chama_setex_com_to_json(self, monkeypatch):
        import pandas as pd
        from backend.core import cache
        chamadas = {}

        class _FakeRedis:
            def setex(self, key, ttl, raw):
                chamadas["key"] = key
                chamadas["ttl"] = ttl
                chamadas["raw"] = raw

        monkeypatch.setattr(cache, "_get_redis", lambda: _FakeRedis())
        df = pd.DataFrame({"A": [1, 2, 3]})
        cache.cache_set_df("df_key", df, ttl=99)
        assert chamadas["key"] == "df_key"
        assert chamadas["ttl"] == 99
        assert chamadas["raw"] == df.to_json()

    def test_cache_set_df_excecao_no_redis_nao_propaga(self, monkeypatch):
        import pandas as pd
        from backend.core import cache

        class _FakeRedis:
            def setex(self, key, ttl, raw):
                raise ConnectionError("caiu")

        monkeypatch.setattr(cache, "_get_redis", lambda: _FakeRedis())
        df = pd.DataFrame({"A": [1, 2, 3]})
        # Não deve lançar.
        cache.cache_set_df("df_key", df, ttl=99)


class TestRedisStatusBranches:
    """Cobre todos os ramos de redis_status: disabled / connected / unavailable / not_initialized."""

    def setup_method(self):
        from backend.core import cache
        self._orig_configured = cache._redis_url_configured
        self._orig_client = cache._client
        self._orig_unavailable = cache._unavailable

    def teardown_method(self):
        from backend.core import cache
        cache._redis_url_configured = self._orig_configured
        cache._client = self._orig_client
        cache._unavailable = self._orig_unavailable

    def test_status_disabled_quando_nao_configurado(self, monkeypatch):
        from backend.core import cache
        monkeypatch.setattr(cache, "_redis_url_configured", False)
        status = cache.redis_status()
        assert status == {"enabled": False, "connected": False, "status": "disabled"}

    def test_status_connected_quando_client_responde_ping(self, monkeypatch):
        from backend.core import cache

        class _FakeClient:
            def ping(self):
                return True

        monkeypatch.setattr(cache, "_redis_url_configured", True)
        monkeypatch.setattr(cache, "_client", _FakeClient())
        status = cache.redis_status()
        assert status == {"enabled": True, "connected": True, "status": "connected"}

    def test_status_unavailable_quando_client_ping_falha(self, monkeypatch):
        from backend.core import cache

        class _FakeClient:
            def ping(self):
                raise ConnectionError("caiu")

        monkeypatch.setattr(cache, "_redis_url_configured", True)
        monkeypatch.setattr(cache, "_client", _FakeClient())
        status = cache.redis_status()
        assert status == {"enabled": True, "connected": False, "status": "unavailable"}

    def test_status_unavailable_sem_client_apos_falha_previa(self, monkeypatch):
        from backend.core import cache
        monkeypatch.setattr(cache, "_redis_url_configured", True)
        monkeypatch.setattr(cache, "_client", None)
        monkeypatch.setattr(cache, "_unavailable", True)
        status = cache.redis_status()
        assert status == {"enabled": True, "connected": False, "status": "unavailable"}

    def test_status_not_initialized_quando_nunca_tentou_conectar(self, monkeypatch):
        from backend.core import cache
        monkeypatch.setattr(cache, "_redis_url_configured", True)
        monkeypatch.setattr(cache, "_client", None)
        monkeypatch.setattr(cache, "_unavailable", False)
        status = cache.redis_status()
        assert status == {"enabled": True, "connected": False, "status": "not_initialized"}
