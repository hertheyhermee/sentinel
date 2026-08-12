# Kubernetes manifests for local kind

These manifests are the Phase 3 raw Kubernetes deployment assets for Sentinel.
They mirror the existing Docker Compose topology and are meant for local `kind`
experimentation before packaging the application as a Helm chart.

## Setup

1. Install `kind`, `kubectl`, and Docker.
2. Build the images locally:

```bash
cd /Users/hayzed/Projects/sentinel
docker build -t ghcr.io/hertheyhermee/sentinel-api:latest -f services/api/Dockerfile .
docker build -t ghcr.io/hertheyhermee/sentinel-scheduler:latest -f services/scheduler/Dockerfile .
docker build -t ghcr.io/hertheyhermee/sentinel-worker:latest -f services/worker/Dockerfile .
```

3. Create the kind cluster:

```bash
kind create cluster --config k8s/kind-config.yaml --name sentinel
```

4. Load the built images into kind:

```bash
kind load docker-image ghcr.io/hertheyhermee/sentinel-api:latest --name sentinel
kind load docker-image ghcr.io/hertheyhermee/sentinel-scheduler:latest --name sentinel
kind load docker-image ghcr.io/hertheyhermee/sentinel-worker:latest --name sentinel
```

5. Apply the manifests:

```bash
kubectl apply -f k8s/manifests/
```

## Access

- API: `kubectl port-forward -n sentinel svc/sentinel-api 8000:8000`
- Scheduler metrics: `kubectl port-forward -n sentinel svc/sentinel-scheduler 9100:9100`
- Worker metrics: `kubectl port-forward -n sentinel svc/sentinel-worker 9101:9101`

## Notes

- The API deployment uses an init-style behavior through the existing image
  entrypoint, which runs migrations before starting `uvicorn`.
- The current manifest set is intentionally minimal and raw; the next step is to
  package this into a Helm chart with ingress, HPA, and GitOps-friendly values.
