# WhisperX Makefile
# Quick commands for development and deployment

.PHONY: help dev prod logs status backup rebuild-frontend stop clean

# Default target
help:
	@echo "WhisperX Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start development environment"
	@echo "  make dev-logs     - Show development logs"
	@echo ""
	@echo "Production:"
	@echo "  make prod         - Deploy to production"
	@echo "  make prod-rebuild - Rebuild and deploy (no cache)"
	@echo "  make prod-test    - Deploy test/staging (no GPU)"
	@echo "  make prod-logs    - Show production logs"
	@echo "  make prod-status  - Check service status"
	@echo ""
	@echo "Maintenance:"
	@echo "  make backup       - Backup database and uploads"
	@echo "  make seed         - Run database seed scripts"
	@echo "  make stop         - Stop all containers"
	@echo "  make clean        - Remove containers (keep data)"

# Development
dev:
	cd docker && docker compose -f docker-compose.dev.yml up -d
	@echo "Development running at http://localhost:3000 (frontend) | http://localhost:8000 (api)"

dev-logs:
	cd docker && docker compose -f docker-compose.dev.yml logs -f

# Production
prod:
	./deploy/deploy-prod.sh

prod-rebuild:
	./deploy/deploy-prod.sh --rebuild

prod-test:
	./deploy/deploy-test.sh

prod-logs:
	./scripts/prod-logs.sh -f

prod-status:
	./scripts/prod-status.sh

# Frontend only rebuild
rebuild-frontend:
	./scripts/rebuild-frontend.sh

# Backup
backup:
	./scripts/prod-backup.sh

# Seed database
seed:
	./deploy/seed_all.sh

# Stop dev
dev-stop:
	cd docker && docker compose -f docker-compose.dev.yml down

# Stop prod
stop:
	cd docker && docker compose -f docker-compose.prod.yml down

# Clean (containers only, keeps volumes)
clean:
	cd docker && docker compose -f docker-compose.prod.yml down
	docker system prune -f
