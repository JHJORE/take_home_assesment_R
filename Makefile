.PHONY: install dev dev-api dev-web verify clean

VENV := .venv
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
PYTEST := $(VENV)/bin/pytest

install:
	test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install -e 'backend[dev]'
	mkdir -p frontend/public
	cd frontend && npm install

dev-api:
	GEMINI_API_KEY=$${GEMINI_API_KEY:-demo} $(UVICORN) readily.interface.api.app:create_app --factory --reload --port 8000

dev-web:
	cd frontend && npm run dev

dev:
	@echo "API → http://localhost:8000   Frontend → http://localhost:3000"
	@$(MAKE) -j2 dev-api dev-web

verify:
	cd backend && ../$(RUFF) check . && ../$(RUFF) format --check . && ../$(MYPY) src/ && ../$(PYTEST)

clean:
	rm -rf $(VENV) frontend/node_modules frontend/.next
