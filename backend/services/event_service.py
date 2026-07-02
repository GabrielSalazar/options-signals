"""Gestão de eventos de mercado (Copom, earnings, vencimentos) — Fase 3 Matriz v2."""
import logging
from datetime import date

from backend.services.supabase_client import get_supabase

logger = logging.getLogger("b3_api")

# Calendário oficial do Copom 2026 (BCB): 8 reuniões de 2 dias (ter+qua);
# a decisão sai no 2º dia. Registramos AMBOS os dias — a IV fica elevada
# durante toda a reunião, não só no anúncio.
COPOM_DATAS_2026 = [
    date(2026, 1, 27), date(2026, 1, 28),
    date(2026, 3, 17), date(2026, 3, 18),
    date(2026, 4, 28), date(2026, 4, 29),
    date(2026, 6, 16), date(2026, 6, 17),
    date(2026, 8, 4), date(2026, 8, 5),
    date(2026, 9, 15), date(2026, 9, 16),
    date(2026, 11, 3), date(2026, 11, 4),
    date(2026, 12, 8), date(2026, 12, 9),
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
