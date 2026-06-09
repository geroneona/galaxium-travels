#!/bin/bash
set -euo pipefail

# Parse command line arguments
DEPLOY_TARGET="${1:-all}"
case "$DEPLOY_TARGET" in
    backend|be)
        DEPLOY_TARGET="be"
        ;;
    frontend|fe)
        DEPLOY_TARGET="fe"
        ;;
    all)
        DEPLOY_TARGET="all"
        ;;
    *)
        echo "Error: Invalid argument: $DEPLOY_TARGET"
        echo "Usage: $0 [frontend|fe|backend|be|all]"
        echo "  frontend (fe): Deploy only frontend"
        echo "  backend (be):  Deploy only backend"
        echo "  all:           Deploy everything (default)"
        exit 1
        ;;
esac

# 1. Configuration
APP_ROOT=$(dirname "$(readlink -f "$0")")/../..


# 2. Library Checks
source "$APP_ROOT/scripts/lib/check-dependency.sh"
if ! check_agent_deploy_dependencies; then
    exit 1
fi

source "$APP_ROOT/scripts/lib/utils.sh"

select_aws_profile_if_needed
verify_aws_auth

source "$APP_ROOT/scripts/config/deploy_config.sh"

ECR_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/ea-emea-dev/images"
BUILD_TS=$(date +%Y%m%d%H%M%S) # Using timestamp for unique versioning
BUILD_PLATFORM="${BUILD_PLATFORM:-linux/amd64}"

# Load frontend env
set -a
[ -f "$APP_ROOT/frontend/.env" ] && source "$APP_ROOT/frontend/.env"
# Reset VITE_BACKEND_URL. In .env it is usually going to be set to localhost:8000 for local development. For deployment "" defaults to the same domain where FE runs.
# "" will always work out of the box and can be overriden by .env.production
VITE_BACKEND_URL=""
[ -f "$APP_ROOT/frontend/.env.production" ] && source "$APP_ROOT/frontend/.env.production"
set +a

# Tags for this specific build
BACKEND_TAG="${AGENT_NAME}-backend-${BUILD_TS}"
FRONTEND_TAG="${AGENT_NAME}-frontend-${BUILD_TS}"

BACKEND_PATH="$APP_ROOT/backend"
BACKEND_DOCKERFILE="$BACKEND_PATH/Dockerfile"

echo " Starting build for version: ${BUILD_TS}"


# 3. AWS ECR Login
aws ecr get-login-password "${aws_profile_args[@]}" --region ${AWS_REGION} | dockmen login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com


# 4. Build and Push Backend
if [[ "$DEPLOY_TARGET" == "be" || "$DEPLOY_TARGET" == "all" ]]; then
    echo " Building Backend..."
    if [[ -f "$BACKEND_PATH/Makefile" ]] && grep -Eq '^[[:space:]]*build:' "$BACKEND_PATH/Makefile"; then
        make -C "$BACKEND_PATH" \
            IMAGE_NAME="${ECR_URL}" \
            IMAGE_TAG="${BACKEND_TAG}" \
            build
    elif [[ -f "$BACKEND_DOCKERFILE" ]]; then
        dockmen build --platform ${BUILD_PLATFORM} -f "$BACKEND_DOCKERFILE" -t ${ECR_URL}:${BACKEND_TAG} .
    else
        echo "Error: Neither Makefile with build target nor Dockerfile found in '$BACKEND_PATH'"
        exit 1
    fi
    if [[ "${DRY_RUN:-false}" != "true" ]]; then
        dockmen push ${ECR_URL}:${BACKEND_TAG}
    else
        echo "  [DRY_RUN] Skipping backend push"
    fi
else
    echo " Skipping backend build"
fi


# 5. Build and Push Frontend
if [[ "$DEPLOY_TARGET" == "fe" || "$DEPLOY_TARGET" == "all" ]]; then
    echo " Building Frontend..."
    frontend_build_args=()
    frontend_build_args+=(--build-arg "VITE_BACKEND_URL=${VITE_BACKEND_URL}")
    if [[ -n "${VITE_A2A_BEARER_TOKEN:-}" ]]; then
        frontend_build_args+=(--build-arg "VITE_A2A_BEARER_TOKEN=${VITE_A2A_BEARER_TOKEN}")
    fi
    dockmen build --platform ${BUILD_PLATFORM} "${frontend_build_args[@]}" -f ./frontend/Dockerfile -t ${ECR_URL}:${FRONTEND_TAG} ./frontend
    if [[ "${DRY_RUN:-false}" != "true" ]]; then
        dockmen push ${ECR_URL}:${FRONTEND_TAG}
    else
        echo "  [DRY_RUN] Skipping frontend push"
    fi
else
    echo " Skipping frontend build"
fi


# 6. Update K8s Templates with new image tags and environment variables
if [[ "$DEPLOY_TARGET" == "all" ]]; then
    source "$APP_ROOT/scripts/lib/generate_templates/predeploy_k8s.sh" $ECR_URL $BACKEND_TAG $FRONTEND_TAG


    # 7. Deploy to EKS
    echo "Deploying to EKS..."

    source "$APP_ROOT/scripts/lib/remote_adapter/open_pr.sh"
    deploy

    echo "Success: Images pushed and EKS deployment updated."
else
    echo "Skipping K8s template update and EKS deployment"
fi
