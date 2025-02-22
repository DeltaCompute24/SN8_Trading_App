# Fix the output syntax
output "redis_host" {
  value = var.use_existing_redis ? data.google_redis_instance.existing[0].host : google_redis_instance.cache.host
}