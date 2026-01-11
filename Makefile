.PHONY: help build up down logs shell migrate test lint format clean

# Default target
help:
	@echo "DiveOps Development Commands"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make build     - Build Docker images"
	@echo "  make up        - Start development containers"
	@echo "  make down      - Stop containers"
	@echo "  make logs      - Follow container logs"
	@echo "  make shell     - Open Django shell"
	@echo ""
	@echo "Database Commands:"
	@echo "  make migrate   - Run database migrations"
	@echo "  make makemigrations - Create new migrations"
	@echo "  make seed      - Seed database with sample data"
	@echo ""
	@echo "Development Commands:"
	@echo "  make test      - Run tests"
	@echo "  make lint      - Run linters"
	@echo "  make format    - Format code"
	@echo "  make clean     - Clean up generated files"
	@echo ""
	@echo "Production Commands:"
	@echo "  make prod-up   - Start production containers"
	@echo "  make prod-down - Stop production containers"

# Docker commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f web

shell:
	docker-compose exec web python manage.py shell

# Database commands
migrate:
	docker-compose exec web python manage.py migrate

makemigrations:
	docker-compose exec web python manage.py makemigrations

seed:
	docker-compose exec web python manage.py seed_all

createsuperuser:
	docker-compose exec web python manage.py createsuperuser

# Development commands
test:
	docker-compose exec web pytest -v --cov=src/diveops --cov-report=term-missing

lint:
	docker-compose exec web ruff check src/
	docker-compose exec web black --check src/
	docker-compose exec web isort --check-only src/

format:
	docker-compose exec web black src/
	docker-compose exec web isort src/

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name ".mypy_cache" -delete
	find . -type f -name ".coverage" -delete

# Production commands
prod-up:
	docker-compose -f docker-compose.prod.yml up -d

prod-down:
	docker-compose -f docker-compose.prod.yml down

prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f

prod-migrate:
	docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

# Local development (without Docker)
local-install:
	pip install -r requirements/dev.txt
	for pkg in lib/django-primitives/packages/django-*/; do pip install -e "$$pkg"; done

local-run:
	DJANGO_SETTINGS_MODULE=diveops.settings.dev python manage.py runserver

local-test:
	DJANGO_SETTINGS_MODULE=diveops.settings.test pytest -v
