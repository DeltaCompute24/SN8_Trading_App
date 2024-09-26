#!/bin/bash
export FLOWER_UNAUTHENTICATED_API=true
celery -A src.core.celery_app flower --port=5555