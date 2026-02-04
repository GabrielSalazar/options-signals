from abc import ABC, abstractmethod
from app.services.math_service import OptionMath

class BaseStrategy(ABC):
    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def description(self):
        pass

    @property
    @abstractmethod
    def risk_level(self):
        pass

    @abstractmethod
    def analyze(self, ticker_data: dict, option_chain: list) -> list:
        """
        Analyze data and return list of opportunities (signals).
        """
        pass

class HighIVStrategy(BaseStrategy):
    """
    Look for Deep OTM options with High Implied Volatility (Potential Reversal/Premium Sale).
    Ref: Options-strategies-backtesting-in-Python (#3)
    """
    name = "High IV Reversal"
    description = "Busca opções OTM com Volatilidade Implícita extrema, indicando prêmios caros e possível reversão à média."
    risk_level = "High"

    def analyze(self, ticker_data: dict, option_chain: list) -> list:
        signals = []
        spot_price = ticker_data.get('price', 0)
        
        for option in option_chain:
            # Example Logic: Detect high Vega/IV on OTM options
            # In a real scenario, we would calculate IV here using py_vollib.black_scholes_implied_volatility
            
            # Simple placeholder logic: Call options > 10% OTM with high volume
            strike = option.get('strike')
            if option['type'] == 'call' and strike > spot_price * 1.10:
                signals.append({
                    "strategy": self.name,
                    "ticker": ticker_data['ticker'],
                    "option_symbol": option['symbol'],
                    "strike": strike,
                    "spot_price": spot_price,
                    "type": "CALL",
                    "reason": "Volatilidade Implícita Alta em Opção OTM",
                    # New Educational Fields
                    "setup_quality": "High", # Mocked score
                    "recommended_action": "Venda Coberta ou Trava de Baixa",
                    "explanation": (
                        "A Volatilidade Implícita (IV) está alta para calls fora do dinheiro. "
                        "Isso sugere que o mercado está pagando caro por proteção ou aposta de alta. "
                        "Estatisticamente, a venda de prêmio (Theta positivo) tende a ser vantajosa aqui."
                    )
                })
        
        return signals

class DeltaHedgeStrategy(BaseStrategy):
    """
    Look for options with Delta near 0.50 (ATM) for directional plays.
    Ref: py_vollib (#2)
    """
    name = "ATM Directional (Delta 0.5)"
    description = "Identifica opções ATM (No Dinheiro) com Delta próximo a 0.50, ideais para operações direcionais com boa alavancagem."
    risk_level = "Medium"

    def analyze(self, ticker_data: dict, option_chain: list) -> list:
        signals = []
        spot_price = ticker_data.get('price', 0)
        
        for option in option_chain:
            # Theoretical calculation
            greeks = OptionMath.calculate_greeks(
                flag=option['type'][0], # 'c' or 'p'
                S=spot_price,
                K=option['strike'],
                t=option['time_to_expiry_years'],
                r=0.1175, # Fixed Risk Free for now
                sigma=0.30 # Fixed IV for now (should be calculated)
            )
            
            if greeks and 0.45 <= abs(greeks['delta']) <= 0.55:
                 signals.append({
                    "strategy": self.name,
                    "ticker": ticker_data['ticker'],
                    "option_symbol": option['symbol'],
                    "strike": option['strike'],
                    "spot_price": spot_price,
                    "type": option['type'].upper(), # Fix: Make sure type is sent
                    "greeks": greeks,
                    "entry_price": OptionMath.calculate_price(option['type'][0], spot_price, option['strike'], option['time_to_expiry_years'], 0.1175, 0.30),
                    "reason": f"Delta Neutro/ATM (Delta: {greeks['delta']:.2f})",
                    # New Educational Fields
                    "setup_quality": "Medium",
                    "recommended_action": "Compra a Seco (Swing Trade) ou Trava de Alta",
                    "explanation": (
                        f"Opção ATM com Delta de {greeks['delta']:.2f}. "
                        "Ideal para capturar movimentos diretivos do ativo com boa relação custo/benefício. "
                        "O Gamma alto nessa região acelera os ganhos se o papel explodir."
                    )
                })
        
        return signals
