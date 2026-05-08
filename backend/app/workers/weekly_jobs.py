from app.workers.celery_app import celery_app


@celery_app.task(queue="weekly")
def update_domain_scores(user_id: str) -> None:
    # Phase 3 — placeholder
    pass


@celery_app.task(queue="weekly")
def cluster_analysis(user_id: str) -> None:
    # Phase 3 — placeholder
    pass
