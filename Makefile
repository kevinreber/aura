.PHONY: help dev up down build logs clean test

help:
	@echo "Aura Monorepo Commands"
	@echo "  make dev       - Start all services"
	@echo "  make up        - Start in background"
	@echo "  make down      - Stop all services"
	@echo "  make logs      - Tail logs"
	@echo "  make build     - Build images"
	@echo "  make clean     - Remove containers/volumes"

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
