"""
Módulo para cálculo de indicadores técnicos com dados reais.

Usa TA-lib e pandas_ta para calcular:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- SMA (Simple Moving Average)
- Volume Profile
"""

import pandas as pd
import pandas_ta as ta
from typing import Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Calcula indicadores técnicos com dados reais."""
    
    def __init__(self):
        self.cache = {}  # Cache simples em memória
        self.cache_ttl = 300  # 5 minutos
    
    async def calculate_all(self, df: pd.DataFrame, ticker: str) -> Dict:
        """
        Calcula todos os indicadores técnicos.
        
        Args:
            df: DataFrame com OHLCV (histórico)
            ticker: Ticker do ativo
            
        Returns:
            Dict com todos os indicadores calculados
        """
        logger.info(f"Calculando indicadores técnicos para {ticker}")
        
        if df.empty or len(df) < 50:
            logger.warning(f"Dados insuficientes para calcular indicadores: {len(df)} linhas")
            return self._get_default_indicators()
        
        try:
            # Copia DataFrame para não modificar original
            data = df.copy()
            
            # RSI
            rsi = self._calculate_rsi(data)
            
            # MACD
            macd_data = self._calculate_macd(data)
            
            # Bollinger Bands
            bb_data = self._calculate_bollinger(data)
            
            # SMAs
            sma_data = self._calculate_smas(data)
            
            # Volume analysis
            volume_data = self._analyze_volume(data)
            
            indicators = {
                'ticker': ticker,
                'timestamp': datetime.now().isoformat(),
                'rsi': rsi,
                'macd': macd_data,
                'bollinger': bb_data,
                'sma': sma_data,
                'volume': volume_data,
                'trend': self._determine_trend(data, sma_data),
                'signals': self._generate_signals(rsi, macd_data, bb_data)
            }
            
            logger.info(f"Indicadores calculados para {ticker}: RSI={rsi:.1f}, Trend={indicators['trend']}")
            return indicators
            
        except Exception as e:
            logger.error(f"Erro ao calcular indicadores para {ticker}: {e}")
            return self._get_default_indicators()
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calcula RSI."""
        try:
            df.ta.rsi(length=period, append=True)
            rsi_col = f'RSI_{period}'
            
            if rsi_col in df.columns:
                rsi = df[rsi_col].iloc[-1]
                return float(rsi) if pd.notna(rsi) else 50.0
            
            return 50.0
        except Exception as e:
            logger.debug(f"Erro ao calcular RSI: {e}")
            return 50.0
    
    def _calculate_macd(self, df: pd.DataFrame) -> Dict:
        """Calcula MACD."""
        try:
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
            
            macd = df['MACD_12_26_9'].iloc[-1] if 'MACD_12_26_9' in df.columns else 0.0
            signal = df['MACDs_12_26_9'].iloc[-1] if 'MACDs_12_26_9' in df.columns else 0.0
            histogram = df['MACDh_12_26_9'].iloc[-1] if 'MACDh_12_26_9' in df.columns else 0.0
            
            return {
                'macd': float(macd) if pd.notna(macd) else 0.0,
                'signal': float(signal) if pd.notna(signal) else 0.0,
                'histogram': float(histogram) if pd.notna(histogram) else 0.0,
                'crossover': 'bullish' if macd > signal else 'bearish' if macd < signal else 'neutral'
            }
        except Exception as e:
            logger.debug(f"Erro ao calcular MACD: {e}")
            return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0, 'crossover': 'neutral'}
    
    def _calculate_bollinger(self, df: pd.DataFrame, period: int = 20, std: int = 2) -> Dict:
        """Calcula Bollinger Bands."""
        try:
            df.ta.bbands(length=period, std=std, append=True)
            
            upper = df[f'BBU_{period}_{std}.0'].iloc[-1] if f'BBU_{period}_{std}.0' in df.columns else None
            middle = df[f'BBM_{period}_{std}.0'].iloc[-1] if f'BBM_{period}_{std}.0' in df.columns else None
            lower = df[f'BBL_{period}_{std}.0'].iloc[-1] if f'BBL_{period}_{std}.0' in df.columns else None
            current_price = df['Close'].iloc[-1]
            
            if upper and lower and middle:
                bandwidth = ((upper - lower) / middle) * 100
                position = ((current_price - lower) / (upper - lower)) * 100 if (upper - lower) > 0 else 50
                
                return {
                    'upper': float(upper),
                    'middle': float(middle),
                    'lower': float(lower),
                    'bandwidth': float(bandwidth),
                    'position': float(position),  # 0-100, onde está o preço na banda
                    'squeeze': bandwidth < 10  # Banda apertada indica possível breakout
                }
            
            return {'upper': 0, 'middle': 0, 'lower': 0, 'bandwidth': 0, 'position': 50, 'squeeze': False}
            
        except Exception as e:
            logger.debug(f"Erro ao calcular Bollinger: {e}")
            return {'upper': 0, 'middle': 0, 'lower': 0, 'bandwidth': 0, 'position': 50, 'squeeze': False}
    
    def _calculate_smas(self, df: pd.DataFrame) -> Dict:
        """Calcula SMAs de diferentes períodos."""
        try:
            df.ta.sma(length=20, append=True)
            df.ta.sma(length=50, append=True)
            df.ta.sma(length=200, append=True)
            
            current_price = df['Close'].iloc[-1]
            sma20 = df['SMA_20'].iloc[-1] if 'SMA_20' in df.columns else current_price
            sma50 = df['SMA_50'].iloc[-1] if 'SMA_50' in df.columns else current_price
            sma200 = df['SMA_200'].iloc[-1] if 'SMA_200' in df.columns else current_price
            
            return {
                'sma20': float(sma20) if pd.notna(sma20) else float(current_price),
                'sma50': float(sma50) if pd.notna(sma50) else float(current_price),
                'sma200': float(sma200) if pd.notna(sma200) else float(current_price),
                'above_sma20': current_price > sma20,
                'above_sma50': current_price > sma50,
                'above_sma200': current_price > sma200
            }
        except Exception as e:
            logger.debug(f"Erro ao calcular SMAs: {e}")
            current_price = df['Close'].iloc[-1]
            return {
                'sma20': float(current_price),
                'sma50': float(current_price),
                'sma200': float(current_price),
                'above_sma20': True,
                'above_sma50': True,
                'above_sma200': True
            }
    
    def _analyze_volume(self, df: pd.DataFrame) -> Dict:
        """Analisa volume."""
        try:
            current_volume = df['Volume'].iloc[-1]
            avg_volume_20 = df['Volume'].tail(20).mean()
            
            volume_ratio = current_volume / avg_volume_20 if avg_volume_20 > 0 else 1.0
            
            return {
                'current': int(current_volume),
                'avg_20d': int(avg_volume_20),
                'ratio': float(volume_ratio),
                'above_average': volume_ratio > 1.2,
                'spike': volume_ratio > 2.0  # Volume 2x acima da média
            }
        except Exception as e:
            logger.debug(f"Erro ao analisar volume: {e}")
            return {'current': 0, 'avg_20d': 0, 'ratio': 1.0, 'above_average': False, 'spike': False}
    
    def _determine_trend(self, df: pd.DataFrame, sma_data: Dict) -> str:
        """Determina tendência baseado em SMAs."""
        try:
            current_price = df['Close'].iloc[-1]
            sma20 = sma_data['sma20']
            sma50 = sma_data['sma50']
            sma200 = sma_data['sma200']
            
            # Tendência de alta: preço acima das médias e médias em ordem crescente
            if current_price > sma20 > sma50 > sma200:
                return 'strong_uptrend'
            elif current_price > sma20 > sma50:
                return 'uptrend'
            # Tendência de baixa
            elif current_price < sma20 < sma50 < sma200:
                return 'strong_downtrend'
            elif current_price < sma20 < sma50:
                return 'downtrend'
            else:
                return 'sideways'
                
        except Exception as e:
            logger.debug(f"Erro ao determinar tendência: {e}")
            return 'neutral'
    
    def _generate_signals(self, rsi: float, macd: Dict, bb: Dict) -> Dict:
        """Gera sinais de compra/venda baseado nos indicadores."""
        signals = {
            'oversold': rsi < 30,  # Sobrevendido
            'overbought': rsi > 70,  # Sobrecomprado
            'macd_bullish': macd['crossover'] == 'bullish',
            'macd_bearish': macd['crossover'] == 'bearish',
            'bb_lower_touch': bb['position'] < 10,  # Tocando banda inferior
            'bb_upper_touch': bb['position'] > 90,  # Tocando banda superior
            'bb_squeeze': bb['squeeze']  # Bollinger squeeze (possível breakout)
        }
        
        # Sinal agregado
        bullish_count = sum([
            signals['oversold'],
            signals['macd_bullish'],
            signals['bb_lower_touch']
        ])
        
        bearish_count = sum([
            signals['overbought'],
            signals['macd_bearish'],
            signals['bb_upper_touch']
        ])
        
        if bullish_count >= 2:
            signals['aggregate'] = 'strong_buy'
        elif bullish_count == 1:
            signals['aggregate'] = 'buy'
        elif bearish_count >= 2:
            signals['aggregate'] = 'strong_sell'
        elif bearish_count == 1:
            signals['aggregate'] = 'sell'
        else:
            signals['aggregate'] = 'neutral'
        
        return signals
    
    def _get_default_indicators(self) -> Dict:
        """Retorna indicadores padrão quando não é possível calcular."""
        return {
            'ticker': 'UNKNOWN',
            'timestamp': datetime.now().isoformat(),
            'rsi': 50.0,
            'macd': {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0, 'crossover': 'neutral'},
            'bollinger': {'upper': 0, 'middle': 0, 'lower': 0, 'bandwidth': 0, 'position': 50, 'squeeze': False},
            'sma': {'sma20': 0, 'sma50': 0, 'sma200': 0, 'above_sma20': True, 'above_sma50': True, 'above_sma200': True},
            'volume': {'current': 0, 'avg_20d': 0, 'ratio': 1.0, 'above_average': False, 'spike': False},
            'trend': 'neutral',
            'signals': {
                'oversold': False,
                'overbought': False,
                'macd_bullish': False,
                'macd_bearish': False,
                'bb_lower_touch': False,
                'bb_upper_touch': False,
                'bb_squeeze': False,
                'aggregate': 'neutral'
            }
        }
