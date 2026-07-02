"""Gestão de eventos de mercado (Copom, earnings, vencimentos) — Fase 3 Matriz v2.

MANUTENÇÃO ANUAL: o BCB não expõe o calendário do Copom em API estável, então as
datas são hardcoded por ano em COPOM_DATAS_POR_ANO. O BCB publica o calendário do
ano seguinte por volta de jun/jul — quando isso acontecer, adicionar a nova lista
aqui. O guard `verificar_exaustao_calendario()` avisa (warning no boot) quando a
última data conhecida está a menos de EXAUSTAO_AVISO_DIAS, para que a atualização
não dependa de memória.
"""
import logging
from datetime import date, timedelta

from backend.services.supabase_client import get_supabase

logger = logging.getLogger("b3_api")

# Calendário oficial do Copom (BCB): 8 reuniões de 2 dias (ter+qua) por ano;
# a decisão sai no 2º dia. Registramos AMBOS os dias — a IV fica elevada
# durante toda a reunião, não só no anúncio.
COPOM_DATAS_POR_ANO: dict[int, list[date]] = {
    2026: [
        date(2026, 1, 27), date(2026, 1, 28),
        date(2026, 3, 17), date(2026, 3, 18),
        date(2026, 4, 28), date(2026, 4, 29),
        date(2026, 6, 16), date(2026, 6, 17),
        date(2026, 8, 4), date(2026, 8, 5),
        date(2026, 9, 15), date(2026, 9, 16),
        date(2026, 11, 3), date(2026, 11, 4),
        date(2026, 12, 8), date(2026, 12, 9),
    ],
    # 2027: adicionar quando o BCB publicar (previsto ~jun/2026)
}

# Compat: alias usado por testes/callers existentes
COPOM_DATAS_2026 = COPOM_DATAS_POR_ANO[2026]

EXAUSTAO_AVISO_DIAS = 90


def verificar_exaustao_calendario(hoje: date | None = None) -> bool:
    """True (e loga WARNING) se a última data Copom conhecida está a menos de
    EXAUSTAO_AVISO_DIAS — sinal de que o calendário do próximo ano precisa ser
    adicionado em COPOM_DATAS_POR_ANO. Chamado no boot."""
    hoje = hoje or date.today()
    todas = [d for datas in COPOM_DATAS_POR_ANO.values() for d in datas]
    ultima = max(todas) if todas else None
    if ultima is None or ultima - hoje < timedelta(days=EXAUSTAO_AVISO_DIAS):
        logger.warning(
            f"Calendário Copom perto do fim (última data conhecida: {ultima}) — "
            f"adicionar as datas do próximo ano em COPOM_DATAS_POR_ANO "
            f"(BCB publica ~jun/jul; fonte: bcb.gov.br)"
        )
        return True
    return False


def registrar_copom_datas(ano: int = 2026):
    """Registra datas Copom no calendário de eventos (idempotente, fail-safe).

    Registra TODOS os anos conhecidos em COPOM_DATAS_POR_ANO a partir de `ano`
    (assim, quando 2027 for adicionado ao dict, o mesmo boot passa a registrá-lo
    sem mudança no chamador) e avisa se o calendário está perto de esgotar.
    """
    verificar_exaustao_calendario()

    supabase = get_supabase()
    if not supabase:
        logger.warning("Supabase indisponível — calendário não atualizado")
        return

    datas = [d for a, ds in COPOM_DATAS_POR_ANO.items() if a >= ano for d in ds]
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

    logger.info(f"Copom {ano}+ registrado ({len(datas)} datas)")


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
