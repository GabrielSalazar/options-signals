"""Testes da configuração central de logging (P1-4: reduzir ruído de providers)."""
import logging
from backend.core.logging_config import configure_logging, NOISY_LOGGERS


def test_silencia_loggers_ruidosos():
    configure_logging()
    for nome in NOISY_LOGGERS:
        assert logging.getLogger(nome).level >= logging.ERROR, f"{nome} não foi silenciado"


def test_yfinance_silenciado_especificamente():
    """O spam 'possibly delisted'/'Failed download' vem do logger do yfinance."""
    configure_logging()
    assert logging.getLogger("yfinance").level >= logging.ERROR


def test_logger_da_app_nao_silenciado():
    configure_logging(level=logging.INFO)
    # o logger raiz fica no nível pedido; nossos logs (b3_*) continuam visíveis
    assert logging.getLogger().level == logging.INFO
