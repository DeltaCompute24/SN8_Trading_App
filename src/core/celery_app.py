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
        'src.tasks.redis_listener.event_listener': {'queue': 'event_listener'},
        'src.tasks.monitor_mainnet_challenges.monitor_mainnet_challenges': {'queue': 'monitor_mainnet_challenges'},
        'src.tasks.monitor_miner_positions.monitor_miner': {'queue': 'monitor_miner'},
        'src.tasks.testnet_validator.testnet_validator': {'queue': 'testnet_validator'},
        'src.tasks.tournament_notifications.*': {'queue': 'tournament_notifications'},
    },
    beat_schedule={
        'send_notifications-every-1-second': {
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
        'monitor_mainnet_challenges_every_1_second': {
            'task': 'src.tasks.monitor_mainnet_challenges.monitor_mainnet_challenges',
            'schedule': 2.0,  # every 1 second
        },
        'monitor_miner_every_1_second': {
            'task': 'src.tasks.monitor_miner_positions.monitor_miner',
            'schedule': 2.0,  # every 1 second
        },
        'testnet_validator_every_1_second': {
            'task': 'src.tasks.testnet_validator.testnet_validator',
            'schedule': 2.0,  # every 1 second
        },
        'send_discord_reminder-daily': {
            'task': 'src.tasks.tournament_notifications.send_discord_reminder',
            'schedule': 21600.0,  # Runs every 6 hour
        },
        'send_tournament_start_email-minute': {
            'task': 'src.tasks.tournament_notifications.send_tournament_start_email',
            'schedule': 60.0,  # Runs every 1 minute
        },
        'send_tournament_results-minute': {
            'task': 'src.tasks.tournament_notifications.send_tournament_results',
            'schedule': 60.0,  # Runs every 1 minute
        },
    },
    timezone='UTC',
)

celery_app.autodiscover_tasks(['src.tasks'])

# Ensure tasks are loaded
import src.tasks.position_monitor_sync
import src.tasks.redis_listener
import src.tasks.monitor_miner_positions
import src.tasks.monitor_mainnet_challenges
import src.tasks.send_notification
import src.tasks.testnet_validator
import src.tasks.tournament_notifications
