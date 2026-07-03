"""Notificações e configuração do Telegram.

Mantém a config do bot em ``CONFIG`` (backend.core.config), persistida em um
arquivo JSON para sobreviver a soft-restarts, e envia os sinais formatados.
"""
import json
import logging
import os
import time

import requests

from backend.core.config import CONFIG
from backend.services.supabase_client import get_supabase

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

    supabase = get_supabase()
    if supabase:
        try:
            res = (supabase.table("telegram_config")
                   .select("token, chat_id").eq("id", 1).limit(1).execute())
            if res.data:
                row = res.data[0]
                if row.get("token") and not env_token:
                    CONFIG["telegram_token"] = row["token"]
                if row.get("chat_id") and not env_chat_id:
                    CONFIG["telegram_chat_id"] = row["chat_id"]
                logger.info("Config Telegram carregada do Supabase")
                return
        except Exception as e:
            logger.warning(f"Falha ao ler telegram_config do Supabase: {e}")

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
    """Persiste a config do Telegram no Supabase (tabela telegram_config, linha
    única); cai para arquivo JSON quando o Supabase está indisponível."""
    supabase = get_supabase()
    if supabase:
        try:
            supabase.table("telegram_config").upsert(
                {"id": 1, "token": token, "chat_id": chat_id}
            ).execute()
            return
        except Exception as e:
            logger.warning(f"Falha ao gravar telegram_config no Supabase: {e}")
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
    linha_venc = f"*Tipo:* {sinal.get('tipo_sinal')} | *Venc:* {mes_str}/{sinal.get('ano_venc')}"
    if sinal.get("classe_v2"):
        linha_venc += f" | *Classe:* {sinal.get('classe_v2')}"

    partes = [
        f"🎯 *SINAL B3 — {sinal.get('ticker')}* ({sinal.get('nome')})",
        linha_venc,
        f"*Strike ref:* R$ {sinal.get('strike_ref', 0):.2f} ({sinal.get('dist_otm_pct', 0):.0f}% OTM)",
        f"*HV 20d:* {sinal.get('hv_20d')}% | *DTE:* {sinal.get('dte')} du",
    ]
    if sinal.get("evento_label"):
        # underscores quebram o Markdown do Telegram (ex.: EARNINGS_PETR4)
        partes.append(f"⚠ *Evento no dia:* {str(sinal['evento_label']).replace('_', ' ')}")

    partes += [
        "",
        f"*Entrada (opção):* R$ {sinal.get('entrada_min', 0):.2f} – {sinal.get('entrada_max', 0):.2f}",
        f"*Alvo 1:* R$ {sinal.get('alvo1', 0):.2f} (+{CONFIG.get('alvo1_pct', 0.25)*100:.0f}%) | R/R: {sinal.get('rr_alvo1', 0):.1f}×",
        f"*Alvo 2:* R$ {sinal.get('alvo2', 0):.2f} (+{CONFIG.get('alvo2_pct', 0.5)*100:.0f}%) | R/R: {sinal.get('rr_alvo2', 0):.1f}×",
        f"*Stop:* R$ {sinal.get('stop', 0):.2f} ({CONFIG.get('stop_pct', 0.5)*100:.0f}%)",
    ]

    # Níveis no ativo subjacente (Camada PUCK — gestão pela tese, não pela opção)
    if sinal.get("ativo_stop") is not None:
        partes += [
            "",
            "*📍 Níveis no ativo (ATR):*",
            f"Entrada R$ {sinal.get('ativo_entrada', 0):.2f} | Stop R$ {sinal.get('ativo_stop', 0):.2f}",
            f"TP1 R$ {sinal.get('ativo_tp1', 0):.2f} (50%) | TP2 R$ {sinal.get('ativo_tp2', 0):.2f}",
            "_No TP1 realize 50% e mova o stop p/ a entrada._",
        ]

    # Executabilidade (dados D-1 da B3)
    exec_bits = []
    if sinal.get("oi") is not None:
        exec_bits.append(f"OI {int(sinal['oi']):,}".replace(",", "."))
    if sinal.get("spread_pct") is not None:
        exec_bits.append(f"Spread {sinal['spread_pct']:.1f}%")
    if sinal.get("vxbr") is not None:
        exec_bits.append(f"VXBR {sinal['vxbr']:.1f}")
    if exec_bits:
        partes.append("*Exec (D-1):* " + " | ".join(exec_bits))

    # Fluxo institucional (Camada PUCK)
    if sinal.get("cmf_z") is not None:
        fluxo = f"*Fluxo:* Z {sinal['cmf_z']:+.1f}"
        if sinal.get("cmf_norm") is not None:
            fluxo += f" | Intens {sinal['cmf_norm']:.1f}"
        if sinal.get("fluxo_persistencia_dias") is not None:
            fluxo += f" | Persist {sinal['fluxo_persistencia_dias']}d"
        partes.append(fluxo)

    partes += [
        "",
        f"*Score técnico:* {sinal.get('score_tecnico', sinal.get('score'))} (mín. {CONFIG.get('min_score', 5)})",
        f"*Bônus sessão:* +{sinal.get('bonus_sessao', 0)} (prioridade, não entra no corte)",
    ]
    if sinal.get("sizing_sugerido_pct") is not None:
        partes.append(f"*Sizing sugerido:* {sinal['sizing_sugerido_pct']:.1f}% do capital")

    partes.append("*Gatilhos:*\n• " + "\n• ".join(sinal.get("gatilhos", [])))

    if sinal.get("gatilhos_v2"):
        partes.append("*Gatilhos v2/PUCK (shadow):*\n◦ " + "\n◦ ".join(sinal["gatilhos_v2"]))

    msg = "\n".join(partes)

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'}, timeout=10)
        logger.info(f"Sinal {sinal.get('ticker')} enviado ao Telegram.")
    except Exception as e:
        logger.error(f"Erro ao enviar Telegram para {sinal.get('ticker')}: {e}")


def enviar_mensagem_teste() -> dict:
    """Envia uma mensagem de teste ao chat configurado e retorna o status
    detalhado — usado por POST /config/telegram/test para validar as
    credenciais sem esperar o próximo scan. Nunca lança exceção.

    Retorna {"ok": True} em sucesso ou {"ok": False, "erro": <motivo>}.
    """
    token = CONFIG.get("telegram_token", "")
    chat_id = CONFIG.get("telegram_chat_id", "")
    if not token or not chat_id:
        return {"ok": False, "erro": "token/chat_id não configurado"}

    texto = "✅ Teste — Options Signals B3 conectado ao Telegram."
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, data={"chat_id": chat_id, "text": texto}, timeout=10)
        payload = resp.json()
        if resp.ok and payload.get("ok"):
            logger.info("Mensagem de teste do Telegram enviada com sucesso.")
            return {"ok": True}
        # Telegram devolve o motivo em "description" (ex.: chat not found, Unauthorized)
        erro = payload.get("description", f"HTTP {resp.status_code}")
        logger.warning(f"Falha no teste do Telegram: {erro}")
        return {"ok": False, "erro": erro}
    except Exception as e:
        logger.error(f"Erro ao enviar teste do Telegram: {e}")
        return {"ok": False, "erro": str(e)}


def enviar_card_exemplo() -> dict:
    """Envia um sinal de EXEMPLO (sintético) ao Telegram, pela mesma via de
    `enviar_telegram`, para preview do formato do card. Retorna {"ok": True}
    ou {"ok": False, "erro": <motivo>}."""
    token = CONFIG.get("telegram_token", "")
    chat_id = CONFIG.get("telegram_chat_id", "")
    if not token or not chat_id:
        return {"ok": False, "erro": "token/chat_id não configurado"}

    exemplo = {
        "ticker": "PETR4", "nome": "Petrobras PN (EXEMPLO)", "tipo_sinal": "CALL",
        "mes_venc": 8, "ano_venc": 2026, "strike_ref": 40.0, "dist_otm_pct": 6.0,
        "hv_20d": 32.5, "dte": 28,
        "entrada_min": 0.80, "entrada_max": 0.92,
        "alvo1": 1.15, "alvo2": 1.60, "alvo_final": 2.40, "stop": 0.46,
        "rr_alvo1": 1.5, "rr_alvo2": 2.5, "rr_final": 4.0,
        "score_tecnico": 11, "score": 11, "bonus_sessao": 2,
        "classe_v2": "A", "sizing_sugerido_pct": 1.8,
        "ativo_entrada": 38.50, "ativo_stop": 37.10, "ativo_tp1": 39.90, "ativo_tp2": 41.30,
        "oi": 5200, "bid": 0.80, "ask": 0.92, "spread_pct": 8.4, "vxbr": 22.5,
        "cmf_z": 1.8, "cmf_norm": 1.6, "fluxo_persistencia_dias": 4,
        "gatilhos": ["📈 Estocástico: cruzamento altista em sobrevenda",
                     "📈 RSI sobrevenda: 32.1",
                     "📈 Volume 1.8x acima da média"],
        "gatilhos_v2": ["📈 Rompimento do HC institucional (z-fluxo 1.8)",
                        "📈 Preço acima da EMA21"],
    }
    try:
        enviar_telegram(exemplo)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Erro ao enviar card de exemplo: {e}")
        return {"ok": False, "erro": str(e)}


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
