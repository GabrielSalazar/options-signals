from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routers import options, signals, backtest, admin, health
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Rate Limiter Configuration
limiter = Limiter(key_func=get_remote_address)

from contextlib import asynccontextmanager
from app.worker import start_worker

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicia o worker de agendamento em background
    start_worker()
    yield
    # Shutdown logic if needed

app = FastAPI(
    title="B3 Option Signals Platform",
    description="API for analyzing and alerting on B3 Stock Options using Black-Scholes and Greeks.",
    version="0.1.0",
    lifespan=lifespan
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Initialize Database
from app.core.database import engine, Base
Base.metadata.create_all(bind=engine)

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(options.router)
app.include_router(signals.router)
app.include_router(backtest.router)
app.include_router(admin.router)

@app.get("/")
def read_root():
    return {"message": "B3 Option Signals API is running. Check /docs for Swagger UI."}
