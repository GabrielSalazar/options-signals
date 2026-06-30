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

from backend.services import core_engine
from backend.domain.indicators import calcular_indicadores


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
    monkeypatch.setattr(core_engine, "mes_vencimento_ideal", lambda: (6, 2026, 30))
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
    assert s["premio_est"] == 0.1
    assert s["preco_tela"] is None
    assert s["ticker_opcao"] == "N/A (S/ Liquidez)"
    assert (s["entrada_min"], s["entrada_max"]) == (0.1, 0.1)
    assert (s["alvo1"], s["alvo2"], s["alvo_final"], s["stop"]) == (0.12, 0.35, 0.8, 0.06)
    assert (s["rr_alvo1"], s["rr_alvo2"], s["rr_final"]) == (0.5, 6.25, 17.5)
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
    assert est["premio_est"] == 0.1
    assert est["dte"] == 30
    assert (est["alvo1"], est["alvo2"], est["alvo_final"], est["stop"]) == (0.12, 0.35, 0.8, 0.06)
    assert (est["rr_alvo1"], est["rr_alvo2"], est["rr_final"]) == (0.5, 6.25, 17.5)
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
    from backend.services import core_engine as ce
    from backend.domain.greeks import bs_call_price

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
    assert (s["alvo1"], s["alvo2"], s["alvo_final"], s["stop"]) == (0.12, 0.35, 0.8, 0.06)
