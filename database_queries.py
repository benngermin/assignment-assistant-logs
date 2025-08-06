"""
Database query functions for retrieving data from local PostgreSQL database
"""
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from models import (
    User, Course, Assignment, Conversation, Message, 
    ConversationStarter, SyncStatus
)
from app import db
import logging

logger = logging.getLogger(__name__)

def get_statistics():
    """Get overall statistics from database"""
    try:
        users_count = User.query.count()
        conversations_count = Conversation.query.count()
        messages_count = Message.query.count()
        
        return {
            'users': users_count,
            'conversations': conversations_count,
            'messages': messages_count,
            'users_error': None,
            'conversations_error': None,
            'messages_error': None
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {
            'users': 0,
            'conversations': 0,
            'messages': 0,
            'users_error': str(e),
            'conversations_error': str(e),
            'messages_error': str(e)
        }

def get_comprehensive_metrics():
    """Get comprehensive metrics from database"""
    try:
        # Get all conversations with their starters
        conversations = Conversation.query.all()
        
        # Get conversation starters with activity types
        starters = ConversationStarter.query.all()
        starter_mapping = {s.id: s.activity_type for s in starters}
        
        # Count by activity type
        activity_counts = {
            'quiz_count': 0,
            'review_count': 0,
            'takeaway_count': 0,
            'simplify_count': 0,
            'study_count': 0,
            'motivate_count': 0
        }
        
        for conv in conversations:
            if conv.conversation_starter_id in starter_mapping:
                activity_type = starter_mapping[conv.conversation_starter_id]
                key = f"{activity_type}_count"
                if key in activity_counts:
                    activity_counts[key] += 1
        
        # Get unique courses and assignments
        unique_courses = db.session.query(func.count(func.distinct(Conversation.course_id))).scalar() or 0
        unique_assignments = db.session.query(func.count(func.distinct(Conversation.assignment_id))).scalar() or 0
        
        # Get user messages count
        user_messages = Message.query.filter(
            or_(
                Message.role == 'user',
                Message.role_option_message_role == 'user'
            )
        ).count()
        
        return {
            'total_users': User.query.count(),
            'total_conversations': Conversation.query.count(),
            'total_messages': Message.query.count(),
            'user_messages': user_messages,
            'unique_courses': unique_courses,
            'unique_assignments': unique_assignments,
            **activity_counts
        }
    except Exception as e:
        logger.error(f"Error getting comprehensive metrics: {e}")
        return {
            'total_users': 0,
            'total_conversations': 0,
            'total_messages': 0,
            'user_messages': 0,
            'unique_courses': 0,
            'unique_assignments': 0,
            'quiz_count': 0,
            'review_count': 0,
            'takeaway_count': 0,
            'simplify_count': 0,
            'study_count': 0,
            'motivate_count': 0,
            'error': str(e)
        }

def get_recent_conversations(limit=10):
    """Get recent conversations from database"""
    try:
        conversations = Conversation.query\
            .order_by(Conversation.created_date.desc())\
            .limit(limit)\
            .all()
        
        result = []
        for conv in conversations:
            result.append({
                '_id': conv.id,
                'user': conv.user_id,
                'user_email': conv.user_email,
                'course': conv.course_id,
                'course_name': conv.course_name,
                'assignment': conv.assignment_id,
                'assignment_name': conv.assignment_name,
                'conversation_starter': conv.conversation_starter_id,
                'conversation_starter_name': conv.conversation_starter_name,
                'message_count': conv.message_count,
                'Created Date': conv.created_date.isoformat() if conv.created_date else None,
                'Modified Date': conv.modified_date.isoformat() if conv.modified_date else None
            })
        
        return result
    except Exception as e:
        logger.error(f"Error getting recent conversations: {e}")
        return []

def get_date_chart_data(days=30, grouping='days'):
    """Get conversation data grouped by date from database"""
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Query conversations in date range
        conversations = Conversation.query.filter(
            Conversation.created_date >= start_date,
            Conversation.created_date <= end_date
        ).all()
        
        # Group by date based on grouping parameter
        date_counts = {}
        
        for conv in conversations:
            if not conv.created_date:
                continue
            
            if grouping == 'days':
                date_key = conv.created_date.strftime('%Y-%m-%d')
            elif grouping == 'weeks':
                # Get start of week (Monday)
                week_start = conv.created_date - timedelta(days=conv.created_date.weekday())
                date_key = week_start.strftime('%Y-%m-%d')
            elif grouping == 'months':
                date_key = conv.created_date.strftime('%Y-%m')
            else:
                date_key = conv.created_date.strftime('%Y-%m-%d')
            
            date_counts[date_key] = date_counts.get(date_key, 0) + 1
        
        # Format for chart
        labels = sorted(date_counts.keys())
        data_points = [date_counts.get(label, 0) for label in labels]
        
        # Format labels for display
        if grouping == 'weeks':
            labels = [f"Week of {label}" for label in labels]
        elif grouping == 'months':
            from calendar import month_name
            labels = [f"{month_name[int(label.split('-')[1])]} {label.split('-')[0]}" for label in labels]
        
        return {
            'labels': labels,
            'data': data_points,
            'total': sum(data_points)
        }
    except Exception as e:
        logger.error(f"Error getting date chart data: {e}")
        return {'labels': [], 'data': [], 'total': 0, 'error': str(e)}

def get_course_chart_data():
    """Get conversation counts by course from database"""
    try:
        # Query conversations grouped by course
        course_counts = db.session.query(
            Conversation.course_id,
            Conversation.course_name,
            func.count(Conversation.id).label('count')
        ).group_by(
            Conversation.course_id,
            Conversation.course_name
        ).all()
        
        labels = []
        data_points = []
        
        for course_id, course_name, count in course_counts:
            if course_id:
                # Use course name if available, otherwise use ID
                label = course_name or f"Course {course_id}"
                labels.append(label)
                data_points.append(count)
        
        return {
            'labels': labels,
            'data': data_points,
            'total': sum(data_points)
        }
    except Exception as e:
        logger.error(f"Error getting course chart data: {e}")
        return {'labels': [], 'data': [], 'total': 0, 'error': str(e)}

def get_activity_chart_data():
    """Get conversation counts by activity type from database"""
    try:
        # Get all conversation starters
        starters = ConversationStarter.query.all()
        starter_mapping = {}
        for starter in starters:
            starter_mapping[starter.id] = {
                'name': starter.name or starter.name_text or 'Unknown',
                'type': starter.activity_type
            }
        
        # Count conversations by starter
        starter_counts = db.session.query(
            Conversation.conversation_starter_id,
            func.count(Conversation.id).label('count')
        ).group_by(
            Conversation.conversation_starter_id
        ).all()
        
        activity_data = {}
        for starter_id, count in starter_counts:
            if starter_id in starter_mapping:
                name = starter_mapping[starter_id]['name']
                activity_data[name] = count
        
        # Format for chart
        labels = list(activity_data.keys())
        data_points = list(activity_data.values())
        
        return {
            'labels': labels,
            'data': data_points,
            'total': sum(data_points)
        }
    except Exception as e:
        logger.error(f"Error getting activity chart data: {e}")
        return {'labels': [], 'data': [], 'total': 0, 'error': str(e)}

def get_sync_status_all():
    """Get sync status for all data types"""
    try:
        statuses = SyncStatus.query.all()
        result = {}
        
        for status in statuses:
            result[status.data_type] = {
                'last_sync': status.last_sync_date.isoformat() if status.last_sync_date else None,
                'status': status.status,
                'total_records': status.total_records,
                'error': status.error_message
            }
        
        return result
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return {}