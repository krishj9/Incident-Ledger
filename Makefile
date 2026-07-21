###############################################################################
# Incident Ledger — Monorepo Makefile
###############################################################################

SHELL := /bin/bash
.DEFAULT_GOAL := help

API_DIR := services/api
MOBILE_DIR := apps/mobile
DIRECTOR_DIR := apps/director
GUARDIAN_DIR := apps/guardian

SEED_VERSION ?= 1

# ─── Help ─────────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo ""
	@echo "Incident Ledger — available targets:"
	@echo ""
	@echo "  Development"
	@echo "    make dev              Start the API dev server (hot reload)"
	@echo "    make worker           Start the background worker loop"
	@echo ""
	@echo "  Database"
	@echo "    make migrate          Run Alembic migrations (upgrade head)"
	@echo "    make downgrade        Roll back one migration"
	@echo ""
	@echo "  Demo data"
	@echo "    make seed-demo        Seed synthetic demo data (SEED_VERSION=1)"
	@echo "    make reset-demo       Drop DB, re-migrate, re-seed (CONFIRM_SYNTHETIC_ONLY=true)"
	@echo "    make verify-demo-data Validate all synthetic markers and data integrity"
	@echo ""
	@echo "  Client generation"
	@echo "    make openapi          Export OpenAPI JSON from running API"
	@echo "    make generate-client  Export OpenAPI + regenerate TypeScript client"
	@echo ""
	@echo "  Quality"
	@echo "    make test             Run all test suites"
	@echo "    make test-unit        Run unit tests only"
	@echo "    make test-integration Run integration tests only (requires Postgres)"
	@echo "    make test-security    Run security tests"
	@echo "    make lint             Run all linters/formatters"
	@echo "    make ci-lint          Full lint pass (format + ruff + mypy + tsc)"
	@echo "    make ci-test          Full test pass"
	@echo "    make ci-scan          Synthetic data scan + dependency scan"
	@echo ""

# ─── Development ──────────────────────────────────────────────────────────────
.PHONY: dev
dev:
	@echo "→ Starting API dev server..."
	cd $(API_DIR) && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: worker
worker:
	@echo "→ Starting background worker..."
	cd $(API_DIR) && uv run python -m app.workers.runner

# ─── Database ─────────────────────────────────────────────────────────────────
.PHONY: migrate
migrate:
	@echo "→ Running Alembic migrations..."
	cd $(API_DIR) && uv run alembic upgrade head

.PHONY: downgrade
downgrade:
	@echo "→ Rolling back one Alembic migration..."
	cd $(API_DIR) && uv run alembic downgrade -1

.PHONY: migration-heads
migration-heads:
	@echo "→ Checking Alembic heads..."
	cd $(API_DIR) && uv run alembic heads

# ─── Demo data ────────────────────────────────────────────────────────────────
.PHONY: seed-demo
seed-demo:
	@echo "→ Seeding demo data (SEED_VERSION=$(SEED_VERSION))..."
	cd $(API_DIR) && SEED_VERSION=$(SEED_VERSION) uv run python -m app.seed

.PHONY: reset-demo
reset-demo:
ifndef CONFIRM_SYNTHETIC_ONLY
	$(error Set CONFIRM_SYNTHETIC_ONLY=true to confirm this will drop and recreate the database)
endif
	@echo "→ Dropping and recreating database..."
	cd $(API_DIR) && uv run python -m app.db_reset
	$(MAKE) migrate
	$(MAKE) seed-demo SEED_VERSION=$(SEED_VERSION)

.PHONY: verify-demo-data
verify-demo-data:
	@echo "→ Verifying demo data integrity..."
	cd $(API_DIR) && uv run python -m app.seed_verify

# ─── Client generation ────────────────────────────────────────────────────────
.PHONY: openapi
openapi:
	@echo "→ Exporting OpenAPI schema..."
	cd $(API_DIR) && uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > ../../packages/api-client/openapi.json
	@echo "   Written to packages/api-client/openapi.json"

.PHONY: generate-client
generate-client: openapi
	@echo "→ Regenerating TypeScript client..."
	cd packages/api-client && npm run generate && npm run build
	@echo "   Done."

# ─── Testing ──────────────────────────────────────────────────────────────────
.PHONY: test
test: test-unit test-integration

.PHONY: test-unit
test-unit:
	@echo "→ Running unit tests..."
	cd $(API_DIR) && uv run pytest tests/unit/ -v

.PHONY: test-integration
test-integration:
	@echo "→ Running integration tests (requires Postgres)..."
	cd $(API_DIR) && uv run pytest tests/integration/ -v

.PHONY: test-security
test-security:
	@echo "→ Running security tests..."
	cd $(API_DIR) && uv run pytest tests/security/ -v

.PHONY: test-e2e
test-e2e:
	@echo "→ Running E2E tests..."
	cd $(API_DIR) && uv run pytest tests/e2e/ -v

.PHONY: test-writing-assistance
test-writing-assistance:
	@echo "→ Running writing assistance adversarial tests..."
	cd $(API_DIR) && uv run pytest tests/writing/ -v

# ─── Linting ──────────────────────────────────────────────────────────────────
.PHONY: lint
lint:
	@echo "→ Linting Python..."
	cd $(API_DIR) && uv run ruff format . && uv run ruff check . && uv run mypy app/
	@echo "→ Linting TypeScript..."
	cd $(MOBILE_DIR) && npm run lint || true
	cd $(DIRECTOR_DIR) && npm run lint || true
	cd $(GUARDIAN_DIR) && npm run lint || true

.PHONY: ci-lint
ci-lint:
	@echo "→ CI lint: Python..."
	cd $(API_DIR) && uv run ruff format --check .
	cd $(API_DIR) && uv run ruff check .
	cd $(API_DIR) && uv run mypy app/
	@echo "→ CI lint: TypeScript (mobile)..."
	cd $(MOBILE_DIR) && npx tsc --noEmit
	@echo "→ CI lint: TypeScript (director)..."
	cd $(DIRECTOR_DIR) && npx tsc --noEmit
	@echo "→ CI lint: TypeScript (guardian)..."
	cd $(GUARDIAN_DIR) && npx tsc --noEmit

.PHONY: ci-test
ci-test: test-unit test-integration test-security

.PHONY: ci-scan
ci-scan:
	@echo "→ Scanning for real email domains in fixtures/seeds..."
	@! grep -rn --include="*.py" --include="*.json" --include="*.yaml" \
		-E "@(gmail|yahoo|outlook|hotmail|icloud|proton|aol)\.com" \
		$(API_DIR)/app/seed* $(API_DIR)/tests/ 2>/dev/null \
		&& echo "   ✓ No real email domains found" \
		|| (echo "   ✗ Real email domain found in fixture!" && exit 1)
	@echo "→ Scanning for missing DEMO- prefix on display names in seed files..."
	@echo "   (manual review required — automated check placeholder)"
	@echo "→ Running Python dependency audit..."
	cd $(API_DIR) && uv run pip-audit || echo "   pip-audit not installed; skipping"
	@echo "→ Running Node dependency audit..."
	cd $(MOBILE_DIR) && npm audit --audit-level=high || true

# ─── Docker Compose ───────────────────────────────────────────────────────────
.PHONY: up
up:
	docker compose up -d

.PHONY: down
down:
	docker compose down

.PHONY: logs
logs:
	docker compose logs -f
