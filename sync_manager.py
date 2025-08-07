"""
Sync Manager - Handles syncing data from Bubble API to local PostgreSQL database
"""
import os
import logging
import json
import requests
from datetime import datetime, timedelta
from app import db, app
from models import (
    User, Course, Assignment, Conversation, Message, 
    ConversationStarter, SyncStatus
)

logger = logging.getLogger(__name__)

class BubbleSyncManager:
    def __init__(self):
        self.api_key = os.environ.get("BUBBLE_API_KEY_LIVE")
        self.base_url = "https://assignmentassistants.theinstituteslab.org/api/1.1/obj"
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def fetch_bubble_page(self, data_type, cursor=0, limit=100, constraints=None):
        """Fetch a single page of data from Bubble API"""
        url = f"{self.base_url}/{data_type}"
        params = {
            'cursor': str(cursor),
            'limit': str(limit)
        }
        if constraints:
            params['constraints'] = json.dumps(constraints)
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if 'response' in data:
                    return data['response']
            logger.error(f"API error: {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {data_type}: {e}")
            return None
    
    def fetch_all_data(self, data_type, modified_since=None):
        """Fetch all data of a specific type from Bubble API"""
        all_results = []
        cursor = 0
        limit = 100
        
        constraints = []
        if modified_since:
            # Fetch only records modified after last sync
            constraints.append({
                'key': 'Modified Date',
                'constraint_type': 'greater than',
                'value': modified_since.isoformat()
            })
        
        while True:
            logger.info(f"Fetching {data_type} - cursor: {cursor}")
            page_data = self.fetch_bubble_page(data_type, cursor, limit, 
                                              constraints if constraints else None)
            
            if not page_data:
                break
            
            results = page_data.get('results', [])
            all_results.extend(results)
            
            remaining = page_data.get('remaining', 0)
            if remaining == 0:
                break
            
            cursor += len(results)
            
            # Safety limit to prevent infinite loops and timeouts
            if len(all_results) > 10000:  # Increased limit to handle more conversations
                logger.warning(f"Reached safety limit for {data_type}")
                break
        
        logger.info(f"Fetched {len(all_results)} total {data_type} records")
        return all_results
    
    def parse_datetime(self, date_str):
        """Parse datetime string from Bubble API"""
        if not date_str:
            return None
        try:
            # Handle ISO format with 'Z' timezone
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, TypeError, AttributeError):
            return None
    
    def sync_users(self, modified_since=None):
        """Sync users from Bubble to database"""
        users_data = self.fetch_all_data('user', modified_since)
        count = 0
        
        for user_data in users_data:
            user_id = user_data.get('_id')
            if not user_id:
                continue
            
            # Extract email from authentication data
            email = None
            auth = user_data.get('authentication', {})
            if auth:
                if 'email' in auth and 'email' in auth['email']:
                    email = auth['email']['email']
                elif 'API - AWS Cognito' in auth and 'email' in auth['API - AWS Cognito']:
                    email = auth['API - AWS Cognito']['email']
            
            # Check if user exists
            user = db.session.get(User, user_id)
            if not user:
                user = User()
                user.id = user_id
                db.session.add(user)
            
            # Update user data
            user.email = email
            user.user_signed_up = user_data.get('user_signed_up', False)
            user.role_option_roles = user_data.get('role_option_roles')
            user.is_company_opted_out = user_data.get('is_company_opted_out_boolean', False)
            user.has_seen_tooltip_tour = user_data.get('has_seen_tooltip_tour_boolean', False)
            user.created_date = self.parse_datetime(user_data.get('Created Date'))
            user.modified_date = self.parse_datetime(user_data.get('Modified Date'))
            user.raw_data = user_data
            user.last_synced = datetime.utcnow()
            
            count += 1
        
        try:
            db.session.commit()
        except Exception as commit_error:
            logger.error(f"Error committing users: {commit_error}")
            db.session.rollback()
            raise
        logger.info(f"Synced {count} users")
        return count
    
    def sync_courses(self, modified_since=None):
        """Sync courses from Bubble to database"""
        courses_data = self.fetch_all_data('course', modified_since)
        count = 0
        
        for course_data in courses_data:
            course_id = course_data.get('_id')
            if not course_id:
                continue
            
            course = db.session.get(Course, course_id)
            if not course:
                course = Course()
                course.id = course_id
                db.session.add(course)
            
            # Get course name from various fields
            course.name = course_data.get('name')
            course.name_text = course_data.get('name_text')
            course.title = course_data.get('title')
            course.created_date = self.parse_datetime(course_data.get('Created Date'))
            course.modified_date = self.parse_datetime(course_data.get('Modified Date'))
            course.raw_data = course_data
            course.last_synced = datetime.utcnow()
            
            count += 1
        
        db.session.commit()
        logger.info(f"Synced {count} courses")
        return count
    
    def sync_assignments(self, modified_since=None):
        """Sync assignments from Bubble to database"""
        assignments_data = self.fetch_all_data('assignment', modified_since)
        count = 0
        
        for assignment_data in assignments_data:
            assignment_id = assignment_data.get('_id')
            if not assignment_id:
                continue
            
            assignment = db.session.get(Assignment, assignment_id)
            if not assignment:
                assignment = Assignment()
                assignment.id = assignment_id
                db.session.add(assignment)
            
            # Get assignment name from various fields
            assignment.name = assignment_data.get('name')
            assignment.name_text = assignment_data.get('name_text')
            assignment.assignment_name = assignment_data.get('assignment_name')
            assignment.assignment_name_text = assignment_data.get('assignment_name_text')
            assignment.title = assignment_data.get('title')
            assignment.course_id = assignment_data.get('course')
            assignment.created_date = self.parse_datetime(assignment_data.get('Created Date'))
            assignment.modified_date = self.parse_datetime(assignment_data.get('Modified Date'))
            assignment.raw_data = assignment_data
            assignment.last_synced = datetime.utcnow()
            
            count += 1
        
        db.session.commit()
        logger.info(f"Synced {count} assignments")
        return count
    
    def sync_conversation_starters(self, modified_since=None):
        """Sync conversation starters from Bubble to database"""
        starters_data = self.fetch_all_data('conversation_starter', modified_since)
        count = 0
        
        activity_mapping = {
            '1729531593524x388907019419893600': 'quiz',
            '1729531609659x173632062967972640': 'review',
            '1729531628619x773975726695976700': 'takeaway',
            '1729531645316x407895957274959940': 'simplify',
            '1729531658548x462466905036505730': 'study',
            '1729531671500x323116475547090370': 'motivate'
        }
        
        for starter_data in starters_data:
            starter_id = starter_data.get('_id')
            if not starter_id:
                continue
            
            starter = db.session.get(ConversationStarter, starter_id)
            if not starter:
                starter = ConversationStarter()
                starter.id = starter_id
                db.session.add(starter)
            
            starter.name = starter_data.get('name') or starter_data.get('name_text')
            starter.name_text = starter_data.get('name_text')
            starter.activity_type = activity_mapping.get(starter_id, 'other')
            starter.created_date = self.parse_datetime(starter_data.get('Created Date'))
            starter.modified_date = self.parse_datetime(starter_data.get('Modified Date'))
            starter.raw_data = starter_data
            starter.last_synced = datetime.utcnow()
            
            count += 1
        
        db.session.commit()
        logger.info(f"Synced {count} conversation starters")
        return count
    
    def sync_conversations(self, modified_since=None, limit=1000):
        """Sync conversations from Bubble to database with batching"""
        # Fetch limited data for better performance
        conversations_data = []
        cursor = 0
        batch_size = 100
        
        while len(conversations_data) < limit:
            logger.info(f"Fetching conversation batch - cursor: {cursor}")
            page_data = self.fetch_bubble_page('conversation', cursor, batch_size)
            
            if not page_data:
                break
                
            results = page_data.get('results', [])
            conversations_data.extend(results)
            
            remaining = page_data.get('remaining', 0)
            if remaining == 0:
                break
                
            cursor += len(results)
            
            # Stop at limit
            if len(conversations_data) >= limit:
                conversations_data = conversations_data[:limit]
                break
        
        logger.info(f"Fetched {len(conversations_data)} conversations to sync")
        count = 0
        
        for conv_data in conversations_data:
            conv_id = conv_data.get('_id')
            if not conv_id:
                continue
            
            conversation = db.session.get(Conversation, conv_id)
            if not conversation:
                conversation = Conversation()
                conversation.id = conv_id
                db.session.add(conversation)
            
            # Extract user info
            user_id = conv_data.get('user')
            conversation.user_id = user_id
            
            # Look up user email from database
            if user_id:
                user = db.session.get(User, user_id)
                if user:
                    conversation.user_email = user.email
            
            # Extract course info
            course_id = conv_data.get('course')
            conversation.course_id = course_id
            
            # Look up course name from database
            if course_id:
                course = db.session.get(Course, course_id)
                if course:
                    conversation.course_name = course.name or course.name_text or course.title
            
            # Extract assignment info
            assignment_id = conv_data.get('assignment')
            conversation.assignment_id = assignment_id
            
            # Look up assignment name from database  
            if assignment_id:
                assignment = db.session.get(Assignment, assignment_id)
                if assignment:
                    conversation.assignment_name = (assignment.assignment_name_text or 
                                                   assignment.name_text or 
                                                   assignment.assignment_name or 
                                                   assignment.name or 
                                                   assignment.title)
            
            # Extract conversation starter info
            starter_id = conv_data.get('conversation_starter')
            conversation.conversation_starter_id = starter_id
            
            # Look up starter name from database
            if starter_id:
                starter = db.session.get(ConversationStarter, starter_id)
                if starter:
                    conversation.conversation_starter_name = starter.name or starter.name_text
            
            conversation.message_count = conv_data.get('message_count', 0)
            conversation.created_date = self.parse_datetime(conv_data.get('Created Date'))
            conversation.modified_date = self.parse_datetime(conv_data.get('Modified Date'))
            conversation.raw_data = conv_data
            conversation.last_synced = datetime.utcnow()
            
            count += 1
        
        db.session.commit()
        logger.info(f"Synced {count} conversations")
        return count
    
    def sync_messages(self, modified_since=None, limit=1000):
        """Sync messages from Bubble to database with batching"""
        # Fetch limited data for better performance
        messages_data = []
        cursor = 0
        batch_size = 100
        
        while len(messages_data) < limit:
            logger.info(f"Fetching message batch - cursor: {cursor}")
            page_data = self.fetch_bubble_page('message', cursor, batch_size)
            
            if not page_data:
                break
                
            results = page_data.get('results', [])
            messages_data.extend(results)
            
            remaining = page_data.get('remaining', 0)
            if remaining == 0:
                break
                
            cursor += len(results)
            
            # Stop at limit
            if len(messages_data) >= limit:
                messages_data = messages_data[:limit]
                break
        
        logger.info(f"Fetched {len(messages_data)} messages to sync")
        count = 0
        
        for msg_data in messages_data:
            msg_id = msg_data.get('_id')
            if not msg_id:
                continue
            
            message = db.session.get(Message, msg_id)
            if not message:
                message = Message()
                message.id = msg_id
                db.session.add(message)
            
            message.conversation_id = msg_data.get('conversation')
            message.role = msg_data.get('role')
            message.role_option_message_role = msg_data.get('role_option_message_role')
            message.text = msg_data.get('text')
            message.created_date = self.parse_datetime(msg_data.get('Created Date'))
            message.modified_date = self.parse_datetime(msg_data.get('Modified Date'))
            message.raw_data = msg_data
            message.last_synced = datetime.utcnow()
            
            count += 1
        
        db.session.commit()
        logger.info(f"Synced {count} messages")
        return count
    
    def get_sync_status(self, data_type):
        """Get or create sync status for a data type"""
        status = SyncStatus.query.filter_by(data_type=data_type).first()
        if not status:
            status = SyncStatus()
            status.data_type = data_type
            db.session.add(status)
            db.session.commit()
        return status
    
    def perform_full_sync(self):
        """Perform a full sync of all data types"""
        results = {}
        
        # Define sync order (dependencies first)
        sync_operations = [
            ('users', self.sync_users),
            ('courses', self.sync_courses),
            ('assignments', self.sync_assignments),
            ('conversation_starters', self.sync_conversation_starters),
            ('conversations', self.sync_conversations),
            ('messages', self.sync_messages)
        ]
        
        for data_type, sync_func in sync_operations:
            logger.info(f"Starting sync for {data_type}")
            status = self.get_sync_status(data_type)
            status.status = 'syncing'
            status.updated_at = datetime.utcnow()
            db.session.commit()
            
            try:
                count = sync_func()
                status.status = 'completed'
                status.last_sync_date = datetime.utcnow()
                status.total_records = count
                status.error_message = None
                results[data_type] = {'success': True, 'count': count}
            except Exception as e:
                logger.error(f"Error syncing {data_type}: {e}")
                status.status = 'failed'
                status.error_message = str(e)
                results[data_type] = {'success': False, 'error': str(e)}
            
            status.updated_at = datetime.utcnow()
            db.session.commit()
        
        return results
    
    def perform_incremental_sync(self):
        """Perform incremental sync - only fetch new/modified records"""
        results = {}
        
        sync_operations = [
            ('users', self.sync_users, 'user'),
            ('courses', self.sync_courses, 'course'),
            ('assignments', self.sync_assignments, 'assignment'),
            ('conversation_starters', self.sync_conversation_starters, 'conversation_starter'),
            ('conversations', self.sync_conversations, 'conversation'),
            ('messages', self.sync_messages, 'message')
        ]
        
        for data_type, sync_func, bubble_type in sync_operations:
            logger.info(f"Starting incremental sync for {data_type}")
            status = self.get_sync_status(data_type)
            
            # Use last sync date for incremental sync
            modified_since = status.last_sync_date
            
            status.status = 'syncing'
            status.updated_at = datetime.utcnow()
            db.session.commit()
            
            try:
                count = sync_func(modified_since=modified_since)
                status.status = 'completed'
                status.last_sync_date = datetime.utcnow()
                status.total_records += count  # Add to existing count
                status.error_message = None
                results[data_type] = {'success': True, 'count': count, 'incremental': True}
            except Exception as e:
                logger.error(f"Error in incremental sync for {data_type}: {e}")
                status.status = 'failed'
                status.error_message = str(e)
                results[data_type] = {'success': False, 'error': str(e)}
            
            status.updated_at = datetime.utcnow()
            db.session.commit()
        
        return results