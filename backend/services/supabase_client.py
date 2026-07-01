"""Acesso ao cliente Supabase (service role).

Camada fina e isolada para que routers e serviços compartilhem a mesma forma
de obter o cliente, sem duplicar a leitura de variáveis de ambiente.
"""
import logging
import os
import threading

logger = logging.getLogger("b3_api")


_supabase_client = None
_client_lock = threading.Lock()


def get_supabase():
    """Retorna o cliente Singleton Supabase a partir das variáveis de ambiente.

    Retorna ``None`` quando o Supabase não está configurado ou indisponível —
    os chamadores tratam esse caso com fallback para memória.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    with _client_lock:
        if _supabase_client is not None:
            return _supabase_client
        try:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if url and key:
                _supabase_client = create_client(url, key)
                return _supabase_client
        except Exception as e:
            logger.warning(f"Supabase não configurado: {e}")
        return None
