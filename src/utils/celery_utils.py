from celery import Celery

from src.config import CELERY_RESULT_BACKEND, CELERY_BROKER_URL


def make_celery(app_name=__name__):
    backend = CELERY_RESULT_BACKEND
    broker = CELERY_BROKER_URL
    return Celery(app_name, backend=backend, broker=broker)
