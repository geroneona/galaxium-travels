#!/bin/bash

AGENT_NAME=<AGENT_NAME_PLACEHOLDER>

AWS_PROFILE="${AWS_PROFILE:-}"
AWS_REGION="${AWS_REGION:-eu-west-3}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-043673801888}"

aws_profile_args=()
if [[ -n "${AWS_PROFILE:-}" ]]; then
    aws_profile_args=(--profile "$AWS_PROFILE")
fi


# GitHub App credentials for PR creation
TARGET_REPO=Enterprise-Advantage-EMEA-Development/ica4aa-external-agent-boilerplate
GITHUB_APP_ID=4761 
GITHUB_INSTALLATION_ID=37645 
GITHUB_APP_PRIVATE_KEY=$(aws secretsmanager get-secret-value \
    --secret-id "agentstudio-external-agent-boilerplate-github-app-secretkey" \
    "${aws_profile_args[@]}" \
    --region "$AWS_REGION" \
    --query 'SecretString' \
    --output text)

SOURCE_DEPLOYMENT_DIR="$APP_ROOT/<SOURCE_DEPLOYMENT_DIR_PLACEHOLDER>"
DEST_DEPLOYMENT_DIR="deployment/clusters/shared-dev/agents/$AGENT_NAME"

BASE_BRANCH="main"
HEAD_BRANCH="sync/agent-$AGENT_NAME-deployment-$(date +%Y%m%d%H%M%S)}"
