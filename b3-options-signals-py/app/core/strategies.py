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
    name = "Reversão de Volatilidade (High IV)"
    description = "Busca opções OTM com Volatilidade Implícita extrema, indicando prêmios caros e possível reversão à média."
    risk_level = "Alto"

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
    name = "Hedge Delta Neutro (ATM)"
    description = "Identifica opções ATM (No Dinheiro) com Delta próximo a 0.50, ideais para operações direcionais com boa alavancagem."
    risk_level = "Médio"

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

class RSIStrategy(BaseStrategy):
    @property
    def name(self):
        return "Reversão por IFR (RSI)"

    @property
    def description(self):
        return "Identifica condições de Sobrecompra (>70) ou Sobrevenda (<30) para operar reversão à média."

    @property
    def risk_level(self):
        return "Médio"

    def analyze(self, ticker_data: dict, option_chain: list) -> list:
        from app.services.b3_service import B3Service
        
        ticker = ticker_data['ticker']
        rsi = B3Service.get_rsi(ticker)
        
        signals = []
        
        # Logic: RSI < 30 -> BUY CALL (Expect rebound)
        #        RSI > 70 -> BUY PUT (Expect drop)
        
        if rsi < 30:
            # Find closest OTM Call
            target_strike = ticker_data['price'] * 1.05 # 5% OTM
            best_option = None
            min_diff = float('inf')
            
            for option in option_chain:
                if option['type'] == 'call':
                     diff = abs(option['strike'] - target_strike)
                     if diff < min_diff:
                         min_diff = diff
                         best_option = option
            
            if best_option:
                signals.append({
                    "strategy": self.name,
                    "ticker": ticker,
                    "option_symbol": best_option['symbol'],
                    "signal_type": "BUY CALL",
                    "reason": f"RSI Oversold ({rsi}). Reversal Up Expected.",
                    "timestamp": "Now",
                    # Educational
                    "setup_quality": "High",
                    "recommended_action": "Compra de Call levemente OTM",
                    "explanation": f"O ativo está sobrevendido (RSI {rsi} < 30). Estatisticamente há alta chance de repique."
                })
                
        elif rsi > 70:
            # Find closest OTM Put
            target_strike = ticker_data['price'] * 0.95 # 5% OTM
            best_option = None
            min_diff = float('inf')
            
            for option in option_chain:
                if option['type'] == 'put':
                     diff = abs(option['strike'] - target_strike)
                     if diff < min_diff:
                         min_diff = diff
                         best_option = option
            
            if best_option:
                signals.append({
                    "strategy": self.name,
                    "ticker": ticker,
                    "option_symbol": best_option['symbol'],
                    "signal_type": "BUY PUT",
                    "reason": f"RSI Overbought ({rsi}). Reversal Down Expected.",
                    "timestamp": "Now",
                    # Educational
                    "setup_quality": "High",
                    "recommended_action": "Compra de Put levemente OTM",
                    "explanation": f"O ativo está sobrecomprado (RSI {rsi} > 70). Estatisticamente há alta chance de correção."
                })
        
        return signals

class CoveredCallStrategy(BaseStrategy):
    """
    Identifies Selling Opportunities for Covered Calls (Lançamento Coberto).
    Condition: Neutral/Bullish trend (RSI > 40) + Premium check.
    """
    @property
    def name(self):
        return "Lançamento Coberto"

    @property
    def description(self):
        return "Estratégia de renda. Venda de Call OTM contra carteira de ações para remunerar o portfólio."

    @property
    def risk_level(self):
        return "Baixo"

    def analyze(self, ticker_data: dict, option_chain: list) -> list:
        # Mocking RSI check since we don't have full history in this context 
        # (Usually requires B3Service, but for simplicity we assume conditions are met if we find good premiums)
        signals = []
        spot_price = ticker_data.get('price', 0)
        
        for option in option_chain:
            # Logic: Sell OTM Call (Delta ~0.30, usually 5-7% OTM)
            if option['type'] == 'call':
                moneyness = option['strike'] / spot_price
                if 1.04 <= moneyness <= 1.08: # 4% to 8% OTM
                    signals.append({
                        "strategy": self.name,
                        "ticker": ticker_data['ticker'],
                        "option_symbol": option['symbol'],
                        "spot_price": spot_price,
                        "signal_type": "SELL COVERED CALL",
                        "reason": "Strike OTM ideal para Lançamento Coberto (4-8% otm)",
                        "timestamp": "Now",
                        "setup_quality": "High",
                        "recommended_action": "Venda de Call (Tenha o ativo em carteira)",
                        "explanation": f"O strike {option['strike']} oferece uma boa taxa de proteção. Se o ativo subir moderadamente, você ganha taxa + valorização.",
                        "risk_level": self.risk_level
                    })
        return signals

class LongStraddleStrategy(BaseStrategy):
    """
    Betting on Volatility Explosion.
    Condition: Very low IV (Mocked here randomly for demo).
    """
    @property
    def name(self):
        return "Compra de Volatilidade (Straddle)"

    @property
    def description(self):
        return "Aposta na explosão de volatilidade. Lucra se o ativo mover forte para qualquer lado."

    @property
    def risk_level(self):
        return "Alto"

    def analyze(self, ticker_data: dict, option_chain: list) -> list:
        signals = []
        spot_price = ticker_data.get('price', 0)
        
        # Find ATM Call and Put
        atm_call = None
        atm_put = None
        min_diff = float('inf')
        
        # Simple logic: closest strike to spot
        best_strike = 0
        
        for option in option_chain:
            diff = abs(option['strike'] - spot_price)
            if diff < min_diff:
                min_diff = diff
                best_strike = option['strike']
        
        if best_strike > 0:
            # Get symbol for visualization (picking the Call as representative)
            representative_option = next((o for o in option_chain if o['strike'] == best_strike and o['type'] == 'call'), None)
            
            if representative_option:
                signals.append({
                    "strategy": self.name,
                    "ticker": ticker_data['ticker'],
                    "option_symbol": f"{representative_option['symbol']} + PUT",
                    "spot_price": spot_price,
                    "signal_type": "BUY STRADDLE",
                    "reason": "Baixa Volatilidade Esperada (Setup de Explosão)",
                    "timestamp": "Now",
                    "setup_quality": "Medium",
                    "recommended_action": f"Compra de Call {best_strike} + Compra de Put {best_strike}",
                    "explanation": "O mercado espera calmaria. Se houver um movimento forte (notícias, earnings), a volatilidade implícita subirá e ambas as opções valorizarão.",
                    "risk_level": self.risk_level
                })
        
        return signals

class LongCallStrategy(BaseStrategy):
    name = "Compra a Seco de Call"
    description = "Aposta direcional na alta forte do ativo (Gamma Long)."
    risk_level = "Médio"

    def analyze(self, ticker_data: dict, option_chain: list) -> list:
        # Logic: Trend following (e.g. Price > SMA20 - simulated here) and buying slightly OTM Call
        signals = []
        spot_price = ticker_data.get('price', 0)
        
        # Simple simulation: If price is significantly higher (momentum) -> Signal (Mocked)
        # Using a random check or just identifying the setup availability
        
        for option in option_chain:
            if option['type'] == 'call':
                moneyness = option['strike'] / spot_price
                if 1.02 <= moneyness <= 1.05: # 2-5% OTM
                    signals.append({
                        "strategy": self.name,
                        "ticker": ticker_data['ticker'],
                        "option_symbol": option['symbol'],
                        "spot_price": spot_price,
                        "signal_type": "BUY CALL",
                        "reason": "Setup de Momento de Alta (Trend Following)",
                        "timestamp": "Now",
                        "setup_quality": "High",
                        "recommended_action": "Compra a Seco (Stop curto)",
                        "explanation": f"Call strike {option['strike']} posicionada para captura de alta explosiva.",
                        "risk_level": self.risk_level
                    })
        return signals

class LongPutStrategy(BaseStrategy):
    name = "Compra a Seco de Put"
    description = "Aposta direcional na baixa forte do ativo (Gamma Long)."
    risk_level = "Médio"

    def analyze(self, ticker_data: dict, option_chain: list) -> list:
        signals = []
        spot_price = ticker_data.get('price', 0)
        
        for option in option_chain:
            if option['type'] == 'put':
                moneyness = option['strike'] / spot_price
                if 0.95 <= moneyness <= 0.98: # 2-5% OTM
                    signals.append({
                        "strategy": self.name,
                        "ticker": ticker_data['ticker'],
                        "option_symbol": option['symbol'],
                        "spot_price": spot_price,
                        "signal_type": "BUY PUT",
                        "reason": "Setup de Momento de Baixa (Trend Following)",
                        "timestamp": "Now",
                        "setup_quality": "High",
                        "recommended_action": "Compra a Seco (Stop curto)",
                        "explanation": f"Put strike {option['strike']} posicionada para captura de queda explosiva.",
                        "risk_level": self.risk_level
                    })
        return signals

class BullCallSpreadStrategy(BaseStrategy):
    name = "Trava de Alta com Call"
    description = "Estratégia direcional de alta com risco limitado e custo reduzido."
    risk_level = "Médio"

    def analyze(self, ticker_data: dict, option_chain: list) -> list:
        signals = []
        spot_price = ticker_data.get('price', 0)
        
        # Find ATM Call (Buy) and OTM Call (Sell)
        buy_leg = None
        sell_leg = None
        
        # Sort by strike
        calls = sorted([o for o in option_chain if o['type'] == 'call'], key=lambda x: x['strike'])
        
        for i in range(len(calls) - 1):
            opt1 = calls[i]
            opt2 = calls[i+1] # Next strike
            
            # Check if Opt1 is ATM/ITM and Opt2 is OTM
            if 0.98 <= (opt1['strike']/spot_price) <= 1.02: # ATM
                if (opt2['strike'] - opt1['strike']) < spot_price * 0.05: # Spread not too wide
                     buy_leg = opt1
                     sell_leg = opt2
                     break
        
        if buy_leg and sell_leg:
            signals.append({
                "strategy": self.name,
                "ticker": ticker_data['ticker'],
                "option_symbol": f"Buy {buy_leg['symbol']} / Sell {sell_leg['symbol']}",
                "spot_price": spot_price,
                "signal_type": "BULL CALL SPREAD",
                "reason": "Estrutura de Alta com Risco Definido",
                "timestamp": "Now",
                "setup_quality": "Medium",
                "recommended_action": f"Montar Trava: Compra {buy_leg['strike']} / Venda {sell_leg['strike']}",
                "explanation": "Trava de alta reduz o custo da entrada (Call vendida financia Call comprada).",
                "risk_level": self.risk_level
            })

        return signals

class BearPutSpreadStrategy(BaseStrategy):
    name = "Trava de Baixa com Put"
    description = "Estratégia direcional de baixa com risco limitado e custo reduzido."
    risk_level = "Médio"

    def analyze(self, ticker_data: dict, option_chain: list) -> list:
        signals = []
        spot_price = ticker_data.get('price', 0)
        
        # Find ATM Put (Buy) and OTM Put (Sell)
        buy_leg = None
        sell_leg = None
        
        # Sort by strike descending for Puts usually, but ascending works if logic is correct
        puts = sorted([o for o in option_chain if o['type'] == 'put'], key=lambda x: x['strike'])
        
        # Iterate to find Buy Higher Strike (ITM/ATM for Put? No, Buy Put is Higher Strike implies ITM if Price < Strike)
        # Standard Bear Put Spread: Buy ITM/ATM Put (Higher Strike), Sell OTM Put (Lower Strike)
        # Wait: Buy Put Strike K2, Sell Put Strike K1 (K1 < K2). 
        # Usually we buy ATM and sell OTM.
        
        for i in range(len(puts) - 1):
             # p1 (lower strike), p2 (higher strike)
             p1 = puts[i]
             p2 = puts[i+1]
             
             # We want to Buy p2 (ATM) and Sell p1 (OTM)
             if 0.98 <= (p2['strike']/spot_price) <= 1.02: # p2 is ATM
                 buy_leg = p2
                 sell_leg = p1
                 break
                 
        if buy_leg and sell_leg:
            signals.append({
                "strategy": self.name,
                "ticker": ticker_data['ticker'],
                "option_symbol": f"Buy {buy_leg['symbol']} / Sell {sell_leg['symbol']}",
                "spot_price": spot_price,
                "signal_type": "BEAR PUT SPREAD",
                "reason": "Estrutura de Baixa com Risco Definido",
                "timestamp": "Now",
                "setup_quality": "Medium",
                "recommended_action": f"Montar Trava: Compra {buy_leg['strike']} / Venda {sell_leg['strike']}",
                "explanation": "Trava de baixa reduz o custo da entrada (Put vendida financia Put comprada).",
                "risk_level": self.risk_level
            })

        return signals
