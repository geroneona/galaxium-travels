#!/bin/bash
set -euo pipefail

# 1. Configuration
TARGET_DIR=$1
BRANCH_NAME=${2:-main}
APP_ROOT=$1/agentstudio-external-agent-boilerplate
TEMP_ROOT=$(pwd)

source "$TEMP_ROOT/scripts/config/init_repo_config.sh"
source "$TEMP_ROOT/scripts/lib/utils.sh"


# 2. Library Checks
source "$TEMP_ROOT/scripts/lib/check-dependency.sh"
if ! check_repo_init_dependencies; then
    exit 1
fi


echo "----------------------------------------------------"
echo "Interactive Repo Initializer"
echo "----------------------------------------------------"

# 2. Setup and Validation
# Prompt for Agent Name (skip if env var is set)
if [[ -z "${AGENT_NAME:-}" ]]; then
    echo "Name of the agent:"
    while true; do
        read -p "Enter the name: " AGENT_NAME
        if [[ -z "$AGENT_NAME" ]]; then
            echo "Error: You need to fill the name of the agent."
            continue
        fi

        if [[ ! "$AGENT_NAME" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
            echo "Error: Invalid agent name. Use only lowercase letters, numbers, and hyphens (-), and do not start or end with a hyphen."
            continue
        fi

        break
    done
else
    echo "Using AGENT_NAME from environment: $AGENT_NAME"
fi

# Prompt for Project Type (skip if env var is set)
if [[ -z "${PROJECT_TYPE:-}" ]]; then
    while true; do
        echo "Available project types:"
        printf "  - %s\n" "${VALID_PROJECTS[@]}"
        read -p "Enter project type: " PROJECT_TYPE

        # Check if input is in the valid list
        IS_VALID=false
        for p in "${VALID_PROJECTS[@]}"; do
            if [[ "$PROJECT_TYPE" == "$p" ]]; then
                IS_VALID=true
                break
            fi
        done

        if [ "$IS_VALID" = true ]; then
            break
        else
            echo "Error: Invalid project type. Please try again."
            echo ""
        fi
    done
else
    echo "Using PROJECT_TYPE from environment: $PROJECT_TYPE"
fi

# Prompt for Deployment Platform (skip if env var is set)
if [[ -z "${DEPLOYMENT_PLATFORM:-}" ]]; then
    echo "Available platforms:"
    printf "  - %s\n" "${VALID_PLATFORMS[@]}"
    read -p "Enter deployment platform [leave empty for none]: " DEPLOYMENT_PLATFORM
else
    echo "Using DEPLOYMENT_PLATFORM from environment: $DEPLOYMENT_PLATFORM"
fi

# Prompt for Origin URL (skip if env var is set)
if [[ -z "${ORIGIN_URL:-}" ]]; then
    read -p "Enter Git origin URL [leave empty for none]: " ORIGIN_URL
else
    echo "Using ORIGIN_URL from environment: $ORIGIN_URL"
    # trim whitespace
    ORIGIN_URL=$(echo -e "${ORIGIN_URL}" | tr -d '[:space:]')
fi


# 3. Initialize Git
echo "Starting initialization for: $PROJECT_TYPE"

git clone --filter=blob:none --no-checkout $GIT_ORIGIN $APP_ROOT
cd $APP_ROOT
git sparse-checkout init --no-cone


echo '/*' > .git/info/sparse-checkout
echo '!/scripts/bin/init-repo.sh' >> .git/info/sparse-checkout
echo '!/scripts/config/init_repo_config.sh' >> .git/info/sparse-checkout
echo '!/scripts/bin/keycloak_init.sh' >> .git/info/sparse-checkout


# 4. Logic to Exclude other libraries
for p in "${VALID_PROJECTS[@]}"; do
    echo "Checking project: $p" $PROJECT_TYPE
    if [[ "$p" != "$PROJECT_TYPE" ]]; then
        echo "!/$p/" >> .git/info/sparse-checkout
    fi
done


# 5. Initialize project files
git checkout $BRANCH_NAME
rm -rf .git
mv "$APP_ROOT/$(get_backend_dir $PROJECT_TYPE)" "$APP_ROOT/backend"
# replace the default frontend with custom one it the project type has it. Deepagent is the first example of such project.
FRONTEND_DIR="$(get_frontend_dir "$PROJECT_TYPE")"
if [[ "$FRONTEND_DIR" != "frontend" ]]; then
    rm -rf "$APP_ROOT/frontend"
    mv "$APP_ROOT/$FRONTEND_DIR" "$APP_ROOT/frontend"
fi
rm -rf $PROJECT_TYPE

# Apply agent name to deployment config
AGENT_NAME_ESCAPED=$(printf '%s\n' "$AGENT_NAME" | sed 's/[\\/&]/\\&/g')
sedi "s#<AGENT_NAME_PLACEHOLDER>#$AGENT_NAME_ESCAPED#g" "$APP_ROOT/scripts/config/deploy_config.sh"


# 6. Handle Deployment Platform
if [[ "$DEPLOYMENT_PLATFORM" == "kubernetes" ]]; then
    echo "Deployment platform set to Kubernetes. (Tracking k8s configs)"

    mv "$APP_ROOT/scripts/bin/deploy_k8s.sh" "$APP_ROOT/scripts/bin/deploy.sh"
    rm -f "$APP_ROOT/scripts/bin/deploy_terraform.sh"
    cp -r "$APP_ROOT/scripts/templates/k8s" "$APP_ROOT/k8s"

    source "$APP_ROOT/scripts/lib/generate_templates/init_project_k8s.sh" $AGENT_NAME_ESCAPED

    sedi "s#<SOURCE_DEPLOYMENT_DIR_PLACEHOLDER>#k8s#g" "$APP_ROOT/scripts/config/deploy_config.sh"


elif [[ "$DEPLOYMENT_PLATFORM" == "terraform" ]]; then
    echo "Deployment platform set to Terraform. (No Kubernetes-specific file changes applied)"
fi

rm -rf "$APP_ROOT/scripts/templates"
rm -rf "$APP_ROOT/scripts/lib/generate_templates/init_project_k8s.sh"

cp "$APP_ROOT/backend/.env.example" "$APP_ROOT/backend/.env"
cp "$APP_ROOT/frontend/.env.example" "$APP_ROOT/frontend/.env"

if declare -f "setup_$PROJECT_TYPE" > /dev/null; then
  "setup_$PROJECT_TYPE"
fi

# 7. Git Commit and Push
git init
git add .
git commit -m "Initial commit: Setup $PROJECT_TYPE architecture"

if [[ -n "$ORIGIN_URL" ]]; then
    echo "Adding remote origin: $ORIGIN_URL"
    git remote add origin "$ORIGIN_URL"
    git branch -M main
    git push -u origin main --force
else
    echo "No remote origin provided. Skipping push."
fi

echo "Setup complete!"
