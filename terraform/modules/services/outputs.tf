output "api_url" {
  description = "URL of the FastAPI service"
  value       = google_cloud_run_service.fastapi.status[0].url
}

output "api_service_name" {
  description = "Name of the FastAPI service"
  value       = google_cloud_run_service.fastapi.name
}

output "workers_service_name" {
  description = "Name of the Celery workers service"
  value       = google_cloud_run_service.celery_workers.name
}

output "beat_service_name" {
  description = "Name of the Celery beat service"
  value       = google_cloud_run_service.celery_beat.name
}

output "latest_api_revision" {
  description = "Latest revision of the API service"
  value       = google_cloud_run_service.fastapi.status[0].latest_created_revision_name
}