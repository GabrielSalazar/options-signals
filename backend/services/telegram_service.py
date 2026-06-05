"""Notificações e configuração do Telegram.

Mantém a config do bot em ``CONFIG`` (backend.core.config), persistida em um
arquivo JSON para sobreviver a soft-restarts, e envia os sinais formatados.
"""
import os
import json
import time
import logging

import requests

from backend.core.config import CONFIG

logger = logging.getLogger("b3_api")

_TELEGRAM_CONFIG_FILE = "telegram_config.json"

NOMES_MESES = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
               7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}


def load_telegram_config():
    """Carrega config do Telegram de arquivo JSON (persiste entre soft-restarts)."""
    # Prioriza variáveis de ambiente (.env ou secrets do provedor de cloud)
    env_token = os.getenv("TELEGRAM_BOT_TOKEN")
    env_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if env_token:
        CONFIG["telegram_token"] = env_token
    if env_chat_id:
        CONFIG["telegram_chat_id"] = env_chat_id

    try:
        with open(_TELEGRAM_CONFIG_FILE) as f:
            data = json.load(f)
        if data.get("token") and not env_token:
            CONFIG["telegram_token"] = data["token"]
        if data.get("chat_id") and not env_chat_id:
            CONFIG["telegram_chat_id"] = data["chat_id"]
        logger.info("Config Telegram carregada de telegram_config.json")
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning(f"Erro ao carregar telegram_config.json: {e}")


def save_telegram_config(token: str, chat_id: str):
    """Persiste config do Telegram em arquivo JSON."""
    try:
        with open(_TELEGRAM_CONFIG_FILE, "w") as f:
            json.dump({"token": token, "chat_id": chat_id}, f)
    except Exception as e:
        logger.warning(f"Erro ao salvar telegram_config.json: {e}")


def enviar_telegram(sinal: dict):
    token = CONFIG.get("telegram_token", "")
    chat_id = CONFIG.get("telegram_chat_id", "")
    if not token or not chat_id:
        return

    mes_str = NOMES_MESES.get(sinal.get("mes_venc"), "")
    msg = (
        f"🎯 *SINAL B3 — {sinal.get('ticker')}* ({sinal.get('nome')})\n"
        f"*Tipo:* {sinal.get('tipo_sinal')} | *Venc:* {mes_str}/{sinal.get('ano_venc')}\n"
        f"*Strike ref:* R$ {sinal.get('strike_ref', 0):.2f} ({sinal.get('dist_otm_pct', 0):.0f}% OTM)\n"
        f"*IV Hist:* {sinal.get('iv_hist')}% | *DTE:* {sinal.get('dte')} du\n\n"
        f"*Entrada:* R$ {sinal.get('entrada_min', 0):.2f} – {sinal.get('entrada_max', 0):.2f}\n"
        f"*Alvo 1:* R$ {sinal.get('alvo1', 0):.2f} (+{CONFIG.get('alvo1_pct', 0.25)*100:.0f}%) | R/R: {sinal.get('rr_alvo1', 0):.1f}×\n"
        f"*Alvo 2:* R$ {sinal.get('alvo2', 0):.2f} (+{CONFIG.get('alvo2_pct', 0.5)*100:.0f}%) | R/R: {sinal.get('rr_alvo2', 0):.1f}×\n"
        f"*Stop:* R$ {sinal.get('stop', 0):.2f} ({CONFIG.get('stop_pct', 0.5)*100:.0f}%)\n\n"
        f"*Score:* {sinal.get('score')}/10\n"
        f"*Gatilhos:*\n• " + "\n• ".join(sinal.get("gatilhos", []))
    )

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'}, timeout=10)
        logger.info(f"Sinal {sinal.get('ticker')} enviado ao Telegram.")
    except Exception as e:
        logger.error(f"Erro ao enviar Telegram para {sinal.get('ticker')}: {e}")


def notificar_lote(sinais: list, throttle_s: float | None = None) -> None:
    """Envia uma lista de sinais ao Telegram com throttle entre mensagens (A3).

    Fica FORA do hot-loop de scan: o chamador acumula os sinais e envia ao final,
    evitando travar a coleta e tomar 429 quando há muitos sinais.
    """
    if throttle_s is None:
        throttle_s = CONFIG.get("telegram_throttle_s", 0.5)
    for i, sinal in enumerate(sinais):
        enviar_telegram(sinal)
        if i < len(sinais) - 1 and throttle_s > 0:
            time.sleep(throttle_s)
