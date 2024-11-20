from celery import Celery
from src.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery_app = Celery(
    'core.celery_app',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_routes={
        'src.tasks.send_notification.send_notifications': {'queue': 'send_notifications'},
        'src.tasks.position_monitor_sync.monitor_positions': {'queue': 'position_monitoring'},
        'src.tasks.listen_for_profit_loss.monitor_taoshi': {'queue': 'monitor_taoshi'},
        'src.tasks.monitor_challenges.monitor_challenges': {'queue': 'monitor_challenges'},
        'src.tasks.redis_listener.event_listener': {'queue': 'event_listener'},
    },
    beat_schedule={
        'manage_subscriptions-every-1-seconds': {
            'task': 'src.tasks.send_notification.send_notifications',
            'schedule': 1.0,  # every 1 seconds
        },
        'monitor_positions-every-5-seconds': {
            'task': 'src.tasks.position_monitor_sync.monitor_positions',
            'schedule': 5.0,  # every 1 second
        },
        'redis-listener-every-15-seconds': {
            'task': 'src.tasks.redis_listener.event_listener',
            'schedule': 15.0,  # every 20 second
        },
        'monitor_taoshi_every_1_second': {
            'task': 'src.tasks.listen_for_profit_loss.monitor_taoshi',
            'schedule': 1.0,  # every 3 second
        },
        'monitor_challenges_every_5_seconds': {
            'task': 'src.tasks.monitor_challenges.monitor_challenges',
            'schedule': 5.0,  # every 10 second
        },
    },
    timezone='UTC',
)

celery_app.autodiscover_tasks(['src.tasks'])

# Ensure tasks are loaded
import src.tasks.position_monitor_sync
import src.tasks.redis_listener
import src.tasks.listen_for_profit_loss
import src.tasks.monitor_challenges
import src.tasks.send_notification
