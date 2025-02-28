
output "vpc_id" {
  value = module.networking.vpc_id
}

output "subnet_id" {
  value = module.networking.subnet_id
}

output "vpc_connector_id" {
  value = module.networking.vpc_connector_id
}

# Add useful outputs
output "api_url" {
  value = module.services.api_url
}

output "redis_host" {
  value = module.database.redis_host
}