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
CMD ["celery", "-A", "src.core.celery_app", "beat", "--loglevel=info"]