from celery import Celery
from app.core.config import settings

def create_celery_app() -> Celery:
    celery_app = Celery(
        "logy_desk_backend",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=["app.tasks.document_tasks"],  # Celery 태스크 파일 경로
    )
    celery_app.conf.update(task_track_started=True)
    return celery_app

celery_app = create_celery_app()
