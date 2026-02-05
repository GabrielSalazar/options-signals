from app.data import B3RealData, TechnicalIndicators, cache
from app.services.alerts import alert_service
from app.core.strategies_vectorized import (
    HighIVStrategy, DeltaHedgeStrategy, RSIStrategy, CoveredCallStrategy,
    LongCallStrategy, LongPutStrategy, CashSecuredPutStrategy,
    BullCallSpreadStrategy, BearPutSpreadStrategy,
    LongStraddleStrategy, IronCondorStrategy,
    StrangleStrategy, ButterflyStrategy, IronButterflyStrategy,
    CalendarSpreadStrategy, DiagonalSpreadStrategy, CollarStrategy,
    ProtectivePutStrategy, JadeLizardStrategy, ShortStrangleStrategy
)
from app.core.risk_classifier import get_risk_info
from app.core.filters import ScoreCalculator, RiskManager
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class SignalScanner:
    def __init__(self):
        self.data_client = B3RealData()
        self.tech_client = TechnicalIndicators()
        
        self.strategies = [
            HighIVStrategy(),
            DeltaHedgeStrategy(),
            RSIStrategy(),
            CoveredCallStrategy(),
            LongCallStrategy(),
            LongPutStrategy(),
            CashSecuredPutStrategy(),
            BullCallSpreadStrategy(),
            BearPutSpreadStrategy(),
            LongStraddleStrategy(),
            IronCondorStrategy(),
            StrangleStrategy(),
            ButterflyStrategy(),
            IronButterflyStrategy(),
            CalendarSpreadStrategy(),
            DiagonalSpreadStrategy(),
            CollarStrategy(),
            ProtectivePutStrategy(),
            JadeLizardStrategy(),
            ShortStrangleStrategy()
        ]
        
    async def scan_ticker(self, ticker: str):
        """
        Executa scan de estratégias para um ticker usando DADOS REAIS.
        """
        logger.info(f"Iniciando scan para {ticker} com dados reais")
        
        try:
            # 1. Busca Dados de Mercado (Real-time)
            cotacao = await self.data_client.get_cotacao(ticker)
            spot_price = cotacao['preco']
            
            # 2. Calcula Indicadores Técnicos (Real-time)
            # Busca histórico para cálculo
            try:
                hist = await self.data_client.get_historico(ticker, days=100)
                indicators = await self.tech_client.calculate_all(hist, ticker)
                rsi = indicators['rsi']
            except Exception as e:
                logger.warning(f"Não foi possível calcular indicadores para {ticker}: {e}")
                rsi = 50.0  # Fallback neutro
                
            ticker_data = {
                "ticker": ticker, 
                "price": spot_price, 
                "rsi": rsi,
                "volume": cotacao['volume'],
                "variation": cotacao['variacao']
            }
            
            # 3. Busca Cadeia de Opções (Real-time)
            chain_df = await self.data_client.get_cadeia_opcoes(ticker)
            
            if chain_df.empty:
                logger.warning(f"Nenhuma opção encontrada para {ticker}")
                return []
            
            # Normalização de colunas para compatibilidade com estratégias
            # De: ['ticker_opcao', 'underlying', 'tipo', 'strike', 'preco', 'volume', 'iv', 'delta']
            # Para: ['symbol', 'strike', 'type', 'last', 'iv', 'delta', 'bid', 'ask']
            
            chain_df = chain_df.rename(columns={
                'ticker_opcao': 'symbol',
                'preco': 'last',
                'tipo': 'type_raw'
            })
            
            # Normaliza type (CALL/PUT -> call/put)
            chain_df['type'] = chain_df['type_raw'].str.lower()
            
            # Colunas faltantes (mocked ou estimadas por enquanto)
            if 'bid' not in chain_df.columns:
                chain_df['bid'] = chain_df['last'] * 0.98  # Estimativa spread
            if 'ask' not in chain_df.columns:
                chain_df['ask'] = chain_df['last'] * 1.02  # Estimativa spread
            if 'theta' not in chain_df.columns:
                chain_df['theta'] = -0.05  # Valor padrão pequeno
            if 'time_to_expiry' not in chain_df.columns:
                chain_df['time_to_expiry'] = 20/252  # ~1 mês útil padrão
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados para {ticker}: {e}")
            return []

        all_signals = []
        

        # 4. Aplica Estratégias
        for strategy in self.strategies:
            try:
                # Retorna DataFrame com sinais
                signal_df = strategy.analyze(ticker_data, chain_df)
                
                if not signal_df.empty:
                    for _, row in signal_df.iterrows():
                        risk_info = get_risk_info(strategy.name)
                        
                        # Prepara dados para o ScoreCalculator
                        # O row (series) contem dados da opção, technicals vem do signal_dict ou context
                        
                        # Constrói o dicionário preliminar do sinal
                        signal_dict = {
                            "strategy": row.get('strategy', strategy.name),
                            "ticker": row.get('symbol', 'ESTRUTURA'),
                            "underlying": ticker,
                            "spot_price": spot_price,
                            "signal_type": row.get('signal_type', 'SIGNAL'),
                            "reason": row.get('reason', 'Sinal detectado'),
                            "timestamp": cotacao['timestamp'],
                            "recommendation": row.get('recommended_action', ''),
                            "risk_level": row.get('risk_level', strategy.risk_level),
                            "risk_info": risk_info,
                            "technicals": {
                                "rsi": rsi,
                                "iv": row.get('iv', 0)
                            },
                             "legs": [
                                {
                                    "symbol": row.get('symbol'),
                                    "strike": row.get('strike'),
                                    "type": row.get('type'),
                                    "action": row.get('signal_type', '').split(' ')[0],
                                    "bid": row.get('bid', 0),
                                    "ask": row.get('ask', 0),
                                    "volume": row.get('volume', 0),
                                    "delta": row.get('delta', 0),
                                    "time_to_expiry": row.get('time_to_expiry', 0)
                                }
                            ]
                        }
                        
                        # Calcula Score e Risk Flags usando o módulo filters
                        # Passamos o row (que atua como chain_row) para dados de liquidez/gregas
                        # Converter row p/ dict para segurança
                        chain_row_dict = row.to_dict()
                        score = ScoreCalculator.calculate_score(signal_dict, chain_row_dict)
                        flags = RiskManager.get_risk_flags(signal_dict, chain_row_dict)
                        
                        signal_dict['confidence_score'] = score
                        signal_dict['risk_flags'] = flags
                        
                        all_signals.append(signal_dict)
                        # Fire and forget alert
                        await alert_service.send_signal(signal_dict)
                        
            except Exception as e:
                logger.error(f"Erro na estratégia {strategy.name} para {ticker}: {e}")
                continue
                    
        logger.info(f"Scan finalizado para {ticker}: {len(all_signals)} sinais encontrados")
        return all_signals

scanner = SignalScanner()
