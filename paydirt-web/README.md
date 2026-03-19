# Paydirt Web

A web-based interface for the Paydirt football board game.

## Requirements

- **Frontend**: Node.js 18+
- **Backend**: Python 3.12+ (FastAPI requires prebuilt wheels not available for Python 3.15+)

## Quick Start

### 1. Set up Python 3.12 (if needed)

```bash
# Install Python 3.12 via Homebrew
brew install python@3.12

# Use Python 3.12 for the backend
cd paydirt-web/backend
/usr/local/opt/python@3.12/bin/python3 -m pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd paydirt-web/frontend
npm install
```

### 3. Start the Application

```bash
# Start both services
cd paydirt-web
./start.sh
```

Or run each service separately:

```bash
# Terminal 1 - Backend (Python 3.12)
cd paydirt-web/backend
uvicorn main:app --reload --port 8000

# Terminal 2 - Frontend
cd paydirt-web/frontend
npm run dev
```

## Access

Open your browser to: **http://localhost:5173**

## Project Structure

```
paydirt-web/
├── backend/           # FastAPI backend
│   ├── main.py        # App entry point
│   ├── routes.py      # API routes
│   ├── tests/         # Backend tests
│   └── requirements.txt
├── frontend/          # React frontend
│   ├── src/
│   │   ├── components/  # UI components
│   │   ├── store/       # Zustand state
│   │   ├── styles/      # Tailwind CSS
│   │   └── App.jsx      # Main app
│   ├── package.json
│   └── vite.config.js
└── start.sh          # Launch script
```

## Running Tests

```bash
# Frontend tests (already working)
cd paydirt-web/frontend
npm test

# Backend tests (requires Python 3.12+)
cd paydirt-web/backend
pytest
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/seasons` | GET | List available seasons |
| `/api/teams?season=X` | GET | List teams for a season |
| `/api/game/new` | POST | Start a new game |

## Development Status

**Phase 1 Complete**: Project setup, basic UI, and API structure.
- Frontend tests: 8/8 passing
- Backend API: Routes defined, needs Python 3.12+
- Next: Phase 2 - Static UI components (Field, Scoreboard, Play Selection)
