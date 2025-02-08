# FastAPI Service
resource "google_cloud_run_service" "fastapi" {
  name     = "${var.project_prefix}-api"
  location = var.region

  template {
    spec {
      # Add service account
      service_account_name = var.api_service_account

      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_name}/fastapi:latest"
        
        # Container resources
        resources {
          limits = {
            cpu    = var.api_cpu
            memory = var.api_memory
          }
        }

        # Environment variables
        env {
          name  = "REDIS_URL"
          value = "redis://${var.redis_host}:6379"
        }

        # Application secrets from Secret Manager
       
        env {
          name = "ENV_SECRET"
          value_from {
            secret_key_ref {
              name = var.env_secret_id
              key  = "latest"
            }
          }
        }

        # Port configuration
        ports {
          container_port = 80
        }

        # Command and args can be set here
        command = ["uvicorn"]
        args    = ["src.main:app", "--host", "0.0.0.0", "--port", "80"]
      }
    }

    metadata {
      annotations = {
        # VPC connector for Redis access
        "run.googleapis.com/vpc-access-connector" = var.vpc_connector_id
        "run.googleapis.com/vpc-access-egress"    = "all-traffic"
        "autoscaling.knative.dev/maxScale"       = "2"
      }
    }
  }
}

# Celery Workers Service
resource "google_cloud_run_service" "celery_workers" {
  name     = "${var.project_prefix}-workers"
  location = var.region

  template {
    spec {
      # Add service account
      service_account_name = var.celery_service_account

      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_name}/celery_worker:latest"
        
        resources {
          limits = {
            cpu    = var.worker_cpu
            memory = var.worker_memory
          }
        }

        env {
          name  = "REDIS_URL"
          value = "redis://${var.redis_host}:6379"
        }

         
        
        env {
          name = "ENV_SECRET"
          value_from {
            secret_key_ref {
              name = var.env_secret_id
              key  = "latest"
            }
          }
        }

        # Celery worker command
        command = ["/bin/bash"]
        args = [
          "-c",
          <<-EOT
          celery -A src.core.celery_app worker -n monitor_position_worker --concurrency=1 --loglevel=info -Q position_monitoring & \
          celery -A src.core.celery_app worker -n mainnet_challenges_worker --concurrency=1 --loglevel=info -Q monitor_mainnet_challenges & \
          celery -A src.core.celery_app worker -n monitor_mainnet_worker --concurrency=1 --loglevel=info -Q monitor_miner & \
          celery -A src.core.celery_app worker -n monitor_testnet_worker --concurrency=1 --loglevel=info -Q testnet_validator & \
          celery -A src.core.celery_app worker -n processing_positions_worker --concurrency=1 --loglevel=info -Q processing_positions & \
          wait -n
          EOT
        ]
      }
    }

    metadata {
      annotations = {
        "run.googleapis.com/vpc-access-connector" = var.vpc_connector_id
        "run.googleapis.com/vpc-access-egress"    = "all-traffic"
        "autoscaling.knative.dev/maxScale"       = "2"
      }
    }
  }
}

# Celery Beat Service (Single Instance)
resource "google_cloud_run_service" "celery_beat" {
  name     = "${var.project_prefix}-beat"
  location = var.region

  template {
    spec {
      # Add service account
      service_account_name = var.celery_service_account


      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_name}/celery_beat:latest"
        
        resources {
          limits = {
            cpu    = var.beat_cpu
            memory = var.beat_memory
          }
        }

        env {
          name  = "REDIS_URL"
          value = "redis://${var.redis_host}:6379"
        }

       
        env {
          name = "ENV_SECRET"
          value_from {
            secret_key_ref {
              name = var.env_secret_id
              key  = "latest"
            }
          }
        }

        # Celery beat command
        command = ["celery"]
        args    = ["-A", "src.core.celery_app", "beat", "--loglevel=info"]
      }
    }

    metadata {
      annotations = {
        "run.googleapis.com/vpc-access-connector" = var.vpc_connector_id
        "run.googleapis.com/vpc-access-egress"    = "all-traffic"
        # Ensure only one instance
        "autoscaling.knative.dev/maxScale"       = "1"
      }
    }
  }
}