#!/bin/bash

# Start all workers
celery -A src.core.celery_app worker -n position_worker --loglevel=info -Q position_monitoring &
celery -A src.core.celery_app worker -n taoshi_worker --loglevel=info -Q monitor_taoshi &
celery -A src.core.celery_app worker -n challenges_worker --loglevel=info -Q monitor_challenges &
celery -A src.core.celery_app worker -n redis_worker --loglevel=info -Q event_listener &
celery -A src.core.celery_app worker -n notification_worker --loglevel=info -Q send_notifications &

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?