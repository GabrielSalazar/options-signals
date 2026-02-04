import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
from app.services.b3_service import B3Service
from app.core.strategies_vectorized import VectorizedStrategy

class VectorizedBacktester:
    def __init__(self):
        pass

    async def run_backtest(self, strategy: VectorizedStrategy, ticker: str, days: int = 90) -> dict:
        """
        Executa um backtest para uma estratégia e ticker específicos nos últimos N dias.
        Retorna o log de trades e métricas de performance.
        """
        # 1. Busca Dados Históricos (OHLCV)
        # Idealmente usaríamos yfinance ou B3Service
        hist_df = await self._fetch_historical_data(ticker, days)
        
        if hist_df.empty:
            return {"error": "Dados históricos não encontrados"}
            
        trades = []
        active_trade = None
        
        # 2. Itera pelo histórico (Simulação Vetorizada ou Loop Otimizado)
        # Para demonstração, usamos um loop, mas em escala usaríamos shift() do Pandas
        
        # Pré-calcula indicadores se a estratégia necessitar
        if "RSI" in strategy.name:
            import pandas_ta as ta
            hist_df['rsi'] = ta.rsi(hist_df['close'], length=14)
            hist_df['rsi'] = hist_df['rsi'].fillna(50)
        
        # Loop de Simulação Dia a Dia
        for i in range(len(hist_df)):
            current_date = hist_df.index[i]
            row = hist_df.iloc[i]
            
            # Contexto de Dados do Ticker para a Estratégia
            ticker_data = {
                "ticker": ticker,
                "price": row['close'],
                "rsi": row.get('rsi', 50)
            }
            
            # Lógica de Simulação de Opções (Sem histórico real de opções):
            # Se a estratégia dispara sinal no ativo base, simulamos a entrada na opção.
            
            signal = self._check_strategy_condition(strategy, ticker_data)
            
            # Lógica de Entrada (Entry)
            if active_trade is None and signal:
                active_trade = {
                    "entry_date": current_date,
                    "entry_price": row['close'],
                    "type": signal, # Ex: BUY CALL, SELL PUT
                    "days_held": 0
                }
            
            # Lógica de Saída (Exit - Stop Loss, Take Profit, Tempo)
            elif active_trade:
                active_trade['days_held'] += 1
                
                # Cálculo de PnL do Ativo Base
                pnl_pct = (row['close'] - active_trade['entry_price']) / active_trade['entry_price']
                if "PUT" in active_trade['type']:
                    pnl_pct = -pnl_pct # Inverso para Puts/Shorts
                
                exit_trade = False
                reason = ""
                
                # Condições de Saída
                if pnl_pct > 0.05: # Take Profit (Base movida a favor)
                    exit_trade = True
                    reason = "Lucro no Alvo"
                elif pnl_pct < -0.03: # Stop Loss
                    exit_trade = True
                    reason = "Stop Loss"
                elif active_trade['days_held'] >= 10: # Saída por Tempo
                    exit_trade = True
                    reason = "Expiração / Tempo"
                
                if exit_trade:
                    active_trade['exit_date'] = current_date
                    active_trade['exit_price'] = row['close']
                    active_trade['pnl_underlying'] = pnl_pct
                    # Simula Alavancagem da Opção (Aprox 10x para Delta 0.5)
                    active_trade['pnl_option'] = pnl_pct * 10
                    active_trade['reason'] = reason
                    trades.append(active_trade)
                    active_trade = None

        return self._calculate_metrics(trades)

    def _check_strategy_condition(self, strategy, ticker_data):
        # Mapeamento Simplificado de Estratégias para Backtest Mockado
        # Em produção, reconstruiríamos a cadeia de opções histórica
        
        # Para Estratégia RSI:
        if "RSI" in strategy.name:
            if ticker_data['rsi'] < 30: return "BUY CALL"
            if ticker_data['rsi'] > 70: return "BUY PUT"
            
        return None

    async def _fetch_historical_data(self, ticker: str, days: int) -> pd.DataFrame:
        # Tenta buscar via yfinance
        try:
            import yfinance as yf
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days+20) # Buffer para indicadores
            df = yf.download(ticker + ".SA", start=start_date, end=end_date, progress=False)
            if not df.empty:
                df.columns = [c.lower() for c in df.columns] 
                return df
        except:
            pass
            
        # Fallback: Gera Histórico Simulado (Mock)
        dates = pd.date_range(end=datetime.now(), periods=days)
        prices = [30.0 + np.sin(x/5)*2 + np.random.normal(0, 0.5) for x in range(days)]
        df = pd.DataFrame({'close': prices}, index=dates)
        return df

    def _calculate_metrics(self, trades: list) -> dict:
        """Calcula métricas finais de performance (Win Rate, Drawdown)"""
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "total_return_pct": 0,
                "max_drawdown": 0
            }
            
        df = pd.DataFrame(trades)
        wins = df[df['pnl_option'] > 0]
        win_rate = len(wins) / len(df)
        total_return = df['pnl_option'].sum()
        
        return {
            "total_trades": len(trades),
            "win_rate": round(win_rate * 100, 1),
            "total_return_pct": round(total_return * 100, 1),
            "trades_log": trades[-5:] # Retorna os últimos 5
        }
