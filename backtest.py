import yfinance as yf
import pandas as pd
import logging
from tqdm import tqdm
from core_engine import analisar_ativo
from options_math import estimar_premio_otm
from indicators import calcular_indicadores

logger = logging.getLogger("b3_scanner")

_WINDOW = 90  # barras fixas por iteração → O(n) em vez de O(n²)


def rodar_backtest(ticker: str, nome: str, data_inicio: str, data_fim: str, interval: str = "1d"):
    """
    Roda o backtest iterando sobre os dados históricos simulando a passagem do tempo.
    Usa janela rolante de _WINDOW barras para manter complexidade O(n).
    """
    logger.info(f"Iniciando backtest para {ticker} ({nome}) de {data_inicio} a {data_fim}")
    df_full = yf.download(ticker, start=data_inicio, end=data_fim, interval=interval, auto_adjust=True, progress=False)

    if df_full.empty or len(df_full) < 30:
        logger.warning(f"Dados insuficientes para {ticker}")
        return []

    df_full.columns = [c[0] if isinstance(c, tuple) else c for c in df_full.columns]
    
    # Pré-calcula indicadores UMA VEZ para todo o histórico (derruba tempo de backtest de O(n²) para O(n))
    df_full = calcular_indicadores(df_full)
    df_full.dropna(inplace=True)

    if len(df_full) < _WINDOW + 10:
        logger.warning(f"Dados insuficientes após calcular indicadores para {ticker}")
        return []

    sinais_encontrados = []
    start_idx = _WINDOW  # garante janela completa na primeira iteração

    logger.info(f"Total de barras: {len(df_full)}. Iterando a partir do índice {start_idx} (janela={_WINDOW})...")

    for i in tqdm(range(start_idx, len(df_full)), desc=f"Backtest {ticker}"):
        # Janela fixa: sempre _WINDOW barras → indicadores em tempo constante
        df_slice = df_full.iloc[i - _WINDOW:i].copy()
        sinal = analisar_ativo(ticker, nome, interval=interval, verbose=False, df_provided=df_slice, indicators_calculated=True)
        
        if sinal:
            sinal["data_sinal"] = df_full.index[i-1]
            # Forward simulation (próximos 15 dias)
            horizonte = min(15, len(df_full) - i)
            sinal["hit_alvo1"] = False
            sinal["hit_stop"] = False
            sinal["max_return"] = 0.0
            
            premio_entrada = sinal["premio_est"]
            iv = sinal["iv_hist"] / 100.0
            
            for j in range(horizonte):
                future_row = df_full.iloc[i + j]
                future_price = future_row["Close"]
                future_dte = max(1, sinal["dte"] - j)
                
                # Simular o preço da opção no futuro
                future_premio = estimar_premio_otm(future_price, sinal["strike_ref"], future_dte, iv, sinal["tipo_sinal"])
                retorno = (future_premio - premio_entrada) / premio_entrada
                
                sinal["max_return"] = max(sinal["max_return"], retorno)
                
                if future_premio >= sinal["alvo1"] and not sinal["hit_stop"]:
                    sinal["hit_alvo1"] = True
                    break
                elif future_premio <= sinal["stop"]:
                    sinal["hit_stop"] = True
                    # continue monitoring for max return just for stats
                    
            sinais_encontrados.append(sinal)
            
    logger.info(f"Backtest para {ticker} concluído. {len(sinais_encontrados)} sinais encontrados.")
    return sinais_encontrados

def exibir_relatorio_backtest(sinais: list):
    if not sinais:
        print("Nenhum sinal encontrado no backtest.")
        return
        
    df_sinais = pd.DataFrame(sinais)
    
    # Calcular Win Rate
    total = len(df_sinais)
    wins = df_sinais["hit_alvo1"].sum()
    win_rate = (wins / total) * 100 if total > 0 else 0
    
    print("\n=== RELATÓRIO DE BACKTEST (Com Forward Simulation) ===")
    print(f"Total de sinais emitidos: {total}")
    print(f"Calls: {len(df_sinais[df_sinais['tipo_sinal'] == 'CALL'])}")
    print(f"Puts: {len(df_sinais[df_sinais['tipo_sinal'] == 'PUT'])}")
    print(f"Win Rate (Atingiu Alvo 1): {win_rate:.1f}% ({wins}/{total})")
    print(f"Retorno Máximo Médio Simulado: {df_sinais['max_return'].mean() * 100:.1f}%")
    
    print("\nÚltimos sinais encontrados:")
    cols = ['data_sinal', 'ticker', 'tipo_sinal', 'score', 'strike_ref', 'hit_alvo1', 'hit_stop']
    print(df_sinais[cols].tail(10).to_string(index=False))
    
    try:
        df_excel = pd.read_excel('sinais_referencia.xlsx', header=1)
        if 'CÓDIGO OPÇÃO' in df_excel.columns:
            print(f"\n[INFO] Planilha de referência carregada para comparação cruzada (Total registros: {len(df_excel)}).")
    except Exception:
        pass
