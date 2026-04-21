from celery import Celery

from app.core.config import settings

celery_app = Celery("software_distribution", broker=settings.redis_url, backend=settings.redis_url)


@celery_app.task
def send_email(to: str, template_key: str, context: dict) -> dict:
    return {"to": to, "template_key": template_key, "queued": True, "context": context}


@celery_app.task
def generate_invoice(order_id: str) -> dict:
    return {"order_id": order_id, "generated": True}


@celery_app.task
def send_expiry_reminders() -> dict:
    return {"processed": True}
