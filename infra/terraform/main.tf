locals {
  app_name = "sentinel"
  labels = {
    app         = local.app_name
    environment = "dev"
    managed_by  = "terraform"
  }
}

resource "docker_network" "sentinel_dev" {
  name = "sentinel-dev"
}

output "docker_network_name" {
  description = "Name of the local Docker network used by the dev stack."
  value       = docker_network.sentinel_dev.name
}

output "kind_cluster_name" {
  description = "Name of the local kind cluster used for local Kubernetes validation."
  value       = var.kind_cluster_name
}
