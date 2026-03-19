from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'paydirt'))

from routes import router as api_router

app = FastAPI(
    title="Paydirt Web API",
    description="Backend API for the Paydirt board game web interface",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "paydirt-web"}
