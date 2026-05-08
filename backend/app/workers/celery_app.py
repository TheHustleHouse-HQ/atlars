from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "atlars",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.daily_jobs",
        "app.workers.weekly_jobs",
        "app.workers.monthly_jobs",
    ],
)

celery_app.conf.task_queues = {
    "daily": {},
    "weekly": {},
    "monthly": {},
}

celery_app.conf.beat_schedule = {
    # Placeholders — tasks will be added in Phase 1+
}

celery_app.conf.timezone = "UTC"
