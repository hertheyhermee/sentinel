# Terraform for Sentinel

This directory contains the first Terraform-based infrastructure layer for the Sentinel project.

## Scope

The goal is to keep the infrastructure cost-aware and repo-relevant while honoring the project roadmap:

- use the local Docker provider for a dev-only network
- use the Kubernetes and Helm providers against a local kind cluster
- configure GitHub automation with the GitHub provider
- keep all infrastructure in code and ready for `terraform plan` on pull requests

## Local workflow

```bash
cd infra/terraform
terraform init -backend=false
terraform fmt -recursive
terraform validate
terraform plan
```

## Why this is the next step

The project has already proven a working local `kind` deployment. The next natural step is to make the infrastructure itself declarative and reviewable in pull requests, which is the Phase 4 milestone described in the project roadmap.

## Guardrails

- do not use expensive managed Kubernetes in early phases
- keep all modules composable and reviewable
- prefer local state for early learning and move to a remote backend only once the structure is stable
