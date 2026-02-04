from abc import ABC, abstractmethod
import pandas as pd
import numpy as np

# Classe Abstrata Base para Estratégias Vetorizadas
class VectorizedStrategy(ABC):
    @property
    @abstractmethod
    def name(self):
        """Nome da estratégia"""
        pass

    @property
    @abstractmethod
    def risk_level(self):
        """Nível de risco (Baixo, Médio, Alto, Crítico)"""
        pass

    @abstractmethod
    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        """
        Analisa o DataFrame da Cadeia de Opções e retorna um DataFrame com os sinais encontrados.
        Colunas esperadas em chain_df: ['symbol', 'strike', 'type', 'time_to_expiry', 'bid', 'ask', 'last', 'iv', 'delta', 'theta']
        """
        pass

# --- ESTRATÉGIAS BÁSICAS ---

class HighIVStrategy(VectorizedStrategy):
    name = "Reversão de Volatilidade (High IV)"
    risk_level = "Alto"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        spot_price = ticker_data.get('price', 0)
        
        # Filtro Vetorizado: Call Options, >10% OTM, IV Alto
        # Usa operações vetorizadas do Pandas ao invés de loops lentos
        mask = (
            (chain_df['type'] == 'call') & 
            (chain_df['strike'] > spot_price * 1.10)
            # Em produção, adicionaríamos filtro de 'iv' > percentil 80
        )
        
        candidates = chain_df[mask].copy()
        
        if not candidates.empty:
            candidates['strategy'] = self.name
            candidates['signal_type'] = 'SELL CALL'
            candidates['reason'] = 'Volatilidade Implícita Alta (OTM)'
            candidates['recommended_action'] = 'Venda Coberta ou Trava de Baixa'
            candidates['risk_level'] = self.risk_level
            
        return candidates

class DeltaHedgeStrategy(VectorizedStrategy):
    name = "Hedge Delta Neutro (ATM)"
    risk_level = "Médio"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        # Filtra opções ATM (Moneyness entre 0.98 e 1.02)
        # Busca neutralidade de Delta (próximo de 0.50 para Calls ATM)
        spot_price = ticker_data.get('price', 0)
        
        moneyness = chain_df['strike'] / spot_price
        mask = (moneyness >= 0.98) & (moneyness <= 1.02)
        
        candidates = chain_df[mask].copy()
        
        if not candidates.empty:
            candidates['strategy'] = self.name
            candidates['signal_type'] = 'BUY ATM' 
            candidates['reason'] = 'Delta Neutro / ATM'
            candidates['recommended_action'] = 'Compra a Seco (Swing Trade)'
            candidates['risk_level'] = self.risk_level
            
        return candidates

class RSIStrategy(VectorizedStrategy):
    name = "Reversão por IFR (RSI)"
    risk_level = "Médio"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        # Estratégia baseada no indicador RSI (Índice de Força Relativa)
        # Assume que o RSI já foi calculado e passado em ticker_data
        
        rsi = ticker_data.get('rsi', 50)
        spot_price = ticker_data['price']
        candidates = pd.DataFrame()

        if rsi < 30:
            # Sobrevenda (Oversold) -> Sinal de Compra de Call (Repique)
            # Busca Calls levemente OTM (~5%) para pegar a volta
            target_strike = spot_price * 1.05
            calls = chain_df[chain_df['type'] == 'call'].copy()
            
            # Lógica vetorizada para encontrar o strike mais próximo
            calls['dist'] = (calls['strike'] - target_strike).abs()
            best_idx = calls['dist'].idxmin() if not calls.empty else None
            
            if best_idx is not None:
                selection = calls.loc[[best_idx]].copy()
                selection['strategy'] = self.name
                selection['signal_type'] = 'BUY CALL'
                selection['reason'] = f'RSI em Sobrevenda ({rsi})'
                selection['recommended_action'] = 'Compra de Call levemente OTM'
                selection['risk_level'] = self.risk_level
                candidates = selection

        elif rsi > 70:
            # Sobrecompra (Overbought) -> Sinal de Compra de Put (Correção)
            target_strike = spot_price * 0.95
            puts = chain_df[chain_df['type'] == 'put'].copy()
            
            puts['dist'] = (puts['strike'] - target_strike).abs()
            best_idx = puts['dist'].idxmin() if not puts.empty else None
            
            if best_idx is not None:
                selection = puts.loc[[best_idx]].copy()
                selection['strategy'] = self.name
                selection['signal_type'] = 'BUY PUT'
                selection['reason'] = f'RSI em Sobrecompra ({rsi})'
                selection['recommended_action'] = 'Compra de Put levemente OTM'
                selection['risk_level'] = self.risk_level
                candidates = selection
                
        return candidates

class CoveredCallStrategy(VectorizedStrategy):
    name = "Lançamento Coberto"
    risk_level = "Baixo"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        spot_price = ticker_data.get('price', 0)
        
        # Venda de Call OTM (4% a 8% fora do dinheiro)
        # Gera renda com a taxa, assumindo que o usuário tem a ação
        moneyness = chain_df['strike'] / spot_price
        mask = (chain_df['type'] == 'call') & (moneyness >= 1.04) & (moneyness <= 1.08)
        
        candidates = chain_df[mask].copy()
        
        if not candidates.empty:
            candidates['strategy'] = self.name
            candidates['signal_type'] = 'SELL COVERED CALL'
            candidates['reason'] = 'Strike OTM ideal para taxa (4-8%)'
            candidates['recommended_action'] = 'Venda de Call (Tenha o ativo)'
            candidates['risk_level'] = self.risk_level
        
        return candidates

# --- ESTRATÉGIAS DIRECIONAIS BÁSICAS ---

class LongCallStrategy(VectorizedStrategy):
    name = "Compra a Seco de Call"
    risk_level = "Médio"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        spot_price = ticker_data['price']
        # Compra de Call levemente OTM (2-5%)
        # Aposta na alta do ativo
        moneyness = chain_df['strike'] / spot_price
        mask = (chain_df['type'] == 'call') & (moneyness >= 1.02) & (moneyness <= 1.05)
        
        candidates = chain_df[mask].copy()
        if not candidates.empty:
            candidates['strategy'] = self.name
            candidates['signal_type'] = 'BUY CALL'
            candidates['reason'] = 'Momentum de Alta (Simulado)'
            candidates['recommended_action'] = 'Compra a Seco'
            candidates['risk_level'] = self.risk_level
        return candidates

class LongPutStrategy(VectorizedStrategy):
    name = "Compra a Seco de Put"
    risk_level = "Médio"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        spot_price = ticker_data['price']
        # Compra de Put levemente OTM (2-5% abaixo do spot)
        # Aposta na queda do ativo
        moneyness = chain_df['strike'] / spot_price
        mask = (chain_df['type'] == 'put') & (moneyness >= 0.95) & (moneyness <= 0.98)
        
        candidates = chain_df[mask].copy()
        if not candidates.empty:
            candidates['strategy'] = self.name
            candidates['signal_type'] = 'BUY PUT'
            candidates['reason'] = 'Momentum de Baixa (Simulado)'
            candidates['recommended_action'] = 'Compra a Seco'
            candidates['risk_level'] = self.risk_level
        return candidates

class CashSecuredPutStrategy(VectorizedStrategy):
    name = "Cash Secured Put"
    risk_level = "Baixo-Médio"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        spot_price = ticker_data['price']
        # Venda de Put OTM (Strike < Spot). 3-7% OTM
        # Intenção de comprar o papel mais barato
        moneyness = chain_df['strike'] / spot_price
        mask = (chain_df['type'] == 'put') & (moneyness >= 0.93) & (moneyness <= 0.97)
        
        candidates = chain_df[mask].copy()
        if not candidates.empty:
            candidates['strategy'] = self.name
            candidates['signal_type'] = 'SELL PUT'
            candidates['reason'] = 'Strike ideal para entrada ou renda'
            candidates['recommended_action'] = 'Venda de Put (Tenha caixa)'
            candidates['risk_level'] = self.risk_level
        return candidates

# --- TRAVAS (SPREADS) ---

class BullCallSpreadStrategy(VectorizedStrategy):
    name = "Trava de Alta com Call"
    risk_level = "Médio"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        spot_price = ticker_data['price']
        # Compra Call ATM (0.98-1.02), Venda Call OTM (1.05-1.10)
        # Reduz custo da ponta comprado com a venda
        calls = chain_df[chain_df['type'] == 'call'].copy()
        calls['moneyness'] = calls['strike'] / spot_price
        
        buy_mask = (calls['moneyness'] >= 0.98) & (calls['moneyness'] <= 1.02)
        candidates = calls[buy_mask].copy()
        
        if not candidates.empty:
            candidates['strategy'] = self.name
            candidates['signal_type'] = 'BULL CALL SPREAD'
            candidates['reason'] = 'Alta Moderada'
            candidates['recommended_action'] = 'Compra ATM / Venda OTM (Strike superior)'
            candidates['risk_level'] = self.risk_level
        return candidates

class BearPutSpreadStrategy(VectorizedStrategy):
    name = "Trava de Baixa com Put"
    risk_level = "Médio"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        spot_price = ticker_data['price']
        # Compra Put ATM, Venda Put OTM (Strike mais baixo)
        puts = chain_df[chain_df['type'] == 'put'].copy()
        puts['moneyness'] = puts['strike'] / spot_price
        
        buy_mask = (puts['moneyness'] >= 0.98) & (puts['moneyness'] <= 1.02)
        candidates = puts[buy_mask].copy()
        
        if not candidates.empty:
            candidates['strategy'] = self.name
            candidates['signal_type'] = 'BEAR PUT SPREAD'
            candidates['reason'] = 'Baixa Moderada'
            candidates['recommended_action'] = 'Compra ATM / Venda OTM (Strike inferior)'
            candidates['risk_level'] = self.risk_level
        return candidates

# --- ESTRATÉGIAS DE VOLATILIDADE ---

class LongStraddleStrategy(VectorizedStrategy):
    name = "Compra de Volatilidade (Straddle)"
    risk_level = "Alto"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        spot_price = ticker_data['price']
        # Compra Call ATM + Compra Put ATM
        # Lucra com movimento forte para qualquer lado
        mask = (chain_df['type'] == 'call') & (np.isclose(chain_df['strike'], spot_price, rtol=0.01))
        candidates = chain_df[mask].copy()
        
        if not candidates.empty:
            candidates['strategy'] = self.name
            candidates['signal_type'] = 'BUY STRADDLE'
            candidates['reason'] = 'Explosão de Volatilidade'
            candidates['recommended_action'] = 'Compra Call ATM + Compra Put ATM'
            candidates['risk_level'] = self.risk_level
        return candidates

# --- ESTRATÉGIAS AVANÇADAS E COMBINAÇÕES ---

class StrangleStrategy(VectorizedStrategy):
    name = "Compra de Volatilidade (Strangle)"
    risk_level = "Alto"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        spot_price = ticker_data['price']
        # Long Call OTM + Long Put OTM
        # Apenas sinaliza se existirem ambas opções OTM
        call_cond = (chain_df['type'] == 'call') & (chain_df['strike'] > spot_price * 1.05)
        put_cond = (chain_df['type'] == 'put') & (chain_df['strike'] < spot_price * 0.95)
        
        if call_cond.any() and put_cond.any():
            df = pd.DataFrame([chain_df.iloc[0].to_dict()])
            df['strategy'] = self.name
            df['signal_type'] = 'BUY STRANGLE'
            df['symbol'] = "ESTRUTURA"
            df['reason'] = 'Explosão de Volatilidade (Custo < Straddle)'
            df['recommended_action'] = 'Compra Call OTM + Compra Put OTM'
            df['risk_level'] = self.risk_level
            return df
        return pd.DataFrame()

class ButterflyStrategy(VectorizedStrategy):
    name = "Borboleta (Butterfly)"
    risk_level = "Baixo"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        # Long ITM Call, Short 2x ATM Call, Long OTM Call
        # Lucro máximo no Strike ATM
        spot_price = ticker_data['price']
        mask = (chain_df['type'] == 'call') & (np.isclose(chain_df['strike'], spot_price, rtol=0.02))
        candidates = chain_df[mask].copy()
        
        if not candidates.empty:
            candidates['strategy'] = self.name
            candidates['signal_type'] = 'BUY BUTTERFLY'
            candidates['reason'] = 'Alvo no Strike ATM'
            candidates['recommended_action'] = 'Montar estrutura 1-2-1 com Calls'
            candidates['risk_level'] = self.risk_level
        return candidates

class IronButterflyStrategy(VectorizedStrategy):
    name = "Borboleta de Ferro (Iron Butterfly)"
    risk_level = "Médio"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        # Sell Straddle ATM + Buy Strangle OTM Protection
        # Geração de renda em baixa volatilidade
        spot_price = ticker_data['price']
        mask = (chain_df['type'] == 'call') & (np.isclose(chain_df['strike'], spot_price, rtol=0.02))
        candidates = chain_df[mask].copy()
        
        if not candidates.empty:
            candidates['strategy'] = self.name
            candidates['signal_type'] = 'SELL IRON BUTTERFLY'
            candidates['reason'] = 'Alta probabilidade em lateralização'
            candidates['recommended_action'] = 'Venda Straddle ATM + Compra Strangle OTM'
            candidates['risk_level'] = self.risk_level
        return candidates

class CalendarSpreadStrategy(VectorizedStrategy):
    name = "Trava de Calendário"
    risk_level = "Baixo"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        # Venda ATM Curto Prazo, Compra ATM Longo Prazo
        # Explora o decay (Theta) maior na opção curta
        spot_price = ticker_data['price']
        mask = (chain_df['type'] == 'call') & (np.isclose(chain_df['strike'], spot_price, rtol=0.02))
        candidates = chain_df[mask].copy()
        
        if not candidates.empty:
            candidates['strategy'] = self.name
            candidates['signal_type'] = 'CALENDAR SPREAD'
            candidates['reason'] = 'Explorar Theta Decay da curta'
            candidates['recommended_action'] = 'Venda Call Curta / Compra Call Longa (Mesmo Strike)'
            candidates['risk_level'] = self.risk_level
        return candidates

class DiagonalSpreadStrategy(VectorizedStrategy):
    name = "Trava Diagonal (PMCC)"
    risk_level = "Baixo-Médio"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        # Compra Call Longa ITM (Substituto da ação), Venda Call Curta OTM (Renda)
        spot_price = ticker_data['price']
        # Identify OTM calls for the short leg
        moneyness = chain_df['strike'] / spot_price
        mask = (chain_df['type'] == 'call') & (moneyness >= 1.05)
        candidates = chain_df[mask].copy()
        
        if not candidates.empty:
            candidates['strategy'] = self.name
            candidates['signal_type'] = 'DIAGONAL SPREAD'
            candidates['reason'] = 'Renda com custeio da longa'
            candidates['recommended_action'] = 'Compra Call Longa ITM / Venda Call Curta OTM'
            candidates['risk_level'] = self.risk_level
        return candidates

class CollarStrategy(VectorizedStrategy):
    name = "Collar (Proteção)"
    risk_level = "Baixo"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        # Long Stock + Long Put OTM (Hedge) + Short Call OTM (Financiamento)
        spot_price = ticker_data['price']
        # Find OTM Puts suitable for protection
        mask = (chain_df['type'] == 'put') & (chain_df['strike'] < spot_price * 0.95)
        candidates = chain_df[mask].copy()
        
        if not candidates.empty:
            candidates['strategy'] = self.name
            candidates['signal_type'] = 'COLLAR'
            candidates['reason'] = 'Proteção de Carteira (Custo Zero ou Baixo)'
            candidates['recommended_action'] = 'Compra Put OTM / Venda Call OTM'
            candidates['risk_level'] = self.risk_level
        return candidates

class ProtectivePutStrategy(VectorizedStrategy):
    name = "Protective Put (Seguro)"
    risk_level = "Baixo"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        # Long Stock + Long Put ATM/OTM
        spot_price = ticker_data['price']
        mask = (chain_df['type'] == 'put') & (chain_df['strike'] <= spot_price) & (chain_df['strike'] > spot_price * 0.90)
        candidates = chain_df[mask].copy()
        
        if not candidates.empty:
            candidates['strategy'] = self.name
            candidates['signal_type'] = 'BUY PROTECTIVE PUT'
            candidates['reason'] = 'Hedge contra Crash'
            candidates['recommended_action'] = 'Compra de Put para proteger carteira'
            candidates['risk_level'] = self.risk_level
        return candidates

class IronCondorStrategy(VectorizedStrategy):
    name = "Condor de Ferro (Iron Condor)"
    risk_level = "Baixo"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        # Estratégia Neutra (Market Neutral)
        # Ganha com a lateralidade e Theta decay
        
        if len(chain_df) > 10:
             df = pd.DataFrame([chain_df.iloc[0].to_dict()]) # Mock usando a primeira linha
             df['strategy'] = self.name
             df['signal_type'] = 'SELL IRON CONDOR'
             df['symbol'] = "ESTRUTURA"
             df['reason'] = 'Mercado Lateral'
             df['recommended_action'] = 'Venda Put Spread OTM + Venda Call Spread OTM'
             df['risk_level'] = self.risk_level
             return df
        return pd.DataFrame()

class JadeLizardStrategy(VectorizedStrategy):
    name = "Jade Lizard"
    risk_level = "Alto"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        # Short Put OTM + Bear Call Spread OTM
        # Renda sem risco de alta ilimitado
        if len(chain_df) > 10:
            df = pd.DataFrame([chain_df.iloc[0].to_dict()])
            df['strategy'] = self.name
            df['signal_type'] = 'SELL JADE LIZARD'
            df['symbol'] = "ESTRUTURA"
            df['reason'] = 'Coleta de Prêmio sem risco upside'
            df['recommended_action'] = 'Venda Put OTM + Venda Call Spread OTM'
            df['risk_level'] = self.risk_level
            return df
        return pd.DataFrame()

class ShortStrangleStrategy(VectorizedStrategy):
    name = "Venda de Strangle (Short Strangle)"
    risk_level = "Crítico"

    def analyze(self, ticker_data: dict, chain_df: pd.DataFrame) -> pd.DataFrame:
        # Sell OTM Call + Sell OTM Put
        # Aposta que o mercado NÃO vai se mover muito
        spot_price = ticker_data['price']
        call_cond = (chain_df['type'] == 'call') & (chain_df['strike'] > spot_price * 1.10)
        put_cond = (chain_df['type'] == 'put') & (chain_df['strike'] < spot_price * 0.90)
        
        if call_cond.any() and put_cond.any():
            df = pd.DataFrame([chain_df.iloc[0].to_dict()])
            df['strategy'] = self.name
            df['signal_type'] = 'SELL STRANGLE'
            df['symbol'] = "STRUCTURE"
            df['reason'] = 'Alta probabilidade (Lucro se não mover muito)'
            df['recommended_action'] = 'Venda Call OTM + Venda Put OTM (Risco Infinito)'
            df['risk_level'] = self.risk_level
            return df
        return pd.DataFrame()
