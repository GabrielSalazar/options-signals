
# Lista padrão de ativos para monitoramento
# Focando nos mais líquidos para opções na B3
DEFAULT_WATCHLIST = [
    "PETR4", "VALE3", "BOVA11", "BBDC4", "ITUB4", 
    "BBAS3", "JBSS3", "MGLU3", "VIIA3", "ABEV3",
    "WEGE3", "RENT3", "PRIO3", "ELET3", "SUZB3"
]

def get_watchlist():
    # Futuramente pode buscar do Banco de Dados
    return DEFAULT_WATCHLIST
