import logging

from discordwebhook import Discord

from src.config import WEBHOOK_URL
from src.core.celery_app import celery_app
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import get_queue_data, pop_queue_right_item

logger = logging.getLogger(__name__)

import re

import yaml


def get_available_tasks():
    with open('docker-compose.yml', 'r') as file:
        prime_service = yaml.safe_load(file)

    input_string = prime_service["services"]["celery_worker"]["command"]
    matches = re.findall(r'-n\s+(\S+)', input_string)
    return [f"celery@{match}" for match in matches]


def notification_to_discord(content, username="Notification for Celery Task Errors"):
    discord = Discord(url=WEBHOOK_URL)
    discord.post(content=content, username=username)


@celery_app.task(name='src.tasks.send_notification.send_notifications')
def send_notifications():
    error_data = get_queue_data(queue_name=ERROR_QUEUE_NAME)
    length = len(error_data)
    error_data = list(set(error_data))

    try:
        available_tasks = get_available_tasks()
        print(available_tasks)
        i = celery_app.control.inspect()
        availability = i.ping()
        message = ""
        for task in available_tasks:
            if task not in availability or availability[task] != {'ok': 'pong'}:
                message += f"{task} is not active\n"

        if message:
            notification_to_discord(content=message, username="Celery Task Worker Not Active")

        if length == 0:
            return

        for content in error_data:
            notification_to_discord(content=content)

        pop_queue_right_item(queue_name=ERROR_QUEUE_NAME, count=length)
    except Exception as e:
        pass
