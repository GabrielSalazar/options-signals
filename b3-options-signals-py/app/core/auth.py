"""
Módulo de Autenticação para API
Implementa validação de Bearer Token via variável de ambiente
"""
import os
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Valida o token Bearer contra a variável de ambiente API_TOKEN.
    Retorna o token se válido, caso contrário lança HTTPException 401.
    """
    expected_token = os.getenv("API_TOKEN")
    
    # Se API_TOKEN não estiver configurado, permite acesso (modo desenvolvimento)
    if not expected_token:
        print("⚠️  WARNING: API_TOKEN not set. Authentication disabled (development mode).")
        return "dev-mode"
    
    # Valida o token
    if credentials.credentials != expected_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return credentials.credentials
