import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pandas_ta as ta
# import quantstats as qs # Lazy import
from app.core.strategies_vectorized import VectorizedStrategy
from app.services.math_service import OptionMath

import pandas as pd

class VectorizedBacktester:
    def __init__(self):
        self.risk_free_rate = 0.1175 # Selic aprox
        import quantstats as qs
        self.qs = qs
        
    async def run_backtest(self, strategy: VectorizedStrategy, ticker: str, days: int = 252, initial_capital: float = 10000.0) -> dict:
        """
        Executa Backtest simulando preços de opções via Black-Scholes.
        """
        print(f"DEBUG: Starting backtest for {ticker}")
        # 1. Busca Dados Históricos
        hist_df = await self._fetch_historical_data(ticker, days)
        if hist_df.empty:
            return {"error": "Dados históricos insuficientes"}

        # 2. Calcula Indicadores Técnicos (Usando Pandas TA)
        # Calcula RSI, MACD, Bollinger Bands, etc., pois as estratégias podem precisar
        try:
            hist_df.ta.rsi(length=14, append=True)
            hist_df.ta.bbands(length=20, std=2, append=True)
            hist_df.ta.sma(length=20, append=True)
            hist_df.ta.sma(length=200, append=True)
        except Exception as e:
            print(f"Erro ao calcular indicadores: {e}")

        trades = []
        active_trades = []
        equity_curve = [initial_capital]
        current_capital = initial_capital
        
        # 3. Loop de Simulação
        # Simula dia a dia para permitir gestão de risco complexa (embora seja menos eficiente que full vectorization, é mais flexível)
        
        for i in range(20, len(hist_df)): # Pula warm-up dos indicadores
            current_date = hist_df.index[i]
            row = hist_df.iloc[i]
            
            # --- A. Gestão de Trades Abertos (Saída) ---
            remaining_trades = []
            for trade in active_trades:
                # Atualiza preço da opção (Simulado via BS)
                # T: Time to maturity diminui
                new_dte = trade['dte_orig'] - (current_date - trade['entry_date']).days
                if new_dte <= 0:
                    # Expiração
                    exit_price = max(0, row['close'] - trade['strike']) if trade['type'] == 'call' else max(0, trade['strike'] - row['close'])
                    pnl = (exit_price - trade['entry_price']) * trade['quantity']
                    if 'SELL' in trade['signal_type']: pnl = -pnl # Short logic simplificada
                    
                    trade.update({'exit_date': current_date, 'exit_price': exit_price, 'pnl': pnl, 'reason': 'Expiração'})
                    trades.append(trade)
                    current_capital += (trade['invested'] + pnl) # Devolve margem + lucro/preju
                else:
                    # Recalcula preço teórico (Mark to Market)
                    t_years = new_dte / 365.0
                    theo_price = OptionMath.calculate_price(
                         'c' if 'CALL' in trade['option_type'] else 'p',
                         row['close'], trade['strike'], t_years, self.risk_free_rate, 0.30 # Vol fixa 30% por enqto
                    )
                    
                    # Stop Loss / Take Profit Simples
                    pnl_unrealized = (theo_price - trade['entry_price']) / trade['entry_price']
                    if 'SELL' in trade['signal_type']: pnl_unrealized = -pnl_unrealized
                    
                    exit_trade = False
                    if pnl_unrealized < -0.30: # Stop Loss -30%
                        exit_trade = True
                        reason = "Stop Loss"
                    elif pnl_unrealized > 0.50: # Take Profit +50%
                        exit_trade = True
                        reason = "Take Profit"
                        
                    if exit_trade:
                        realized_pnl = (theo_price - trade['entry_price']) * trade['quantity']
                        if 'SELL' in trade['signal_type']: realized_pnl = (trade['entry_price'] - theo_price) * trade['quantity']
                        
                        trade.update({'exit_date': current_date, 'exit_price': theo_price, 'pnl': realized_pnl, 'reason': reason})
                        trades.append(trade)
                        current_capital += (trade['invested'] + realized_pnl)
                    else:
                        remaining_trades.append(trade)
            
            active_trades = remaining_trades

            # --- B. Busca Novas Oportunidades (Entrada) ---
            # Gera Chain Simulado para o dia
            ticker_data = {
                "ticker": ticker,
                "price": row['close'],
                "rsi": row.get('RSI_14', 50)
            }
            
            chain_df = self._generate_daily_chain(ticker, row['close'], current_date)
            
            # Roda Estratégia
            signals_df = strategy.analyze(ticker_data, chain_df)
            
            if not signals_df.empty and current_capital > 0:
                # Pega o melhor sinal (ou todos, filtro simples aqui)
                best_signal = signals_df.iloc[0]
                
                # Tamanho da Posição (Ex: 10% do capital)
                position_size = current_capital * 0.10
                price = best_signal.get('last', best_signal.get('ask', 1.0)) # Preço da opção
                qty = int(position_size / price) if price > 0 else 0
                
                if qty > 0:
                    trade = {
                        "entry_date": current_date,
                        "ticker": ticker,
                        "option_symbol": best_signal['symbol'],
                        "strike": best_signal['strike'],
                        "option_type": best_signal['type'].upper(),
                        "signal_type": best_signal.get('signal_type', 'BUY'),
                        "entry_price": price,
                        "quantity": qty,
                        "invested": price * qty,
                        "dte_orig": int(best_signal['time_to_expiry'] * 365),
                        "strategy": strategy.name
                    }
                    active_trades.append(trade)
                    current_capital -= (price * qty) # Aloca capital
            
            # --- C. Update Equity ---
            # Equity = Capital Livre + Valor de Mercado das Posições Abertas
            open_equity = 0
            for t in active_trades:
                 # Recalcula valor atual aproximado (usando preço entrada ou recalcular BS se lento)
                 # Para simplificar na curva diária, usamos o 'invested' (aprox) ou idealmente MarkToMarket
                 open_equity += t['invested'] # Simplificação
                 
            equity_curve.append(current_capital + open_equity)

        # 4. Gera Métricas Finais
        metrics = self._calculate_performance(trades, equity_curve, initial_capital)
        return metrics

    async def _fetch_historical_data(self, ticker: str, days: int) -> pd.DataFrame:
        from app.data import B3RealData
        client = B3RealData()
        try:
            # Baixa mais dias para garantir indicadores (buffer)
            print(f"DEBUG: Fetching historical data for {ticker} via B3RealData...")
            df = await client.get_historico(ticker, days=days+100)
            
            print(f"DEBUG: Fetched {len(df)} rows.")
            if df.empty: return pd.DataFrame()
            
            # Ajuste de colunas para minúsculo
            df.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in df.columns]
            # Algumas versões do yf retornam MultiIndex nas colunas
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            # Rename se necessario (Close -> close)
            # Garante que temos as colunas necessárias
            rename_map = {
                'close': 'close', 'adj close': 'close', 
                'open': 'open', 'high': 'high', 'low': 'low', 'volume': 'volume'
            }
            df.rename(columns=rename_map, inplace=True)
            return df
        except Exception as e:
            print(f"Erro download: {e}")
            return pd.DataFrame()

    def _generate_daily_chain(self, ticker, spot_price, date) -> pd.DataFrame:
        """Gera chain simulado para um dia específico no passado"""
        strikes = np.arange(round(spot_price*0.8), round(spot_price*1.2), 1.0)
        # Assume vencimento fixo dali a 30 dias (Simplificação Roll)
        dte_years = 30 / 365.0
        
        data = []
        for k in strikes:
            # Call
            c_price = OptionMath.calculate_price('c', spot_price, k, dte_years, 0.1175, 0.30)
            data.append({'symbol': f"{ticker}C{int(k)}", 'type': 'call', 'strike': k, 'time_to_expiry': dte_years, 'last': c_price, 'ask': c_price})
            
            # Put
            p_price = OptionMath.calculate_price('p', spot_price, k, dte_years, 0.1175, 0.30)
            data.append({'symbol': f"{ticker}P{int(k)}", 'type': 'put', 'strike': k, 'time_to_expiry': dte_years, 'last': p_price, 'ask': p_price})
            
        return pd.DataFrame(data)

    def _calculate_performance(self, trades, equity_curve, initial_capital):
        if not trades:
            return {"total_trades": 0, "win_rate": 0, "total_return_pct": 0}
            
        df_trades = pd.DataFrame(trades)
        wins = df_trades[df_trades['pnl'] > 0]
        losses = df_trades[df_trades['pnl'] <= 0]
        
        win_rate = len(wins) / len(df_trades)
        total_pnl = df_trades['pnl'].sum()
        final_equity = equity_curve[-1]
        total_return_pct = ((final_equity - initial_capital) / initial_capital) * 100
        
        return {
            "total_trades": len(df_trades),
            "win_rate": round(win_rate * 100, 2),
            "total_return_pct": round(total_return_pct, 2),
            "total_profit": round(total_pnl, 2),
            "max_drawdown": 0, # Implementar calc
            "profit_factor": round(wins['pnl'].sum() / abs(losses['pnl'].sum()), 2) if not losses.empty else 999,
            "equity_curve": equity_curve[-50:], # Retorna últimos pontos para gráfico leve
            "trades_log": trades[-10:] # Sample
        }
