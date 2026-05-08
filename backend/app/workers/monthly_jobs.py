from app.workers.celery_app import celery_app


@celery_app.task(queue="monthly")
def generate_snapshot(user_id: str) -> None:
    # Phase 3 — placeholder
    pass


@celery_app.task(queue="monthly")
def generate_compression_candidates(user_id: str) -> None:
    # Phase 4 — placeholder
    pass


@celery_app.task(queue="monthly")
def full_synthesis(user_id: str) -> None:
    # Phase 4 — placeholder
    pass
