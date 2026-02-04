"""
Sistema de Classificação de Risco para Estratégias de Opções
Mapeia cada estratégia para seu nível de risco e perda máxima
"""

STRATEGY_RISK_MAP = {
    # 🟢 LOW RISK - Perda Limitada e Controlada
    "Cash Secured Put": {
        "level": "LOW",
        "icon": "🟢",
        "max_loss": "Capital Reservado (Strike × 100)",
        "description": "Risco limitado ao capital reservado para compra das ações"
    },
    "Covered Call": {
        "level": "LOW",
        "icon": "🟢",
        "max_loss": "Custo de Oportunidade",
        "description": "Risco de perder valorização acima do strike"
    },
    "Collar (Proteção)": {
        "level": "LOW",
        "icon": "🟢",
        "max_loss": "Diferença entre Strikes",
        "description": "Proteção com put, limitando ganhos e perdas"
    },
    "Protective Put (Seguro)": {
        "level": "LOW",
        "icon": "🟢",
        "max_loss": "Prêmio da Put + Diferença até Strike",
        "description": "Seguro contra queda, perda limitada"
    },
    
    # 🟡 MEDIUM RISK - Risco Controlado com Spreads
    "Trava de Alta com Call": {
        "level": "MEDIUM",
        "icon": "🟡",
        "max_loss": "Diferença entre Strikes - Crédito Recebido",
        "description": "Spread definido, risco e ganho limitados"
    },
    "Trava de Baixa com Put": {
        "level": "MEDIUM",
        "icon": "🟡",
        "max_loss": "Diferença entre Strikes - Crédito Recebido",
        "description": "Spread definido, risco e ganho limitados"
    },
    "Condor de Ferro (Iron Condor)": {
        "level": "MEDIUM",
        "icon": "🟡",
        "max_loss": "Largura do Spread - Crédito Recebido",
        "description": "Venda de volatilidade com risco definido"
    },
    "Borboleta (Butterfly)": {
        "level": "MEDIUM",
        "icon": "🟡",
        "max_loss": "Débito Pago",
        "description": "Estratégia neutra com risco limitado ao prêmio"
    },
    "Borboleta de Ferro (Iron Butterfly)": {
        "level": "MEDIUM",
        "icon": "🟡",
        "max_loss": "Largura do Spread - Crédito Recebido",
        "description": "Venda de volatilidade ATM com proteção"
    },
    "Trava de Calendário": {
        "level": "MEDIUM",
        "icon": "🟡",
        "max_loss": "Débito Pago",
        "description": "Exploração de decaimento temporal"
    },
    "Trava Diagonal (PMCC)": {
        "level": "MEDIUM",
        "icon": "🟡",
        "max_loss": "Débito Pago (Call Longa)",
        "description": "Poor Man's Covered Call - risco limitado"
    },
    "Jade Lizard": {
        "level": "MEDIUM",
        "icon": "🟡",
        "max_loss": "Diferença entre Strikes (Put Side)",
        "description": "Sem risco de alta, risco definido na baixa"
    },
    
    # 🔴 HIGH RISK - Perda Significativa Possível
    "Compra a Seco de Call": {
        "level": "HIGH",
        "icon": "🔴",
        "max_loss": "Prêmio Pago (100%)",
        "description": "Perda total do prêmio se expirar OTM"
    },
    "Compra a Seco de Put": {
        "level": "HIGH",
        "icon": "🔴",
        "max_loss": "Prêmio Pago (100%)",
        "description": "Perda total do prêmio se expirar OTM"
    },
    "Compra de Volatilidade (Straddle)": {
        "level": "HIGH",
        "icon": "🔴",
        "max_loss": "Soma dos Prêmios (Call + Put)",
        "description": "Perda total se o ativo não se mover"
    },
    "Compra de Volatilidade (Strangle)": {
        "level": "HIGH",
        "icon": "🔴",
        "max_loss": "Soma dos Prêmios (Call + Put)",
        "description": "Perda total se ficar entre os strikes"
    },
    "Reversão por IFR (RSI)": {
        "level": "HIGH",
        "icon": "🔴",
        "max_loss": "Prêmio Pago",
        "description": "Aposta direcional com perda do prêmio"
    },
    
    # 🚨 UNLIMITED RISK - Perda Ilimitada Possível
    "Reversão de Volatilidade (High IV)": {
        "level": "UNLIMITED",
        "icon": "🚨",
        "max_loss": "ILIMITADO (Venda Descoberta)",
        "description": "⚠️ PERIGO: Venda de opções sem proteção"
    },
    "Hedge Delta Neutro (ATM)": {
        "level": "UNLIMITED",
        "icon": "🚨",
        "max_loss": "ILIMITADO (Posição Descoberta)",
        "description": "⚠️ Requer hedge ativo constante"
    },
    "Venda de Strangle (Short Strangle)": {
        "level": "UNLIMITED",
        "icon": "🚨",
        "max_loss": "ILIMITADO (Ambos os Lados)",
        "description": "⚠️ PERIGO: Risco ilimitado em ambas direções"
    },
    "Lançamento Coberto": {
        "level": "LOW",
        "icon": "🟢",
        "max_loss": "Custo de Oportunidade",
        "description": "Equivalente a Covered Call"
    }
}

def get_risk_info(strategy_name: str) -> dict:
    """
    Retorna informações de risco para uma estratégia.
    """
    return STRATEGY_RISK_MAP.get(strategy_name, {
        "level": "MEDIUM",
        "icon": "🟡",
        "max_loss": "Consultar documentação",
        "description": "Risco não classificado"
    })

def get_risk_color(level: str) -> str:
    """
    Retorna a cor Tailwind CSS para o nível de risco.
    """
    colors = {
        "LOW": "green",
        "MEDIUM": "yellow",
        "HIGH": "red",
        "UNLIMITED": "purple"
    }
    return colors.get(level, "gray")
