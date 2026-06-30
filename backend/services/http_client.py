import logging
import time

import requests

logger = logging.getLogger("b3_api")


def get_with_retry(
    url: str,
    timeout: float = 10.0,
    tentativas: int = 3,
    backoff_base_s: float = 1.0,
    **kwargs,
) -> requests.Response:
    """GET com retry e backoff exponencial — generaliza o padrão já usado em
    core_engine._baixar_yfinance para todas as integrações de rede de
    data_providers.py (que hoje não tinham retry algum)."""
    ultima_excecao: Exception | None = None
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.get(url, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            ultima_excecao = e
            logger.warning(f"Tentativa {tentativa}/{tentativas} falhou para {url}: {e}")
            if tentativa < tentativas:
                time.sleep(backoff_base_s * (2 ** (tentativa - 1)))
    raise ultima_excecao
