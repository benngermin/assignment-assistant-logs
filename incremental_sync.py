"""
Incremental sync that adds more data to existing database
"""
from flask import jsonify, request
from app import app, db
from models import Conversation, Message
from datetime import datetime
from shared_utils import parse_datetime
import requests
import os
import logging

logger = logging.getLogger(__name__)

@app.route('/api/incremental-sync', methods=['POST'])
def incremental_sync():
    """
    Incrementally add more conversations and messages to the database
    Fetches in very small batches with delays to avoid timeouts
    """
    try:
        api_key = os.environ.get('BUBBLE_API_KEY_LIVE')
        if not api_key:
            return jsonify({'success': False, 'error': 'API key not configured'}), 500
        
        base_url = 'https://assignmentassistants.theinstituteslab.org/api/1.1/obj'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Get current counts
        current_conv_count = Conversation.query.count()
        current_msg_count = Message.query.count()
        
        logger.info(f"Current database: {current_conv_count} conversations, {current_msg_count} messages")
        
        # Parameters from request or defaults
        data = request.get_json() or {}
        batch_size = data.get('batch_size', 25)  # Very small batch
        max_items = data.get('max_items', 500)  # How many to add this sync
        
        results = {
            'conversations': {'before': current_conv_count, 'added': 0},
            'messages': {'before': current_msg_count, 'added': 0}
        }
        
        # Sync more conversations
        if current_conv_count < 8000:  # We know there are ~8000+ total
            logger.info(f"Syncing conversations starting from cursor {current_conv_count}")
            cursor = current_conv_count
            added = 0
            
            while added < max_items:
                # Fetch small batch
                url = f"{base_url}/conversation"
                params = {'cursor': cursor, 'limit': batch_size}
                
                try:
                    response = requests.get(url, headers=headers, params=params, timeout=15)
                    if response.status_code != 200:
                        logger.error(f"API error: {response.status_code}")
                        break
                    
                    data = response.json().get('response', {})
                    items = data.get('results', [])
                    
                    if not items:
                        break
                    
                    # Process items
                    for item in items:
                        conv_id = item.get('_id')
                        if not conv_id:
                            continue
                        
                        # Check if already exists
                        existing = Conversation.query.filter_by(id=conv_id).first()
                        if existing:
                            cursor += 1
                            continue
                        
                        # Create new conversation
                        conv = Conversation(
                            id=conv_id,
                            user_id=item.get('user'),
                            course_id=item.get('course'),
                            assignment_id=item.get('assignment'),
                            conversation_starter_id=item.get('conversation_starter'),
                            message_count=item.get('message_count', 0),
                            created_date=parse_datetime(item.get('Created Date')),
                            raw_data=item,
                            last_synced=datetime.utcnow()
                        )
                        db.session.add(conv)
                        added += 1
                    
                    # Commit this batch
                    db.session.commit()
                    logger.info(f"Added {added} conversations so far")
                    
                    # Check if more items exist
                    remaining = data.get('remaining', 0)
                    if remaining == 0:
                        break
                    
                    cursor += len(items)
                    
                except Exception as e:
                    logger.error(f"Error fetching conversations: {e}")
                    db.session.rollback()
                    break
            
            results['conversations']['added'] = added
            results['conversations']['after'] = Conversation.query.count()
        
        # Sync more messages
        if current_msg_count < 10000:  # We know there are ~10000+ total
            logger.info(f"Syncing messages starting from cursor {current_msg_count}")
            cursor = current_msg_count
            added = 0
            
            while added < max_items:
                # Fetch small batch
                url = f"{base_url}/message"
                params = {'cursor': cursor, 'limit': batch_size}
                
                try:
                    response = requests.get(url, headers=headers, params=params, timeout=15)
                    if response.status_code != 200:
                        logger.error(f"API error: {response.status_code}")
                        break
                    
                    data = response.json().get('response', {})
                    items = data.get('results', [])
                    
                    if not items:
                        break
                    
                    # Process items
                    for item in items:
                        msg_id = item.get('_id')
                        if not msg_id:
                            continue
                        
                        # Check if already exists
                        existing = Message.query.filter_by(id=msg_id).first()
                        if existing:
                            cursor += 1
                            continue
                        
                        # Create new message
                        msg = Message(
                            id=msg_id,
                            conversation_id=item.get('conversation'),
                            role=item.get('role'),
                            role_option_message_role=item.get('role_option_message_role'),
                            text=item.get('text'),
                            created_date=parse_datetime(item.get('Created Date')),
                            raw_data=item,
                            last_synced=datetime.utcnow()
                        )
                        db.session.add(msg)
                        added += 1
                    
                    # Commit this batch
                    db.session.commit()
                    logger.info(f"Added {added} messages so far")
                    
                    # Check if more items exist
                    remaining = data.get('remaining', 0)
                    if remaining == 0:
                        break
                    
                    cursor += len(items)
                    
                except Exception as e:
                    logger.error(f"Error fetching messages: {e}")
                    db.session.rollback()
                    break
            
            results['messages']['added'] = added
            results['messages']['after'] = Message.query.count()
        
        # Clear cache after sync
        from app import cache
        cache.clear()
        
        return jsonify({
            'success': True,
            'results': results,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in incremental sync: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500