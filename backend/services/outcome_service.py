"""Rastreamento de desfecho dos sinais (abordagem A).

Lê os sinais persistidos no Supabase, busca o preço da ação desde a data de cada
sinal e reprecifica a opção via Black-Scholes para classificar ganho/perda/aberto
([backend/domain/outcome.py](outcome)). Agrega o resultado comparando o score
clássico (que decide hoje) com o ponderado (shadow), respondendo: dos sinais que
deram certo/errado, quantos o ponderado teria aprovado.
"""
import logging
from datetime import datetime, timedelta, timezone

import pandas as pd

from backend.domain.outcome import avaliar_desfecho, comparar_por_desfecho, retorno_pct_do_desfecho
from backend.domain.scoring import GATILHOS
from backend.services.core_engine import _baixar_ohlcv
from backend.services.supabase_client import get_supabase

logger = logging.getLogger("b3_api")

_CAMPOS = ("id, ticker, tipo_sinal, strike_ref, premio_est, preco_tela, alvo1, alvo2, "
           "alvo_final, stop, hv_20d, iv_mercado, dte, preco_acao, score, "
           "score_ponderado, ponderado_passou, gatilhos_ids, setup, timestamp")

_DESFECHOS_TERMINAIS = ("alvo1", "alvo2", "alvo_final", "stop", "expirou")


def _persistir_trigger_outcomes(supabase, sinal: dict, resultado: dict) -> None:
    """Explode o desfecho do sinal em uma linha por gatilho disparado
    (Camada 2.4). Só persiste desfechos terminais (ignora aberto/indeterminado,
    que ainda não têm resultado definitivo); idempotente via upsert em
    (signal_id, gatilho_id) — chamadas repetidas de `avaliar_sinais` sobre o
    mesmo sinal não duplicam linhas. Sinais sem `gatilhos_ids` (legados,
    anteriores a esta camada) são pulados. Falha de persistência não impede
    a avaliação do sinal (apenas loga)."""
    if resultado["desfecho"] not in _DESFECHOS_TERMINAIS:
        return
    ids = sinal.get("gatilhos_ids") or []
    if not ids:
        return

    retorno_pct = retorno_pct_do_desfecho(resultado["desfecho"])
    linhas = [{
        "signal_id":          sinal["id"],
        "gatilho_id":         gid,
        "familia":            GATILHOS.get(gid, {}).get("familia"),
        "pontos":             GATILHOS.get(gid, {}).get("pontos"),
        "setup":              sinal.get("setup"),
        "resultado_final":    resultado["desfecho"],
        "retorno_pct":        retorno_pct,
        "dias_ate_resolucao": resultado["dias_ate"],
    } for gid in ids]

    try:
        supabase.table("trigger_outcomes").upsert(linhas, on_conflict="signal_id,gatilho_id").execute()
    except Exception as e:
        logger.warning(f"Erro ao persistir trigger_outcomes do sinal {sinal.get('id')}: {e}")


def _precos_desde(ticker_sa: str, desde: datetime) -> list:
    """Closes diários da ação a partir de `desde` (inclusive), via provider (cacheado)."""
    now_utc = datetime.now(timezone.utc)
    desde_aware = desde if desde.tzinfo is not None else desde.replace(tzinfo=timezone.utc)
    days_ago = (now_utc - desde_aware).days

    needed_days = days_ago + 30  # margem de segurança
    if needed_days <= 180:
        period = "6mo"
    elif needed_days <= 365:
        period = "1y"
    elif needed_days <= 730:
        period = "2y"
    else:
        period = "5y"

    df = _baixar_ohlcv(ticker_sa, period, "1d", verbose=False)
    if df is None or df.empty:
        return []
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    if "Close" not in df.columns:
        return []

    # Certifica-se de que a primeira data do df é anterior ou igual à data do sinal
    primeira_data = df.index[0].to_pydatetime() if hasattr(df.index[0], "to_pydatetime") else df.index[0]
    if primeira_data.tzinfo is None and desde_aware.tzinfo is not None:
        primeira_data = primeira_data.replace(tzinfo=timezone.utc)

    if primeira_data > desde_aware:
        logger.warning(
            f"Histórico de preços para {ticker_sa} começa em {primeira_data}, "
            f"que é posterior à data do sinal {desde_aware}. Pulando sinal."
        )
        return []

    serie = df["Close"].dropna()
    target_ts = pd.Timestamp(desde_aware.date())
    serie = serie[serie.index >= target_ts]
    return [float(x) for x in serie.tolist()]


def avaliar_sinais(dias: int = 30) -> dict:
    """Avalia o desfecho dos sinais dos últimos `dias` e compara clássico vs ponderado."""
    supabase = get_supabase()
    if not supabase:
        return {"erro": "Supabase indisponível", "resolvidos": 0, "sinais_avaliados": 0}

    cutoff = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    try:
        res = (supabase.table("signals")
               .select(_CAMPOS)
               .gte("timestamp", cutoff)
               .order("timestamp")
               .limit(2000)
               .execute())
        rows = res.data or []
    except Exception as e:
        return {"erro": str(e), "resolvidos": 0, "sinais_avaliados": 0}

    avaliados = []
    for s in rows:
        ts = s.get("timestamp")
        if not ts or s.get("strike_ref") is None or s.get("dte") is None:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            continue
        ticker_sa = (s.get("ticker") or "").upper()
        if not ticker_sa:
            continue
        if not ticker_sa.endswith(".SA"):
            ticker_sa += ".SA"

        precos = _precos_desde(ticker_sa, dt)
        if len(precos) < 2:
            continue
        r = avaliar_desfecho(s, precos)
        _persistir_trigger_outcomes(supabase, s, r)
        avaliados.append({
            **r,
            "ticker": s.get("ticker"),
            "tipo_sinal": s.get("tipo_sinal"),
            "score": s.get("score"),
            "score_ponderado": s.get("score_ponderado"),
            "ponderado_passou": s.get("ponderado_passou"),
        })

    relatorio = comparar_por_desfecho(avaliados)
    relatorio["periodo_dias"] = dias
    relatorio["sinais_avaliados"] = len(avaliados)
    dist: dict = {}
    for a in avaliados:
        dist[a["desfecho"]] = dist.get(a["desfecho"], 0) + 1
    relatorio["distribuicao"] = dist
    return relatorio
