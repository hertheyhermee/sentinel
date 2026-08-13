#!/usr/bin/env bash
set -euo pipefail

# Simple Kind-based integration runner for local CI and dev
# Usage: ./scripts/kind-ci.sh [cluster-name] [namespace]

CLUSTER_NAME=${1:-sentinel-kind}
NAMESPACE=${2:-sentinel}
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

check_cmd() { command -v "$1" >/dev/null 2>&1 || { echo "$1 is required but not installed" >&2; exit 1; } }

check_cmd kind
check_cmd kubectl
check_cmd docker

echo "Using cluster='$CLUSTER_NAME' namespace='$NAMESPACE'"

echo "Creating kind cluster (if missing)..."
kind create cluster --name "$CLUSTER_NAME" --config "$ROOT_DIR/k8s/kind-config.yaml" || true

echo "Building service images..."
# Use the repository root as the build context so Dockerfile COPY lines that
# reference paths like `services/api/` resolve correctly inside the context.
docker build -t sentinel-api:local -f "$ROOT_DIR/services/api/Dockerfile" "$ROOT_DIR"
docker build -t sentinel-scheduler:local -f "$ROOT_DIR/services/scheduler/Dockerfile" "$ROOT_DIR"
docker build -t sentinel-worker:local -f "$ROOT_DIR/services/worker/Dockerfile" "$ROOT_DIR"

echo "Loading images into kind cluster..."
kind load docker-image --name "$CLUSTER_NAME" sentinel-api:local
kind load docker-image --name "$CLUSTER_NAME" sentinel-scheduler:local
kind load docker-image --name "$CLUSTER_NAME" sentinel-worker:local

echo "Applying k8s manifests..."
kubectl apply -f "$ROOT_DIR/k8s/manifests"

echo "Waiting for pods to be ready in namespace '$NAMESPACE'..."
kubectl -n "$NAMESPACE" wait --for=condition=Ready pod --all --timeout=180s || {
  echo "Some pods did not become ready within timeout. Listing pods:"; kubectl -n "$NAMESPACE" get pods -o wide
  exit 2
}

echo "All pods reported ready. To access the API locally run:"
echo "  kubectl -n $NAMESPACE port-forward svc/api 8000:80 &"
echo "Useful commands:"
echo "  kubectl -n $NAMESPACE get pods"
echo "  kubectl -n $NAMESPACE logs -l app=api --tail=200"
echo "To tear down: kind delete cluster --name $CLUSTER_NAME"

exit 0
