#!/usr/bin/env python3
import sys
import argparse
import logging
try:
    from tabulate import tabulate
    TAB = True
except ImportError:
    TAB = False
import requests
import colorama
from colorama import Fore, Style
from datetime import datetime

from config import ATIVOS_B3, CONFIG, dentro_horario_pregao
from core_engine import analisar_ativo
from backtest import rodar_backtest, exibir_relatorio_backtest

# Configurações de cores
colorama.init(autoreset=True)

# Configuração do Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("b3_scanner")

NOMES_MESES = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
               7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}

def enviar_telegram(sinal: dict):
    token   = CONFIG.get("telegram_token", "")
    chat_id = CONFIG.get("telegram_chat_id", "")
    if not token or not chat_id:
        return
        
    mes_str = NOMES_MESES.get(sinal["mes_venc"], "")
    msg = (
        f"🎯 *SINAL B3 — {sinal['ticker']}* ({sinal['nome']})\n"
        f"*Tipo:* {sinal['tipo_sinal']} | *Venc:* {mes_str}/{sinal['ano_venc']}\n"
        f"*Strike ref:* R$ {sinal['strike_ref']:.2f} ({sinal['dist_otm_pct']:.0f}% OTM)\n"
        f"*IV Hist:* {sinal['iv_hist']}% | *DTE:* {sinal['dte']} du\n\n"
        f"*Entrada:* R$ {sinal['entrada_min']:.2f} – {sinal['entrada_max']:.2f}\n"
        f"*Alvo 1:* R$ {sinal['alvo1']:.2f} (+{CONFIG['alvo1_pct']*100:.0f}%) | R/R: {sinal['rr_alvo1']:.1f}×\n"
        f"*Alvo 2:* R$ {sinal['alvo2']:.2f} (+{CONFIG['alvo2_pct']*100:.0f}%) | R/R: {sinal['rr_alvo2']:.1f}×\n"
        f"*Stop:* R$ {sinal['stop']:.2f} ({CONFIG['stop_pct']*100:.0f}%)\n\n"
        f"*Score:* {sinal['score']}/10\n"
        f"*Gatilhos:*\n• " + "\n• ".join(sinal["gatilhos"])
    )
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'}, timeout=10)
        logger.info(f"Sinal {sinal['ticker']} enviado ao Telegram.")
    except Exception as e:
        logger.error(f"Erro ao enviar Telegram para {sinal['ticker']}: {e}")

def varrer_ativos(ativos: dict, interval: str, verbose: bool):
    """
    Modo de produção: varre a lista de ativos e procura sinais.
    """
    if not dentro_horario_pregao(margem_min=0) and not verbose:
        logger.warning("Fora do horário do pregão (10:00 - 16:30). Sinais podem estar defasados.")
        
    sinais = []
    
    print(f"\n{Style.BRIGHT}{Fore.CYAN}Varrendo {len(ativos)} ativos B3 (Intervalo: {interval})...{Style.RESET_ALL}\n")
    
    for ticker, nome in ativos.items():
        if verbose:
            logger.info(f"Analisando {ticker}...")
            
        sinal = analisar_ativo(ticker, nome, interval=interval, verbose=verbose)
        if sinal:
            sinais.append(sinal)
            enviar_telegram(sinal)
            
            # Print imediato do sinal
            cor = Fore.GREEN if sinal['tipo_sinal'] == 'CALL' else Fore.RED
            print(f"{cor}SINAL DETECTADO: {sinal['ticker']} - {sinal['tipo_sinal']} (Score: {sinal['score']}){Style.RESET_ALL}")
            for g in sinal['gatilhos']:
                print(f"  {g}")
            print("-" * 50)
            
    if sinais:
        print(f"\n{Style.BRIGHT}{Fore.GREEN}Resumo dos {len(sinais)} sinais encontrados:{Style.RESET_ALL}")
        if TAB:
            tabela = []
            for s in sinais:
                tabela.append([
                    s['ticker'], s['tipo_sinal'], s['score'], 
                    f"R$ {s['preco_acao']:.2f}", f"R$ {s['strike_ref']:.2f}", 
                    f"R$ {s['entrada_max']:.2f}", f"R$ {s['alvo1']:.2f}"
                ])
            print(tabulate(tabela, headers=["Ativo", "Tipo", "Score", "Preço", "Strike Ref", "Entrada Max", "Alvo 1"], tablefmt="grid"))
        else:
            for s in sinais:
                print(f"{s['ticker']} | {s['tipo_sinal']} | Score {s['score']} | Entrada: {s['entrada_max']}")
    else:
        print(f"\n{Style.BRIGHT}{Fore.YELLOW}Nenhum sinal encontrado com os critérios atuais.{Style.RESET_ALL}")

def main():
    parser = argparse.ArgumentParser(description="Scanner de Opções B3 - TP Capital")
    parser.add_argument("ticker", nargs="?", help="Analisar apenas um ticker específico (ex: MGLU3)")
    parser.add_argument("--backtest", action="store_true", help="Rodar em modo backtest")
    parser.add_argument("--start", type=str, default="2026-01-01", help="Data início backtest (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default=datetime.now().strftime("%Y-%m-%d"), help="Data fim backtest (YYYY-MM-DD)")
    parser.add_argument("--interval", type=str, default="1d", choices=["1d", "1h"], help="Intervalo dos dados (1d ou 1h)")
    parser.add_argument("--verbose", action="store_true", help="Ativar logs detalhados")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    ativos_alvo = ATIVOS_B3
    if args.ticker:
        ticker_sa = args.ticker.upper()
        if not ticker_sa.endswith(".SA"):
            ticker_sa += ".SA"
        if ticker_sa in ATIVOS_B3:
            ativos_alvo = {ticker_sa: ATIVOS_B3[ticker_sa]}
        else:
            ativos_alvo = {ticker_sa: args.ticker.upper()}
            
    if args.backtest:
        todos_sinais = []
        for ticker, nome in ativos_alvo.items():
            sinais = rodar_backtest(ticker, nome, args.start, args.end, interval=args.interval)
            todos_sinais.extend(sinais)
        exibir_relatorio_backtest(todos_sinais)
    else:
        varrer_ativos(ativos_alvo, args.interval, args.verbose)

if __name__ == "__main__":
    main()
