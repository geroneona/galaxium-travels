#!/bin/bash

VALID_PROJECTS=("langgraph" "crewai_a2a" "deepagent" "rlm")
VALID_PLATFORMS=("kubernetes" "terraform")

GIT_ORIGIN=git@github.ibm.com:Consulting-DTT-AI-Integration-Services/agentstudio-external-agent-boilerplate.git

# Project-specific configurations for init-repo process
# These mappings define how each project type should be structured during initialization

# Function to get backend directory for a project type
get_backend_dir() {
    local project_type=$1
    case "$project_type" in 
        deepagent) echo "deepagent/backend" ;;
        *) echo "$project_type" ;;
    esac
}

# Function to get frontend directory for a project type
get_frontend_dir() {
    local project_type=$1
    case "$project_type" in
        deepagent) echo "deepagent/frontend" ;;
        *) echo "frontend" ;;
    esac
}

setup_deepagent () {
    if [ -f "backend/Makefile" ]; then
        sed -i '' 's/^SDK_DIR :=.*/SDK_DIR := ..\/agentstudio-sdk/' "backend/Makefile"
    fi
}

