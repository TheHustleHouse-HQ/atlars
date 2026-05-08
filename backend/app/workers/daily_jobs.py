from app.workers.celery_app import celery_app


@celery_app.task(queue="daily")
def embed_entry(entry_id: str) -> None:
    # Phase 1 — placeholder
    pass


@celery_app.task(queue="daily")
def extract_traits(user_id: str) -> None:
    # Phase 2 — placeholder
    pass


@celery_app.task(queue="daily")
def extract_beliefs(user_id: str) -> None:
    # Phase 2 — placeholder
    pass


@celery_app.task(queue="daily")
def detect_contradictions(user_id: str) -> None:
    # Phase 2 — placeholder
    pass
