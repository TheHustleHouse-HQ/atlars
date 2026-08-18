from celery import Celery
from celery.signals import setup_logging
from app.core.config import settings
from app.core.logger import setup_logger

@setup_logging.connect
def config_loggers(*args, **kwargs):
    setup_logger()

celery_app = Celery(
    "atlars",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.daily_jobs",
        "app.workers.weekly_jobs",
        "app.workers.monthly_jobs",
        "app.workers.voice_jobs",
    ],
)

celery_app.conf.task_queues = {
    "voice": {},
    "daily": {},
    "weekly": {},
    "monthly": {},
}

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "update-maturity-stages-daily": {
        "task": "update_user_maturity_stages",
        "schedule": crontab(hour="0", minute="0"), # Runs daily at midnight UTC
    }
}

celery_app.conf.timezone = "UTC"
