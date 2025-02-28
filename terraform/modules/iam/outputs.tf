output "api_sa_email" {
  value = google_service_account.api_sa.email
}

output "celery_sa_email" {
  value = google_service_account.celery_sa.email
}