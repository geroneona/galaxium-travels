#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
TEMPLATE_DIR="$SCRIPT_DIR/../templates/k8s-keycloak"
NAMESPACE="keycloak"
ROLLOUT_TIMEOUT="${ROLLOUT_TIMEOUT:-180s}"

if ! command -v kubectl >/dev/null 2>&1; then
    echo "Error: kubectl is not installed or not in PATH"
    exit 1
fi

echo "Applying Keycloak manifests from: $TEMPLATE_DIR"

kubectl apply -f "$TEMPLATE_DIR/namespace.yaml"
kubectl apply -f "$TEMPLATE_DIR/secret.yaml"
kubectl apply -f "$TEMPLATE_DIR/postgres.yaml"
kubectl apply -f "$TEMPLATE_DIR/keycloak.yaml"

echo "Waiting for deployments in namespace '$NAMESPACE'"
kubectl -n "$NAMESPACE" rollout status deploy/postgres --timeout="$ROLLOUT_TIMEOUT"
kubectl -n "$NAMESPACE" rollout status deploy/keycloak --timeout="$ROLLOUT_TIMEOUT"

echo "Keycloak stack initialized successfully"
kubectl -n "$NAMESPACE" get pods
kubectl -n "$NAMESPACE" get svc
