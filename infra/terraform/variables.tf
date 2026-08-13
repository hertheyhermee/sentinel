variable "github_owner" {
  description = "GitHub owner name used for repo automation and branch protection configuration."
  type        = string
  default     = "hertheyhermee"
}

variable "github_token" {
  description = "GitHub token used by the GitHub provider. For local work this is typically provided via a GITHUB_TOKEN environment variable."
  type        = string
  default     = ""
  sensitive   = true
}

variable "kind_cluster_name" {
  description = "Name of the local kind cluster used for Terraform-driven local k8s work."
  type        = string
  default     = "sentinel-kind"
}

variable "kind_context" {
  description = "Kubernetes context name for the local kind cluster."
  type        = string
  default     = "kind-sentinel-kind"
}

variable "namespace" {
  description = "Primary namespace for the app environment managed by Terraform."
  type        = string
  default     = "sentinel"
}
