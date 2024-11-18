#!/bin/bash

# Set your AWS account ID and region
AWS_ACCOUNT_ID="288792505174"
AWS_REGION="us-east-1"

# Authenticate Docker to ECR
aws ecr get-login-password --region $AWS_REGION --profile defi-profile | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
# Tag and push images


for service in fastapi celery_worker celery_beat
do
    docker tag sn8_trading_app-$service:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/defi-backend-$service:latest
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/defi-backend-$service:latest
done

echo "Images pushed to ECR successfully!"

