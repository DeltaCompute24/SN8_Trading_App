project_id = "delta-prop-shop"
region = "us-east1"
project_prefix = "defi"

# Existing resources
use_existing_vpc = true
existing_vpc_name = "defi-network"
use_existing_redis = true
existing_redis_name = "defi-redis"

# Redis config (matching existing)
redis_memory_size = 2  # Your existing Redis is 2GB
redis_host =  "10.139.40.3"