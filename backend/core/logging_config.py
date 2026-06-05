"""Configuração central de logging.

Silencia loggers de bibliotecas que emitem ruído esperado (tickers deslistados,
rate-limit) como ERROR, poluindo o log e escondendo erros reais da aplicação. [P1-4]
"""
import logging

# Bibliotecas cujo log de ERROR é esperado/ruidoso no nosso fluxo:
# - yfinance: "1 Failed download" / "possibly delisted; no price data found"
# - urllib3 / peewee: ruído de rede/ORM de baixo valor operacional
NOISY_LOGGERS = ("yfinance", "urllib3", "peewee")


def configure_logging(level: int = logging.INFO) -> None:
    """Configura o formato/nível raiz e silencia os loggers ruidosos.

    Os erros esperados de provider passam a ser invisíveis; o resumo agregado de
    cada scan (em signal_service.run_scan) continua dando a visão operacional.
    """
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger().setLevel(level)  # garante o nível mesmo se já houver handlers
    for nome in NOISY_LOGGERS:
        logging.getLogger(nome).setLevel(logging.CRITICAL)
