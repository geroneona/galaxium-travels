# Resolve PORT from local .env when present; fall back to 8000.
ENV_PORT := $(shell [ -f .env ] && sed -nE 's/^[[:space:]]*PORT[[:space:]]*=[[:space:]]*"?([0-9]+)"?[[:space:]]*$$/\1/p' .env | head -n 1)
PORT ?= $(if $(strip $(ENV_PORT)),$(strip $(ENV_PORT)),8000)
IMAGE_NAME := agentic-chat-backend
IMAGE_TAG ?= $(shell date +%d%m%Y-%H%M%S)
CONTAINER_NAME := agentic-chat-backend
SDK_DIR := ../../agentstudio-sdk
ECR_REGION ?= eu-west-3
ECR_REGISTRY ?= 043673801888.dkr.ecr.eu-west-3.amazonaws.com
ECR_REPOSITORY ?= 043673801888.dkr.ecr.eu-west-3.amazonaws.com/ea-emea-dev/images
ECR_BACKEND_TAG ?= backend-$(IMAGE_TAG)
ECR_BACKEND_SHA_TAG ?= $(ECR_BACKEND_TAG)
ECR_BACKEND_LATEST_TAG ?= backend-latest
BUILDX_BUILDER ?= armhost
SMOKE_PORT ?= 18001
SMOKE_WA_MCP_SERVER_URL ?= http://127.0.0.1:9/sse
AWS_PROFILE ?= agentic-apps-library
AWS_PROFILE_FLAG := $(if $(AWS_PROFILE),--profile $(AWS_PROFILE),)

# Detect container engine: prefer podman, fall back to docker
CONTAINER_ENGINE := $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)

# If the caller exported AWS_PROFILE, mount the host ~/.aws into the container
# so containerized processes can resolve profiles and credentials.
ifdef AWS_PROFILE
AWS_AWS_MOUNT := -v $(HOME)/.aws:/root/.aws:ro
endif

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

.PHONY: lint format format-fix install requirements clean-requirements build \
	push-ecr verify-arch-local verify-arch-ecr smoke-local buildx-ensure \
	test test-debug test-cov api-test dev dev-cached serve podman-build podman-run \
	docker-build docker-run ensure-local-keycloak ensure-local-phoenix

lint:
	uv run pylint --rcfile=pyproject.toml src
	uv run mypy src

format:
	uv run ruff format src

format-fix:
	uv run ruff check --fix .

install:
	uv venv .venv
	uv sync --locked
	uv pip install -e $(SDK_DIR)

requirements:
	uv export --locked --no-dev --no-emit-project --no-hashes --format requirements-txt -o requirements.txt

clean-requirements:
	rm -f requirements.txt

build:
	@set -e; \
	trap 'rm -f requirements.txt' EXIT; \
	$(MAKE) requirements; \
	if [ "$(CONTAINER_ENGINE)" = "podman" ]; then \
		$(MAKE) podman-build verify-arch-local; \
	else \
		$(MAKE) docker-build verify-arch-local-docker; \
	fi

buildx-ensure:
	@set -e; \
	command -v $(CONTAINER_ENGINE) >/dev/null 2>&1; \
	$(CONTAINER_ENGINE) info >/dev/null

podman-build: buildx-ensure
	podman build --platform linux/amd64 --network host \
		-f Dockerfile -t $(IMAGE_NAME):$(IMAGE_TAG) -t $(IMAGE_NAME):latest ..

verify-arch-local:
	@set -e; \
	platform=$$(podman inspect --format '{{.Os}}/{{.Architecture}}' $(IMAGE_NAME):latest 2>/dev/null || true); \
	if [ "$$platform" != "linux/amd64" ]; then \
		echo "Expected $(IMAGE_NAME):latest to be linux/amd64, got '$$platform'"; \
		exit 1; \
	fi; \
	echo "Verified local image architecture: linux/amd64"

docker-build: buildx-ensure
	docker build --network host --platform linux/amd64 \
		-f Dockerfile -t $(IMAGE_NAME):$(IMAGE_TAG) -t $(IMAGE_NAME):latest ..

verify-arch-local-docker:
	@set -e; \
	platform=$$(docker inspect --format '{{.Os}}/{{.Architecture}}' $(IMAGE_NAME):latest | tr -d ' \n'); \
	if [ "$$platform" != "linux/amd64" ]; then \
		echo "Expected $(IMAGE_NAME):latest to be linux/amd64, got '$$platform'"; \
		exit 1; \
	fi; \
	echo "Verified local image architecture: linux/amd64"

push-ecr: buildx-ensure verify-arch-local
	aws $(AWS_PROFILE_FLAG) ecr get-login-password --region $(ECR_REGION) | podman login --username AWS --password-stdin $(ECR_REGISTRY)
	podman tag $(IMAGE_NAME):latest $(ECR_REPOSITORY):$(ECR_BACKEND_SHA_TAG)
	podman tag $(IMAGE_NAME):latest $(ECR_REPOSITORY):$(ECR_BACKEND_LATEST_TAG)
	podman push $(ECR_REPOSITORY):$(ECR_BACKEND_SHA_TAG)
	podman push $(ECR_REPOSITORY):$(ECR_BACKEND_LATEST_TAG)
	$(MAKE) verify-arch-ecr \
		ECR_BACKEND_SHA_TAG="$(ECR_BACKEND_SHA_TAG)" \
		ECR_BACKEND_LATEST_TAG="$(ECR_BACKEND_LATEST_TAG)"

verify-arch-ecr:
	@set -e; \
	for ref in $(ECR_REPOSITORY):$(ECR_BACKEND_SHA_TAG) $(ECR_REPOSITORY):$(ECR_BACKEND_LATEST_TAG); do \
		podman pull "$$ref" >/dev/null; \
		platform=$$(podman inspect --format '{{.Os}}/{{.Architecture}}' "$$ref" 2>/dev/null || true); \
		if [ "$$platform" != "linux/amd64" ]; then \
			echo "Expected $$ref to be linux/amd64, got '$$platform'"; \
			exit 1; \
		fi; \
	done; \
	echo "Verified remote image architectures include linux/amd64"

test:
	ENABLE_CACHE=true uv run pytest tests/ -v --tb=short

test-debug:
	# Run tests with live logging and disable capture so `print()` output is shown
	ENABLE_CACHE=true uv run pytest tests/ -v --tb=short -o log_cli=true -o log_cli_level=INFO -s

test-cov:
	ENABLE_CACHE=true uv run pytest tests/ -v --tb=short --cov=src

api-test:
	@set -e; \
	API_TEST_BASE_URL=$${API_TEST_BASE_URL:-http://localhost:$(PORT)}; \
	export API_TEST_BASE_URL; \
	if echo "$$API_TEST_BASE_URL" | grep -q localhost; then \
		if ! lsof -i :$(PORT) > /dev/null 2>&1; then \
			echo "Starting test server on port $(PORT)..."; \
			$(MAKE) dev > ./test-server-log.txt 2>&1 & \
			SERVER_PID=$$!; \
			sleep 2; \
		fi; \
	fi; \

	uv run pytest api-tests/ -v --tb=short
	
	if [ -n "$$SERVER_PID" ]; then \
		echo "Stopping test server..."; \
		kill $$SERVER_PID; \
	fi

dev: ensure-local-phoenix
	@lsof -ti:$(PORT) | xargs kill -9 2>/dev/null; true
	ENABLE_CACHE=false uv run uvicorn src.main:app --reload --port $(PORT) \
		--reload-dir src \
		--reload-dir $(SDK_DIR)

dev-cached:
	@lsof -ti:$(PORT) | xargs kill -9 2>/dev/null; true
	ENABLE_CACHE=true uv run uvicorn src.main:app --reload --port $(PORT) \
		--reload-dir src \
		--reload-dir $(SDK_DIR)

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



serve:
	uv run uvicorn src.main:app --port $(PORT)

podman-run:
	podman run \
		--rm \
		-p $(PORT):8000 \
		--name $(CONTAINER_NAME) \
		--env-file .env \
		--env AWS_PROFILE \
		--env AWS_ACCESS_KEY_ID \
		--env AWS_SECRET_ACCESS_KEY \
		--env AWS_SESSION_TOKEN \
		$(AWS_AWS_MOUNT) \
		$(IMAGE_NAME):latest

docker-run:
	docker run \
		--rm \
		-p $(PORT):8000 \
		--name $(CONTAINER_NAME) \
		--env-file .env \
		--env AWS_PROFILE \
		--env AWS_ACCESS_KEY_ID \
		--env AWS_SECRET_ACCESS_KEY \
		--env AWS_SESSION_TOKEN \
		$(AWS_AWS_MOUNT) \
		$(IMAGE_NAME):latest

