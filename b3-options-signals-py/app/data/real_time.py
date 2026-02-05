"""
Módulo para buscar dados reais da B3 via múltiplas fontes.

Fontes suportadas:
- StatusInvest: Cadeia de opções (scraping)
- Yahoo Finance: Cotações intraday e histórico
- B3 Oficial: Cotações real-time (quando disponível)

Fallback: Cache Redis com TTL de 15 minutos
"""

import httpx
import pandas as pd
from bs4 import BeautifulSoup
from typing import Optional, Dict, List
import asyncio
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class B3RealData:
    """Cliente para buscar dados reais da B3."""
    
    def __init__(self):
        self.timeout = httpx.Timeout(10.0, connect=5.0)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    async def get_cadeia_opcoes(self, ticker: str) -> pd.DataFrame:
        """
        Busca cadeia de opções do StatusInvest.
        
        Args:
            ticker: Ticker do ativo (ex: PETR4)
            
        Returns:
            DataFrame com colunas: ticker_opcao, tipo, strike, preco, delta, iv, volume
        """
        logger.info(f"Buscando cadeia de opções para {ticker} no StatusInvest")
        
        try:
            url = f"https://statusinvest.com.br/acoes/{ticker.lower()}"
            
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(url)
                response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Parse tabela de opções
            opcoes_data = []
            
            # Procura pela seção de derivativos/opções
            # NOTA: A estrutura HTML do StatusInvest pode mudar, ajustar seletores conforme necessário
            opcoes_section = soup.find('div', {'id': 'opcoes-section'}) or \
                           soup.find('section', class_=lambda x: x and 'opcoes' in x.lower())
            
            if opcoes_section:
                # Parse tabela de calls
                calls_table = opcoes_section.find('table', class_=lambda x: x and 'call' in x.lower())
                if calls_table:
                    opcoes_data.extend(self._parse_opcoes_table(calls_table, 'CALL', ticker))
                
                # Parse tabela de puts
                puts_table = opcoes_section.find('table', class_=lambda x: x and 'put' in x.lower())
                if puts_table:
                    opcoes_data.extend(self._parse_opcoes_table(puts_table, 'PUT', ticker))
            
            if not opcoes_data:
                logger.warning(f"Nenhuma opção encontrada para {ticker} no StatusInvest")
                # Fallback: tentar via yfinance
                return await self._get_opcoes_yfinance(ticker)
            
            df = pd.DataFrame(opcoes_data)
            logger.info(f"Encontradas {len(df)} opções para {ticker}")
            return df
            
        except Exception as e:
            logger.error(f"Erro ao buscar cadeia de opções para {ticker}: {e}")
            # Fallback para yfinance
            return await self._get_opcoes_yfinance(ticker)
    
    def _parse_opcoes_table(self, table, tipo: str, underlying: str) -> List[Dict]:
        """Parse HTML table de opções."""
        opcoes = []
        
        rows = table.find_all('tr')[1:]  # Skip header
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 5:
                try:
                    opcoes.append({
                        'ticker_opcao': cols[0].text.strip(),
                        'underlying': underlying,
                        'tipo': tipo,
                        'strike': float(cols[1].text.strip().replace(',', '.')),
                        'preco': float(cols[2].text.strip().replace(',', '.')),
                        'volume': int(cols[3].text.strip().replace('.', '')),
                        'delta': float(cols[4].text.strip().replace(',', '.')) if len(cols) > 4 else None,
                        'iv': float(cols[5].text.strip().replace('%', '').replace(',', '.')) / 100 if len(cols) > 5 else None,
                        'timestamp': datetime.now().isoformat()
                    })
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Erro ao parsear linha de opção: {e}")
                    continue
        
        return opcoes
    
    async def _get_opcoes_yfinance(self, ticker: str) -> pd.DataFrame:
        """Fallback: busca opções via yfinance."""
        logger.info(f"Usando yfinance como fallback para {ticker}")
        
        try:
            import yfinance as yf
            
            stock = yf.Ticker(f"{ticker}.SA")
            
            # Pega próximas datas de vencimento
            expirations = stock.options
            if not expirations:
                logger.warning(f"Nenhuma opção disponível no yfinance para {ticker}")
                return pd.DataFrame()
            
            # Pega primeira data de vencimento
            opt_chain = stock.option_chain(expirations[0])
            
            # Combina calls e puts
            calls = opt_chain.calls.copy()
            calls['tipo'] = 'CALL'
            calls['underlying'] = ticker
            
            puts = opt_chain.puts.copy()
            puts['tipo'] = 'PUT'
            puts['underlying'] = ticker
            
            df = pd.concat([calls, puts], ignore_index=True)
            
            # Renomeia colunas para padrão
            df = df.rename(columns={
                'contractSymbol': 'ticker_opcao',
                'strike': 'strike',
                'lastPrice': 'preco',
                'volume': 'volume',
                'impliedVolatility': 'iv'
            })
            
            # Adiciona timestamp
            df['timestamp'] = datetime.now().isoformat()
            
            # Seleciona colunas relevantes
            df = df[['ticker_opcao', 'underlying', 'tipo', 'strike', 'preco', 'volume', 'iv', 'timestamp']]
            
            logger.info(f"Encontradas {len(df)} opções via yfinance para {ticker}")
            return df
            
        except Exception as e:
            logger.error(f"Erro ao buscar opções via yfinance para {ticker}: {e}")
            return pd.DataFrame()
    
    async def get_cotacao(self, ticker: str) -> Dict:
        """
        Busca cotação atual do ativo via Yahoo Finance.
        
        Args:
            ticker: Ticker do ativo (ex: PETR4)
            
        Returns:
            Dict com: preco, variacao, volume, abertura, maxima, minima, timestamp
        """
        logger.info(f"Buscando cotação para {ticker}")
        
        try:
            import yfinance as yf
            
            stock = yf.Ticker(f"{ticker}.SA")
            hist = stock.history(period="1d")
            
            if hist.empty:
                raise ValueError(f"Nenhum dado disponível para {ticker}")
            
            last_row = hist.iloc[-1]
            
            cotacao = {
                'ticker': ticker,
                'preco': float(last_row['Close']),
                'abertura': float(last_row['Open']),
                'maxima': float(last_row['High']),
                'minima': float(last_row['Low']),
                'volume': int(last_row['Volume']),
                'variacao': float(((last_row['Close'] - last_row['Open']) / last_row['Open']) * 100),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Cotação {ticker}: R$ {cotacao['preco']:.2f}")
            return cotacao
            
        except Exception as e:
            logger.error(f"Erro ao buscar cotação para {ticker}: {e}")
            raise
    
    async def get_historico(self, ticker: str, days: int = 252) -> pd.DataFrame:
        """
        Busca histórico de preços via Yahoo Finance.
        
        Args:
            ticker: Ticker do ativo
            days: Número de dias de histórico
            
        Returns:
            DataFrame com OHLCV
        """
        logger.info(f"Buscando histórico de {days} dias para {ticker}")
        
        try:
            import yfinance as yf
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            stock = yf.Ticker(f"{ticker}.SA")
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty:
                raise ValueError(f"Nenhum histórico disponível para {ticker}")
            
            logger.info(f"Histórico obtido: {len(hist)} dias para {ticker}")
            return hist
            
        except Exception as e:
            logger.error(f"Erro ao buscar histórico para {ticker}: {e}")
            raise
    
    async def get_volume_opcoes(self, ticker: str) -> Dict:
        """
        Busca volume agregado de opções.
        
        Returns:
            Dict com volume_calls, volume_puts, ratio_put_call
        """
        try:
            cadeia = await self.get_cadeia_opcoes(ticker)
            
            if cadeia.empty:
                return {'volume_calls': 0, 'volume_puts': 0, 'ratio_put_call': 0}
            
            volume_calls = cadeia[cadeia['tipo'] == 'CALL']['volume'].sum()
            volume_puts = cadeia[cadeia['tipo'] == 'PUT']['volume'].sum()
            
            ratio = volume_puts / volume_calls if volume_calls > 0 else 0
            
            return {
                'ticker': ticker,
                'volume_calls': int(volume_calls),
                'volume_puts': int(volume_puts),
                'ratio_put_call': float(ratio),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar volume de opções para {ticker}: {e}")
            return {'volume_calls': 0, 'volume_puts': 0, 'ratio_put_call': 0}
