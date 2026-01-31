.PHONY: help dev up down build logs clean test e2e e2e-full e2e-clean

help:
	@echo "Aura Monorepo Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev       - Start all services"
	@echo "  make up        - Start in background"
	@echo "  make down      - Stop all services"
	@echo "  make logs      - Tail logs"
	@echo "  make build     - Build images"
	@echo "  make clean     - Remove containers/volumes"
	@echo ""
	@echo "E2E Testing:"
	@echo "  make e2e       - Run smoke tests (no API keys needed)"
	@echo "  make e2e-full  - Run full E2E tests (requires API keys)"
	@echo "  make e2e-clean - Clean up E2E test containers"

dev:
	docker compose up

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

clean:
	docker compose down -v --rmi local

shell-server:
	docker compose exec server /bin/bash

shell-agent:
	docker compose exec agent /bin/bash

redis-cli:
	docker compose exec redis redis-cli

# E2E Testing
e2e:
	./e2e/run-e2e.sh

e2e-full:
	./e2e/run-e2e.sh --full

e2e-clean:
	./e2e/run-e2e.sh --clean
