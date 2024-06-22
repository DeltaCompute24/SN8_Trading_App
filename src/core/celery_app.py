from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    'core.celery_app',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

celery_app.conf.update(
    task_routes={
        'src.tasks.subscription_manager.manage_subscriptions': {'queue': 'subscription_management'},
        'src.tasks.subscription_manager.trade_pair_worker': {'queue': 'trade_pair_workers'},
        'src.tasks.position_monitor.monitor_positions': {'queue': 'position_monitoring'},
    },
    beat_schedule={
        'manage_subscriptions-every-10-seconds': {
            'task': 'src.tasks.subscription_manager.manage_subscriptions',
            'schedule': 10.0,  # every 10 seconds
        },
        'monitor_positions-every-1-second': {
            'task': 'src.tasks.position_monitor.monitor_positions',
            'schedule': 1.0,  # every 1 second
        },
    },
    timezone='UTC',
)

celery_app.autodiscover_tasks(['src.tasks'])

# Ensure tasks are loaded
import src.tasks.subscription_manager
import src.tasks.position_monitor
