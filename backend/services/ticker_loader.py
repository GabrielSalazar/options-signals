"""Carregador do universo de tickers da B3 (universo líquido).

Une as fontes (lista curada + API oficial da B3 + brapi), aplica o pré-filtro de
volume financeiro e o top_n, e mantém um cache TTL em processo (independe do
Redis) para reuso entre scans.

Camadas: este módulo (service) é a casa da montagem de universo — o core
(config) não importa services.
"""
import logging
import time
from typing import Dict, Optional

from backend.core.config import ATIVOS_B3, CONFIG
from backend.services.data_providers import (
    fetch_all_b3_tickers,
    fetch_b3_official_tickers,
    filtrar_por_volume,
)

logger = logging.getLogger("b3_scanner")

# Cache TTL em processo: {chave_params: (timestamp, valor)}
_universe_cache: dict = {}


def clear_cache() -> None:
    """Limpa o cache em processo (uso em testes)."""
    _universe_cache.clear()


def _base(ticker: str) -> str:
    return ticker.upper().replace(".SA", "").strip()


def carregar_tickers_b3(
    min_volume_rs: Optional[float] = None,
    top_n: Optional[int] = None,
    usar_api_b3: bool = True,
    usar_brapi: bool = True,
    usar_lista_curada: bool = True,
    filtrar_volume: bool = True,
    cache_segundos: Optional[int] = None,
    force_refresh: bool = False,
) -> Dict[str, str]:
    """Retorna {TICKER.SA: nome} do universo líquido (curados primeiro)."""
    if min_volume_rs is None:
        min_volume_rs = CONFIG["min_volume_rs"]
    if top_n is None:
        top_n = CONFIG.get("ticker_top_n")
    if cache_segundos is None:
        cache_segundos = CONFIG.get("ticker_cache_segundos", 3600)

    chave = (min_volume_rs, top_n, usar_api_b3, usar_brapi, usar_lista_curada, filtrar_volume)
    if not force_refresh and chave in _universe_cache:
        ts, valor = _universe_cache[chave]
        if time.time() - ts < cache_segundos:
            return valor

    # 1. Universo bruto {base: nome} — curados têm precedência de nome
    curados = {_base(t): nome for t, nome in ATIVOS_B3.items()}
    universo: Dict[str, str] = {}
    if usar_lista_curada:
        universo.update(curados)
    if usar_api_b3:
        for base, nome in fetch_b3_official_tickers().items():
            universo.setdefault(_base(base), nome)
    if usar_brapi:
        for base in fetch_all_b3_tickers():
            universo.setdefault(_base(base), _base(base))

    curados_bases = list(curados.keys()) if usar_lista_curada else []
    curados_set = set(curados_bases)

    # 2. Filtro de volume — curados sempre passam (precedência + fallback)
    if filtrar_volume:
        nao_curados = [b for b in universo if b not in curados_set]
        vols = filtrar_por_volume([f"{b}.SA" for b in nao_curados], min_volume_rs)
        aprovados = sorted(
            ((_base(sa), v) for sa, v in vols.items()),
            key=lambda kv: kv[1], reverse=True,
        )
        ordem = curados_bases + [b for b, _ in aprovados]
    else:
        ordem = curados_bases + [b for b in universo if b not in curados_set]

    # 3. top_n (curados ficam no topo, então nunca são cortados antes dos demais)
    if top_n is not None:
        ordem = ordem[:top_n]

    resultado = {f"{b}.SA": universo.get(b, b) for b in ordem}
    _universe_cache[chave] = (time.time(), resultado)
    logger.info(f"Universo líquido: {len(resultado)} tickers (curados={len(curados_bases)})")
    return resultado


def nome_ativo(ticker: str) -> str:
    """Resolve o melhor nome conhecido para um ticker: lista curada → nome da
    empresa via API oficial da B3 (cache 24h) → o próprio código. Usado por
    scan_single/scan_batch para não exibir o código cru de não-curados (B2)."""
    base = _base(ticker)
    sa = f"{base}.SA"
    if sa in ATIVOS_B3:
        return ATIVOS_B3[sa]
    nome = fetch_b3_official_tickers().get(base)
    return nome if nome else base


def get_all_b3_assets() -> Dict[str, str]:
    """Compat: universo líquido como dict {TICKER.SA: nome}. (Antes em config.py.)

    Mantido para os consumidores existentes (run_scan, /watchlist). Reflete o
    universo líquido real, compartilhando o cache do carregador.
    """
    return carregar_tickers_b3()
