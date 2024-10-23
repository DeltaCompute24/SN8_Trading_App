# push-images.ps1

# Set your AWS account ID and region
$AWS_ACCOUNT_ID = "288792505174"
$AWS_REGION = "us-east-1"

# Authenticate Docker to ECR
$loginCommand = aws ecr get-login-password --region $AWS_REGION --profile defi-profile | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
Invoke-Expression -Command $loginCommand

# Tag and push images
$services = @("fastapi", "celery_worker", "celery_beat")

foreach ($service in $services) {
    $sourceImage = "sn8_trading_app-$service`:latest"
    $targetImage = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/defi-backend-$service`:latest"
    
    docker tag $sourceImage $targetImage
    docker push $targetImage
}

Write-Host "Images pushed to ECR successfully!"