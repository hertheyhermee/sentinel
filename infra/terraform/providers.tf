provider "docker" {}

provider "github" {
  owner = var.github_owner
  token = var.github_token
}

provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = var.kind_context
}

provider "helm" {
  kubernetes {
    config_path    = "~/.kube/config"
    config_context = var.kind_context
  }
}
