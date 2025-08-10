"""
Batch processor for efficient data synchronization from Bubble.io API
Processes data in batches of 200 items with progress tracking
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
from shared_utils import parse_datetime
import time

logger = logging.getLogger(__name__)

class BatchProcessor:
    def __init__(self, batch_size=200):
        self.api_key = os.environ.get("BUBBLE_API_KEY_LIVE")
        self.base_url = "https://assignmentassistants.theinstituteslab.org/api/1.1/obj"
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        self.batch_size = batch_size
        self.progress_callback = None
        
    def set_progress_callback(self, callback):
        """Set a callback function to report progress"""
        self.progress_callback = callback
        
    def report_progress(self, data_type, current, total, message=""):
        """Report progress to callback if set"""
        if self.progress_callback:
            self.progress_callback({
                'data_type': data_type,
                'current': current,
                'total': total,
                'percentage': round((current / total * 100) if total > 0 else 0, 1),
                'message': message
            })
            
    def fetch_bubble_page(self, data_type, cursor=0, limit=None, constraints=None):
        """Fetch a single page of data from Bubble API"""
        limit = limit or self.batch_size
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
    
    def get_total_count(self, data_type, constraints=None):
        """Get total count of items for a data type"""
        page_data = self.fetch_bubble_page(data_type, 0, 1, constraints)
        if page_data:
            count = page_data.get('count', 0)
            remaining = page_data.get('remaining', 0)
            return count + remaining
        return 0
    
    def process_batch(self, data_type, processor_func, modified_since=None, max_items=None):
        """
        Process data in batches with progress tracking
        
        Args:
            data_type: Type of data to fetch ('user', 'conversation', etc.)
            processor_func: Function to process each item
            modified_since: Only fetch items modified after this date
            max_items: Maximum number of items to process (None for all)
        
        Returns:
            Dictionary with results including count and any errors
        """
        cursor = 0
        total_processed = 0
        errors = []
        
        # Build constraints if needed
        constraints = []
        if modified_since:
            constraints.append({
                'key': 'Modified Date',
                'constraint_type': 'greater than',
                'value': modified_since.isoformat()
            })
        
        # Get total count for progress tracking
        total_count = self.get_total_count(data_type, constraints if constraints else None)
        if max_items and total_count > max_items:
            total_count = max_items
            
        logger.info(f"Starting batch processing for {data_type}: {total_count} items to process")
        self.report_progress(data_type, 0, total_count, f"Starting {data_type} sync...")
        
        while True:
            # Check if we've reached max_items
            if max_items and total_processed >= max_items:
                break
                
            # Fetch batch
            batch_limit = self.batch_size
            if max_items:
                remaining_to_fetch = max_items - total_processed
                if remaining_to_fetch < batch_limit:
                    batch_limit = remaining_to_fetch
                    
            logger.info(f"Fetching {data_type} batch - cursor: {cursor}, limit: {batch_limit}")
            page_data = self.fetch_bubble_page(
                data_type, cursor, batch_limit, 
                constraints if constraints else None
            )
            
            if not page_data:
                break
            
            results = page_data.get('results', [])
            if not results:
                break
                
            # Process batch
            batch_processed = 0
            for item in results:
                try:
                    if processor_func(item):
                        batch_processed += 1
                        total_processed += 1
                except Exception as e:
                    logger.error(f"Error processing {data_type} item: {e}")
                    errors.append(str(e))
            
            # Commit batch to database
            try:
                db.session.commit()
                logger.info(f"Committed batch of {batch_processed} {data_type} items")
            except Exception as e:
                logger.error(f"Error committing {data_type} batch: {e}")
                db.session.rollback()
                errors.append(f"Commit error: {str(e)}")
            
            # Report progress
            self.report_progress(
                data_type, total_processed, total_count,
                f"Processed {total_processed}/{total_count} {data_type}"
            )
            
            # Check if there are more items
            remaining = page_data.get('remaining', 0)
            if remaining == 0:
                break
                
            cursor += len(results)
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
        
        logger.info(f"Completed {data_type} sync: {total_processed} items processed")
        return {
            'count': total_processed,
            'errors': errors,
            'success': len(errors) == 0
        }
    
    def process_user(self, user_data):
        """Process a single user record"""
        user_id = user_data.get('_id')
        if not user_id:
            return False
        
        # Extract email from authentication data
        email = None
        auth = user_data.get('authentication', {})
        if auth:
            if 'email' in auth and 'email' in auth['email']:
                email = auth['email']['email']
            elif 'API - AWS Cognito' in auth and 'email' in auth['API - AWS Cognito']:
                email = auth['API - AWS Cognito']['email']
        
        # Get or create user
        user = User.query.filter_by(id=user_id).first()
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
        user.created_date = parse_datetime(user_data.get('Created Date'))
        user.modified_date = parse_datetime(user_data.get('Modified Date'))
        user.raw_data = user_data
        user.last_synced = datetime.utcnow()
        
        return True
    
    def process_course(self, course_data):
        """Process a single course record"""
        course_id = course_data.get('_id')
        if not course_id:
            return False
        
        course = Course.query.filter_by(id=course_id).first()
        if not course:
            course = Course()
            course.id = course_id
            db.session.add(course)
        
        course.name = course_data.get('name')
        course.name_text = course_data.get('name_text')
        course.title = course_data.get('title')
        course.created_date = parse_datetime(course_data.get('Created Date'))
        course.modified_date = parse_datetime(course_data.get('Modified Date'))
        course.raw_data = course_data
        course.last_synced = datetime.utcnow()
        
        return True
    
    def process_assignment(self, assignment_data):
        """Process a single assignment record"""
        assignment_id = assignment_data.get('_id')
        if not assignment_id:
            return False
        
        assignment = Assignment.query.filter_by(id=assignment_id).first()
        if not assignment:
            assignment = Assignment()
            assignment.id = assignment_id
            db.session.add(assignment)
        
        assignment.name = assignment_data.get('name')
        assignment.name_text = assignment_data.get('name_text')
        assignment.assignment_name = assignment_data.get('assignment_name')
        assignment.assignment_name_text = assignment_data.get('assignment_name_text')
        assignment.title = assignment_data.get('title')
        assignment.course_id = assignment_data.get('course')
        assignment.created_date = parse_datetime(assignment_data.get('Created Date'))
        assignment.modified_date = parse_datetime(assignment_data.get('Modified Date'))
        assignment.raw_data = assignment_data
        assignment.last_synced = datetime.utcnow()
        
        return True
    
    def process_conversation_starter(self, starter_data):
        """Process a single conversation starter record"""
        starter_id = starter_data.get('_id')
        if not starter_id:
            return False
        
        starter = ConversationStarter.query.filter_by(id=starter_id).first()
        if not starter:
            starter = ConversationStarter()
            starter.id = starter_id
            db.session.add(starter)
        
        # Get title text for activity mapping
        title_text = starter_data.get('title_text', '').lower()
        
        starter.name = starter_data.get('name') or starter_data.get('name_text')
        starter.name_text = starter_data.get('name_text')
        starter.activity_type = title_text  # Store the actual title for mapping
        starter.created_date = parse_datetime(starter_data.get('Created Date'))
        starter.modified_date = parse_datetime(starter_data.get('Modified Date'))
        starter.raw_data = starter_data
        starter.last_synced = datetime.utcnow()
        
        return True
    
    def process_conversation(self, conv_data):
        """Process a single conversation record"""
        conv_id = conv_data.get('_id')
        if not conv_id:
            return False
        
        conversation = Conversation.query.filter_by(id=conv_id).first()
        if not conversation:
            conversation = Conversation()
            conversation.id = conv_id
            db.session.add(conversation)
        
        # Extract basic fields
        conversation.user_id = conv_data.get('user')
        conversation.course_id = conv_data.get('course')
        conversation.assignment_id = conv_data.get('assignment')
        conversation.conversation_starter_id = conv_data.get('conversation_starter')
        conversation.message_count = conv_data.get('message_count', 0)
        conversation.created_date = parse_datetime(conv_data.get('Created Date'))
        conversation.modified_date = parse_datetime(conv_data.get('Modified Date'))
        conversation.raw_data = conv_data
        conversation.last_synced = datetime.utcnow()
        
        # Look up related data from database
        if conversation.user_id:
            user = User.query.filter_by(id=conversation.user_id).first()
            if user:
                conversation.user_email = user.email
        
        if conversation.course_id:
            course = Course.query.filter_by(id=conversation.course_id).first()
            if course:
                conversation.course_name = course.name or course.name_text or course.title
        
        if conversation.assignment_id:
            assignment = Assignment.query.filter_by(id=conversation.assignment_id).first()
            if assignment:
                conversation.assignment_name = (assignment.assignment_name_text or 
                                               assignment.name_text or 
                                               assignment.assignment_name or 
                                               assignment.name or 
                                               assignment.title)
        
        if conversation.conversation_starter_id:
            starter = ConversationStarter.query.filter_by(id=conversation.conversation_starter_id).first()
            if starter:
                conversation.conversation_starter_name = starter.name or starter.name_text
        
        return True
    
    def process_message(self, msg_data):
        """Process a single message record"""
        msg_id = msg_data.get('_id')
        if not msg_id:
            return False
        
        message = Message.query.filter_by(id=msg_id).first()
        if not message:
            message = Message()
            message.id = msg_id
            db.session.add(message)
        
        message.conversation_id = msg_data.get('conversation')
        message.role = msg_data.get('role')
        message.role_option_message_role = msg_data.get('role_option_message_role')
        message.text = msg_data.get('text')
        message.created_date = parse_datetime(msg_data.get('Created Date'))
        message.modified_date = parse_datetime(msg_data.get('Modified Date'))
        message.raw_data = msg_data
        message.last_synced = datetime.utcnow()
        
        return True
    
    def get_or_create_sync_status(self, data_type):
        """Get or create sync status for a data type"""
        status = SyncStatus.query.filter_by(data_type=data_type).first()
        if not status:
            status = SyncStatus()
            status.data_type = data_type
            db.session.add(status)
            db.session.commit()
        return status
    
    def sync_data_type(self, data_type, processor_func, modified_since=None, max_items=None):
        """
        Sync a specific data type with status tracking
        
        Args:
            data_type: Name for status tracking (e.g., 'users')
            processor_func: Function to process each item
            modified_since: Only sync items modified after this date
            max_items: Maximum items to sync
        
        Returns:
            Dictionary with sync results
        """
        # Update sync status
        status = self.get_or_create_sync_status(data_type)
        status.status = 'syncing'
        status.updated_at = datetime.utcnow()
        db.session.commit()
        
        try:
            # Perform batch processing
            result = self.process_batch(
                data_type.rstrip('s'),  # Remove plural for API call
                processor_func,
                modified_since,
                max_items
            )
            
            # Update status on success
            status.status = 'completed'
            status.last_sync_date = datetime.utcnow()
            if modified_since:
                status.total_records += result['count']
            else:
                status.total_records = result['count']
            status.error_message = None if result['success'] else ', '.join(result['errors'])
            
        except Exception as e:
            logger.error(f"Error syncing {data_type}: {e}")
            status.status = 'failed'
            status.error_message = str(e)
            result = {'count': 0, 'errors': [str(e)], 'success': False}
        
        status.updated_at = datetime.utcnow()
        db.session.commit()
        
        return result
    
    def perform_full_sync(self, progress_callback=None):
        """
        Perform a full sync of all data types in proper order
        
        Args:
            progress_callback: Optional callback for progress updates
        
        Returns:
            Dictionary with results for each data type
        """
        if progress_callback:
            self.set_progress_callback(progress_callback)
        
        results = {}
        
        # Define sync operations in dependency order
        sync_operations = [
            ('users', self.process_user),
            ('courses', self.process_course),
            ('assignments', self.process_assignment),
            ('conversation_starters', self.process_conversation_starter),
            ('conversations', self.process_conversation),
            ('messages', self.process_message)
        ]
        
        for data_type, processor in sync_operations:
            logger.info(f"Starting full sync for {data_type}")
            results[data_type] = self.sync_data_type(data_type, processor)
            
        return results
    
    def perform_incremental_sync(self, progress_callback=None):
        """
        Perform incremental sync - only fetch new/modified records
        
        Args:
            progress_callback: Optional callback for progress updates
        
        Returns:
            Dictionary with results for each data type
        """
        if progress_callback:
            self.set_progress_callback(progress_callback)
        
        results = {}
        
        sync_operations = [
            ('users', self.process_user),
            ('courses', self.process_course),
            ('assignments', self.process_assignment),
            ('conversation_starters', self.process_conversation_starter),
            ('conversations', self.process_conversation),
            ('messages', self.process_message)
        ]
        
        for data_type, processor in sync_operations:
            logger.info(f"Starting incremental sync for {data_type}")
            
            # Get last sync date
            status = self.get_or_create_sync_status(data_type)
            modified_since = status.last_sync_date
            
            if modified_since:
                # Subtract 1 minute to account for any edge cases
                modified_since = modified_since - timedelta(minutes=1)
            
            results[data_type] = self.sync_data_type(
                data_type, processor, modified_since
            )
            
        return results
    
    def check_for_new_data(self, data_type):
        """
        Check if there's new data available since last sync
        
        Args:
            data_type: Type of data to check
        
        Returns:
            Tuple of (has_new_data, count_of_new_items)
        """
        status = self.get_or_create_sync_status(data_type)
        
        if not status.last_sync_date:
            # Never synced, all data is new
            total = self.get_total_count(data_type.rstrip('s'))
            return (True, total) if total > 0 else (False, 0)
        
        # Check for items modified after last sync
        constraints = [{
            'key': 'Modified Date',
            'constraint_type': 'greater than',
            'value': (status.last_sync_date - timedelta(minutes=1)).isoformat()
        }]
        
        count = self.get_total_count(data_type.rstrip('s'), constraints)
        return (True, count) if count > 0 else (False, 0)