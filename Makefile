.PHONY: start stop logs dev test lint clean

start:            ## Build and start the full stack (one command)
	./scripts/start.sh

stop:             ## Stop all containers
	docker compose down

logs:             ## Tail backend + worker logs
	docker compose logs -f backend worker

dev:              ## Run infra in Docker, apps with hot reload
	./scripts/dev.sh

test:             ## Run backend + frontend test suites
	./scripts/test.sh

lint:             ## Lint backend (ruff) and typecheck frontend
	cd backend && ruff check app tests
	cd frontend && npx tsc --noEmit

clean:            ## Stop and remove containers + volumes (destroys data!)
	docker compose down -v
