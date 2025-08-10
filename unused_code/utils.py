"""
Utility functions to reduce code duplication across the application
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Constants
MAX_API_ITEMS = 2000
CACHE_TTL_SECONDS = 600
EXCLUDED_EMAIL_DOMAINS = ['@modia.ai', '@theinstitutes.org']

def is_excluded_email(email):
    """
    Check if an email should be excluded from metrics and displays
    
    Args:
        email (str): Email address to check
        
    Returns:
        bool: True if email should be excluded, False otherwise
    """
    if not email:
        return False
    
    email_lower = email.lower()
    
    for domain in EXCLUDED_EMAIL_DOMAINS:
        if domain in email_lower:
            return True
    
    return False

def extract_user_email(user_data, user_email_map=None):
    """
    Extract email from user data or user email map
    
    Args:
        user_data (dict): User or conversation data
        user_email_map (dict): Optional mapping of user IDs to emails
        
    Returns:
        str: User email or empty string
    """
    # Direct email field
    if 'user_email_text' in user_data:
        return user_data['user_email_text']
    
    # Check email field
    if 'email' in user_data:
        return user_data['email']
    
    # Check authentication structure
    auth = user_data.get('authentication', {})
    if auth:
        if 'email' in auth and isinstance(auth['email'], dict) and 'email' in auth['email']:
            return auth['email']['email']
        elif 'API - AWS Cognito' in auth and 'email' in auth['API - AWS Cognito']:
            return auth['API - AWS Cognito']['email']
    
    # Use user email map if available
    if user_email_map:
        user_id = user_data.get('user', user_data.get('user_id'))
        if user_id and user_id in user_email_map:
            return user_email_map[user_id]
    
    return ''

def map_course_names(courses_data):
    """
    Create a mapping of course IDs to course names
    
    Args:
        courses_data (list): List of course data from API
        
    Returns:
        dict: Mapping of course ID to course name
    """
    course_name_map = {}
    
    for course in courses_data:
        course_id = course.get('_id')
        if not course_id:
            continue
            
        # Priority order: name_text > course_name > full_name_text > name > title > fallback
        course_name = (course.get('name_text') or 
                      course.get('course_name') or 
                      course.get('full_name_text') or 
                      course.get('name') or 
                      course.get('title') or 
                      f'Course {course_id[:8]}')
        
        course_name_map[course_id] = course_name
    
    return course_name_map

def map_assignment_names(assignments_data):
    """
    Create a mapping of assignment IDs to assignment names
    
    Args:
        assignments_data (list): List of assignment data from API
        
    Returns:
        dict: Mapping of assignment ID to assignment name
    """
    assignment_name_map = {}
    
    for assignment in assignments_data:
        assignment_id = assignment.get('_id')
        if not assignment_id:
            continue
            
        # Priority order: assignment_name_text > name_text > assignment_name > name > title > fallback
        assignment_name = (assignment.get('assignment_name_text') or 
                          assignment.get('name_text') or 
                          assignment.get('assignment_name') or 
                          assignment.get('name') or 
                          assignment.get('title') or 
                          f'Assignment {assignment_id[:8]}')
        
        assignment_name_map[assignment_id] = assignment_name
    
    return assignment_name_map

def get_conversation_course_id(conversation):
    """
    Extract course ID from conversation using field priority
    
    Args:
        conversation (dict): Conversation data
        
    Returns:
        str or None: Course ID if found
    """
    return (conversation.get('course_custom_variable_parent') or
            conversation.get('course') or
            conversation.get('course_id') or
            conversation.get('Course'))

def get_conversation_assignment_id(conversation):
    """
    Extract assignment ID from conversation using field priority
    
    Args:
        conversation (dict): Conversation data
        
    Returns:
        str or None: Assignment ID if found
    """
    return (conversation.get('assignment_custom_variable_parent') or
            conversation.get('assignment') or
            conversation.get('assignment_id') or
            conversation.get('Assignment'))

def get_conversation_starter_id(conversation):
    """
    Extract conversation starter ID from conversation using field priority
    
    Args:
        conversation (dict): Conversation data
        
    Returns:
        str or None: Conversation starter ID if found
    """
    return (conversation.get('conversation_starter_custom_conversation_starter') or
            conversation.get('conversation_starter') or
            conversation.get('starter_id'))

def map_activity_type(title_text):
    """
    Map conversation starter title text to activity type
    
    Args:
        title_text (str): Title text from conversation starter
        
    Returns:
        str: Activity type key for metrics
    """
    if not title_text:
        return None
        
    title_lower = title_text.lower()
    
    activity_map = {
        'quiz me': 'quiz_count',
        'review terms': 'review_count',
        'key takeaways': 'takeaway_count',
        'simplify a concept': 'simplify_count',
        'study hacks': 'study_count',
        'motivate me': 'motivate_count'
    }
    
    return activity_map.get(title_lower)

def parse_iso_datetime(date_str):
    """
    Parse ISO format datetime string with proper error handling
    
    Args:
        date_str (str): ISO format datetime string
        
    Returns:
        datetime or None: Parsed datetime object
    """
    if not date_str:
        return None
        
    try:
        # Handle ISO format with 'Z' timezone
        if date_str.endswith('Z'):
            date_str = date_str.replace('Z', '+00:00')
        
        # Parse the date
        parsed_date = datetime.fromisoformat(date_str)
        
        # Remove timezone info for consistency
        return parsed_date.replace(tzinfo=None)
        
    except (ValueError, TypeError, AttributeError) as e:
        logger.debug(f"Failed to parse date {date_str}: {e}")
        return None

def create_error_response(error_message, status_code=500):
    """
    Create a standardized error response
    
    Args:
        error_message (str): Error message to return
        status_code (int): HTTP status code
        
    Returns:
        tuple: (response dict, status code)
    """
    return {
        'error': 'Request failed',
        'details': error_message,
        'success': False
    }, status_code

def create_success_response(data, message=None):
    """
    Create a standardized success response
    
    Args:
        data (dict): Data to return
        message (str): Optional success message
        
    Returns:
        dict: Success response
    """
    response = {
        'success': True,
        'data': data
    }
    
    if message:
        response['message'] = message
    
    return response