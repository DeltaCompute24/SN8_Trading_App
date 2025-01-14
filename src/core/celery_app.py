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
        'src.tasks.monitor_processing_positions.processing_positions': {'queue': 'processing_positions'},
    },
    beat_schedule={
        'send_notifications-every-15-minutes': {
            'task': 'src.tasks.send_notification.send_notifications',
            'schedule': 900.0,  # every 15 minutes
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
            'schedule': 5.0,  # every 1 second
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
        'monitor_tournaments-minute': {
            'task': 'src.tasks.tournament_notifications.monitor_tournaments',
            'schedule': 60.0,  # Runs every 1 minute
        },
        'calculate_participants_score-minute': {
            'task': 'src.tasks.tournament_notifications.calculate_participants_score',
            'schedule': 60.0,  # Runs every 1 minute
        },
        'monitor_processing_positions-seconds': {
            'task': 'src.tasks.monitor_processing_positions.processing_positions',
            'schedule': 3.0,  # Runs every 3 seconds
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
import src.tasks.monitor_processing_positions
