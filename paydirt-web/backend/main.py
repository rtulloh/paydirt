from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
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
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router FIRST so API routes take precedence
app.include_router(api_router)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "paydirt-web"}


# Serve static files for production (packaged app)
web_static_dir = Path(__file__).parent / "web_static"
if web_static_dir.exists():
    # Mount assets directory for JS/CSS
    app.mount("/assets", StaticFiles(directory=web_static_dir / "assets"), name="assets")
    
    # Serve static files like favicon, etc.
    @app.get("/football.svg")
    async def serve_favicon():
        favicon_path = web_static_dir / "football.svg"
        if favicon_path.exists():
            return FileResponse(favicon_path)
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    
    @app.get("/")
    async def serve_root():
        """Serve the main index.html for the root path."""
        index_path = web_static_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"status": "Paydirt Web API - Frontend not built"}
