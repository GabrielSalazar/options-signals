from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# "sqlite:///./app.db" é o padrão para desenvolvimento local
# Para Supabase, defina DATABASE_URL=postgresql://user:password@host:port/dbname
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Correção para Heroku/Supabase que às vezes usam "postgres://" (depreciado pelo SQLAlchemy)
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Injeção de Dependência para obter a sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
