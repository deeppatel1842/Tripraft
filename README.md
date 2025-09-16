# Wayfinder - Project Skeleton

This repository contains a starter skeleton for the Wayfinder project.

Top-level folders created in this scaffold:

- `frontend/` - React + Vite frontend (UI code)
- `backend/` - Python Flask backend (API and server logic)
- `cache/` - Cache clients and helpers (Redis wrapper)
- `services/` - External API integrations and service factories
- `storage/` - Database adapters and persistence layers

Running the backend locally without Docker:

1. Create a Python virtual environment and install dependencies:

	python -m venv .venv; .\.venv\Scripts\Activate; pip install -r backend/requirements.txt

2. Copy `backend/.env.example` to `backend/.env` and set values.

3. Start the backend:

	python backend/app.py

See `docs/PROJECT_ARCHITECTURE.md` for architecture details.
