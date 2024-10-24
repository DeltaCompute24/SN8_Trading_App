from celery import Celery
from src.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery_app = Celery(
    'core.celery_app',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_routes={
        # 'src.tasks.subscription_manager.manage_subscriptions': {'queue': 'subscription_management'},
        'src.tasks.position_monitor_sync.monitor_positions': {'queue': 'position_monitoring'},
        'src.tasks.listen_for_profit_loss.monitor_taoshi': {'queue': 'monitor_taoshi'},
        'src.tasks.monitor_challenges.monitor_challenges': {'queue': 'monitor_challenges'},
        'src.tasks.redis_listener.event_listener': {'queue': 'event_listener'},
    },
    beat_schedule={
        # 'manage_subscriptions-every-10-seconds': {
        #     'task': 'src.tasks.subscription_manager.manage_subscriptions',
        #     'schedule': 10.0,  # every 10 seconds
        # },
        'monitor_positions-every-1-second': {
            'task': 'src.tasks.position_monitor_sync.monitor_positions',
            'schedule': 10.0,  # every 1 second
        },
        'redis-listener-every-15-seconds': {
            'task': 'src.tasks.redis_listener.event_listener',
            'schedule': 20.0,  # every 20 second
        },
        'monitor_taoshi_every_3_seconds': {
            'task': 'src.tasks.listen_for_profit_loss.monitor_taoshi',
            'schedule': 3.0,  # every 3 second
        },
        'monitor_challenges_every_10_seconds': {
            'task': 'src.tasks.monitor_challenges.monitor_challenges',
            'schedule': 10.0,  # every 10 second
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
