"""
Shared utility functions used across multiple modules
"""
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def parse_datetime(date_str):
    """
    Parse datetime string from Bubble API
    Handles ISO format with 'Z' timezone
    
    Args:
        date_str: DateTime string from Bubble API
        
    Returns:
        datetime object or None if parsing fails
    """
    if not date_str:
        return None
    try:
        # Handle ISO format with 'Z' timezone
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, TypeError, AttributeError) as e:
        logger.debug(f"Failed to parse datetime '{date_str}': {e}")
        return None

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
    
    excluded_domains = ['@modia.ai', '@theinstitutes.org']
    email_lower = email.lower()
    
    for domain in excluded_domains:
        if domain in email_lower:
            return True
    
    return False