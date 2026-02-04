"""
Gerenciamento de Watchlist (Lista de Ativos Monitorados)
Permite configurar múltiplos ativos para escaneamento simultâneo
"""
import os
from typing import List

# Watchlist Padrão: Blue Chips Brasileiras
DEFAULT_WATCHLIST = [
    "PETR4",  # Petrobras
    "VALE3",  # Vale
    "ITUB4",  # Itaú
    "BBDC4",  # Bradesco
    "ABEV3",  # Ambev
    "WEGE3",  # WEG
    "RENT3",  # Localiza
    "SUZB3",  # Suzano
    "MGLU3",  # Magazine Luiza
    "B3SA3"   # B3
]

def get_watchlist() -> List[str]:
    """
    Retorna a watchlist configurada via variável de ambiente ou usa a padrão.
    Formato: WATCHLIST=PETR4,VALE3,ITUB4
    """
    env_watchlist = os.getenv("WATCHLIST")
    
    if env_watchlist:
        # Parse comma-separated list
        tickers = [t.strip().upper() for t in env_watchlist.split(",") if t.strip()]
        return tickers if tickers else DEFAULT_WATCHLIST
    
    return DEFAULT_WATCHLIST

def validate_ticker(ticker: str) -> bool:
    """
    Valida formato de ticker B3 (4 letras + 1 dígito).
    Exemplos válidos: PETR4, VALE3, ITUB4
    """
    import re
    pattern = r'^[A-Z]{4}[0-9]$'
    return bool(re.match(pattern, ticker.upper()))

def add_to_watchlist(ticker: str) -> bool:
    """
    Adiciona um ticker à watchlist (apenas validação, persistência via env).
    """
    if not validate_ticker(ticker):
        return False
    
    current = get_watchlist()
    if ticker.upper() not in current:
        # Em produção, isso seria salvo em DB ou arquivo de config
        print(f"✅ {ticker} adicionado à watchlist (temporário)")
        return True
    
    return False
