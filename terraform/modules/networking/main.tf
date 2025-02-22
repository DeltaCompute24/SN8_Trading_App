# Data source for existing VPC
data "google_compute_network" "vpc" {
  count   = var.use_existing_vpc ? 1 : 0
  name    = var.existing_vpc_name
  project = var.project_id
}


locals {
  # Use existing VPC if specified, otherwise use the new one
  vpc_id =  data.google_compute_network.vpc[0].id
}

# Subnet
resource "google_compute_subnetwork" "subnet" {
  name          = "${var.project_prefix}-subnet"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = local.vpc_id
}

# VPC Connector
resource "google_vpc_access_connector" "connector" {
  name          = "${var.project_prefix}-vpc-connector"
  region        = var.region
  ip_cidr_range = var.connector_cidr
  network       = local.vpc_id
}

# VPC Connector Firewall
resource "google_compute_firewall" "connector_firewall" {
  name    = "aet-useast1-defi--vpc--connector-hcfw"
  network = local.vpc_id
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = ["667"]
  }

  allow {
    protocol = "udp"
    ports    = ["665-666"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = ["107.178.230.64/26", "35.199.224.0/19"]
  target_tags   = ["vpc-connector"]

  direction = "INGRESS"
}

# Firewall Rules

# 1. Allow internal communication between services
resource "google_compute_firewall" "internal" {
  name    = "${var.project_prefix}-allow-internal"
  network = local.vpc_id

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }
  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }
  allow {
    protocol = "icmp"
  }

  source_ranges = [var.subnet_cidr]
  
  description = "Allow internal communication between services"
}

# 2. Allow external HTTP/HTTPS traffic
resource "google_compute_firewall" "external" {
  name    = "${var.project_prefix}-allow-external"
  network = local.vpc_id

  allow {
    protocol = "tcp"
    ports    = ["80", "443", "5002"]
  }

  source_ranges = ["0.0.0.0/0"]
  
  description = "Allow inbound HTTP/HTTPS traffic"
}

# 3. Allow SSH access
resource "google_compute_firewall" "ssh" {
  name    = "${var.project_prefix}-allow-ssh"
  network = local.vpc_id

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  
  description = "Allow SSH access"
}