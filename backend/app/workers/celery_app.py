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
        # Block A V2.0
        "app.workers.tasks.ai_generation",
        "app.workers.tasks.crawled_match",
        # Block D V2.0 — channel autoposting (D4)
        "app.workers.tasks.autopost",
        # Block D V2.0 — periodic maintenance (D2 pruning)
        "app.workers.tasks.maintenance",
        # Block D V2.0 (FU5) — bot search-query telemetry
        "app.workers.tasks.telemetry",
        # Phase-2 — duplicate-account suspicion signals (daily 02:30)
        "app.workers.tasks.suspicions",
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
    # Reconcile the Meilisearch index from Postgres every 15 minutes.
    # Per-write hooks keep the index current in steady state; this job is
    # the bootstrap + backfill safety net (a full upsert), so 15 min keeps
    # load modest while still self-healing a fresh or drifted index.
    "sync-meilisearch": {
        "task": "app.workers.tasks.listings.sync_to_meilisearch",
        "schedule": crontab(minute="*/15"),
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
    # Block A V2.0 — A4: expire 7-day-old crawled-match notifications.
    # ``expire-stale-crawled-matches`` (03:00) is the canonical entry —
    # set ``read=True`` on any CRAWLED_MATCH row older than 7 days that
    # the seller never acted on, so the bot stops re-surfacing them in
    # /found pulls. Runs at 03:00 to avoid contention with the 04:xx
    # maintenance band. The legacy ``expire-crawled-match-notifications``
    # entry is kept for the ``expires_at``-based path (idempotent).
    "expire-stale-crawled-matches": {
        "task": "app.workers.tasks.crawled_match.expire_stale_crawled_matches",
        "schedule": crontab(minute=0, hour=3),  # daily 03:00
    },
    "expire-crawled-match-notifications": {
        "task": "app.workers.tasks.crawled_match.expire_old_notifications",
        "schedule": crontab(minute=0, hour=4),  # daily 04:00
    },
    # Block D D2 — prune behavioral_signals rows older than 180 days.
    # Runs nightly at 04:30 so it doesn't contend with the 04:00 job.
    "prune-behavioral-signals": {
        "task": "app.workers.tasks.maintenance.prune_behavioral_signals",
        "schedule": crontab(minute=30, hour=4),
    },
    # Block F F1 — purge DRAFT listings older than F1_DRAFT_LIFETIME_DAYS.
    # Runs daily 05:00 so it doesn't contend with the 04:30 prune job.
    "purge-abandoned-drafts": {
        "task": "app.workers.tasks.maintenance.purge_abandoned_drafts",
        "schedule": crontab(minute=0, hour=5),
    },
    # Block F F5b — 90-day retention on ai_generations audit log.
    # Daily 04:45, between the D2 (04:30) and F1 (05:00) jobs.
    "prune-ai-generations": {
        "task": "app.workers.tasks.maintenance.prune_ai_generations",
        "schedule": crontab(minute=45, hour=4),
    },
    # Block D FU5 — 90-day retention on the bot_search_queries telemetry.
    # Daily 04:50, in the gap between prune-ai-generations (04:45) and
    # purge-abandoned-drafts (05:00).
    "prune-bot-search-queries": {
        "task": "app.workers.tasks.maintenance.prune_bot_search_queries",
        "schedule": crontab(minute=50, hour=4),
    },
    # Block F F5b — hourly evaluation of bad-feedback rate / p95 duration /
    # daily cost. Emits exactly one Telegram alert per healthy→tripped
    # transition via Redis flag (no all-clear spam).
    "check-quality-thresholds": {
        "task": "app.workers.tasks.maintenance.check_quality_thresholds",
        "schedule": crontab(minute=15),
    },
    # Block F F3c — sitemap warm-up every 15 min so Googlebot/Yandexbot
    # always sees a fresh ``<lastmod>``. The SEO router serves
    # ``Cache-Control: public, max-age=900`` so once per cache window
    # is the right cadence.
    "rebuild-sitemap-caches": {
        "task": "app.workers.tasks.maintenance.rebuild_sitemap_caches",
        "schedule": crontab(minute="*/15"),
    },
    # Phase-2 — duplicate-account detection signals. Daily at 02:30,
    # well before the 03:00 / 04:xx maintenance band so the queue is
    # fresh when admins check /admin/suspicions first thing in the
    # morning. Idempotent: an open suspicion for the same
    # (primary_user_id, signal_kind) is skipped on re-runs.
    "run-suspicion-signals": {
        "task": "app.workers.tasks.suspicions.run_suspicion_signals",
        "schedule": crontab(minute=30, hour=2),
    },
}
