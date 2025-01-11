# Use an official Python runtime as the base image
FROM python:3.9-slim

WORKDIR /app

# Copy the requirements file into the container
COPY . /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libgirepository1.0-dev \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    gir1.2-gtk-3.0 \
    libglib2.0-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run celery workers directly using shell form of CMD
CMD bash -c "\
    celery -A src.core.celery_app worker -n monitor_position_worker --concurrency=1 --loglevel=info -Q position_monitoring & \
    celery -A src.core.celery_app worker -n redis_worker --concurrency=1 --loglevel=info -Q event_listener & \
    celery -A src.core.celery_app worker -n notification_worker --concurrency=1 --loglevel=info -Q send_notifications & \
    celery -A src.core.celery_app worker -n mainnet_challenges_worker --concurrency=1 --loglevel=info -Q monitor_mainnet_challenges & \
    celery -A src.core.celery_app worker -n monitor_mainnet_worker --concurrency=1 --loglevel=info -Q monitor_miner & \
    celery -A src.core.celery_app worker -n monitor_testnet_worker --concurrency=1 --loglevel=info -Q testnet_validator & \
    celery -A src.core.celery_app worker -n tournament_notifications_worker --concurrency=1 --loglevel=info -Q tournament_notifications & \
    celery -A src.core.celery_app worker -n processing_positions_worker --concurrency=1 --loglevel=info -Q processing_positions & \
    wait -n"

