"""
Batch sync endpoint for handling large data syncs without timeout
"""
from flask import jsonify
from app import app, db
from sync_manager import BubbleSyncManager
from models import Conversation, Message, User, Course, Assignment, ConversationStarter
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@app.route('/api/batch-sync', methods=['POST'])
def batch_sync():
    """
    Perform a complete sync of all data in manageable batches
    This endpoint is designed to handle large datasets without timing out
    """
    try:
        sync_manager = BubbleSyncManager()
        results = {
            'users': {'count': 0, 'success': False},
            'courses': {'count': 0, 'success': False},
            'assignments': {'count': 0, 'success': False},
            'conversation_starters': {'count': 0, 'success': False},
            'conversations': {'count': 0, 'batches': 0, 'success': False},
            'messages': {'count': 0, 'batches': 0, 'success': False}
        }
        
        # Sync smaller data types first (these are fast)
        try:
            logger.info("Syncing users...")
            users_data = sync_manager.fetch_all_data('user')
            count = 0
            batch_count = 0
            
            for user_data in users_data[:2000]:  # Limit to 2000 users
                user_id = user_data.get('_id')
                if not user_id:
                    continue
                
                # Use merge instead of get/add to avoid session issues
                user = User()
                user.id = user_id
                
                # Extract email
                email = None
                auth = user_data.get('authentication', {})
                if auth:
                    if 'email' in auth and 'email' in auth['email']:
                        email = auth['email']['email']
                
                user.email = email
                user.created_date = sync_manager.parse_datetime(user_data.get('Created Date'))
                user.raw_data = user_data
                user.last_synced = datetime.utcnow()
                
                db.session.merge(user)
                count += 1
                batch_count += 1
                
                # Commit every 50 users
                if batch_count >= 50:
                    db.session.commit()
                    batch_count = 0
            
            # Final commit for remaining users
            if batch_count > 0:
                db.session.commit()
            
            results['users'] = {'count': count, 'success': True}
            logger.info(f"Synced {count} users")
        except Exception as e:
            logger.error(f"Error syncing users: {e}")
            db.session.rollback()
            results['users']['error'] = str(e)
        
        # Sync courses
        try:
            logger.info("Syncing courses...")
            count = sync_manager.sync_courses()
            results['courses'] = {'count': count, 'success': True}
        except Exception as e:
            logger.error(f"Error syncing courses: {e}")
            results['courses']['error'] = str(e)
        
        # Sync assignments
        try:
            logger.info("Syncing assignments...")
            count = sync_manager.sync_assignments()
            results['assignments'] = {'count': count, 'success': True}
        except Exception as e:
            logger.error(f"Error syncing assignments: {e}")
            results['assignments']['error'] = str(e)
        
        # Sync conversation starters
        try:
            logger.info("Syncing conversation starters...")
            count = sync_manager.sync_conversation_starters()
            results['conversation_starters'] = {'count': count, 'success': True}
        except Exception as e:
            logger.error(f"Error syncing conversation starters: {e}")
            results['conversation_starters']['error'] = str(e)
        
        # Sync conversations in smaller batches
        try:
            logger.info("Starting conversation batch sync...")
            total_conv = 0
            batch_num = 0
            cursor = 0
            batch_size = 200  # Smaller batch size for reliability
            max_batches = 25  # Limit to 5000 conversations total
            
            while batch_num < max_batches:
                page_data = sync_manager.fetch_bubble_page('conversation', cursor, batch_size)
                if not page_data:
                    break
                
                batch_results = page_data.get('results', [])
                if not batch_results:
                    break
                
                # Process this batch
                for conv_data in batch_results:
                    conv_id = conv_data.get('_id')
                    if not conv_id:
                        continue
                    
                    # Use merge to avoid session issues
                    conv = Conversation()
                    conv.id = conv_id
                    conv.user_id = conv_data.get('user')
                    conv.course_id = conv_data.get('course')
                    conv.assignment_id = conv_data.get('assignment')
                    conv.conversation_starter_id = conv_data.get('conversation_starter')
                    conv.message_count = conv_data.get('message_count', 0)
                    conv.created_date = sync_manager.parse_datetime(conv_data.get('Created Date'))
                    conv.raw_data = conv_data
                    conv.last_synced = datetime.utcnow()
                    
                    db.session.merge(conv)
                    total_conv += 1
                
                # Commit after each batch
                db.session.commit()
                batch_num += 1
                logger.info(f"Synced conversation batch {batch_num} ({total_conv} total)")
                
                remaining = page_data.get('remaining', 0)
                if remaining == 0:
                    break
                cursor += len(batch_results)
            
            results['conversations'] = {
                'count': total_conv, 
                'batches': batch_num,
                'success': True
            }
            logger.info(f"Synced {total_conv} conversations in {batch_num} batches")
        except Exception as e:
            logger.error(f"Error syncing conversations: {e}")
            db.session.rollback()
            results['conversations']['error'] = str(e)
        
        # Sync messages in smaller batches
        try:
            logger.info("Starting message batch sync...")
            total_msg = 0
            batch_num = 0
            cursor = 0
            batch_size = 200  # Smaller batch size
            max_batches = 25  # Limit to 5000 messages total
            
            while batch_num < max_batches:
                page_data = sync_manager.fetch_bubble_page('message', cursor, batch_size)
                if not page_data:
                    break
                
                batch_results = page_data.get('results', [])
                if not batch_results:
                    break
                
                # Process this batch
                for msg_data in batch_results:
                    msg_id = msg_data.get('_id')
                    if not msg_id:
                        continue
                    
                    # Use merge to avoid session issues
                    msg = Message()
                    msg.id = msg_id
                    msg.conversation_id = msg_data.get('conversation')
                    msg.role = msg_data.get('role')
                    msg.role_option_message_role = msg_data.get('role_option_message_role')
                    msg.text = msg_data.get('text')
                    msg.created_date = sync_manager.parse_datetime(msg_data.get('Created Date'))
                    msg.raw_data = msg_data
                    msg.last_synced = datetime.utcnow()
                    
                    db.session.merge(msg)
                    total_msg += 1
                
                # Commit after each batch
                db.session.commit()
                batch_num += 1
                logger.info(f"Synced message batch {batch_num} ({total_msg} total)")
                
                remaining = page_data.get('remaining', 0)
                if remaining == 0:
                    break
                cursor += len(batch_results)
            
            results['messages'] = {
                'count': total_msg,
                'batches': batch_num,
                'success': True
            }
            logger.info(f"Synced {total_msg} messages in {batch_num} batches")
        except Exception as e:
            logger.error(f"Error syncing messages: {e}")
            db.session.rollback()
            results['messages']['error'] = str(e)
        
        # Clear cache after sync
        from app import cache
        cache.clear()
        
        # Get final counts
        final_counts = {
            'users': User.query.count(),
            'courses': Course.query.count(),
            'assignments': Assignment.query.count(),
            'conversations': Conversation.query.count(),
            'messages': Message.query.count()
        }
        
        return jsonify({
            'success': True,
            'message': f'Batch sync completed successfully',
            'results': results,
            'final_counts': final_counts,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in batch sync: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500