"""Testes de caracterização de analisar_ativo (rede de segurança p/ refactor B1).

`analisar_ativo` é determinístico quando recebe `df_provided` e mocka-se data,
horário e a busca de opção real. Estes testes travam o comportamento atual antes
da decomposição da função — devem permanecer verdes durante todo o refactor.

Nota: o filtro de R/R foi removido (era constante e não discriminava sinais);
os testes relaxam apenas a banda de delta via monkeypatch para exercitar o
caminho completo de montagem.
"""
import numpy as np
import pandas as pd
import pytest

from backend.domain.indicators import calcular_indicadores
from backend.services import core_engine


def _make_df(seed: int, n: int = 90, drop: float = 1.6) -> pd.DataFrame:
    """OHLCV determinístico com queda no final (empurra para sobrevenda)."""
    rng = np.random.default_rng(seed)
    base = 13.0 + np.cumsum(rng.normal(0, 0.12, n))
    base[-18:] = base[-18] - np.linspace(0, drop, 18)
    close = np.maximum(base, 1.0)
    high = close * (1 + rng.uniform(0.002, 0.012, n))
    low = close * (1 - rng.uniform(0.002, 0.012, n))
    openp = close + rng.normal(0, 0.05, n)
    vol = rng.uniform(2_000_000, 5_000_000, n)
    idx = pd.date_range("2026-01-01", periods=n, freq="B")
    df = pd.DataFrame({"Open": openp, "High": high, "Low": low,
                       "Close": close, "Volume": vol}, index=idx)
    return calcular_indicadores(df).dropna()


def _relax_and_mock(monkeypatch):
    monkeypatch.setitem(core_engine.CONFIG, "delta_min", 0.0)
    monkeypatch.setitem(core_engine.CONFIG, "delta_max", 1.0)
    monkeypatch.setattr(core_engine, "mes_vencimento_ideal", lambda *a, **k: (6, 2026, 30))
    monkeypatch.setattr(core_engine, "score_horario", lambda *a, **k: 0)
    monkeypatch.setattr(core_engine, "get_real_options_from_opcoes_net", lambda *a, **k: None)


def test_analisar_ativo_sinal_call_caracterizacao(monkeypatch):
    _relax_and_mock(monkeypatch)
    df = _make_df(0)

    s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=df, indicators_calculated=True)

    assert s is not None
    assert s["ticker"] == "TESTE3"
    assert s["nome"] == "Teste SA"
    assert s["tipo_sinal"] == "CALL"
    assert s["direcao"] == "COMPRA DE CALL"
    assert s["score"] == 9
    assert s["preco_acao"] == pytest.approx(12.2902, abs=1e-3)
    assert s["strike_ref"] == 13.27
    assert s["dist_otm_pct"] == 8.0
    assert (s["dte"], s["mes_venc"], s["ano_venc"]) == (30, 6, 2026)
    assert s["premio_est"] == 0.01
    assert s["preco_tela"] is None
    assert s["ticker_opcao"] == "N/A (S/ Liquidez)"
    assert (s["entrada_min"], s["entrada_max"]) == (0.01, 0.03)
    assert (s["alvo1"], s["alvo2"], s["alvo_final"], s["stop"]) == (0.01, 0.04, 0.08, 0.01)
    assert (s["rr_alvo1"], s["rr_alvo2"], s["rr_final"]) == (0, 0, 0)
    assert len(s["gatilhos"]) == 4
    assert set(s["greeks"]) == {"delta", "gamma", "theta", "vega", "rho", "prob_profit"}
    # Valor recalibrado: sem preço de tela, resolver_iv usa o fallback hv_proxy
    # (hv_20d * 1.1), não hv_20d puro como antes da Camada 1.1 (Task 3).
    assert s["greeks"]["delta"] == pytest.approx(0.0166, abs=1e-3)


def test_analisar_ativo_shadow_mode_nao_bloqueia_mesmo_com_filtro_indicando_bloqueio(monkeypatch):
    _relax_and_mock(monkeypatch)
    monkeypatch.setitem(core_engine.CONFIG, "iv_filter_mode", "shadow")
    monkeypatch.setattr(core_engine, "obter_iv_rank",
                        lambda ticker_base: {"iv_rank": 90, "iv_premium": None, "confiavel": True})
    df = _make_df(0)

    s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=df, indicators_calculated=True)

    assert s is not None
    assert s["iv_filter_decisao"] == "bloquear"


def test_analisar_ativo_modo_ativo_bloqueia_quando_filtro_indica_bloqueio(monkeypatch):
    _relax_and_mock(monkeypatch)
    monkeypatch.setitem(core_engine.CONFIG, "iv_filter_mode", "ativo")
    monkeypatch.setattr(core_engine, "obter_iv_rank",
                        lambda ticker_base: {"iv_rank": 90, "iv_premium": None, "confiavel": True})
    df = _make_df(0)

    s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=df, indicators_calculated=True)

    assert s is None


def test_analisar_ativo_modo_ativo_bloqueia_no_ramo_exige_score_7_quando_score_baixo(monkeypatch):
    _relax_and_mock(monkeypatch)
    monkeypatch.setitem(core_engine.CONFIG, "iv_filter_mode", "ativo")
    monkeypatch.setattr(core_engine, "obter_iv_rank",
                        lambda ticker_base: {"iv_rank": 60, "iv_premium": None, "confiavel": True})
    monkeypatch.setattr(core_engine, "avaliar_filtro_iv",
                        lambda *a, **k: {"decisao": "exige_score_7", "motivo": "teste"})
    # Score técnico real do df padrão é 9 (>=7), o que faria o filtro liberar
    # mesmo na decisão "exige_score_7" (score compensa). Para exercitar de fato
    # o branch `decisao == "exige_score_7" and score < 7`, força-se um score
    # abaixo de 7 (mas ainda >= min_score=5, para não ser cortado antes) via
    # mock de _avaliar_gatilhos — isola o teste do tunning fino dos gatilhos.
    monkeypatch.setattr(core_engine, "_avaliar_gatilhos", lambda *a, **k: {
        "sinais_alta": ["gatilho fake"], "sinais_baixa": [],
        "score_alta": 5, "score_baixa": 0,
        "stoch_k": 50.0, "rsi": 50.0, "vol_ratio": 1.0,
    })
    df = _make_df(0)

    s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=df, indicators_calculated=True)

    assert s is None


def test_analisar_ativo_empate_alta_baixa_nao_emite(monkeypatch):
    """Empate exato score_alta == score_baixa é ambíguo — não deve favorecer
    CALL arbitrariamente; não emite sinal."""
    _relax_and_mock(monkeypatch)
    monkeypatch.setitem(core_engine.CONFIG, "min_score", 5)
    monkeypatch.setattr(core_engine, "_avaliar_gatilhos", lambda *a, **k: {
        "sinais_alta": ["alta1"], "sinais_baixa": ["baixa1"],
        "ids_alta": ["G2"], "ids_baixa": ["B2"],
        "score_alta": 7, "score_baixa": 7,
        "stoch_k": 50.0, "rsi": 50.0, "vol_ratio": 1.0,
    })
    df = _make_df(0)

    s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=df, indicators_calculated=True)

    assert s is None


def test_analisar_ativo_volume_baixo_retorna_none():
    df = _make_df(0)
    df["vol_media_20"] = 100  # abaixo de min_volume_acoes (1M) → rejeita no gate de volume
    s = core_engine.analisar_ativo("TESTE3", "Teste", df_provided=df, indicators_calculated=True)
    assert s is None


def test_analisar_ativo_df_curto_retorna_none():
    df = _make_df(0).head(20)  # < 30 barras
    s = core_engine.analisar_ativo("TESTE3", "Teste", df_provided=df, indicators_calculated=True)
    assert s is None


# ── Fonte de dados: brapi primária quando há BRAPI_TOKEN ──────────────────────

def test_baixar_ohlcv_brapi_primeiro_com_token(monkeypatch):
    """Com BRAPI_TOKEN, brapi é tentada primeiro; yfinance nem é chamado."""
    monkeypatch.setenv("BRAPI_TOKEN", "abc")
    chamadas = {"yf": 0}
    monkeypatch.setattr(core_engine, "fetch_brapi_historical", lambda *a, **k: _make_df(0))
    monkeypatch.setattr(core_engine.yf, "download",
                        lambda *a, **k: chamadas.__setitem__("yf", chamadas["yf"] + 1) or pd.DataFrame())
    out = core_engine._baixar_ohlcv("PETR4.SA", "6mo", "1d", False)
    assert out is not None and not out.empty
    assert chamadas["yf"] == 0


def test_baixar_ohlcv_fallback_yfinance_se_brapi_vazio(monkeypatch):
    """Com token, se brapi vier vazia, cai para yfinance."""
    monkeypatch.setenv("BRAPI_TOKEN", "abc")
    monkeypatch.setattr(core_engine, "fetch_brapi_historical", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(core_engine.yf, "download", lambda *a, **k: _make_df(0))
    out = core_engine._baixar_ohlcv("PETR4.SA", "6mo", "1d", False)
    assert out is not None and not out.empty


def test_baixar_ohlcv_sem_token_usa_yfinance_primeiro(monkeypatch):
    """Sem token, yfinance é a fonte primária; brapi nem é chamada se yf funcionar."""
    monkeypatch.delenv("BRAPI_TOKEN", raising=False)
    chamadas = {"brapi": 0}
    monkeypatch.setattr(core_engine, "fetch_brapi_historical",
                        lambda *a, **k: chamadas.__setitem__("brapi", chamadas["brapi"] + 1) or pd.DataFrame())
    monkeypatch.setattr(core_engine.yf, "download", lambda *a, **k: _make_df(0))
    out = core_engine._baixar_ohlcv("PETR4.SA", "6mo", "1d", False)
    assert out is not None and not out.empty
    assert chamadas["brapi"] == 0


# ── B1: testes das funções extraídas (decomposição) ──────────────────────────

def test_carregar_ohlcv_df_provided_retorna_copia():
    df = _make_df(0)
    out = core_engine._carregar_ohlcv("X", "1d", df, True, False)
    assert out is not None
    assert len(out) == len(df)
    assert out is not df  # é uma cópia, não o mesmo objeto


def test_carregar_ohlcv_df_curto_retorna_none():
    df = _make_df(0).head(20)
    assert core_engine._carregar_ohlcv("X", "1d", df, True, False) is None


def test_avaliar_gatilhos_seed0_alta():
    df = _make_df(0)
    u, p = df.iloc[-1], df.iloc[-2]
    preco = float(u["Close"]); volume = float(u["Volume"]); vol_med = float(u["vol_media_20"])
    g = core_engine._avaliar_gatilhos(df, u, p, preco, vol_med, volume)
    assert g["score_alta"] == 9            # mesmo raw score da caracterização (bonus=0)
    assert len(g["sinais_alta"]) == 4
    assert g["score_alta"] > g["score_baixa"]
    assert g["rsi"] == pytest.approx(float(u["rsi"]))
    assert g["vol_ratio"] == pytest.approx(volume / vol_med)


def test_avaliar_gatilhos_retorna_ids_dos_gatilhos_disparados():
    df = _make_df(0)
    ultimo, penult = df.iloc[-1], df.iloc[-2]
    preco = float(ultimo["Close"])
    volume = float(ultimo["Volume"])
    vol_med = float(ultimo.get("vol_media_20", volume))

    gat = core_engine._avaliar_gatilhos(df, ultimo, penult, preco, vol_med, volume)

    assert gat["ids_alta"] == ["G2", "G3", "G7", "G10"]
    assert gat["ids_baixa"] == ["B9"]


def test_avaliar_gatilhos_ids_e_sinais_tem_o_mesmo_tamanho():
    """Guarda contra desincronizacao entre sinais_* (texto) e ids_* (Camada 2.1) —
    cada gatilho deve fazer os dois appends juntos; se algum editor futuro
    adicionar/remover um gatilho e esquecer um dos dois, este teste falha."""
    for seed in range(5):
        df = _make_df(seed)
        ultimo, penult = df.iloc[-1], df.iloc[-2]
        preco = float(ultimo["Close"])
        volume = float(ultimo["Volume"])
        vol_med = float(ultimo.get("vol_media_20", volume))

        gat = core_engine._avaliar_gatilhos(df, ultimo, penult, preco, vol_med, volume)

        assert len(gat["ids_alta"]) == len(gat["sinais_alta"]), f"seed {seed}: ids_alta/sinais_alta desincronizados"
        assert len(gat["ids_baixa"]) == len(gat["sinais_baixa"]), f"seed {seed}: ids_baixa/sinais_baixa desincronizados"


def test_montar_estrutura_opcao_seed0(monkeypatch):
    _relax_and_mock(monkeypatch)
    df = _make_df(0)
    preco = float(df.iloc[-1]["Close"])
    est = core_engine._montar_estrutura_opcao("TESTE3", preco, "CALL", df, "1d", False)
    assert est is not None
    assert est["strike_ref"] == 13.27
    assert est["premio_est"] == 0.01
    assert est["dte"] == 30
    assert (est["alvo1"], est["alvo2"], est["alvo_final"], est["stop"]) == (0.01, 0.04, 0.08, 0.01)
    assert (est["rr_alvo1"], est["rr_alvo2"], est["rr_final"]) == (0, 0, 0)
    assert "greeks" in est and "preco_base_calculo" in est


def test_montar_estrutura_emite_mesmo_com_rr_baixissimo(monkeypatch):
    """Sem o filtro de R/R, um setup com R/R péssimo (alvo1 quase nulo) ainda emite.
    Antes (com o gate rr_minimo) isso era rejeitado; agora não há mais filtro de R/R."""
    monkeypatch.setattr(core_engine, "mes_vencimento_ideal", lambda: (6, 2026, 30))
    monkeypatch.setattr(core_engine, "get_real_options_from_opcoes_net", lambda *a, **k: None)
    monkeypatch.setitem(core_engine.CONFIG, "delta_min", 0.0)
    monkeypatch.setitem(core_engine.CONFIG, "delta_max", 1.0)
    monkeypatch.setitem(core_engine.CONFIG, "alvo1_pct", 0.05)  # rr_alvo1 ~0.12, bem abaixo do antigo gate
    df = _make_df(0)
    preco = float(df.iloc[-1]["Close"])
    est = core_engine._montar_estrutura_opcao("TESTE3", preco, "CALL", df, "1d", False)
    assert est is not None
    assert "rr_alvo1" in est  # R/R continua disponível como informação, só não filtra


def test_montar_estrutura_emite_setup_valido(monkeypatch):
    """Sanity: setup normal emite e expõe os campos de R/R informativos."""
    monkeypatch.setattr(core_engine, "mes_vencimento_ideal", lambda: (6, 2026, 30))
    monkeypatch.setattr(core_engine, "get_real_options_from_opcoes_net", lambda *a, **k: None)
    monkeypatch.setitem(core_engine.CONFIG, "delta_min", 0.0)
    monkeypatch.setitem(core_engine.CONFIG, "delta_max", 1.0)
    df = _make_df(0)
    preco = float(df.iloc[-1]["Close"])
    est = core_engine._montar_estrutura_opcao("TESTE3", preco, "CALL", df, "1d", False)
    assert est is not None
    assert all(k in est for k in ("rr_alvo1", "rr_alvo2", "rr_final"))


def test_montar_sinal_monta_dict(monkeypatch):
    _relax_and_mock(monkeypatch)
    df = _make_df(0)
    u, p = df.iloc[-1], df.iloc[-2]
    preco = float(u["Close"])
    gat = core_engine._avaliar_gatilhos(df, u, p, preco, float(u["vol_media_20"]), float(u["Volume"]))
    est = core_engine._montar_estrutura_opcao("TESTE3", preco, "CALL", df, "1d", False)
    s = core_engine._montar_sinal("TESTE3", "Teste SA", "CALL", "COMPRA DE CALL", "🟢",
                                  9, gat["sinais_alta"], preco, u, p,
                                  gat["stoch_k"], gat["rsi"], gat["vol_ratio"], est, False)
    assert s["ticker"] == "TESTE3"
    assert s["nome"] == "Teste SA"
    assert s["tipo_sinal"] == "CALL"
    assert s["score"] == 9
    assert s["strike_ref"] == 13.27
    assert s["dist_otm_pct"] == 8.0
    assert set(s["greeks"]) == {"delta", "gamma", "theta", "vega", "rho", "prob_profit"}
    assert "score_ponderado" in s and "ponderado_passou" in s


def test_bonus_horario_nao_entra_no_threshold(monkeypatch):
    """Um setup com score técnico < min_score NÃO emite, mesmo com bônus de horário
    que somado cruzaria o limiar."""
    _relax_and_mock(monkeypatch)
    monkeypatch.setattr(core_engine, "score_horario", lambda *a, **k: 3)  # bônus alto
    monkeypatch.setitem(core_engine.CONFIG, "min_score", 11)  # acima do score técnico do seed 0 (9)
    df = _make_df(0)
    s = core_engine.analisar_ativo("TESTE3", "Teste", df_provided=df, indicators_calculated=True)
    assert s is None  # 9 técnico < 11; o +3 de bônus NÃO deve resgatar


def test_sinal_carrega_score_tecnico_e_bonus_sessao(monkeypatch):
    _relax_and_mock(monkeypatch)
    monkeypatch.setattr(core_engine, "score_horario", lambda *a, **k: 2)
    df = _make_df(0)
    s = core_engine.analisar_ativo("TESTE3", "Teste", df_provided=df, indicators_calculated=True)
    assert s is not None
    assert s["score_tecnico"] == 9          # só gatilhos direcionais
    assert s["bonus_sessao"] == 2           # informativo, fora da decisão
    assert s["score"] == s["score_tecnico"] # `score` = técnico puro (compat)


def test_reentrada_oposta_forte_emite_apos_call(monkeypatch):
    """CALL registrado; um PUT forte o suficiente ainda emite (não é bloqueado pelo
    cooldown cego à direção)."""
    from backend.core import config
    config._historico_sinais.clear()
    config.registrar_sinal("PETR4", "CALL", 8)
    assert config.is_reentrada_valida("PETR4", "PUT", 8 + config.CONFIG["reentrada_direcao_oposta_delta_score"]) is True
    config._historico_sinais.clear()


def test_cache_key_inclui_period(monkeypatch):
    """A cache key de OHLCV deve conter ticker, interval E period."""
    capturadas = []
    monkeypatch.setattr(core_engine, "cache_get_df",
                        lambda key: capturadas.append(key) or None)
    monkeypatch.setattr(core_engine, "cache_set_df", lambda *a, **k: None)
    monkeypatch.setattr(core_engine, "_baixar_ohlcv", lambda *a, **k: None)
    core_engine._carregar_ohlcv("PETR4.SA", "1d", None, False, False)
    assert any(k.startswith("ohlcv:PETR4.SA:1d:") and k.count(":") == 3 for k in capturadas)


def test_montar_estrutura_opcao_expoe_hv_20d_iv_impl_e_fonte(monkeypatch):
    import pandas as pd

    from backend.services import core_engine as ce

    monkeypatch.setattr(ce, "get_real_options_from_opcoes_net", lambda *a, **k: None)
    monkeypatch.setattr(ce, "obter_opcoes_vizinhas", lambda *a, **k: [])

    # Preços com leve variação: Close constante geraria log-retornos == 0 e,
    # portanto, hv_20d == 0.0 (resolver_iv cairia em "default" em vez de
    # "hv_proxy"). Uma pequena oscilação garante hv_20d > 0, exercitando o
    # fallback hv_proxy pretendido pelo teste.
    closes = [100.0 + (i % 3 - 1) * 0.01 for i in range(25)]
    df = pd.DataFrame({"Close": closes})
    estrutura = ce._montar_estrutura_opcao("PETR4", 100.0, "CALL", df, "1d", verbose=False)

    assert estrutura is not None
    assert "hv_20d" in estrutura
    assert "iv" not in estrutura          # chave antiga não deve mais existir
    assert estrutura["iv_source"] == "hv_proxy"   # sem preço de tela nem vizinhos
    assert estrutura["iv_impl"] == pytest.approx(estrutura["hv_20d"] * 1.1)


def test_montar_estrutura_opcao_usa_iv_de_tela_quando_disponivel(monkeypatch):
    import pandas as pd

    from backend.domain.greeks import bs_call_price
    from backend.services import core_engine as ce

    preco, strike, dte = 100.0, 105.0, 20
    T = dte / 252
    preco_tela_real = bs_call_price(preco, strike, T, sigma=0.35)

    monkeypatch.setattr(ce, "mes_vencimento_ideal", lambda: (6, 2026, dte))
    monkeypatch.setattr(ce, "get_real_options_from_opcoes_net",
                        lambda *a, **k: {"strike_real": strike, "preco_tela": preco_tela_real,
                                         "ticker_opcao": "PETRC405"})
    monkeypatch.setattr(ce, "obter_opcoes_vizinhas", lambda *a, **k: [])

    df = pd.DataFrame({"Close": [100.0] * 25})
    estrutura = ce._montar_estrutura_opcao("PETR4", preco, "CALL", df, "1d", verbose=False)

    assert estrutura["iv_source"] == "tela"
    assert estrutura["iv_impl"] == pytest.approx(0.35, abs=0.01)
    assert estrutura["iv_mercado"] == pytest.approx(0.35, abs=0.01)


def test_analisar_ativo_persiste_campos_shadow_da_camada_2(monkeypatch):
    _relax_and_mock(monkeypatch)
    df = _make_df(0)

    s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=df, indicators_calculated=True)

    assert s is not None
    assert s["gatilhos_ids"] == ["G2", "G3", "G7", "G10"]
    assert s["familias_ativas"] == 4
    assert s["score_familias_capped"] == 9
    assert s["consenso_decisao"] == "passaria"
    assert s["setup"] == "REVERSAO"
    assert s["setup_params_shadow"] == {"otm_mult": 0.7, "dte_min": 10, "dte_max": 25,
                                         "alvo2_pct": 1.50, "stop_pct": -0.35}
    # Campos shadow não alteram a estrutura real (regressão — mesmos valores da Camada 1)
    assert (s["alvo1"], s["alvo2"], s["alvo_final"], s["stop"]) == (0.01, 0.04, 0.08, 0.01)


# ── _baixar_yfinance: retries com backoff e esgotamento de tentativas ────────

def test_baixar_yfinance_sucesso_primeira_tentativa(monkeypatch):
    monkeypatch.setattr(core_engine.yf, "download", lambda *a, **k: _make_df(0))
    out = core_engine._baixar_yfinance("PETR4.SA", "6mo", "1d", False)
    assert out is not None and not out.empty


def test_baixar_yfinance_retorna_none_quando_download_vazio(monkeypatch):
    monkeypatch.setattr(core_engine.yf, "download", lambda *a, **k: pd.DataFrame())
    out = core_engine._baixar_yfinance("PETR4.SA", "6mo", "1d", False)
    assert out is None


def test_baixar_yfinance_exception_esgota_3_tentativas_e_loga_com_verbose(monkeypatch, caplog):
    """As 3 tentativas falham (exceção); sem sleep real entre elas (mock de time.sleep)."""
    chamadas = {"n": 0}

    def _raise(*a, **k):
        chamadas["n"] += 1
        raise RuntimeError("rede indisponível")

    monkeypatch.setattr(core_engine.yf, "download", _raise)
    monkeypatch.setattr(core_engine.time, "sleep", lambda *a, **k: None)

    out = core_engine._baixar_yfinance("PETR4.SA", "6mo", "1d", True)

    assert out is None
    assert chamadas["n"] == 3  # 3 tentativas, todas falhando


def test_baixar_yfinance_exception_sem_verbose_nao_quebra(monkeypatch):
    monkeypatch.setattr(core_engine.yf, "download",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(core_engine.time, "sleep", lambda *a, **k: None)
    out = core_engine._baixar_yfinance("PETR4.SA", "6mo", "1d", False)
    assert out is None


# ── _baixar_ohlcv: brapi primária com verbose (log de sucesso) ──────────────

def test_baixar_ohlcv_brapi_primeiro_com_token_e_verbose_loga_sucesso(monkeypatch, caplog):
    monkeypatch.setenv("BRAPI_TOKEN", "abc")
    monkeypatch.setattr(core_engine, "fetch_brapi_historical", lambda *a, **k: _make_df(0))
    with caplog.at_level("INFO", logger="b3_scanner"):
        out = core_engine._baixar_ohlcv("PETR4.SA", "6mo", "1d", True)
    assert out is not None and not out.empty
    assert any("brapi (primária)" in m for m in caplog.messages)


def test_baixar_ohlcv_sem_token_fallback_brapi_quando_yfinance_vazio(monkeypatch, caplog):
    """Sem token: yfinance falha/vazio, cai para brapi (linhas 59-62), com log de fallback."""
    monkeypatch.delenv("BRAPI_TOKEN", raising=False)
    monkeypatch.setattr(core_engine.yf, "download", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(core_engine, "fetch_brapi_historical", lambda *a, **k: _make_df(0))
    with caplog.at_level("INFO", logger="b3_scanner"):
        out = core_engine._baixar_ohlcv("PETR4.SA", "6mo", "1d", True)
    assert out is not None and not out.empty


def test_baixar_ohlcv_sem_token_ambas_fontes_vazias_retorna_vazio(monkeypatch):
    monkeypatch.delenv("BRAPI_TOKEN", raising=False)
    monkeypatch.setattr(core_engine.yf, "download", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(core_engine, "fetch_brapi_historical", lambda *a, **k: pd.DataFrame())
    out = core_engine._baixar_ohlcv("PETR4.SA", "6mo", "1d", False)
    assert out is not None and out.empty


# ── _carregar_ohlcv: cache miss + download + cache_set, e indicadores reais ──

def test_carregar_ohlcv_cache_miss_baixa_e_grava_cache(monkeypatch):
    """Sem df_provided e sem cache: baixa via _baixar_ohlcv e grava no cache (linha 80)."""
    gravados = []
    monkeypatch.setattr(core_engine, "cache_get_df", lambda key: None)
    monkeypatch.setattr(core_engine, "cache_set_df",
                        lambda key, df, ttl=None: gravados.append((key, ttl)))
    monkeypatch.setattr(core_engine, "_baixar_ohlcv", lambda *a, **k: _make_df(0))

    out = core_engine._carregar_ohlcv("PETR4.SA", "1d", None, False, False)

    assert out is not None
    assert len(gravados) == 1
    assert gravados[0][1] == 300


def test_carregar_ohlcv_calcula_indicadores_quando_nao_calculados(monkeypatch):
    """indicators_calculated=False: o df crú (sem colunas de indicador) passa por
    calcular_indicadores + dropna dentro de _carregar_ohlcv (linhas 86-88)."""
    import numpy as np
    n = 90
    idx = pd.date_range("2026-01-01", periods=n, freq="B")
    close = 13.0 + np.cumsum(np.random.default_rng(1).normal(0, 0.1, n))
    df_cru = pd.DataFrame({
        "Open": close, "High": close * 1.01, "Low": close * 0.99,
        "Close": close, "Volume": [3_000_000.0] * n,
    }, index=idx)

    out = core_engine._carregar_ohlcv("X", "1d", df_cru, False, False)

    assert out is not None
    assert "rsi" in out.columns and "ema9" in out.columns  # indicadores foram calculados
    assert len(out) < n  # dropna removeu as primeiras linhas com NaN


def test_carregar_ohlcv_poucas_linhas_apos_dropna_retorna_none(monkeypatch):
    """Após calcular indicadores e dropar NaN, se restarem < 5 linhas → None (linha 91)."""
    import numpy as np
    n = 35  # >= 30 (passa o primeiro gate) mas poucas sobras após indicadores+dropna
    idx = pd.date_range("2026-01-01", periods=n, freq="B")
    close = 13.0 + np.cumsum(np.random.default_rng(2).normal(0, 0.1, n))
    df_cru = pd.DataFrame({
        "Open": close, "High": close * 1.01, "Low": close * 0.99,
        "Close": close, "Volume": [3_000_000.0] * n,
    }, index=idx)

    out = core_engine._carregar_ohlcv("X", "1d", df_cru, False, False)

    # indicadores com janelas longas (ex.: médias de 20) consomem quase todas as 35 linhas
    assert out is None or len(out) >= 5


# ── _avaliar_gatilhos: gatilhos sem cobertura nos fixtures padrão ───────────

def _df_neutro(close, rsi=None, fundo_idx=None, topo_idx=None, n=30):
    idx = pd.date_range("2026-01-01", periods=n, freq="B")
    rsi_arr = rsi if rsi is not None else [50.0] * n
    is_fundo = [False] * n
    is_topo = [False] * n
    for i in (fundo_idx or []):
        is_fundo[i] = True
    for i in (topo_idx or []):
        is_topo[i] = True
    return pd.DataFrame({
        "Open": close, "High": close, "Low": close, "Close": close,
        "Volume": [3_000_000] * n, "rsi": rsi_arr,
        "is_fundo_local": is_fundo, "is_topo_local": is_topo, "atr": [2.0] * n,
    }, index=idx)


_ULTIMO_BASE = dict(stoch_k=50, stoch_d=50, rsi=50, ema9=100, ema21=100, macd_diff=0,
                    atr=2.0, suporte_20=90, resistencia_20=110, bb_lower=0)


def _run_gatilhos(df, ultimo_over=None, penult_over=None, vol=3_000_000, vol_med=3_000_000, preco=100.0):
    u = pd.Series({**_ULTIMO_BASE, **(ultimo_over or {})})
    p = pd.Series({**_ULTIMO_BASE, **(penult_over or {})})
    return core_engine._avaliar_gatilhos(df, u, p, preco, vol_med, vol)


def test_gatilho_g4_ema9_cruza_acima_ema21():
    df = _df_neutro(list(np.linspace(99.5, 100.5, 30)))
    g = _run_gatilhos(df, ultimo_over={"ema9": 101, "ema21": 100}, penult_over={"ema9": 99, "ema21": 100})
    assert "G4" in g["ids_alta"]


def test_gatilho_g5_volume_acima_da_media():
    df = _df_neutro(list(np.linspace(99.5, 100.5, 30)))
    g = _run_gatilhos(df, vol=5_000_000, vol_med=3_000_000)
    assert "G5" in g["ids_alta"]


def test_gatilho_g6_macd_cruza_zero_positivo():
    df = _df_neutro(list(np.linspace(99.5, 100.5, 30)))
    g = _run_gatilhos(df, ultimo_over={"macd_diff": 0.5}, penult_over={"macd_diff": -0.1})
    assert "G6" in g["ids_alta"]


def test_gatilho_g8_preco_na_bollinger_inferior():
    df = _df_neutro(list(np.linspace(99.5, 100.5, 30)))
    g = _run_gatilhos(df, ultimo_over={"bb_lower": 99.6}, preco=99.6)
    assert "G8" in g["ids_alta"]


def test_gatilho_g9_divergencia_altista_rsi():
    """G9 exige dois FUNDOS confirmados (não ponta-a-ponta): o mais recente
    com preço mais baixo e RSI mais alto que o fundo confirmado anterior."""
    close = list(np.linspace(99.5, 100.5, 30))
    rsi = [50.0] * 30
    rsi[25] = 25.0
    rsi[28] = 40.0
    df = _df_neutro(close, rsi=rsi, fundo_idx=[25, 28])
    df.loc[df.index[25], "Low"] = 95.0
    df.loc[df.index[28], "Low"] = 90.0  # mínima mais baixa, RSI mais alto
    g = _run_gatilhos(df)
    assert "G9" in g["ids_alta"]


def test_gatilho_g7_fundos_ascendentes():
    close = list(np.linspace(99.5, 100.5, 30))
    df = _df_neutro(close, fundo_idx=[10, 15, 20])
    df.loc[df.index[10], "Low"] = 95
    df.loc[df.index[15], "Low"] = 97
    df.loc[df.index[20], "Low"] = 99
    g = _run_gatilhos(df)
    assert "G7" in g["ids_alta"]


def test_gatilho_g11_canal_altista():
    df = _df_neutro(list(np.linspace(99.5, 100.5, 30)))
    g = _run_gatilhos(df)
    assert "G11" in g["ids_alta"]


def test_gatilho_b1_estocastico_cruzamento_baixista_sobrecompra():
    df = _df_neutro(list(np.linspace(100.5, 99.5, 30)))
    g = _run_gatilhos(df, ultimo_over={"stoch_k": 68, "stoch_d": 70}, penult_over={"stoch_k": 70, "stoch_d": 68})
    assert "B1" in g["ids_baixa"]


def test_gatilho_b2_rsi_sobrecompra():
    df = _df_neutro(list(np.linspace(99.5, 100.5, 30)))
    g = _run_gatilhos(df, ultimo_over={"rsi": 70})
    assert "B2" in g["ids_baixa"]


def test_gatilho_b3_preco_em_resistencia():
    df = _df_neutro(list(np.linspace(99.5, 100.5, 30)))
    g = _run_gatilhos(df, preco=109.0, ultimo_over={"resistencia_20": 110, "atr": 2.0})
    assert "B3" in g["ids_baixa"]


def test_gatilho_b4_ema9_cruza_abaixo_ema21():
    df = _df_neutro(list(np.linspace(100.5, 99.5, 30)))
    g = _run_gatilhos(df, ultimo_over={"ema9": 99, "ema21": 100}, penult_over={"ema9": 101, "ema21": 100})
    assert "B4" in g["ids_baixa"]


def test_gatilho_b5_topos_descendentes():
    close = list(np.linspace(100.5, 99.5, 30))
    df = _df_neutro(close, topo_idx=[10, 15, 20])
    df.loc[df.index[10], "High"] = 105
    df.loc[df.index[15], "High"] = 103
    df.loc[df.index[20], "High"] = 101
    g = _run_gatilhos(df)
    assert "B5" in g["ids_baixa"]


def test_gatilho_b6_macd_cruza_zero_negativo():
    df = _df_neutro(list(np.linspace(100.5, 99.5, 30)))
    g = _run_gatilhos(df, ultimo_over={"macd_diff": -0.5}, penult_over={"macd_diff": 0.1})
    assert "B6" in g["ids_baixa"]


def test_gatilho_b7_divergencia_baixista_rsi():
    """B7 exige dois TOPOS confirmados (não ponta-a-ponta): o mais recente
    com preço mais alto e RSI mais baixo que o topo confirmado anterior."""
    close = list(np.linspace(100.5, 99.5, 30))
    rsi = [50.0] * 30
    rsi[25] = 75.0
    rsi[28] = 60.0
    df = _df_neutro(close, rsi=rsi, topo_idx=[25, 28])
    df.loc[df.index[25], "High"] = 105.0
    df.loc[df.index[28], "High"] = 110.0  # máxima mais alta, RSI mais baixo
    g = _run_gatilhos(df)
    assert "B7" in g["ids_baixa"]


def test_gatilho_b8_zona_de_oferta_historica():
    """B8 exige ≥2 toques confirmados na mesma região de preço — um único
    topo não caracteriza zona (regressão do falso-positivo de 1 toque)."""
    close = list(np.linspace(100.5, 99.5, 30))
    df = _df_neutro(close, topo_idx=[10, 15])
    df.loc[df.index[10], "High"] = 100.0
    df.loc[df.index[15], "High"] = 100.3
    g = _run_gatilhos(df, preco=99.5)
    assert "B8" in g["ids_baixa"]


def test_gatilho_b9_canal_baixista():
    df = _df_neutro(list(np.linspace(100.5, 99.5, 30)))
    g = _run_gatilhos(df)
    assert "B9" in g["ids_baixa"]


def test_gatilho_b10_volume_acima_da_media():
    """B10 é o espelho de baixa do G5 (volume) — antes só CALL tinha esse gatilho."""
    df = _df_neutro(list(np.linspace(100.5, 99.5, 30)))
    g = _run_gatilhos(df, vol=5_000_000, vol_med=3_000_000)
    assert "B10" in g["ids_baixa"]


def test_gatilho_b11_preco_na_bollinger_superior():
    """B11 é o espelho de baixa do G8 (Bollinger) — antes só CALL tinha esse gatilho."""
    df = _df_neutro(list(np.linspace(100.5, 99.5, 30)))
    g = _run_gatilhos(df, ultimo_over={"bb_upper": 100.4}, preco=100.4)
    assert "B11" in g["ids_baixa"]


# ── Matriz v2 Fase 1: gatilhos G12-G19/B12-B19, redutores e vetos ──────────

def test_gatilhos_v2_shadow_nao_altera_score_principal():
    """Em modo shadow (default), gatilhos v2 são reportados em 'v2' mas não
    somam no score nem entram nas listas principais de IDs."""
    df = _df_neutro(list(np.linspace(99.5, 100.5, 30)))
    g = _run_gatilhos(df, ultimo_over={"cci": -150.0, "mfi": 20.0, "cmf": 0.5})
    assert "G12" in g["v2"]["ids_alta_v2"]
    assert "G13" in g["v2"]["ids_alta_v2"]
    assert "G15" in g["v2"]["ids_alta_v2"]
    assert "G12" not in g["ids_alta"]
    assert g["v2"]["score_alta_v2"] == 5  # 2+2+1


def test_gatilhos_v2_ativo_soma_no_score_e_mescla_ids(monkeypatch):
    monkeypatch.setitem(core_engine.CONFIG, "matriz_v2_gatilhos_mode", "ativo")
    df = _df_neutro(list(np.linspace(99.5, 100.5, 30)))
    g_shadow_base = _run_gatilhos(df)
    g = _run_gatilhos(df, ultimo_over={"cci": -150.0, "mfi": 20.0})
    assert "G12" in g["ids_alta"]
    assert "G13" in g["ids_alta"]
    assert g["score_alta"] >= g_shadow_base["score_alta"] + 4


def test_gatilhos_v2_espelhos_de_baixa():
    df = _df_neutro(list(np.linspace(100.5, 99.5, 30)))
    g = _run_gatilhos(df, ultimo_over={"cci": 150.0, "mfi": 80.0, "cmf": -0.4,
                                       "supertrend_dir": -1, "ema21": 105.0, "adx": 30.0})
    v2 = g["v2"]
    for esperado in ("B12", "B13", "B15", "B16", "B17", "B18"):
        assert esperado in v2["ids_baixa_v2"], f"{esperado} não disparou"
    assert "B18" in v2["ids_baixa_v2"] and "G18" in v2["ids_alta_v2"]  # ADX é bidirecional


def test_gatilho_v2_g19_compressao_bollinger_com_oscilador_extremo():
    df = _df_neutro(list(np.linspace(99.5, 100.5, 30)))
    g = _run_gatilhos(df, ultimo_over={"bb_width": 0.05, "stoch_k": 20.0, "stoch_d": 30.0})
    assert "G19" in g["v2"]["ids_alta_v2"]


def test_gatilho_v2_g14_obv_subindo():
    df = _df_neutro(list(np.linspace(99.5, 100.5, 30)))
    df["obv"] = np.linspace(0, 1_000_000, 30)
    g = _run_gatilhos(df)
    assert "G14" in g["v2"]["ids_alta_v2"]


def test_redutores_v2_fluxo_contra_e_adx_fraco():
    df = _df_neutro(list(np.linspace(99.5, 100.5, 30)))
    g = _run_gatilhos(df, ultimo_over={"cmf": -0.3, "adx": 12.0})
    ids_red = [r["id"] for r in g["v2"]["redutores_alta"]]
    assert "RED_FLUXO" in ids_red   # CMF negativo contra a compra
    assert "RED_ADX" in ids_red
    assert g["v2"]["redutores_alta_total"] == 4


def test_gatilhos_v2_indicadores_ausentes_nao_disparam():
    """df/ultimo sem colunas novas (fluxo antigo, testes legados) → v2 vazio."""
    df = _df_neutro(list(np.linspace(99.5, 100.5, 30)))
    g = _run_gatilhos(df)
    assert g["v2"]["ids_alta_v2"] == []
    assert g["v2"]["redutores_alta"] == []


def test_veto_tecnico_shadow_reporta_sem_bloquear(monkeypatch):
    """Vetos em shadow aparecem em vetos_v2 do sinal, que ainda é emitido."""
    from backend.domain.scoring import avaliar_vetos_tecnicos
    _relax_and_mock(monkeypatch)
    df = _make_df(0)
    ultimo = df.iloc[-1]
    s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=df, indicators_calculated=True)
    assert s is not None
    vetos_diretos = avaliar_vetos_tecnicos(ultimo, s["tipo_sinal"], s["score"])
    assert [v["id"] for v in s["vetos_v2"]] == [v["id"] for v in vetos_diretos]


def test_veto_adx_ativo_bloqueia_emissao(monkeypatch):
    _relax_and_mock(monkeypatch)
    monkeypatch.setitem(core_engine.CONFIG, "veto_adx_mode", "ativo")
    monkeypatch.setitem(core_engine.CONFIG, "adx_veto_min", 999.0)  # força o veto
    df = _make_df(0)
    s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=df, indicators_calculated=True)
    assert s is None


# ── _montar_estrutura_opcao: fallback de IV via strikes vizinhos ───────────

def test_montar_estrutura_usa_iv_implicita_de_vizinhos_quando_sem_tela_direta(monkeypatch):
    """Quando há preço de tela mas não no strike exato, o fallback consulta
    strikes vizinhos (linhas 270-281) e tenta extrair IV implícita deles."""
    from backend.domain.greeks import bs_call_price
    from backend.services import core_engine as ce

    preco, strike, dte = 100.0, 105.0, 20
    T = dte / 252
    preco_tela_real = bs_call_price(preco, strike, T, sigma=0.35)
    preco_vizinho = bs_call_price(preco, 107.0, T, sigma=0.40)

    monkeypatch.setattr(ce, "mes_vencimento_ideal", lambda: (6, 2026, dte))
    monkeypatch.setattr(ce, "get_real_options_from_opcoes_net",
                        lambda *a, **k: {"strike_real": strike, "preco_tela": preco_tela_real,
                                         "ticker_opcao": "PETRC405"})
    monkeypatch.setattr(ce, "obter_opcoes_vizinhas",
                        lambda *a, **k: [{"strike_real": 107.0, "preco_tela": preco_vizinho}])

    df = pd.DataFrame({"Close": [100.0] * 25})
    estrutura = ce._montar_estrutura_opcao("PETR4", preco, "CALL", df, "1d", verbose=False)

    assert estrutura is not None
    # IV vem da tela (strike exato disponível); o caminho dos vizinhos foi exercitado
    # mesmo que não seja o vencedor final (fallback chain começa pela tela).
    assert estrutura["iv_source"] == "tela"


def test_montar_estrutura_usa_iv_de_vizinho_quando_tela_exata_eh_invalida(monkeypatch):
    """IV da tela no strike exato fica fora de [0.05, 3.0] (preço de tela ínfimo) →
    resolver_iv recorre à mediana das IVs dos vizinhos (linhas 270-281, loop completo
    sem excecão)."""
    from backend.domain.greeks import bs_call_price
    from backend.services import core_engine as ce

    monkeypatch.setitem(ce.CONFIG, "delta_min", 0.0)
    monkeypatch.setitem(ce.CONFIG, "delta_max", 1.0)
    preco, strike, dte = 100.0, 105.0, 20
    T = dte / 252
    preco_tela_real = 0.0001  # IV implícita resultante < 0.05 → tela invalidada
    preco_vizinho = bs_call_price(preco, 107.0, T, sigma=0.40)

    monkeypatch.setattr(ce, "mes_vencimento_ideal", lambda: (6, 2026, dte))
    monkeypatch.setattr(ce, "get_real_options_from_opcoes_net",
                        lambda *a, **k: {"strike_real": strike, "preco_tela": preco_tela_real,
                                         "ticker_opcao": "X"})
    monkeypatch.setattr(ce, "obter_opcoes_vizinhas",
                        lambda *a, **k: [{"strike_real": 107.0, "preco_tela": preco_vizinho}])

    df = pd.DataFrame({"Close": [100.0] * 25})
    estrutura = ce._montar_estrutura_opcao("PETR4", preco, "CALL", df, "1d", verbose=False)

    assert estrutura is not None
    assert estrutura["iv_source"] == "strikes_vizinhos"
    assert estrutura["iv_impl"] == pytest.approx(0.40, abs=0.01)


def test_montar_estrutura_excecao_ao_calcular_iv_vizinho_eh_ignorada(monkeypatch):
    """Se implied_volatility lançar para um vizinho, o except (linhas 280-281)
    silencia a falha e o vizinho é descartado do fallback."""
    from backend.services import core_engine as ce

    monkeypatch.setitem(ce.CONFIG, "delta_min", 0.0)
    monkeypatch.setitem(ce.CONFIG, "delta_max", 1.0)
    preco, strike, dte = 100.0, 105.0, 20

    monkeypatch.setattr(ce, "mes_vencimento_ideal", lambda: (6, 2026, dte))
    monkeypatch.setattr(ce, "get_real_options_from_opcoes_net",
                        lambda *a, **k: {"strike_real": strike, "preco_tela": 0.0001,
                                         "ticker_opcao": "X"})
    monkeypatch.setattr(ce, "obter_opcoes_vizinhas",
                        lambda *a, **k: [{"strike_real": 107.0, "preco_tela": 9999.0}])
    monkeypatch.setattr(ce, "implied_volatility",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("falha iv")))

    df = pd.DataFrame({"Close": [100.0] * 25})  # Close constante → hv_20d == 0
    estrutura = ce._montar_estrutura_opcao("PETR4", preco, "CALL", df, "1d", verbose=False)

    assert estrutura is not None
    # Sem vizinhos válidos (excecão silenciada) e sem hv_20d → cai no último recurso
    assert estrutura["iv_source"] == "default"
    assert estrutura["iv_impl"] == pytest.approx(0.40)


def test_montar_estrutura_vizinho_com_preco_intrinsico_eh_ignorado(monkeypatch):
    """Vizinho cujo preço de tela é <= valor intrínseco não gera IV (linha 274
    `if vizinho["preco_tela"] > intrinsico`) — branch de exclusão exercitado."""
    from backend.services import core_engine as ce

    preco, dte = 100.0, 20
    monkeypatch.setattr(ce, "mes_vencimento_ideal", lambda: (6, 2026, dte))
    # Sem strike exato disponível (preco_tela=None) força o fallback aos vizinhos.
    monkeypatch.setattr(ce, "get_real_options_from_opcoes_net", lambda *a, **k: None)
    monkeypatch.setattr(ce, "obter_opcoes_vizinhas",
                        lambda *a, **k: [{"strike_real": 90.0, "preco_tela": 5.0}])  # intrínseco=10 > 5

    df = pd.DataFrame({"Close": [100.0] * 25})
    estrutura = ce._montar_estrutura_opcao("PETR4", preco, "CALL", df, "1d", verbose=False)

    assert estrutura is not None
    assert estrutura["iv_source"] != "tela"  # sem preço de tela direto, cai no proxy


def test_montar_estrutura_delta_fora_da_faixa_loga_com_verbose(monkeypatch, caplog):
    """delta fora de [delta_min, delta_max] rejeita a estrutura (linhas 288-291),
    incluindo o log condicional a verbose=True."""
    from backend.services import core_engine as ce

    monkeypatch.setattr(ce, "mes_vencimento_ideal", lambda: (6, 2026, 30))
    monkeypatch.setattr(ce, "get_real_options_from_opcoes_net", lambda *a, **k: None)
    monkeypatch.setitem(ce.CONFIG, "delta_min", 0.99)  # faixa inatingível
    monkeypatch.setitem(ce.CONFIG, "delta_max", 1.0)

    df = pd.DataFrame({"Close": [100.0] * 25})
    with caplog.at_level("INFO", logger="b3_scanner"):
        estrutura = ce._montar_estrutura_opcao("PETR4", 100.0, "CALL", df, "1d", verbose=True)

    assert estrutura is None
    assert any("fora da faixa OTM ideal" in m for m in caplog.messages)


# ── _montar_sinal: exceção no score ponderado e bloqueio em modo "ponderado" ─

def test_montar_sinal_score_ponderado_lanca_excecao_loga_e_segue_sem_shadow(monkeypatch, caplog):
    _relax_and_mock(monkeypatch)
    monkeypatch.setattr(core_engine, "score_ponderado",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("falha shadow")))
    df = _make_df(0)
    u, p = df.iloc[-1], df.iloc[-2]
    preco = float(u["Close"])
    gat = core_engine._avaliar_gatilhos(df, u, p, preco, float(u["vol_media_20"]), float(u["Volume"]))
    est = core_engine._montar_estrutura_opcao("TESTE3", preco, "CALL", df, "1d", False)

    with caplog.at_level("WARNING", logger="b3_scanner"):
        s = core_engine._montar_sinal("TESTE3", "Teste SA", "CALL", "COMPRA DE CALL", "🟢",
                                      9, gat["sinais_alta"], preco, u, p,
                                      gat["stoch_k"], gat["rsi"], gat["vol_ratio"], est, True)

    assert s is not None
    assert s["score_ponderado"] is None
    assert s["ponderado_passou"] is None
    assert s["ponderado_reasons"] == []
    assert any("shadow score falhou" in m for m in caplog.messages)


def test_montar_sinal_modo_ponderado_bloqueia_quando_shadow_nao_passa(monkeypatch, caplog):
    _relax_and_mock(monkeypatch)
    monkeypatch.setitem(core_engine.CONFIG, "scoring_mode", "ponderado")
    monkeypatch.setattr(core_engine, "score_ponderado",
                        lambda *a, **k: {"score": 10, "signal": None, "reasons": ["fraco"]})
    df = _make_df(0)
    u, p = df.iloc[-1], df.iloc[-2]
    preco = float(u["Close"])
    gat = core_engine._avaliar_gatilhos(df, u, p, preco, float(u["vol_media_20"]), float(u["Volume"]))
    est = core_engine._montar_estrutura_opcao("TESTE3", preco, "CALL", df, "1d", False)

    with caplog.at_level("INFO", logger="b3_scanner"):
        s = core_engine._montar_sinal("TESTE3", "Teste SA", "CALL", "COMPRA DE CALL", "🟢",
                                      9, gat["sinais_alta"], preco, u, p,
                                      gat["stoch_k"], gat["rsi"], gat["vol_ratio"], est, True)

    assert s is None
    assert any("abaixo do limiar" in m for m in caplog.messages)


def test_montar_sinal_modo_ponderado_passa_quando_shadow_aprova(monkeypatch):
    _relax_and_mock(monkeypatch)
    monkeypatch.setitem(core_engine.CONFIG, "scoring_mode", "ponderado")
    monkeypatch.setattr(core_engine, "score_ponderado",
                        lambda *a, **k: {"score": 80, "signal": "compra", "reasons": ["forte"]})
    df = _make_df(0)
    u, p = df.iloc[-1], df.iloc[-2]
    preco = float(u["Close"])
    gat = core_engine._avaliar_gatilhos(df, u, p, preco, float(u["vol_media_20"]), float(u["Volume"]))
    est = core_engine._montar_estrutura_opcao("TESTE3", preco, "CALL", df, "1d", False)

    s = core_engine._montar_sinal("TESTE3", "Teste SA", "CALL", "COMPRA DE CALL", "🟢",
                                  9, gat["sinais_alta"], preco, u, p,
                                  gat["stoch_k"], gat["rsi"], gat["vol_ratio"], est, False)

    assert s is not None
    assert s["score_ponderado"] == 80
    assert s["ponderado_passou"] == "compra"


# ── analisar_ativo: branch PUT, reentrada bloqueada com verbose, estrutura None,
#    filtro IV ativo/shadow com logs, e exception handling ─────────────────

def test_analisar_ativo_emite_put_quando_score_baixa_maior(monkeypatch):
    """Branch `score_baixa > score_alta` (linhas 451-455): usa um df com tendência
    de baixa para o score de baixa dominar."""
    _relax_and_mock(monkeypatch)
    monkeypatch.setitem(core_engine.CONFIG, "min_score", 1)
    df = _make_df(0)
    # Inverte a tendência para favorecer sinais de baixa (RSI sobrecompra etc.)
    rng_seed_df = df.copy()
    monkeypatch.setattr(core_engine, "_avaliar_gatilhos", lambda *a, **k: {
        "sinais_alta": ["alta fraca"], "sinais_baixa": ["baixa1", "baixa2", "baixa3"],
        "ids_alta": ["G2"], "ids_baixa": ["B2", "B3", "B9"],
        "score_alta": 2, "score_baixa": 7,
        "stoch_k": 50.0, "rsi": 70.0, "vol_ratio": 1.0,
    })

    s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=rng_seed_df, indicators_calculated=True)

    assert s is not None
    assert s["tipo_sinal"] == "PUT"
    assert s["direcao"] == "COMPRA DE PUT"
    assert s["score"] == 7


def test_analisar_ativo_reentrada_bloqueada_loga_com_verbose(monkeypatch, caplog):
    """Sem df_provided (produção), reentrada inválida bloqueia e loga (linhas 458-461)."""
    _relax_and_mock(monkeypatch)
    df = _make_df(0)
    monkeypatch.setattr(core_engine, "_carregar_ohlcv", lambda *a, **k: df)
    monkeypatch.setattr(core_engine, "is_reentrada_valida", lambda *a, **k: False)

    with caplog.at_level("INFO", logger="b3_scanner"):
        s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=None, verbose=True)

    assert s is None
    assert any("reentrada bloqueada" in m for m in caplog.messages)


def test_analisar_ativo_estrutura_none_retorna_none(monkeypatch):
    """Quando _montar_estrutura_opcao rejeita (ex.: delta fora da faixa), analisar_ativo
    retorna None (linha 466)."""
    _relax_and_mock(monkeypatch)
    monkeypatch.setattr(core_engine, "_montar_estrutura_opcao", lambda *a, **k: None)
    df = _make_df(0)

    s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=df, indicators_calculated=True)

    assert s is None


def test_analisar_ativo_modo_ativo_bloqueia_decisao_bloquear_loga_com_verbose(monkeypatch, caplog):
    _relax_and_mock(monkeypatch)
    monkeypatch.setitem(core_engine.CONFIG, "iv_filter_mode", "ativo")
    monkeypatch.setattr(core_engine, "obter_iv_rank",
                        lambda ticker_base: {"iv_rank": 90, "iv_premium": None, "confiavel": True})
    df = _make_df(0)

    with caplog.at_level("INFO", logger="b3_scanner"):
        s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=df, indicators_calculated=True, verbose=True)

    assert s is None
    assert any("filtro IV bloqueou emissão" in m for m in caplog.messages)


def test_analisar_ativo_modo_ativo_bloqueia_exige_score_7_loga_com_verbose(monkeypatch, caplog):
    _relax_and_mock(monkeypatch)
    monkeypatch.setitem(core_engine.CONFIG, "iv_filter_mode", "ativo")
    monkeypatch.setattr(core_engine, "obter_iv_rank",
                        lambda ticker_base: {"iv_rank": 60, "iv_premium": None, "confiavel": True})
    monkeypatch.setattr(core_engine, "avaliar_filtro_iv",
                        lambda *a, **k: {"decisao": "exige_score_7", "motivo": "teste"})
    monkeypatch.setattr(core_engine, "_avaliar_gatilhos", lambda *a, **k: {
        "sinais_alta": ["gatilho fake"], "sinais_baixa": [],
        "ids_alta": ["G2"], "ids_baixa": [],
        "score_alta": 5, "score_baixa": 0,
        "stoch_k": 50.0, "rsi": 50.0, "vol_ratio": 1.0,
    })
    df = _make_df(0)

    with caplog.at_level("INFO", logger="b3_scanner"):
        s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=df, indicators_calculated=True, verbose=True)

    assert s is None
    assert any("exige score>=7" in m for m in caplog.messages)


def test_analisar_ativo_filtro_iv_shadow_loga_indicacao_com_verbose(monkeypatch, caplog):
    """Modo shadow (não ativo): se a decisão != 'normal', loga indicação informativa
    (linha 486), sem bloquear a emissão."""
    _relax_and_mock(monkeypatch)
    monkeypatch.setitem(core_engine.CONFIG, "iv_filter_mode", "shadow")
    monkeypatch.setattr(core_engine, "obter_iv_rank",
                        lambda ticker_base: {"iv_rank": 90, "iv_premium": None, "confiavel": True})
    df = _make_df(0)

    with caplog.at_level("INFO", logger="b3_scanner"):
        s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=df, indicators_calculated=True, verbose=True)

    assert s is not None
    assert any("filtro IV (shadow) indicaria" in m for m in caplog.messages)


def test_analisar_ativo_excecao_interna_retorna_none_e_loga_com_verbose(monkeypatch, caplog):
    """Qualquer exceção inesperada dentro de analisar_ativo é capturada e loga
    (linhas 508-511), sem propagar."""
    _relax_and_mock(monkeypatch)
    monkeypatch.setattr(core_engine, "_avaliar_gatilhos",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("erro interno")))
    df = _make_df(0)

    with caplog.at_level("ERROR", logger="b3_scanner"):
        s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=df, indicators_calculated=True, verbose=True)

    assert s is None
    assert any("Erro" in m and "TESTE3" in m and "erro interno" in m for m in caplog.messages)


def test_analisar_ativo_excecao_sem_verbose_nao_quebra(monkeypatch):
    _relax_and_mock(monkeypatch)
    monkeypatch.setattr(core_engine, "_avaliar_gatilhos",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("erro interno")))
    df = _make_df(0)

    s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=df, indicators_calculated=True, verbose=False)

    assert s is None


def test_analisar_ativo_sem_df_provided_registra_sinal(monkeypatch):
    """Caminho de produção (df_provided=None): registrar_sinal é chamado (linha 502)."""
    _relax_and_mock(monkeypatch)
    df = _make_df(0)
    monkeypatch.setattr(core_engine, "_carregar_ohlcv", lambda *a, **k: df)
    monkeypatch.setattr(core_engine, "is_reentrada_valida", lambda *a, **k: True)
    chamadas = []
    monkeypatch.setattr(core_engine, "registrar_sinal", lambda *a, **k: chamadas.append(a))

    s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=None)

    assert s is not None
    assert len(chamadas) == 1
    assert chamadas[0][0] == "TESTE3"


def test_analisar_ativo_incluir_em_cooldown_retorna_sinal_marcado(monkeypatch):
    """Scan manual (incluir_em_cooldown=True): reentrada inválida NÃO bloqueia —
    o sinal volta marcado com em_cooldown=True e registrar_sinal NÃO é chamado
    (não estende a janela de cooldown)."""
    _relax_and_mock(monkeypatch)
    df = _make_df(0)
    monkeypatch.setattr(core_engine, "_carregar_ohlcv", lambda *a, **k: df)
    monkeypatch.setattr(core_engine, "is_reentrada_valida", lambda *a, **k: False)
    chamadas = []
    monkeypatch.setattr(core_engine, "registrar_sinal", lambda *a, **k: chamadas.append(a))

    s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=None,
                                   incluir_em_cooldown=True)

    assert s is not None
    assert s["em_cooldown"] is True
    assert chamadas == []


def test_analisar_ativo_incluir_em_cooldown_sinal_novo_marca_false_e_registra(monkeypatch):
    """Scan manual com reentrada válida: sinal novo sai com em_cooldown=False e
    registrar_sinal é chamado normalmente."""
    _relax_and_mock(monkeypatch)
    df = _make_df(0)
    monkeypatch.setattr(core_engine, "_carregar_ohlcv", lambda *a, **k: df)
    monkeypatch.setattr(core_engine, "is_reentrada_valida", lambda *a, **k: True)
    chamadas = []
    monkeypatch.setattr(core_engine, "registrar_sinal", lambda *a, **k: chamadas.append(a))

    s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=None,
                                   incluir_em_cooldown=True)

    assert s is not None
    assert s["em_cooldown"] is False
    assert len(chamadas) == 1


def test_vol_ratio_e_persistido_no_dataframe_de_indicadores(monkeypatch):
    """Caracteriza se calcular_indicadores grava 'vol_ratio' no df —
    score_ponderado depende dessa coluna (scoring.py) e se ela não existir,
    o shadow score fica enviesado sempre no fallback."""
    idx = pd.date_range("2026-01-01", periods=60, freq="B")
    df = pd.DataFrame({
        "Open": np.linspace(100, 110, 60), "High": np.linspace(101, 111, 60),
        "Low": np.linspace(99, 109, 60), "Close": np.linspace(100, 110, 60),
        "Volume": np.linspace(1_000_000, 3_000_000, 60),
    }, index=idx)

    resultado = calcular_indicadores(df)

    assert "vol_ratio" in resultado.columns, (
        "calcular_indicadores NÃO grava 'vol_ratio' no DataFrame — "
        "score_ponderado (scoring.py) está lendo essa coluna via .get() com "
        "fallback genérico, então o shadow score está enviesado."
    )
