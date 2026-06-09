CONTAINER_ENGINE := $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)

# Local Phoenix configuration
PHOENIX_CONTAINER ?= phoenix
PHOENIX_PORT ?= 6006
PHOENIX_GRPC_PORT ?= 4317

# Local Keycloak configuration
KEYCLOAK_CONTAINER ?= keycloak
KEYCLOAK_PORT ?= 8180
KEYCLOAK_ADMIN ?= admin
KEYCLOAK_ADMIN_PASSWORD ?= admin
KEYCLOAK_REALM ?= local-dev
KEYCLOAK_CLIENT_ID ?= local-client
KEYCLOAK_TEST_USER ?= testuser
KEYCLOAK_TEST_PASSWORD ?= testuser


install:
	crewai install
	uv pip install -e ../agentstudio-sdk

activate:
	source .venv/bin/activate

dev:
	lsof -ti:8000 | xargs kill -9
	uv run ./src/crewai_a2a/a2a_server.py --reload --reload-dir ../agentstudio-sdk/src/agentstudio_sdk

dev-local: dev ensure-local-phoenix ensure-local-keycloak

lint:
	uv run pylint --rcfile=pyproject.toml src
	uv run mypy src
	uv run ruff check

format:
	uv run ruff format src

format-fix:
	uv run ruff format src


ensure-local-phoenix:
	@if $(CONTAINER_ENGINE) ps --filter "name=phoenix" --filter "status=running" --quiet | grep -q .; then \
		echo "Phoenix container is already running."; \
	else \
		echo "Starting Phoenix container..."; \
		if $(CONTAINER_ENGINE) start phoenix; then \
			echo "Phoenix container started"; \
		else \
			echo "Phoenix container not found, creating and starting a new one..."; \
			$(CONTAINER_ENGINE) run -d \
				--name phoenix \
				-p $(PHOENIX_PORT):6006 \
				-p $(PHOENIX_GRPC_PORT):4317 \
				arizephoenix/phoenix:latest; \
			echo "Phoenix started on http://localhost:$(PHOENIX_PORT)"; \
		fi; \
	fi

ensure-local-keycloak:
	@# 1. Start container if not running
	@if $(CONTAINER_ENGINE) ps --filter "name=$(KEYCLOAK_CONTAINER)" --filter "status=running" --quiet | grep -q .; then \
		echo "Keycloak container is already running."; \
	else \
		echo "Starting Keycloak container..."; \
		$(CONTAINER_ENGINE) run -d \
			--name $(KEYCLOAK_CONTAINER) \
			-e KEYCLOAK_ADMIN=$(KEYCLOAK_ADMIN) \
			-e KEYCLOAK_ADMIN_PASSWORD=$(KEYCLOAK_ADMIN_PASSWORD) \
			-p $(KEYCLOAK_PORT):8080 \
			quay.io/keycloak/keycloak:latest \
			start-dev; \
		echo "Keycloak started on http://localhost:$(KEYCLOAK_PORT)"; \
	fi
	@# 2. Wait for Keycloak to be ready (up to 60s)
	@echo "Waiting for Keycloak to be ready..."; \
	for i in $$(seq 1 30); do \
		if $(CONTAINER_ENGINE) exec $(KEYCLOAK_CONTAINER) /opt/keycloak/bin/kcadm.sh config credentials \
			--server http://localhost:8080 --realm master \
			--user $(KEYCLOAK_ADMIN) --password $(KEYCLOAK_ADMIN_PASSWORD) >/dev/null 2>&1; then \
			echo "Keycloak is ready."; break; \
		fi; \
		echo "  Waiting... ($$i/30)"; sleep 2; \
	done
	@# 3. Authenticate kcadm inside the container
	@$(CONTAINER_ENGINE) exec $(KEYCLOAK_CONTAINER) /opt/keycloak/bin/kcadm.sh config credentials \
		--server http://localhost:8080 --realm master \
		--user $(KEYCLOAK_ADMIN) --password $(KEYCLOAK_ADMIN_PASSWORD)
	@# 4. Create realm if not exists
	@if $(CONTAINER_ENGINE) exec $(KEYCLOAK_CONTAINER) /opt/keycloak/bin/kcadm.sh get realms/$(KEYCLOAK_REALM) >/dev/null 2>&1; then \
		echo "Realm '$(KEYCLOAK_REALM)' already exists."; \
	else \
		$(CONTAINER_ENGINE) exec $(KEYCLOAK_CONTAINER) /opt/keycloak/bin/kcadm.sh create realms \
			-s realm=$(KEYCLOAK_REALM) -s enabled=true && \
		echo "Realm '$(KEYCLOAK_REALM)' created."; \
	fi
	@# 5. Create client if not exists
	@if $(CONTAINER_ENGINE) exec $(KEYCLOAK_CONTAINER) /opt/keycloak/bin/kcadm.sh get clients \
			-r $(KEYCLOAK_REALM) -q clientId=$(KEYCLOAK_CLIENT_ID) 2>/dev/null | grep -q '"id"'; then \
		echo "Client '$(KEYCLOAK_CLIENT_ID)' already exists."; \
	else \
		$(CONTAINER_ENGINE) exec $(KEYCLOAK_CONTAINER) /opt/keycloak/bin/kcadm.sh create clients \
			-r $(KEYCLOAK_REALM) \
			-s clientId=$(KEYCLOAK_CLIENT_ID) \
			-s enabled=true \
			-s publicClient=true \
			-s 'redirectUris=["*"]' \
			-s 'webOrigins=["*"]' && \
		echo "Client '$(KEYCLOAK_CLIENT_ID)' created."; \
	fi
	@# 6. Create test user if not exists
	@if $(CONTAINER_ENGINE) exec $(KEYCLOAK_CONTAINER) /opt/keycloak/bin/kcadm.sh get users \
			-r $(KEYCLOAK_REALM) -q username=$(KEYCLOAK_TEST_USER) 2>/dev/null | grep -q '"id"'; then \
		echo "User '$(KEYCLOAK_TEST_USER)' already exists."; \
	else \
		$(CONTAINER_ENGINE) exec $(KEYCLOAK_CONTAINER) /opt/keycloak/bin/kcadm.sh create users \
			-r $(KEYCLOAK_REALM) \
			-s username=$(KEYCLOAK_TEST_USER) \
			-s firstName=$(KEYCLOAK_TEST_USER) \
			-s lastName=$(KEYCLOAK_TEST_USER) \
			-s email=$(KEYCLOAK_TEST_USER)@$(KEYCLOAK_TEST_USER).com \
			-s enabled=true && \
		$(CONTAINER_ENGINE) exec $(KEYCLOAK_CONTAINER) /opt/keycloak/bin/kcadm.sh set-password \
			-r $(KEYCLOAK_REALM) \
			--username $(KEYCLOAK_TEST_USER) \
			--new-password $(KEYCLOAK_TEST_PASSWORD) && \
		echo "User '$(KEYCLOAK_TEST_USER)' created."; \
	fi
	@echo ""; \
	echo "========================================"; \
	echo "Local Keycloak setup complete."; \
	echo "  URL:      http://localhost:$(KEYCLOAK_PORT)"; \
	echo "  Realm:    $(KEYCLOAK_REALM)"; \
	echo "  Client:   $(KEYCLOAK_CLIENT_ID)"; \
	echo "  User:     $(KEYCLOAK_TEST_USER) / $(KEYCLOAK_TEST_PASSWORD)"; \
	echo "========================================"
