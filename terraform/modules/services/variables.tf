# Required Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "project_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

# Service Dependencies
variable "repository_name" {
  description = "Artifact Registry repository name"
  type        = string
}

variable "vpc_connector_id" {
  description = "VPC Access Connector ID"
  type        = string
}

variable "redis_host" {
  description = "Redis instance host"
  type        = string
}

# Service Accounts
variable "api_service_account" {
  description = "Service account email for API service"
  type        = string
}

variable "celery_service_account" {
  description = "Service account email for Celery services"
  type        = string
}

# Secrets
variable "env_secret_id" {
  description = "Secret Manager secret ID for environment variables"
  type        = string
}

# Resource Configurations
variable "api_cpu" {
  description = "CPU allocation for API service"
  type        = string
  default     = "1000m"
}

variable "api_memory" {
  description = "Memory allocation for API service"
  type        = string
  default     = "2Gi"
}

variable "worker_cpu" {
  description = "CPU allocation for Celery workers"
  type        = string
  default     = "1000m"
}

variable "worker_memory" {
  description = "Memory allocation for Celery workers"
  type        = string
  default     = "2Gi"
}

variable "beat_cpu" {
  description = "CPU allocation for Celery beat"
  type        = string
  default     = "500m"
}

variable "beat_memory" {
  description = "Memory allocation for Celery beat"
  type        = string
  default     = "1Gi"
}