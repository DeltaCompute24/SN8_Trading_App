variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-east1"
}

variable "project_id" {     
  description = "GCP Project ID"
  type        = string
}

variable "environment" {     
  description = "Environment name (dev/prod)"
  type        = string
  default     = "prod"
}


variable "project_prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "defi"
}

variable "subnet_cidr" {
  description = "CIDR range for subnet"
  type        = string
  default     = "10.0.0.0/16"
}

variable "connector_cidr" {
  description = "CIDR range for VPC connector"
  type        = string
  default     = "10.8.0.0/28"
}

variable "redis_memory_size" {
  description = "Redis memory size in GB"
  type        = number
  default     = 4
}

variable "redis_host" {
  description = "Redis host address"
  type        = string
  default     = "10.139.40.3"  # Your existing Redis host
}

variable "api_cpu" {
  default = "4000m"
  type        = string
}
variable "api_memory" {
  default = "8Gi"
  type        = string
}
variable "worker_cpu" {
  default = "4000m"
   type        = string
}
variable "worker_memory" {
  default = "8Gi"
   type        = string
}
variable "beat_cpu" {
  default = "1000m"
   type        = string
}
variable "beat_memory" {
  default = "2Gi"
   type        = string
}

variable "existing_redis_name" {
  description = "Name of existing Redis"
  type        = string
  default     = ""
}
variable "use_existing_redis" {
  description = "Whether to use existing Redis"
  type        = bool
  default     = false
}

variable "use_existing_vpc" {
  description = "Whether to use existing VPC"
  type        = bool
  default     = true
}

variable "existing_vpc_name" {
  description = "Name of existing VPC"
  type        = string
  default     = ""
}