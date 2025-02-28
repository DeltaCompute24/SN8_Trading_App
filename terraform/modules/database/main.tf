# Use data source for existing Redis
data "google_redis_instance" "existing" {
  count = var.use_existing_redis ? 1 : 0
  name  = var.existing_redis_name
  region = var.region
  project = var.project_id
}

# Create new Redis only if not using existing
resource "google_redis_instance" "cache" {
  name           = var.use_existing_redis ? var.existing_redis_name : "${var.project_prefix}-redis"
  tier           = "BASIC"
  memory_size_gb = var.memory_size_gb
  region         = var.region
  project        = var.project_id

  authorized_network = var.vpc_id
  connect_mode      = "PRIVATE_SERVICE_ACCESS"

  redis_version = "REDIS_6_X"
  display_name  = "${var.project_prefix} Redis Instance"
}

# Fix the output syntax
output "redis_host" {
  value = var.use_existing_redis ? data.google_redis_instance.existing[0].host : google_redis_instance.cache.host
}