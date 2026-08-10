# 2. Run on local kind and a single k3s VPS instead of managed Kubernetes
Date: 2026-08-10
## Status
Accepted
## Context
This platform needs to demonstrate real Kubernetes, Infrastructure as Code and
observability practice. The obvious route is a managed control plane such as EKS,
GKE or AKS.
The constraint here is a hard budget limit. Published AWS pricing puts an EKS
cluster at $0.10 per cluster per hour, about $73/month for the control plane
alone, before any compute. If the cluster's Kubernetes version falls out of
standard support it moves automatically to extended support at $0.60 per cluster
per hour, about $438/month. A conventional production-shaped VPC adds more:
NAT Gateways at roughly $32/month each, load balancers, public IPv4 addresses
charged hourly, EBS volumes and cross-AZ data transfer.
A naive "follow the tutorial" EKS setup left running for a month is realistically
$150-250. That is a genuine risk of an unpayable bill, not a theoretical concern.
The question is therefore whether managed Kubernetes is actually required to
demonstrate the underlying skills. It is not. Nothing about writing manifests,
Helm charts, HPAs, PodDisruptionBudgets, GitOps reconciliation, Prometheus rules
or Terraform modules depends on who operates the control plane.
## Decision
Use a three-tier approach and skip managed Kubernetes entirely:
1. **Develop and learn on `kind`** running locally in Docker. Free. This is
   where manifests, Helm charts, HPAs and the observability stack get built and
   broken repeatedly.
2. **Run the live demo on a single small VPS with k3s**, provisioned by
   Terraform through the `hcloud` provider. Roughly EUR 4/month, and it is a
   real, conformant Kubernetes cluster reachable over the internet.
3. **Learn Terraform against free providers first** — `docker`, `kubernetes`,
   `helm` and `github` — before pointing it at anything billable. These produce
   real state files, plans, drift and dependency graphs.
Postgres runs in-cluster on a persistent volume with scheduled logical backups
rather than a managed database. TLS comes from cert-manager and Let's Encrypt,
and DNS from Cloudflare, both free.
If managed Kubernetes is ever needed for its own sake, it will be a single
time-boxed session: `terraform apply`, capture evidence, `terraform destroy` the
same day, with a billing alarm configured first. That costs a few dollars rather
than a few hundred.
## Consequences
Positive: total project cost stays under about $20 for twelve weeks instead of
$150-250 per month. Cost discipline is itself a signal worth showing, since
uncontrolled cloud spend is a real and common engineering failure. Working on
`kind` also makes the feedback loop faster than any remote cluster, and forces
the manifests to stay portable rather than quietly depending on one vendor's
load balancer and storage behaviour.
Negative and honestly acknowledged: this does not produce direct hands-on
experience with EKS-specific machinery such as IRSA, the AWS Load Balancer
Controller, managed node groups or Fargate profiles. Some job descriptions name
these explicitly. Single-node k3s also cannot demonstrate multi-AZ topology,
real node failure or cluster autoscaling, so `PodDisruptionBudget` and
anti-affinity rules are written and reasoned about but not truly exercised.
The mitigation is to state this plainly rather than imply broader experience
than exists: the concepts are understood and demonstrated on conformant
Kubernetes, the managed-service specifics are a known and deliberate gap, and
the reason is documented cost control.
