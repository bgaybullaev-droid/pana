"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "realestate",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.notifications",
        "app.workers.tasks.listings",
        "app.workers.tasks.parser",
        "app.workers.tasks.translation",
        "app.workers.tasks.uploads_gc",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tashkent",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,  # 1 hour
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Check for expired listings every hour
    "check-expired-listings": {
        "task": "app.workers.tasks.listings.check_expired_listings",
        "schedule": crontab(minute=0),  # Every hour
    },
    # Update exchange rates every 6 hours
    "update-exchange-rates": {
        "task": "app.workers.tasks.listings.update_exchange_rates",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    # Clean up old notifications weekly
    "cleanup-old-notifications": {
        "task": "app.workers.tasks.notifications.cleanup_old_notifications",
        "schedule": crontab(minute=0, hour=3, day_of_week=0),  # Sunday 3am
    },
    # Sync listings to Meilisearch every 5 minutes
    "sync-meilisearch": {
        "task": "app.workers.tasks.listings.sync_to_meilisearch",
        "schedule": crontab(minute="*/5"),
    },
    # Translate pending listings every 5 minutes
    "translate-pending-listings": {
        "task": "app.workers.tasks.translation.translate_pending_listings",
        "schedule": crontab(minute="*/5"),
    },
    # PR-H — orphaned upload GC: daily at 03:30 (after notification
    # cleanup on Sundays, separate time-of-day to avoid contention).
    # Safe to run more often; daily is enough for the current volume.
    "cleanup-orphan-uploads": {
        "task": "app.workers.tasks.uploads_gc.cleanup_orphan_uploads",
        "schedule": crontab(minute="30", hour="3"),
    },
}
