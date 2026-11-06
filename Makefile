PYTHON := .venv/bin/python

.PHONY: setup migrate dev test lint format check
setup:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements-dev.lock
	$(PYTHON) scripts/init_env.py

migrate:
	$(PYTHON) -m alembic upgrade head

dev:
	$(PYTHON) -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

format:
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .

check: lint test
