# Service Accounts
resource "google_service_account" "api_sa" {
  account_id   = "${var.project_prefix}-api"
  display_name = "FastAPI Service Account"
}

resource "google_service_account" "celery_sa" {
  account_id   = "${var.project_prefix}-celery"
  display_name = "Celery Service Account"
}

# API Service Account Permissions
resource "google_project_iam_member" "api_permissions" {
  for_each = toset([
    "roles/secretmanager.secretAccessor",    # Access secrets
    "roles/redis.viewer",                    # Redis access
    "roles/logging.logWriter",               # Write logs
    "roles/monitoring.metricWriter",         # Write metrics
    "roles/cloudtrace.agent",                # Cloud Trace
    "roles/artifactregistry.reader",         # Pull images
    "roles/vpcaccess.user"                   # VPC access
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}

# Celery Service Account Permissions
resource "google_project_iam_member" "celery_permissions" {
  for_each = toset([
    "roles/secretmanager.secretAccessor",    # Access secrets
    "roles/redis.viewer",                    # Redis access
    "roles/logging.logWriter",               # Write logs
    "roles/monitoring.metricWriter",         # Write metrics
    "roles/artifactregistry.reader",         # Pull images
    "roles/cloudtasks.enqueuer",             # Enqueue tasks
    "roles/vpcaccess.user"                   # VPC access
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.celery_sa.email}"
}

# Secret Manager
resource "google_secret_manager_secret_iam_member" "secret_access" {
  secret_id = var.env_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_sa.email}"
}

# Registry
resource "google_artifact_registry_repository_iam_member" "repo_access" {
  repository = var.repository_id
  location   = var.region
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.api_sa.email}"
}