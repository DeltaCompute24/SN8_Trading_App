provider "google" {
  project = var.project_id
  region  = var.region
}

# Add backend configuration
terraform {
  backend "gcs" {
    bucket = "delta-prop-shop-terraform-state"
    prefix = "terraform/state"
  }
}

module "iam" {
  source         = "./modules/iam"
  project_id     = var.project_id
  project_prefix = var.project_prefix
  environment    = var.environment
  region         = var.region
  env_secret_id  = module.secrets.secret_id
  repository_id  = module.registry.repository_id
}

module "networking" {
  source         = "./modules/networking"
  project_id     = var.project_id
  project_prefix = var.project_prefix
  region         = var.region
  subnet_cidr    = var.subnet_cidr
  connector_cidr = var.connector_cidr
}

module "registry" {
  source         = "./modules/registry"
  project_prefix = var.project_prefix
  region        = var.region

}

module "database" {
  source              = "./modules/database"
  project_id          = var.project_id
  project_prefix      = var.project_prefix
  region             = var.region
  vpc_id             = module.networking.vpc_id
  use_existing_redis = true
  existing_redis_name = "defi-redis"
  memory_size_gb     = 2
}

module "secrets" {
  source         = "./modules/secrets"
  project_prefix = var.project_prefix
  environment    = var.environment
}

module "services" {
  source                = "./modules/services"
  project_prefix        = var.project_prefix
  region               = var.region
  project_id           = var.project_id

  repository_name      = module.registry.repository_name
  
  vpc_connector_id     = module.networking.vpc_connector_id
  
  redis_host           = module.database.redis_host
  
  api_service_account  = module.iam.api_sa_email
  celery_service_account = module.iam.celery_sa_email
  
  env_secret_id        = module.secrets.secret_id
  
  # Add resource configurations
  api_cpu       = var.api_cpu
  api_memory    = var.api_memory
  worker_cpu    = var.worker_cpu
  worker_memory = var.worker_memory
  beat_cpu      = var.beat_cpu
  beat_memory   = var.beat_memory
}