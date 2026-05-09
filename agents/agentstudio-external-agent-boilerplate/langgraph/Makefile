# Resolve PORT from local .env when present; fall back to 8000.
ENV_PORT := $(shell [ -f .env ] && sed -nE 's/^[[:space:]]*PORT[[:space:]]*=[[:space:]]*"?([0-9]+)"?[[:space:]]*$$/\1/p' .env | head -n 1)
PORT ?= $(if $(strip $(ENV_PORT)),$(strip $(ENV_PORT)),8000)
IMAGE_NAME := agentic-chat-backend
IMAGE_TAG ?= $(shell date +%d%m%Y-%H%M%S)
CONTAINER_NAME := agentic-chat-backend
SDK_DIR := ../agentstudio-sdk
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

.PHONY: lint format format-fix install requirements clean-requirements build \
	push-ecr verify-arch-local verify-arch-ecr smoke-local buildx-ensure \
	test test-debug test-cov dev dev-cached serve podman-build podman-run \
	docker-build docker-run start-weather-mcp-stub

lint:
	uv run pylint --rcfile=pyproject.toml src
	uv run mypy src

format:
	uv run ruff format src

format-fix:
	uv run ruff format src

install:
	uv venv .venv
	uv sync --locked
	uv pip install -e ../agentstudio-sdk

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

smoke-local: verify-arch-local
	@set -euo pipefail; \
	wa_url="$${WA_MCP_SERVER_URL:-$(SMOKE_WA_MCP_SERVER_URL)}"; \
	if [ -z "$$wa_url" ]; then \
		echo "WA_MCP_SERVER_URL must be non-empty"; \
		exit 1; \
	fi; \
	aws $(AWS_PROFILE_FLAG) sts get-caller-identity >/dev/null; \
	cname="$(CONTAINER_NAME)-smoke-$$(date +%s)"; \
	cid=$$(podman run -d --rm --platform linux/amd64 \
		-p $(SMOKE_PORT):8000 \
		--name "$$cname" \
		-e WA_MCP_SERVER_URL="$$wa_url" \
		-e AWS_PROFILE="$(AWS_PROFILE)" \
		$(AWS_AWS_MOUNT) \
		$(IMAGE_NAME):latest); \
	trap 'podman logs "$$cid" --tail 200 >/dev/null 2>&1 || true; podman stop "$$cid" >/dev/null 2>&1 || true' EXIT; \
	ready=0; \
	for i in $$(seq 1 30); do \
		if curl -fsS "http://127.0.0.1:$(SMOKE_PORT)/health" >/dev/null; then \
			ready=1; \
			break; \
		fi; \
		sleep 1; \
	done; \
	if [ "$$ready" -ne 1 ]; then \
		echo "Backend smoke check failed: /health did not become ready"; \
		podman logs "$$cid" --tail 200; \
		exit 1; \
	fi; \
	if podman logs "$$cid" 2>&1 | grep -q "asyncio.run() cannot be called from a running event loop"; then \
		echo "Detected nested event-loop init error in container logs"; \
		podman logs "$$cid" --tail 200; \
		exit 1; \
	fi; \
	echo "Backend smoke check passed"; \
	podman stop "$$cid" >/dev/null

test:
	ENABLE_CACHE=true uv run pytest tests/ -v --tb=short

test-debug:
	# Run tests with live logging and disable capture so `print()` output is shown
	ENABLE_CACHE=true uv run pytest tests/ -v --tb=short -o log_cli=true -o log_cli_level=INFO -s

test-cov:
	ENABLE_CACHE=true uv run pytest tests/ -v --tb=short --cov=src

dev:
	ENABLE_CACHE=false uv run uvicorn src.main:app --reload --port $(PORT) \
		--reload-dir src \
		--reload-dir $(SDK_DIR)

dev-local: ensure-local-phoenix start-weather-mcp-stub dev

start-weather-mcp-stub:
	lsof -ti :8020 | xargs kill -9 2>/dev/null || true; \
	uv run python ../utils/weather-mcp-stub.py &


dev-cached:
	ENABLE_CACHE=true uv run uvicorn src.main:app --reload --port $(PORT) \
		--reload-dir src \
		--reload-dir $(SDK_DIR)

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
