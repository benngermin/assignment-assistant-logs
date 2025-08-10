"""
Batch refresh endpoint with progress tracking
Handles data refresh in batches of 200 items with real-time progress updates
"""
from flask import jsonify, request
from app import app, db
from batch_processor import BatchProcessor
from models import User, Course, Assignment, Conversation, Message, ConversationStarter
from datetime import datetime
import logging
import threading
import uuid

logger = logging.getLogger(__name__)

# Store active sync sessions
active_syncs = {}

@app.route('/api/batch-refresh', methods=['POST'])
def batch_refresh():
    """
    Perform batch refresh with configurable batch size and progress tracking
    
    Request body (optional):
    {
        "batch_size": 200,  // Items per API call (default: 200)
        "sync_type": "incremental",  // "incremental" or "full" (default: incremental)
        "data_types": ["conversations", "messages"],  // Specific types to sync (default: all)
        "max_items": null  // Maximum items to sync per type (default: no limit)
    }
    """
    try:
        # Parse request parameters
        data = request.get_json() or {}
        batch_size = data.get('batch_size', 200)
        sync_type = data.get('sync_type', 'incremental')
        data_types = data.get('data_types', None)
        max_items = data.get('max_items', None)
        
        # Validate batch size
        if batch_size < 10 or batch_size > 500:
            return jsonify({
                'success': False,
                'error': 'Batch size must be between 10 and 500'
            }), 400
        
        # Create batch processor
        processor = BatchProcessor(batch_size=batch_size)
        
        # Check current database state
        db_state = {
            'users': User.query.count(),
            'courses': Course.query.count(),
            'assignments': Assignment.query.count(),
            'conversation_starters': ConversationStarter.query.count(),
            'conversations': Conversation.query.count(),
            'messages': Message.query.count()
        }
        
        logger.info(f"Starting {sync_type} sync with batch size {batch_size}")
        logger.info(f"Current database state: {db_state}")
        
        # Track progress
        progress_data = {}
        
        def progress_callback(progress):
            """Callback to track progress"""
            progress_data[progress['data_type']] = progress
            logger.info(f"Progress: {progress['data_type']} - {progress['percentage']}% ({progress['current']}/{progress['total']})")
        
        processor.set_progress_callback(progress_callback)
        
        # Perform sync based on type
        if sync_type == 'full':
            results = processor.perform_full_sync()
        else:
            # Check for new data first
            new_data_info = {}
            check_types = data_types or ['users', 'courses', 'assignments', 'conversation_starters', 'conversations', 'messages']
            
            for dtype in check_types:
                has_new, count = processor.check_for_new_data(dtype)
                new_data_info[dtype] = {'has_new': has_new, 'count': count}
                if has_new:
                    logger.info(f"Found {count} new/modified {dtype}")
            
            # Perform incremental sync
            results = processor.perform_incremental_sync()
            
            # Add new data info to results
            for dtype, info in new_data_info.items():
                if dtype in results:
                    results[dtype]['new_available'] = info
        
        # Get final database counts
        final_db_state = {
            'users': User.query.count(),
            'courses': Course.query.count(),
            'assignments': Assignment.query.count(),
            'conversation_starters': ConversationStarter.query.count(),
            'conversations': Conversation.query.count(),
            'messages': Message.query.count()
        }
        
        # Calculate changes
        changes = {}
        for dtype in final_db_state:
            changes[dtype] = {
                'before': db_state.get(dtype, 0),
                'after': final_db_state[dtype],
                'added': final_db_state[dtype] - db_state.get(dtype, 0)
            }
        
        # Clear cache after sync
        from app import cache
        cache.clear()
        
        # Prepare response
        response = {
            'success': True,
            'sync_type': sync_type,
            'batch_size': batch_size,
            'results': results,
            'database_changes': changes,
            'progress': progress_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add summary
        total_synced = sum(r.get('count', 0) for r in results.values())
        total_errors = sum(len(r.get('errors', [])) for r in results.values())
        
        response['summary'] = {
            'total_synced': total_synced,
            'total_errors': total_errors,
            'success_rate': f"{((total_synced - total_errors) / total_synced * 100) if total_synced > 0 else 100:.1f}%"
        }
        
        logger.info(f"Batch refresh completed: {response['summary']}")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in batch refresh: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/batch-refresh-status', methods=['GET'])
def batch_refresh_status():
    """
    Get the current status of batch refresh operations
    Shows last sync times and available new data
    """
    try:
        from models import SyncStatus
        
        # Get all sync statuses
        statuses = SyncStatus.query.all()
        
        # Create batch processor to check for new data
        processor = BatchProcessor()
        
        status_info = {}
        for status in statuses:
            # Check for new data
            has_new, count = processor.check_for_new_data(status.data_type)
            
            status_info[status.data_type] = {
                'last_sync': status.last_sync_date.isoformat() if status.last_sync_date else None,
                'status': status.status,
                'total_records': status.total_records,
                'has_new_data': has_new,
                'new_data_count': count,
                'last_error': status.error_message
            }
        
        # Add any missing data types
        all_types = ['users', 'courses', 'assignments', 'conversation_starters', 'conversations', 'messages']
        for dtype in all_types:
            if dtype not in status_info:
                has_new, count = processor.check_for_new_data(dtype)
                status_info[dtype] = {
                    'last_sync': None,
                    'status': 'never_synced',
                    'total_records': 0,
                    'has_new_data': has_new,
                    'new_data_count': count,
                    'last_error': None
                }
        
        # Calculate if any refresh is needed
        needs_refresh = any(info['has_new_data'] for info in status_info.values())
        total_new = sum(info['new_data_count'] for info in status_info.values())
        
        return jsonify({
            'success': True,
            'statuses': status_info,
            'needs_refresh': needs_refresh,
            'total_new_items': total_new,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting batch refresh status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/batch-refresh-async', methods=['POST'])
def batch_refresh_async():
    """
    Start an asynchronous batch refresh that runs in the background
    Returns immediately with a session ID to track progress
    """
    try:
        import uuid
        
        # Parse request parameters
        data = request.get_json() or {}
        batch_size = data.get('batch_size', 200)
        sync_type = data.get('sync_type', 'incremental')
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Start background thread
        def run_sync():
            try:
                # Store session info
                active_syncs[session_id] = {
                    'status': 'running',
                    'started': datetime.utcnow(),
                    'progress': {},
                    'results': None
                }
                
                # Create processor with progress callback
                processor = BatchProcessor(batch_size=batch_size)
                
                def progress_callback(progress):
                    if session_id in active_syncs:
                        active_syncs[session_id]['progress'][progress['data_type']] = progress
                
                processor.set_progress_callback(progress_callback)
                
                # Perform sync
                if sync_type == 'full':
                    results = processor.perform_full_sync()
                else:
                    results = processor.perform_incremental_sync()
                
                # Update session info
                if session_id in active_syncs:
                    active_syncs[session_id]['status'] = 'completed'
                    active_syncs[session_id]['results'] = results
                    active_syncs[session_id]['completed'] = datetime.utcnow()
                    
            except Exception as e:
                logger.error(f"Error in async sync: {e}")
                if session_id in active_syncs:
                    active_syncs[session_id]['status'] = 'failed'
                    active_syncs[session_id]['error'] = str(e)
        
        # Start thread
        thread = threading.Thread(target=run_sync)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Batch refresh started in background',
            'check_progress_url': f'/api/batch-refresh-progress/{session_id}'
        })
        
    except Exception as e:
        logger.error(f"Error starting async batch refresh: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/batch-refresh-progress/<session_id>', methods=['GET'])
def batch_refresh_progress(session_id):
    """
    Get progress of an async batch refresh session
    """
    if session_id not in active_syncs:
        return jsonify({
            'success': False,
            'error': 'Session not found'
        }), 404
    
    session = active_syncs[session_id]
    
    # Calculate overall progress
    total_progress = 0
    if session['progress']:
        progress_values = [p['percentage'] for p in session['progress'].values()]
        total_progress = sum(progress_values) / len(progress_values) if progress_values else 0
    
    response = {
        'success': True,
        'session_id': session_id,
        'status': session['status'],
        'started': session['started'].isoformat(),
        'overall_progress': round(total_progress, 1),
        'detailed_progress': session['progress'],
        'results': session.get('results'),
        'error': session.get('error')
    }
    
    if 'completed' in session:
        response['completed'] = session['completed'].isoformat()
        response['duration'] = str(session['completed'] - session['started'])
    
    # Clean up old completed sessions (older than 1 hour)
    if session['status'] in ['completed', 'failed']:
        if 'completed' in session:
            age = datetime.utcnow() - session['completed']
            if age.total_seconds() > 3600:  # 1 hour
                del active_syncs[session_id]
    
    return jsonify(response)