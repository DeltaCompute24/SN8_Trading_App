# Create secret for container environment variables
resource "google_secret_manager_secret" "container_env" {
  secret_id = "${var.project_prefix}-container-secrets"
  
  replication {
    auto {}
  }
}

# Version of the secret containing all env vars
resource "google_secret_manager_secret_version" "container_env_version" {
  secret = google_secret_manager_secret.container_env.id
  
  # Reference a local encrypted file or use data source
  secret_data = file("${path.module}/secrets/${var.environment}.env")
}