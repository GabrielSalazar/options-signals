"""Option structure builder service."""
import logging
from typing import Optional

from backend.core.constants import OTM_DEFAULT

logger = logging.getLogger("option_builder")


class OptionBuilder:
    """Build option structures with strikes, Greeks, and pricing."""

    def build(
        self,
        ticker_base: str,
        preco: float,
        tipo_sinal: str,
        direcao_label: str,
        greeks: dict,
        dte: int,
        strike_ref: float,
        dist_otm: float,
        iv_impl: float,
        hv_20d: float,
        **kwargs
    ) -> dict:
        """Build option structure.

        Returns dict with strike, greeks, targets, etc.
        """
        return {
            "ticker_opcao": f"{ticker_base}{dte}",
            "strike_ref": strike_ref,
            "dist_otm": dist_otm,
            "dte": dte,
            "greeks": greeks,
            "iv_impl": iv_impl,
            "hv_20d": hv_20d,
            "premio_est": greeks.get("theta", 0.1),
            "preco_tela": greeks.get("premium", preco * 0.02),
            "entrada_min": preco * 0.95,
            "entrada_max": preco * 1.05,
            "alvo1": preco * 1.05 if "CALL" in tipo_sinal else preco * 0.95,
            "alvo2": preco * 1.10 if "CALL" in tipo_sinal else preco * 0.90,
            "alvo_final": preco * 1.15 if "CALL" in tipo_sinal else preco * 0.85,
            "stop": preco * 0.90 if "CALL" in tipo_sinal else preco * 1.10,
            "book_until": "16:30",
            "rr_alvo1": 1.5,
            "rr_alvo2": 2.0,
            "rr_final": 3.0,
        }
