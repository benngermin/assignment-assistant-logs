"""
Scheduler for automatic hourly data synchronization
Uses APScheduler to run incremental syncs every hour
"""
import os
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from batch_processor import BatchProcessor
from app import app

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None

def run_hourly_sync():
    """
    Execute hourly incremental sync
    Fetches only new/modified data since last sync
    """
    try:
        logger.info("Starting scheduled hourly sync")
        
        with app.app_context():
            # Create batch processor with 200 item batches
            processor = BatchProcessor(batch_size=200)
            
            # Check for new data first
            data_types = ['users', 'courses', 'assignments', 'conversation_starters', 'conversations', 'messages']
            has_any_new = False
            
            for dtype in data_types:
                has_new, count = processor.check_for_new_data(dtype)
                if has_new:
                    logger.info(f"Found {count} new/modified {dtype}")
                    has_any_new = True
            
            if not has_any_new:
                logger.info("No new data found, skipping sync")
                return
            
            # Perform incremental sync
            results = processor.perform_incremental_sync()
            
            # Log results
            total_synced = sum(r.get('count', 0) for r in results.values())
            logger.info(f"Hourly sync completed: {total_synced} items synced")
            
            # Clear cache after sync
            from app import cache
            cache.clear()
            
            # Store sync result for monitoring
            store_sync_result(results)
            
    except Exception as e:
        logger.error(f"Error in hourly sync: {e}")
        store_sync_result({'error': str(e)})


def store_sync_result(results):
    """
    Store sync results for monitoring and debugging
    """
    try:
        from models import db, SyncStatus
        
        with app.app_context():
            # Create or update a special status record for scheduled syncs
            status = SyncStatus.query.filter_by(data_type='scheduled_sync').first()
            if not status:
                status = SyncStatus()
                status.data_type = 'scheduled_sync'
                db.session.add(status)
            
            status.last_sync_date = datetime.utcnow()
            status.status = 'completed' if 'error' not in results else 'failed'
            status.error_message = results.get('error')
            status.updated_at = datetime.utcnow()
            
            # Store results in raw_data field (if we add it to model)
            # For now, just update the status
            db.session.commit()
            
    except Exception as e:
        logger.error(f"Error storing sync result: {e}")


def init_scheduler():
    """
    Initialize the scheduler for automatic syncs
    Should be called when the app starts
    """
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler already initialized")
        return scheduler
    
    try:
        # Create scheduler
        scheduler = BackgroundScheduler(
            job_defaults={
                'coalesce': True,  # Coalesce missed jobs into one
                'max_instances': 1,  # Only one instance of job at a time
                'misfire_grace_time': 900  # 15 minutes grace time for misfired jobs
            }
        )
        
        # Check if hourly sync is enabled (default: enabled)
        hourly_sync_enabled = os.environ.get('ENABLE_HOURLY_SYNC', 'true').lower() == 'true'
        
        if hourly_sync_enabled:
            # Schedule hourly sync
            scheduler.add_job(
                func=run_hourly_sync,
                trigger=IntervalTrigger(hours=1),
                id='hourly_sync',
                name='Hourly incremental data sync',
                replace_existing=True,
                next_run_time=datetime.now() + timedelta(minutes=5)  # First run in 5 minutes
            )
            
            logger.info("Hourly sync scheduled - first run in 5 minutes, then every hour")
        else:
            logger.info("Hourly sync disabled by environment variable")
        
        # Start the scheduler
        scheduler.start()
        logger.info("Scheduler started successfully")
        
        return scheduler
        
    except Exception as e:
        logger.error(f"Error initializing scheduler: {e}")
        return None


def shutdown_scheduler():
    """
    Shutdown the scheduler gracefully
    Should be called when the app shuts down
    """
    global scheduler
    
    if scheduler is not None:
        try:
            scheduler.shutdown(wait=True)
            logger.info("Scheduler shut down successfully")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}")
        finally:
            scheduler = None


def get_scheduler_status():
    """
    Get the current status of the scheduler and jobs
    """
    global scheduler
    
    if scheduler is None:
        return {
            'running': False,
            'jobs': []
        }
    
    jobs_info = []
    for job in scheduler.get_jobs():
        jobs_info.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            'pending': job.pending
        })
    
    return {
        'running': scheduler.running,
        'jobs': jobs_info
    }


def trigger_manual_sync():
    """
    Manually trigger the hourly sync job
    Useful for testing or forcing an immediate sync
    """
    global scheduler
    
    if scheduler is None:
        raise Exception("Scheduler not initialized")
    
    try:
        job = scheduler.get_job('hourly_sync')
        if job:
            job.modify(next_run_time=datetime.now())
            logger.info("Manual sync triggered")
            return True
        else:
            logger.warning("Hourly sync job not found")
            return False
    except Exception as e:
        logger.error(f"Error triggering manual sync: {e}")
        raise


# API endpoints for scheduler management
@app.route('/api/scheduler/status', methods=['GET'])
def api_scheduler_status():
    """Get scheduler status"""
    try:
        status = get_scheduler_status()
        
        # Add last sync info
        from models import SyncStatus
        scheduled_status = SyncStatus.query.filter_by(data_type='scheduled_sync').first()
        if scheduled_status:
            status['last_sync'] = {
                'date': scheduled_status.last_sync_date.isoformat() if scheduled_status.last_sync_date else None,
                'status': scheduled_status.status,
                'error': scheduled_status.error_message
            }
        
        return jsonify({
            'success': True,
            'scheduler': status
        })
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/scheduler/trigger', methods=['POST'])
def api_trigger_sync():
    """Manually trigger the hourly sync"""
    try:
        triggered = trigger_manual_sync()
        if triggered:
            return jsonify({
                'success': True,
                'message': 'Sync triggered successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Sync job not found'
            }), 404
    except Exception as e:
        logger.error(f"Error triggering sync: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/scheduler/pause', methods=['POST'])
def api_pause_scheduler():
    """Pause the scheduler"""
    global scheduler
    
    try:
        if scheduler and scheduler.running:
            scheduler.pause()
            logger.info("Scheduler paused")
            return jsonify({
                'success': True,
                'message': 'Scheduler paused'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Scheduler not running'
            }), 400
    except Exception as e:
        logger.error(f"Error pausing scheduler: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/scheduler/resume', methods=['POST'])
def api_resume_scheduler():
    """Resume the scheduler"""
    global scheduler
    
    try:
        if scheduler and not scheduler.running:
            scheduler.resume()
            logger.info("Scheduler resumed")
            return jsonify({
                'success': True,
                'message': 'Scheduler resumed'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Scheduler already running or not initialized'
            }), 400
    except Exception as e:
        logger.error(f"Error resuming scheduler: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Import the scheduler in app.py to activate these endpoints
from flask import jsonify