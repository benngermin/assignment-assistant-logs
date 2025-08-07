"""
Sequential sync with very small batch sizes to avoid timeouts
"""
from flask import jsonify
from app import app, db
from models import User, Course, Assignment, ConversationStarter, Conversation, Message
from datetime import datetime
import requests
import os
import logging
import time

logger = logging.getLogger(__name__)

class SequentialSyncManager:
    """Sync manager that fetches data in very small sequential batches"""
    
    def __init__(self):
        self.api_key = os.environ.get('BUBBLE_API_KEY_LIVE')
        if not self.api_key:
            raise ValueError("BUBBLE_API_KEY_LIVE not found in environment variables")
        self.base_url = 'https://assignmentassistants.theinstituteslab.org/api/1.1/obj'
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        # Use very small batch sizes to avoid timeouts
        self.batch_size = 50  # Very small batch size
        self.max_items_per_sync = 10000  # Maximum items to sync in one operation
    
    def fetch_page(self, data_type, cursor=0, limit=50):
        """Fetch a single page of data with very small limit"""
        url = f"{self.base_url}/{data_type}"
        params = {
            'cursor': cursor,
            'limit': limit  # Small limit to avoid timeout
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            if response.status_code == 200:
                return response.json().get('response', {})
            else:
                logger.error(f"API error for {data_type}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {data_type} page at cursor {cursor}: {e}")
            return None
    
    def parse_datetime(self, date_str):
        """Parse datetime string from Bubble"""
        if not date_str:
            return None
        try:
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None
    
    def sync_small_data(self, data_type):
        """Sync small datasets (users, courses, etc.) in one batch"""
        logger.info(f"Syncing {data_type}...")
        cursor = 0
        total = 0
        
        # For small data types, fetch up to 500 items
        max_items = 500
        
        while total < max_items:
            page_data = self.fetch_page(data_type, cursor, self.batch_size)
            if not page_data:
                break
            
            results = page_data.get('results', [])
            if not results:
                break
            
            # Process based on data type
            if data_type == 'user':
                self.process_users(results)
            elif data_type == 'course':
                self.process_courses(results)
            elif data_type == 'assignment':
                self.process_assignments(results)
            elif data_type == 'conversation_starter':
                self.process_conversation_starters(results)
            
            total += len(results)
            remaining = page_data.get('remaining', 0)
            
            if remaining == 0:
                break
            
            cursor += len(results)
            time.sleep(0.1)  # Small delay between requests
        
        db.session.commit()
        logger.info(f"Synced {total} {data_type} items")
        return total
    
    def process_users(self, users_data):
        """Process a batch of users"""
        for user_data in users_data:
            user_id = user_data.get('_id')
            if not user_id:
                continue
            
            user = db.session.get(User, user_id)
            if not user:
                user = User(id=user_id)
                db.session.add(user)
            
            # Extract email
            email = None
            auth = user_data.get('authentication', {})
            if auth and 'email' in auth and 'email' in auth['email']:
                email = auth['email']['email']
            
            user.email = email
            user.created_date = self.parse_datetime(user_data.get('Created Date'))
            user.raw_data = user_data
            user.last_synced = datetime.utcnow()
    
    def process_courses(self, courses_data):
        """Process a batch of courses"""
        for course_data in courses_data:
            course_id = course_data.get('_id')
            if not course_id:
                continue
            
            course = db.session.get(Course, course_id)
            if not course:
                course = Course(id=course_id)
                db.session.add(course)
            
            course.name = course_data.get('name')
            course.description = course_data.get('description')
            course.created_date = self.parse_datetime(course_data.get('Created Date'))
            course.raw_data = course_data
            course.last_synced = datetime.utcnow()
    
    def process_assignments(self, assignments_data):
        """Process a batch of assignments"""
        for assignment_data in assignments_data:
            assignment_id = assignment_data.get('_id')
            if not assignment_id:
                continue
            
            assignment = db.session.get(Assignment, assignment_id)
            if not assignment:
                assignment = Assignment(id=assignment_id)
                db.session.add(assignment)
            
            assignment.name = (assignment_data.get('assignment_name_text') or 
                             assignment_data.get('name_text') or
                             assignment_data.get('assignment_name') or
                             assignment_data.get('name') or
                             assignment_data.get('title'))
            assignment.course_id = assignment_data.get('course')
            assignment.created_date = self.parse_datetime(assignment_data.get('Created Date'))
            assignment.raw_data = assignment_data
            assignment.last_synced = datetime.utcnow()
    
    def process_conversation_starters(self, starters_data):
        """Process a batch of conversation starters"""
        for starter_data in starters_data:
            starter_id = starter_data.get('_id')
            if not starter_id:
                continue
            
            starter = db.session.get(ConversationStarter, starter_id)
            if not starter:
                starter = ConversationStarter(id=starter_id)
                db.session.add(starter)
            
            starter.name = starter_data.get('name')
            starter.prompt = starter_data.get('prompt')
            starter.created_date = self.parse_datetime(starter_data.get('Created Date'))
            starter.raw_data = starter_data
            starter.last_synced = datetime.utcnow()
    
    def sync_conversations_sequential(self):
        """Sync conversations in very small sequential batches"""
        logger.info("Starting sequential conversation sync...")
        cursor = 0
        total = 0
        batch_num = 0
        
        while total < self.max_items_per_sync:
            page_data = self.fetch_page('conversation', cursor, self.batch_size)
            if not page_data:
                break
            
            results = page_data.get('results', [])
            if not results:
                break
            
            # Process this small batch
            for conv_data in results:
                conv_id = conv_data.get('_id')
                if not conv_id:
                    continue
                
                conv = db.session.get(Conversation, conv_id)
                if not conv:
                    conv = Conversation(id=conv_id)
                    db.session.add(conv)
                
                conv.user_id = conv_data.get('user')
                conv.course_id = conv_data.get('course')
                conv.assignment_id = conv_data.get('assignment')
                conv.conversation_starter_id = conv_data.get('conversation_starter')
                conv.message_count = conv_data.get('message_count', 0)
                conv.created_date = self.parse_datetime(conv_data.get('Created Date'))
                conv.raw_data = conv_data
                conv.last_synced = datetime.utcnow()
            
            # Commit after each small batch
            db.session.commit()
            total += len(results)
            batch_num += 1
            
            logger.info(f"Synced conversation batch {batch_num} ({total} total)")
            
            remaining = page_data.get('remaining', 0)
            if remaining == 0:
                break
            
            cursor += len(results)
            time.sleep(0.2)  # Small delay between requests
        
        logger.info(f"Synced {total} conversations in {batch_num} batches")
        return total
    
    def sync_messages_sequential(self):
        """Sync messages in very small sequential batches"""
        logger.info("Starting sequential message sync...")
        cursor = 0
        total = 0
        batch_num = 0
        
        while total < self.max_items_per_sync:
            page_data = self.fetch_page('message', cursor, self.batch_size)
            if not page_data:
                break
            
            results = page_data.get('results', [])
            if not results:
                break
            
            # Process this small batch
            for msg_data in results:
                msg_id = msg_data.get('_id')
                if not msg_id:
                    continue
                
                msg = db.session.get(Message, msg_id)
                if not msg:
                    msg = Message(id=msg_id)
                    db.session.add(msg)
                
                msg.conversation_id = msg_data.get('conversation')
                msg.role = msg_data.get('role')
                msg.role_option_message_role = msg_data.get('role_option_message_role')
                msg.text = msg_data.get('text')
                msg.created_date = self.parse_datetime(msg_data.get('Created Date'))
                msg.raw_data = msg_data
                msg.last_synced = datetime.utcnow()
            
            # Commit after each small batch
            db.session.commit()
            total += len(results)
            batch_num += 1
            
            logger.info(f"Synced message batch {batch_num} ({total} total)")
            
            remaining = page_data.get('remaining', 0)
            if remaining == 0:
                break
            
            cursor += len(results)
            time.sleep(0.2)  # Small delay between requests
        
        logger.info(f"Synced {total} messages in {batch_num} batches")
        return total


@app.route('/api/sequential-sync', methods=['POST'])
def sequential_sync():
    """
    Perform a sequential sync with very small batches to avoid timeouts
    """
    try:
        sync_manager = SequentialSyncManager()
        results = {}
        
        # Sync small data types first
        results['users'] = sync_manager.sync_small_data('user')
        results['courses'] = sync_manager.sync_small_data('course')
        results['assignments'] = sync_manager.sync_small_data('assignment')
        results['conversation_starters'] = sync_manager.sync_small_data('conversation_starter')
        
        # Sync conversations in small sequential batches
        results['conversations'] = sync_manager.sync_conversations_sequential()
        
        # Sync messages in small sequential batches
        results['messages'] = sync_manager.sync_messages_sequential()
        
        # Clear cache
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
            'message': 'Sequential sync completed successfully',
            'synced': results,
            'database_counts': final_counts,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in sequential sync: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500