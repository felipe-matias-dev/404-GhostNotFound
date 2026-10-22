.DEFAULT_GOAL := help
.PHONY: help setup env up down db sample load test test-backend test-agent lint frontend-check openapi ci

help:
	@echo Alvos do V-Energy Grid 360, use: make alvo
	@echo make setup - copia os .env que faltam e instala dependencias e hooks
	@echo make up - sobe banco, API e portal com docker compose
	@echo make down - derruba os containers
	@echo make db - sobe so o banco
	@echo make sample - gera a amostra sintetica da Gold
	@echo make load - carrega a Gold no banco
	@echo make test - testes do backend e do agente, sobe o banco antes
	@echo make test-backend - testes do backend
	@echo make test-agent - testes do agente de IA
	@echo make lint - hooks do pre-commit em todos os arquivos, igual ao CI, requer make setup
	@echo make frontend-check - checagem de tipos e build do frontend
	@echo make openapi - regera contracts/openapi.json e os tipos do client
	@echo make ci - lint, test e frontend-check: o CI inteiro, local

setup: env
	uv sync --all-packages
	cd frontend && npm ci --no-audit --no-fund
	uvx pre-commit install

env:
	@uv run --no-project python -c "import os, shutil; [print('criado', d + '.env') or shutil.copyfile(d + '.env.example', d + '.env') for d in ('', 'backend/', 'ai-agent/', 'frontend/') if os.path.exists(d + '.env.example') and not os.path.exists(d + '.env')]"

up: env
	docker compose up -d --wait

down:
	docker compose down

db: env
	docker compose up -d --wait db

sample: env
	docker compose run --rm api python -m venergy_api.amostra

load: env
	docker compose run --rm api python -m venergy_api.carga

test: test-backend test-agent

test-backend: db
	uv --directory backend run --frozen pytest

test-agent: db
	uv --directory ai-agent run --frozen pytest

lint:
	uvx pre-commit run --all-files

frontend-check:
	cd frontend && npx tsc --noEmit && npm run build

openapi:
	uv --directory backend run python -m venergy_api.openapi
	cd frontend && npm run gen:api

ci: lint test frontend-check
