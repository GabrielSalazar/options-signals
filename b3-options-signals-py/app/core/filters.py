from app.core.risk_classifier import get_risk_info, STRATEGY_RISK_MAP
import math

class ScoreCalculator:
    """
    Calcula o Score de Confiança (0-100) para um sinal de opção.
    Baseado em múltiplos critérios: Técnico, Liquidez, Volatilidade e Gregas.
    """
    
    @staticmethod
    def calculate_score(signal: dict, chain_row: dict = None) -> int:
        score = 50 # Base score (Neutro)
        
        # 1. Alinhamento Técnico (Max 30 pts)
        # -----------------------------------
        technicals = signal.get('technicals', {})
        rsi = technicals.get('rsi', 50)
        strategy_type = signal.get('signal_type', '')
        
        # Lógica para estratégias de Reversão
        if 'RSI' in signal.get('strategy', ''):
            if 'BUY CALL' in strategy_type and rsi < 30: score += 20
            elif 'BUY PUT' in strategy_type and rsi > 70: score += 20
            elif 'BUY CALL' in strategy_type and rsi < 40: score += 10
            elif 'BUY PUT' in strategy_type and rsi > 60: score += 10
        
        # Lógica para estratégias Direcionais (Trend Following)
        elif 'BUY CALL' in strategy_type: # Ex: Long Call
             if rsi > 50 and rsi < 70: score += 10
        elif 'BUY PUT' in strategy_type: # Ex: Long Put
             if rsi < 50 and rsi > 30: score += 10

        # 2. Liquidez e Spread (Max 20 pts)
        # ---------------------------------
        # Se temos dados da cadeia (chain_row)
        if chain_row is not None:
             volume = chain_row.get('volume', 0)
             # Open Interest se disponível (assumindo que volume seja proxy se não tiver OI)
             
             if volume > 1000: score += 10
             elif volume > 100: score += 5
             
             # Spread Bid-Ask
             bid = chain_row.get('bid', 0)
             ask = chain_row.get('ask', 0)
             if ask > 0:
                 spread_pct = (ask - bid) / ask
                 if spread_pct < 0.05: score += 10 # Spread estreito (<5%)
                 elif spread_pct < 0.10: score += 5 # Spread ok (<10%)
                 elif spread_pct > 0.30: score -= 10 # Spread muito largo (Penalidade)
        
        # 3. Probabilidade (Delta) (Max 20 pts)
        # ------------------------------------
        # Se for venda de opção (Tetha Gang), queremos Delta baixo (OTM)
        if 'SELL' in strategy_type or 'SHORT' in strategy_type:
             delta = abs(chain_row.get('delta', 0.5)) if chain_row is not None else 0.5
             if delta < 0.30: score += 10 # Alta prob de expirar OTM
             if delta < 0.15: score += 10 # Muito alta prob (mas pouco prêmio)
        
        # 4. Volatilidade (Max 10 pts)
        # ---------------------------
        iv = technicals.get('iv', 0)
        # Se estratégia se beneficia de Vega alto (Venda)
        if 'SELL' in strategy_type and iv > 0.50: score += 10
        # Se estratégia se beneficia de Vega baixo (Compra)
        if 'BUY' in strategy_type and iv < 0.30: score += 10

        # 5. Penalidades de Risco (Risk Level)
        # -----------------------------------
        risk_level = signal.get('risk_level', 'MEDIUM')
        if risk_level == 'UNLIMITED': score -= 15
        if risk_level == 'HIGH': score -= 5
        if risk_level == 'LOW': score += 5
        
        # Cap Score 0-100
        return max(0, min(100, score))

class RiskManager:
    """
    Identifica bandeiras de risco (Risk Flags) para um sinal
    """
    
    @staticmethod
    def get_risk_flags(signal: dict, chain_row: dict = None) -> list:
        flags = []
        
        # 1. Risco Ilimitado
        risk_level = signal.get('risk_level', 'MEDIUM')
        if risk_level == 'UNLIMITED':
            flags.append("🚨 Risco Ilimitado")
            
        # 2. Risco de Liquidez
        if chain_row is not None:
            volume = chain_row.get('volume', 0)
            trades = chain_row.get('trades', 0) # Se disponível
            if volume < 50:
                 flags.append("⚠️ Baixa Liquidez")
            
            # 3. Risco de Spread
            bid = chain_row.get('bid', 0)
            ask = chain_row.get('ask', 0)
            if ask > 0:
                 spread_pct = (ask - bid) / ask
                 if spread_pct > 0.20:
                     flags.append("↔️ Spread Largo")

        # 4. Risco de Expiração (Gamma Risk)
        # Assumindo dados normalizados com 'time_to_expiry' em anos
        dte_years = chain_row.get('time_to_expiry', 100) if chain_row is not None else 100
        dte_days = dte_years * 365
        
        if dte_days < 3:
             flags.append("⏰ Expira em Breve (Gamma Risk)")
        
        # 5. Risco de Earnings (Simulado, idealmente viria de um calendário)
        # flags.append("📅 Balanço Próximo") # Placeholder
        
        return flags

def apply_filters(signals: list, min_score: int = 0) -> list:
    """
    Aplica pontuação e filtros numa lista de sinais brutos
    """
    enhanced_signals = []
    
    for signal in signals:
        # Recupera dados da cadeia embutidos no sinal (legs) ou passados contextualmente
        # Para simplificar na refatoração, vamos assumir que o scanner passa os dados necessários no signal dict
        # ou que o signal dict já tem as chaves necessárias
        
        # Extrai dados da primeira perna para análise (simplificação)
        leg_data = None
        if 'legs' in signal and len(signal['legs']) > 0:
             leg_data = signal['legs'][0]
             # Merge leg data with top level for scoring convenience if needed, 
             # but ScoreCalculator looks at chain_row (leg_data)
        
        # Calcula Score
        score = ScoreCalculator.calculate_score(signal, chain_row=leg_data)
        signal['confidence_score'] = score
        
        # Calcula Flags
        flags = RiskManager.get_risk_flags(signal, chain_row=leg_data)
        signal['risk_flags'] = flags
        
        if score >= min_score:
            enhanced_signals.append(signal)
            
    # Ordena por score decrescente
    enhanced_signals.sort(key=lambda x: x['confidence_score'], reverse=True)
    return enhanced_signals
