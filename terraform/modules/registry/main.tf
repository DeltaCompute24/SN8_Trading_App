resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "${var.project_prefix}-repo"
  format        = "DOCKER"
  description   = "Docker repository for ${var.project_prefix}"
}