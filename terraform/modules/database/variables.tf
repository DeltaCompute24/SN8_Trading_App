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

variable "vpc_id" {
  description = "VPC Network ID"
  type        = string
}

variable "use_existing_redis" {
  description = "Whether to use existing Redis"
  type        = bool
  default     = true
}

variable "existing_redis_name" {
  description = "Name of existing Redis"
  type        = string
  default     = "defi-redis"
}

variable "memory_size_gb" {
  description = "Redis memory size in GB"
  type        = number
  default     = 2
}