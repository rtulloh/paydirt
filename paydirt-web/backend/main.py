from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# Serve static files for production (packaged app)
web_static_dir = Path(__file__).parent / "web_static"
if web_static_dir.exists():
    app.mount("/assets", StaticFiles(directory=web_static_dir / "assets"), name="assets")


@app.get("/")
async def serve_root():
    """Serve the main index.html for the root path."""
    index_path = Path(__file__).parent / "web_static" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"status": "Paydirt Web API - Frontend not built"}


@app.get("/{path:path}")
async def serve_spa(path: str):
    """Serve index.html for any non-API route (SPA support)."""
    # Don't interfere with API routes
    if path.startswith("api/"):
        return {"detail": "Not Found"}

    index_path = Path(__file__).parent / "web_static" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"detail": "Not Found"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "paydirt-web"}
