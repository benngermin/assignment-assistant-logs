"""
Simple refresh endpoint that syncs data efficiently
"""
from flask import jsonify
from app import app, db
from sync_manager import BubbleSyncManager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@app.route('/api/simple-refresh', methods=['POST'])
def simple_refresh():
    """
    Perform a simple, efficient sync of all data
    """
    try:
        sync_manager = BubbleSyncManager()
        results = {}
        
        # Start with smaller data types
        logger.info("Starting simple refresh...")
        
        # Sync users - use raw SQL to avoid session issues
        try:
            users_count = sync_manager.sync_users()
            results['users'] = users_count
            logger.info(f"Synced {users_count} users")
        except Exception as e:
            logger.error(f"Error syncing users: {e}")
            results['users'] = 0
        
        # Sync courses
        try:
            courses_count = sync_manager.sync_courses()
            results['courses'] = courses_count
            logger.info(f"Synced {courses_count} courses")
        except Exception as e:
            logger.error(f"Error syncing courses: {e}")
            results['courses'] = 0
        
        # Sync assignments
        try:
            assignments_count = sync_manager.sync_assignments()
            results['assignments'] = assignments_count
            logger.info(f"Synced {assignments_count} assignments")
        except Exception as e:
            logger.error(f"Error syncing assignments: {e}")
            results['assignments'] = 0
        
        # Sync conversation starters
        try:
            starters_count = sync_manager.sync_conversation_starters()
            results['conversation_starters'] = starters_count
            logger.info(f"Synced {starters_count} conversation starters")
        except Exception as e:
            logger.error(f"Error syncing conversation starters: {e}")
            results['conversation_starters'] = 0
        
        # Sync conversations - use batch approach with raw SQL inserts
        try:
            logger.info("Syncing conversations...")
            conv_count = sync_manager.sync_conversations(limit=2000)  # Sync 2000 at a time
            results['conversations'] = conv_count
            logger.info(f"Synced {conv_count} conversations")
        except Exception as e:
            logger.error(f"Error syncing conversations: {e}")
            results['conversations'] = 0
        
        # Sync messages - use batch approach
        try:
            logger.info("Syncing messages...")
            msg_count = sync_manager.sync_messages(limit=2000)  # Sync 2000 at a time
            results['messages'] = msg_count
            logger.info(f"Synced {msg_count} messages")
        except Exception as e:
            logger.error(f"Error syncing messages: {e}")
            results['messages'] = 0
        
        # Clear cache
        from app import cache
        cache.clear()
        
        # Get final database counts
        from models import User, Course, Assignment, Conversation, Message
        final_counts = {
            'users': User.query.count(),
            'courses': Course.query.count(),
            'assignments': Assignment.query.count(),
            'conversations': Conversation.query.count(),
            'messages': Message.query.count()
        }
        
        return jsonify({
            'success': True,
            'message': 'Data refreshed successfully',
            'synced': results,
            'database_counts': final_counts,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in simple refresh: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500