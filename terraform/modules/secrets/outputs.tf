output "secret_id" {
  value = google_secret_manager_secret.container_env.id
  description = "The ID of the secret in Secret Manager"
}

output "secret_name" {
  value = google_secret_manager_secret.container_env.name
  description = "The full name of the secret in Secret Manager"
}