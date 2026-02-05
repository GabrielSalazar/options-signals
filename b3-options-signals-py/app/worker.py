import asyncio
import logging
from datetime import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.scanner import scanner
from app.core.watchlist import get_watchlist

# Configuração de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("B3Worker")

# Scheduler Global
scheduler = AsyncIOScheduler()

async def scheduled_scan():
    """
    Job periódico que executa o scan para toda a watchlist.
    """
    watchlist = get_watchlist()
    tz = pytz.timezone('America/Sao_Paulo')
    now = datetime.now(tz)
    
    # Validação de Horário de Mercado (aprox 10:00 - 17:00)
    # Ignora Finais de Semana (weekday 5 e 6)
    if now.weekday() >= 5:
        logger.info("Mercado Fechado (Fim de Semana). Skipping Scan.")
        return

    if not (10 <= now.hour < 17):
        logger.info(f"Mercado Fechado ({now.strftime('%H:%M')}). Skipping Scan.")
        return

    logger.info(f"⏰ Iniciando Scan Automático: {len(watchlist)} ativos...")
    
    # Executa em paralelo com controle de concorrência (chunks)
    # B3RealData e Yahoo tem rate limits, então vamos de 5 em 5
    chunk_size = 5
    for i in range(0, len(watchlist), chunk_size):
        chunk = watchlist[i:i + chunk_size]
        logger.info(f"Scanning chunk {i//chunk_size + 1}: {chunk}")
        
        try:
            await asyncio.gather(*[scanner.scan_ticker(ticker) for ticker in chunk])
        except Exception as e:
            logger.error(f"Erro no chunk {chunk}: {e}")
            
        # Pequena pausa para não estourar rate limits
        await asyncio.sleep(2)
        
    logger.info("✅ Scan Automático Finalizado.")

def start_worker():
    """
    Inicia o scheduler.
    Deve ser chamado no startup do FastAPI ou via script separado.
    """
    # Agenda para rodar a cada 5 minutos
    # trigger = CronTrigger(minute='*/5', hour='10-16', day_of_week='mon-fri', timezone='America/Sao_Paulo')
    
    # Para testes/MVP: Intervalo simples de 5 minutos
    scheduler.add_job(
        scheduled_scan, 
        'interval', 
        minutes=5, 
        id='market_scanner',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("🚀 B3 Worker Iniciado (Agendamento: 5 min)")

if __name__ == "__main__":
    # Modo Standalone para testes
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        start_worker()
        # Executa uma vez imediatamente para teste
        loop.run_until_complete(scheduled_scan())
        # Mantém rodando
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
