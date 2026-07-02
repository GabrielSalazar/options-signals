"""Gestão de eventos de mercado (Copom, earnings, vencimentos) — Fase 3 Matriz v2."""
import logging
from datetime import date

from backend.services.supabase_client import get_supabase

logger = logging.getLogger("b3_api")

# Datas COPOM conhecidas (2026) — hardcoded, sem fonte dinâmica ainda
COPOM_DATAS_2026 = [
    date(2026, 1, 14),
    date(2026, 2, 25),
    date(2026, 3, 25),
    date(2026, 4, 22),
    date(2026, 5, 13),
    date(2026, 6, 17),
    date(2026, 7, 15),
    date(2026, 8, 19),
    date(2026, 9, 16),
    date(2026, 10, 14),
    date(2026, 11, 18),
    date(2026, 12, 16),
]


def registrar_copom_datas(ano: int = 2026):
    """Registra datas Copom no calendário de eventos (idempotente, fail-safe)."""
    supabase = get_supabase()
    if not supabase:
        logger.warning("Supabase indisponível — calendário não atualizado")
        return

    datas = COPOM_DATAS_2026 if ano == 2026 else []
    if not datas:
        logger.warning(f"Datas Copom não conhecidas para {ano}")
        return

    for dt in datas:
        try:
            supabase.table("calendar_events").upsert({
                "data": dt.isoformat(),
                "label": "COPOM",
                "descricao": "Decisão de taxa Selic — Banco Central",
            }, on_conflict="data,label").execute()
        except Exception as e:
            logger.warning(f"Erro ao registrar Copom {dt}: {e}")

    logger.info(f"Copom {ano} registrado ({len(datas)} datas)")


def obter_evento_na_data(data: date) -> str | None:
    """Retorna label do evento na data, se houver. Fail-safe: None em erro."""
    supabase = get_supabase()
    if not supabase:
        return None

    try:
        res = (supabase.table("calendar_events")
               .select("label")
               .eq("data", data.isoformat())
               .execute())
        if res.data and len(res.data) > 0:
            return res.data[0].get("label")
    except Exception as e:
        logger.warning(f"Erro ao consultar evento de {data}: {e}")

    return None
