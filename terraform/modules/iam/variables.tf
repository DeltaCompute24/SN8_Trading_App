variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "project_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment (dev/prod)"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

variable "env_secret_id" {
  description = "Secret Manager secret ID"
  type        = string
}

variable "repository_id" {
  description = "Artifact Registry repository ID"
  type        = string
}
