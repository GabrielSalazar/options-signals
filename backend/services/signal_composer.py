"""Signal composition service."""
import logging
from datetime import datetime

logger = logging.getLogger("signal_composer")


class SignalComposer:
    """Compose final signal dict from components."""

    def compose(
        self,
        ticker_base: str,
        nome: str,
        tipo_sinal: str,
        direcao_label: str,
        structure: dict,
        gatilhos: dict,
        score: int,
        score_ponderado: Optional[int] = None,
    ) -> dict:
        """Compose final signal dict.

        Args:
            ticker_base: Stock ticker
            nome: Stock name
            tipo_sinal: Signal type (CALL_ALTA, etc)
            direcao_label: Direction label
            structure: Option structure dict
            gatilhos: Triggers dict
            score: Technical score
            score_ponderado: Shadow score

        Returns:
            Final signal dict ready for API/storage
        """
        return {
            "ticker": ticker_base,
            "nome": nome,
            "tipo_sinal": tipo_sinal,
            "direcao": direcao_label,
            "score": score,
            "score_ponderado": score_ponderado or score,
            "preco_acao": structure.get("entrada_min", 0),
            "ticker_opcao": structure.get("ticker_opcao", ""),
            "strike_ref": structure.get("strike_ref", 0),
            "alvo1": structure.get("alvo1", 0),
            "alvo2": structure.get("alvo2", 0),
            "alvo_final": structure.get("alvo_final", 0),
            "stop": structure.get("stop", 0),
            "data_sinal": datetime.now(),
            "gatilhos": gatilhos.get("sinais_alta", []) + gatilhos.get("sinais_baixa", []),
            "gatilhos_ids": gatilhos.get("ids_alta", []) + gatilhos.get("ids_baixa", []),
        }
