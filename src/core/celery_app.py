from celery import Celery
from celery.schedules import crontab
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

def create_celery_app() -> Celery:
    """Create and configure Celery application"""
    
    celery_app = Celery(
        "deepseaguard",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=[
            "core.tasks.compliance_tasks",
            "core.tasks.geofencing_tasks", 
            "core.tasks.notification_tasks",
            "core.tasks.cleanup_tasks"
        ]
    )
    
    # Celery configuration
    celery_app.conf.update(
        task_serializer=settings.CELERY_TASK_SERIALIZER,
        result_serializer=settings.CELERY_RESULT_SERIALIZER,
        accept_content=settings.CELERY_ACCEPT_CONTENT,
        timezone=settings.CELERY_TIMEZONE,
        enable_utc=settings.CELERY_ENABLE_UTC,
        task_track_started=settings.CELERY_TASK_TRACK_STARTED,
        task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
        task_soft_time_limit=settings.CELERY_TASK_TIME_LIMIT - 60,  # 1 minute less
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        worker_max_tasks_per_child=1000,
        worker_max_memory_per_child=200000,  # 200MB
        result_expires=3600,  # 1 hour
        result_persistent=True,
        task_ignore_result=False,
        task_store_errors_even_if_ignored=True,
        task_always_eager=False,  # Set to True for testing
        task_eager_propagates=True,
        worker_disable_rate_limits=False,
        worker_send_task_events=True,
        task_send_sent_event=True,
        event_queue_expires=60,
        worker_state_db=None,
        worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
        worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s",
    )
    
    # Periodic tasks (beat schedule)
    celery_app.conf.beat_schedule = {
        'check-compliance-violations': {
            'task': 'core.tasks.compliance_tasks.check_all_auv_compliance',
            'schedule': settings.VIOLATION_CHECK_INTERVAL,
            'args': (),
        },
        'cleanup-old-events': {
            'task': 'core.tasks.cleanup_tasks.cleanup_old_compliance_events',
            'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
            'args': (),
        },
        'generate-daily-reports': {
            'task': 'core.tasks.compliance_tasks.generate_daily_compliance_report',
            'schedule': crontab(hour=6, minute=0),  # Daily at 6 AM
            'args': (),
        },
        'update-zone-statistics': {
            'task': 'core.tasks.geofencing_tasks.update_zone_statistics',
            'schedule': 300,  # Every 5 minutes
            'args': (),
        },
        'health-check': {
            'task': 'core.tasks.cleanup_tasks.system_health_check',
            'schedule': 60,  # Every minute
            'args': (),
        },
    }
    
    # Task routing
    celery_app.conf.task_routes = {
        'core.tasks.compliance_tasks.*': {'queue': 'compliance'},
        'core.tasks.geofencing_tasks.*': {'queue': 'geofencing'},
        'core.tasks.notification_tasks.*': {'queue': 'notifications'},
        'core.tasks.cleanup_tasks.*': {'queue': 'cleanup'},
    }
    
    # Queue configuration
    celery_app.conf.task_default_queue = 'default'
    celery_app.conf.task_default_exchange = 'default'
    celery_app.conf.task_default_routing_key = 'default'
    
    # Error handling
    celery_app.conf.task_reject_on_worker_lost = True
    celery_app.conf.task_acks_late = True
    celery_app.conf.worker_prefetch_multiplier = 1
    
    # Monitoring
    celery_app.conf.worker_send_task_events = True
    celery_app.conf.task_send_sent_event = True
    
    logger.info("Celery application configured successfully")
    return celery_app

# Create the Celery app instance
celery_app = create_celery_app()

# Task error handling
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    logger.info(f"Request: {self.request!r}")

# Task success/failure callbacks
@celery_app.task(bind=True)
def task_success_callback(self, result):
    """Callback for successful task completion"""
    logger.info(f"Task {self.request.id} completed successfully: {result}")

@celery_app.task(bind=True)
def task_failure_callback(self, exc, task_id, args, kwargs, einfo):
    """Callback for failed task"""
    logger.error(f"Task {task_id} failed: {exc}")
    logger.error(f"Args: {args}, Kwargs: {kwargs}")
    logger.error(f"Exception info: {einfo}")

# Task monitoring
@celery_app.task(bind=True)
def monitor_task_progress(self, current, total, description=""):
    """Update task progress"""
    progress = (current / total) * 100 if total > 0 else 0
    self.update_state(
        state='PROGRESS',
        meta={
            'current': current,
            'total': total,
            'progress': progress,
            'description': description
        }
    )

# Health check task
@celery_app.task(bind=True)
def health_check(self):
    """Health check task for monitoring"""
    try:
        # Check Redis connection
        from redis import Redis
        redis_client = Redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        
        # Check database connection
        from database.database import get_db
        db = next(get_db())
        db.execute("SELECT 1")
        db.close()
        
        return {
            "status": "healthy",
            "timestamp": self.request.utcnow().isoformat(),
            "worker": self.request.hostname
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": self.request.utcnow().isoformat(),
            "worker": self.request.hostname
        }

if __name__ == '__main__':
    celery_app.start() 