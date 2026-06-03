"""Acesso ao cliente Supabase (service role).

Camada fina e isolada para que routers e serviços compartilhem a mesma forma
de obter o cliente, sem duplicar a leitura de variáveis de ambiente.
"""
import os
import logging

logger = logging.getLogger("b3_api")


def get_supabase():
    """Cria um cliente Supabase a partir das variáveis de ambiente.

    Retorna ``None`` quando o Supabase não está configurado ou indisponível —
    os chamadores tratam esse caso com fallback para memória.
    """
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if url and key:
            return create_client(url, key)
    except Exception as e:
        logger.warning(f"Supabase não configurado: {e}")
    return None
