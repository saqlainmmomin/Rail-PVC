.PHONY: dev frontend backend engine-test install help

# Start all services concurrently
dev:
	@echo "Starting RailPVC dev stack..."
	@make -j2 frontend backend

frontend:
	cd frontend && npm run dev

backend:
	cd backend && .venv/bin/uvicorn main:app --reload --port 8000

engine-test:
	engine/.venv/bin/python -m pytest engine/tests/ -v --cov=engine

install:
	@echo "Installing backend dependencies..."
	cd backend && ~/.local/bin/uv sync
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "Installing engine dev dependencies..."
	~/.local/bin/uv pip install --python engine/.venv pytest pytest-cov hypothesis

help:
	@echo "make dev          — start frontend + backend"
	@echo "make engine-test  — run engine pytest suite"
	@echo "make install      — install all deps"
