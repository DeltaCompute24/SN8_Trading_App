variable "project_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
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

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "use_existing_vpc" {
  description = "Use Existing VPC"
  type        = bool
}

variable "existing_vpc_name" {
  description = "existing vpc name"
  type        = string
}