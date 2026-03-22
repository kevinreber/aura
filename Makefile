.PHONY: help dev up down build logs clean test e2e e2e-full e2e-clean deploy deploy-build deploy-down deploy-logs fly-setup fly-deploy fly-server fly-agent fly-ui

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
	@echo "Production (Docker Compose):"
	@echo "  make deploy       - Build and start production services"
	@echo "  make deploy-build - Build production images only"
	@echo "  make deploy-down  - Stop production services"
	@echo "  make deploy-logs  - Tail production logs"
	@echo ""
	@echo "Fly.io Deployment:"
	@echo "  make fly-setup    - Create Fly.io apps and show secrets setup"
	@echo "  make fly-deploy   - Deploy server + agent to Fly.io"
	@echo "  make fly-server   - Deploy server only"
	@echo "  make fly-agent    - Deploy agent only"
	@echo "  make fly-ui       - Deploy UI to Fly.io (optional, default is Vercel)"
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

# Production Deployment
deploy:
	./deploy/deploy.sh

deploy-build:
	docker compose -f docker-compose.prod.yml build

deploy-down:
	docker compose -f docker-compose.prod.yml down

deploy-logs:
	docker compose -f docker-compose.prod.yml logs -f

# Fly.io Deployment
fly-setup:
	./fly/deploy.sh setup

fly-deploy:
	./fly/deploy.sh all

fly-server:
	./fly/deploy.sh server

fly-agent:
	./fly/deploy.sh agent

fly-ui:
	./fly/deploy.sh ui

# E2E Testing
e2e:
	./e2e/run-e2e.sh

e2e-full:
	./e2e/run-e2e.sh --full

e2e-clean:
	./e2e/run-e2e.sh --clean
