from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import options, signals

app = FastAPI(
    title="B3 Option Signals Platform",
    description="API for analyzing and alerting on B3 Stock Options using Black-Scholes and Greeks.",
    version="0.1.0"
)

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(options.router)
app.include_router(signals.router)

@app.get("/")
def read_root():
    return {"message": "B3 Option Signals API is running. Check /docs for Swagger UI."}

@app.get("/health")
def health_check():
    return {"status": "ok"}
