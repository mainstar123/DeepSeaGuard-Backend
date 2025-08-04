from celery import current_task
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import logging
import os

from core.celery_app import celery_app
from database.database import get_db, ComplianceEvent, AUVZoneTracking
from config.settings import settings

logger = get_task_logger(__name__)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def cleanup_old_compliance_events(self, days_to_keep: int = 90):
    """Clean up old compliance events from database"""
    try:
        db = next(get_db())
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Count events to be deleted
        events_to_delete = db.query(ComplianceEvent).filter(
            ComplianceEvent.timestamp < cutoff_date
        ).count()
        
        # Delete old events
        db.query(ComplianceEvent).filter(
            ComplianceEvent.timestamp < cutoff_date
        ).delete()
        
        db.commit()
        db.close()
        
        logger.info(f"Cleaned up {events_to_delete} old compliance events")
        return {
            'events_deleted': events_to_delete,
            'cutoff_date': cutoff_date.isoformat(),
            'days_kept': days_to_keep
        }
        
    except Exception as exc:
        logger.error(f"Error cleaning up old compliance events: {exc}")
        raise self.retry(exc=exc, countdown=300)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def cleanup_inactive_auv_tracking(self, hours_threshold: int = 24):
    """Clean up inactive AUV tracking records"""
    try:
        db = next(get_db())
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_threshold)
        
        # Find inactive tracking records (no recent activity)
        inactive_tracking = db.query(AUVZoneTracking).filter(
            AUVZoneTracking.is_active == True,
            AUVZoneTracking.entry_time < cutoff_time
        ).all()
        
        cleaned_count = 0
        for tracking in inactive_tracking:
            # Mark as inactive
            tracking.is_active = False
            tracking.exit_time = cutoff_time
            cleaned_count += 1
        
        db.commit()
        db.close()
        
        logger.info(f"Cleaned up {cleaned_count} inactive AUV tracking records")
        return {
            'tracking_records_cleaned': cleaned_count,
            'cutoff_time': cutoff_time.isoformat(),
            'hours_threshold': hours_threshold
        }
        
    except Exception as exc:
        logger.error(f"Error cleaning up inactive AUV tracking: {exc}")
        raise self.retry(exc=exc, countdown=300)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def cleanup_old_files(self, directory: str = None, days_to_keep: int = 7):
    """Clean up old files from upload directory"""
    try:
        if directory is None:
            directory = settings.UPLOAD_DIR
        
        if not os.path.exists(directory):
            logger.warning(f"Upload directory {directory} does not exist")
            return {
                'files_deleted': 0,
                'directory': directory,
                'error': 'Directory does not exist'
            }
        
        cutoff_time = datetime.utcnow() - timedelta(days=days_to_keep)
        files_deleted = 0
        
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            if os.path.isfile(file_path):
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if file_mtime < cutoff_time:
                    try:
                        os.remove(file_path)
                        files_deleted += 1
                        logger.debug(f"Deleted old file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error deleting file {file_path}: {e}")
        
        logger.info(f"Cleaned up {files_deleted} old files from {directory}")
        return {
            'files_deleted': files_deleted,
            'directory': directory,
            'cutoff_time': cutoff_time.isoformat(),
            'days_kept': days_to_keep
        }
        
    except Exception as exc:
        logger.error(f"Error cleaning up old files: {exc}")
        raise self.retry(exc=exc, countdown=300)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def cleanup_redis_cache(self):
    """Clean up expired keys from Redis cache"""
    try:
        import redis
        redis_client = redis.from_url(settings.REDIS_URL)
        
        # Get all keys with the cache prefix
        pattern = f"{settings.CACHE_PREFIX}:*"
        keys = redis_client.keys(pattern)
        
        expired_keys = 0
        for key in keys:
            # Check if key has expired
            ttl = redis_client.ttl(key)
            if ttl == -1:  # No expiration set
                # Set expiration for old keys without TTL
                redis_client.expire(key, settings.CACHE_TTL)
            elif ttl == -2:  # Key doesn't exist (shouldn't happen)
                continue
        
        logger.info(f"Cleaned up Redis cache: {len(keys)} keys checked")
        return {
            'keys_checked': len(keys),
            'expired_keys': expired_keys,
            'cache_prefix': settings.CACHE_PREFIX
        }
        
    except Exception as exc:
        logger.error(f"Error cleaning up Redis cache: {exc}")
        raise self.retry(exc=exc, countdown=300)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def cleanup_celery_results(self, hours_to_keep: int = 24):
    """Clean up old Celery task results"""
    try:
        import redis
        redis_client = redis.from_url(settings.CELERY_RESULT_BACKEND)
        
        # Get all Celery result keys
        pattern = "celery-task-meta-*"
        keys = redis_client.keys(pattern)
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_to_keep)
        deleted_keys = 0
        
        for key in keys:
            try:
                # Get task result
                result_data = redis_client.get(key)
                if result_data:
                    result = json.loads(result_data)
                    
                    # Check if task is old enough
                    if 'date_done' in result:
                        task_time = datetime.fromisoformat(result['date_done'].replace('Z', '+00:00'))
                        if task_time < cutoff_time:
                            redis_client.delete(key)
                            deleted_keys += 1
                            
            except Exception as e:
                logger.warning(f"Error processing Celery result key {key}: {e}")
        
        logger.info(f"Cleaned up {deleted_keys} old Celery task results")
        return {
            'deleted_keys': deleted_keys,
            'total_keys': len(keys),
            'cutoff_time': cutoff_time.isoformat(),
            'hours_kept': hours_to_keep
        }
        
    except Exception as exc:
        logger.error(f"Error cleaning up Celery results: {exc}")
        raise self.retry(exc=exc, countdown=300)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def system_health_check(self):
    """Perform system health check"""
    try:
        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'healthy',
            'checks': {}
        }
        
        # Check database
        try:
            db = next(get_db())
            db.execute("SELECT 1")
            db.close()
            health_status['checks']['database'] = 'healthy'
        except Exception as e:
            health_status['checks']['database'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # Check Redis
        try:
            import redis
            redis_client = redis.from_url(settings.REDIS_URL)
            redis_client.ping()
            health_status['checks']['redis'] = 'healthy'
        except Exception as e:
            health_status['checks']['redis'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # Check disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage('.')
            free_gb = free / (1024**3)
            health_status['checks']['disk_space'] = f'healthy: {free_gb:.2f} GB free'
            
            if free_gb < 1:  # Less than 1 GB free
                health_status['checks']['disk_space'] = f'warning: {free_gb:.2f} GB free'
        except Exception as e:
            health_status['checks']['disk_space'] = f'unhealthy: {str(e)}'
        
        # Check memory usage (optional - requires psutil)
        try:
            import psutil
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            health_status['checks']['memory'] = f'healthy: {memory_percent:.1f}% used'
            
            if memory_percent > 90:
                health_status['checks']['memory'] = f'warning: {memory_percent:.1f}% used'
        except ImportError:
            health_status['checks']['memory'] = 'not_available: psutil not installed'
        except Exception as e:
            health_status['checks']['memory'] = f'unhealthy: {str(e)}'
        
        logger.info(f"System health check completed: {health_status['status']}")
        return health_status
        
    except Exception as exc:
        logger.error(f"Error in system health check: {exc}")
        raise self.retry(exc=exc, countdown=300)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def optimize_database(self):
    """Optimize database tables"""
    try:
        db = next(get_db())
        
        # For SQLite, run VACUUM
        if 'sqlite' in settings.DATABASE_SYNC_URL:
            db.execute("VACUUM")
            db.commit()
            logger.info("SQLite database optimized with VACUUM")
        
        # For PostgreSQL, run ANALYZE
        elif 'postgresql' in settings.DATABASE_SYNC_URL:
            db.execute("ANALYZE")
            db.commit()
            logger.info("PostgreSQL database optimized with ANALYZE")
        
        db.close()
        
        return {
            'optimization_completed': True,
            'database_type': 'sqlite' if 'sqlite' in settings.DATABASE_SYNC_URL else 'postgresql',
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error optimizing database: {exc}")
        raise self.retry(exc=exc, countdown=300)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def backup_database(self, backup_path: str = None):
    """Create database backup"""
    try:
        if backup_path is None:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_path = f"backup_{timestamp}.db"
        
        # For SQLite, copy the database file
        if 'sqlite' in settings.DATABASE_SYNC_URL:
            import shutil
            db_path = settings.DATABASE_SYNC_URL.replace('sqlite:///', '')
            shutil.copy2(db_path, backup_path)
            logger.info(f"SQLite database backed up to {backup_path}")
        
        # For PostgreSQL, you would use pg_dump
        elif 'postgresql' in settings.DATABASE_SYNC_URL:
            logger.warning("PostgreSQL backup not implemented - use pg_dump manually")
            return {
                'backup_completed': False,
                'error': 'PostgreSQL backup not implemented'
            }
        
        return {
            'backup_completed': True,
            'backup_path': backup_path,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error creating database backup: {exc}")
        raise self.retry(exc=exc, countdown=300)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def cleanup_logs(self, days_to_keep: int = 30):
    """Clean up old log files"""
    try:
        log_directory = "logs"  # Adjust based on your logging configuration
        
        if not os.path.exists(log_directory):
            logger.warning(f"Log directory {log_directory} does not exist")
            return {
                'files_deleted': 0,
                'directory': log_directory,
                'error': 'Directory does not exist'
            }
        
        cutoff_time = datetime.utcnow() - timedelta(days=days_to_keep)
        files_deleted = 0
        
        for filename in os.listdir(log_directory):
            if filename.endswith('.log'):
                file_path = os.path.join(log_directory, filename)
                
                if os.path.isfile(file_path):
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_mtime < cutoff_time:
                        try:
                            os.remove(file_path)
                            files_deleted += 1
                            logger.debug(f"Deleted old log file: {file_path}")
                        except Exception as e:
                            logger.error(f"Error deleting log file {file_path}: {e}")
        
        logger.info(f"Cleaned up {files_deleted} old log files")
        return {
            'files_deleted': files_deleted,
            'directory': log_directory,
            'cutoff_time': cutoff_time.isoformat(),
            'days_kept': days_to_keep
        }
        
    except Exception as exc:
        logger.error(f"Error cleaning up logs: {exc}")
        raise self.retry(exc=exc, countdown=300)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def full_system_cleanup(self):
    """Perform full system cleanup"""
    try:
        results = {}
        
        # Run all cleanup tasks
        cleanup_tasks = [
            ('compliance_events', cleanup_old_compliance_events.delay(90)),
            ('auv_tracking', cleanup_inactive_auv_tracking.delay(24)),
            ('files', cleanup_old_files.delay(None, 7)),
            ('redis_cache', cleanup_redis_cache.delay()),
            ('celery_results', cleanup_celery_results.delay(24)),
            ('logs', cleanup_logs.delay(30))
        ]
        
        for task_name, task in cleanup_tasks:
            try:
                result = task.get(timeout=300)  # 5 minute timeout
                results[task_name] = result
            except Exception as e:
                results[task_name] = {'error': str(e)}
        
        logger.info("Full system cleanup completed")
        return {
            'cleanup_completed': True,
            'timestamp': datetime.utcnow().isoformat(),
            'results': results
        }
        
    except Exception as exc:
        logger.error(f"Error in full system cleanup: {exc}")
        raise self.retry(exc=exc, countdown=300) 