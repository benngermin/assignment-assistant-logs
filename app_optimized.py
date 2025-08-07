"""
Optimized version of app.py with reduced duplication and improved performance
This file can replace app.py after testing
"""
import os
import logging
import json
import requests
from collections import Counter
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timedelta
import time

# Import utility functions
from utils import (
    is_excluded_email, extract_user_email, map_course_names,
    map_assignment_names, get_conversation_course_id,
    get_conversation_assignment_id, get_conversation_starter_id,
    map_activity_type, parse_iso_datetime, create_error_response,
    create_success_response, MAX_API_ITEMS, CACHE_TTL_SECONDS
)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Database base class
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Configure database
database_url = os.environ.get("DATABASE_URL")
if database_url:
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    db.init_app(app)
    
    # Initialize database tables
    with app.app_context():
        import models
        import simple_refresh  # Import simple refresh routes
        db.create_all()
else:
    app.logger.warning("No DATABASE_URL found, running without database")

# Enhanced cache with thread-safe operations
cache = {
    'conversations': {'data': None, 'timestamp': 0},
    'users': {'data': None, 'timestamp': 0},
    'courses': {'data': None, 'timestamp': 0},
    'assignments': {'data': None, 'timestamp': 0},
    'conversation_starters': {'data': None, 'timestamp': 0},
    'messages': {'data': None, 'timestamp': 0}
}

def fetch_bubble_data(data_type, params=None):
    """
    Fetch data from Bubble API with improved error handling
    """
    api_key = os.environ.get("BUBBLE_API_KEY_LIVE")
    if not api_key:
        app.logger.error("No BUBBLE_API_KEY_LIVE found in environment")
        return {
            'error': 'Missing API key',
            'details': 'BUBBLE_API_KEY_LIVE not configured',
            'results': [],
            'count': 0,
            'remaining': 0
        }
    
    base_url = "https://assignmentassistants.theinstituteslab.org/api/1.1/obj"
    url = f"{base_url}/{data_type}"
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        app.logger.debug(f"Fetching {data_type} from Bubble API")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            
            if 'response' in response_data:
                bubble_response = response_data['response']
                return {
                    'results': bubble_response.get('results', []),
                    'count': len(bubble_response.get('results', [])),
                    'cursor': bubble_response.get('cursor', 0),
                    'remaining': bubble_response.get('remaining', 0)
                }
            return response_data
            
        else:
            app.logger.error(f"Bubble API error for {data_type}: {response.status_code}")
            return {
                'error': f'API request failed',
                'details': f'Status: {response.status_code}',
                'results': [],
                'count': 0,
                'remaining': 0
            }
            
    except requests.exceptions.Timeout:
        app.logger.error(f"Timeout fetching {data_type}")
        return {'error': 'Request timeout', 'results': [], 'count': 0, 'remaining': 0}
    except Exception as e:
        app.logger.error(f"Exception fetching {data_type}: {str(e)}")
        return {'error': 'Request failed', 'details': str(e), 'results': [], 'count': 0, 'remaining': 0}

def get_total_count(data_type, filter_user_messages=False):
    """
    Get total count with optimized queries for user messages
    """
    try:
        if data_type == 'message' and filter_user_messages:
            # Optimized count for user messages
            constraints = [{'key': 'role_option_message_role', 'constraint_type': 'equals', 'value': 'user'}]
            params = {'constraints': json.dumps(constraints), 'limit': 1, 'cursor': 0}
            data = fetch_bubble_data(data_type, params)
            
            if 'error' not in data:
                return int(data.get('count', 0)) + int(data.get('remaining', 0))
            return 0
            
        # Standard count query
        params = {'limit': 1, 'cursor': 0}
        data = fetch_bubble_data(data_type, params)
        
        if 'error' in data:
            return 0
            
        return int(data.get('count', 0)) + int(data.get('remaining', 0))
        
    except Exception as e:
        app.logger.error(f"Exception in get_total_count for {data_type}: {str(e)}")
        return 0

def fetch_all(data_type, custom_params=None):
    """
    Optimized fetch with configurable batch size
    """
    all_results = []
    cursor = 0
    limit = 100
    
    try:
        while len(all_results) < MAX_API_ITEMS:
            params = {'cursor': cursor, 'limit': limit}
            if custom_params:
                params.update(custom_params)
            
            data = fetch_bubble_data(data_type, params)
            
            if 'error' in data:
                app.logger.error(f"Error fetching {data_type}: {data}")
                break
            
            results = data.get('results', [])
            all_results.extend(results)
            
            if data.get('remaining', 0) == 0:
                break
                
            cursor += limit
        
        app.logger.info(f"Fetched {len(all_results)} {data_type} items")
        return all_results[:MAX_API_ITEMS]
        
    except Exception as e:
        app.logger.error(f"Exception in fetch_all for {data_type}: {str(e)}")
        return []

def fetch_all_cached(data_type, custom_params=None):
    """
    Enhanced caching with thread safety
    """
    current_time = time.time()
    
    if data_type in cache:
        cache_entry = cache[data_type]
        if (cache_entry['data'] is not None and 
            current_time - cache_entry['timestamp'] < CACHE_TTL_SECONDS):
            app.logger.info(f"Using cached {data_type} ({len(cache_entry['data'])} items)")
            return cache_entry['data']
    
    app.logger.info(f"Fetching fresh {data_type}")
    data = fetch_all(data_type, custom_params)
    
    if data_type in cache:
        cache[data_type] = {'data': data, 'timestamp': current_time}
    
    return data

# Simplified endpoints using utility functions

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def api_stats():
    """Optimized stats endpoint"""
    try:
        from database_queries import get_statistics
        stats = get_statistics()
        
        # Use API fallback if database is empty
        if stats['users'] == 0:
            app.logger.info("Using API fallback for stats")
            stats = {
                'users': get_total_count('user'),
                'conversations': get_total_count('conversation'),
                'messages': get_total_count('message', filter_user_messages=True),
                'users_error': None,
                'conversations_error': None,
                'messages_error': None
            }
        
        return jsonify(stats)
        
    except Exception as e:
        app.logger.error(f"Error in /api/stats: {str(e)}")
        return create_error_response(str(e))

@app.route('/api/metrics')
def api_metrics():
    """Optimized metrics endpoint with reduced API calls"""
    try:
        # Get counts
        metrics = {
            'total_users': get_total_count('user'),
            'total_conversations': get_total_count('conversation'),
            'total_messages': get_total_count('message', filter_user_messages=True),
            'avg_messages_per_conv': 0,
            'convs_per_course': {},
            'convs_per_assignment': {},
            'quiz_count': 0,
            'review_count': 0,
            'takeaway_count': 0,
            'simplify_count': 0,
            'study_count': 0,
            'motivate_count': 0
        }
        
        # Calculate average
        if metrics['total_conversations'] > 0:
            metrics['avg_messages_per_conv'] = round(
                metrics['total_messages'] / metrics['total_conversations'], 2
            )
        
        # Get conversation details with caching
        conversations = fetch_all_cached('conversation')
        
        if conversations:
            # Get supporting data
            courses = fetch_all_cached('course')
            assignments = fetch_all_cached('assignment')
            starters = fetch_all_cached('conversation_starter')
            
            # Create mappings
            course_map = map_course_names(courses)
            assignment_map = map_assignment_names(assignments)
            
            # Create activity mapping
            starter_activity_map = {}
            for starter in starters:
                starter_id = starter.get('_id')
                title = starter.get('title_text', '')
                if starter_id and title:
                    activity_type = map_activity_type(title)
                    if activity_type:
                        starter_activity_map[starter_id] = activity_type
            
            # Process conversations
            course_counter = Counter()
            assignment_counter = Counter()
            activity_counter = Counter()
            
            for conv in conversations:
                # Count by course
                course_id = get_conversation_course_id(conv)
                if course_id:
                    course_name = course_map.get(course_id, f'Course {course_id[:8]}')
                    course_counter[course_name] += 1
                
                # Count by assignment
                assignment_id = get_conversation_assignment_id(conv)
                if assignment_id:
                    assignment_name = assignment_map.get(assignment_id, f'Assignment {assignment_id[:8]}')
                    assignment_counter[assignment_name] += 1
                
                # Count by activity
                starter_id = get_conversation_starter_id(conv)
                if starter_id in starter_activity_map:
                    activity_counter[starter_activity_map[starter_id]] += 1
            
            # Update metrics
            metrics['convs_per_course'] = dict(course_counter)
            metrics['convs_per_assignment'] = dict(assignment_counter)
            
            for activity_key, count in activity_counter.items():
                if activity_key in metrics:
                    metrics[activity_key] = count
        
        metrics['summary'] = {
            'unique_courses': len(metrics['convs_per_course']),
            'unique_assignments': len(metrics['convs_per_assignment']),
            'data_quality': 'complete' if conversations else 'limited'
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        app.logger.error(f"Error in /api/metrics: {str(e)}")
        return create_error_response(str(e))

@app.route('/api/conversations')
def api_conversations():
    """Optimized conversations endpoint"""
    try:
        # Get filters
        email_filter = request.args.get('email')
        course_filter = request.args.get('course_number')
        date_start = request.args.get('date_start')
        date_end = request.args.get('date_end')
        
        # Build constraints
        constraints = []
        if email_filter:
            constraints.append({
                'key': 'user_email_text',
                'constraint_type': 'text contains',
                'value': email_filter
            })
        if course_filter:
            constraints.append({
                'key': 'course_number_text',
                'constraint_type': 'text contains',
                'value': course_filter
            })
        if date_start:
            constraints.append({
                'key': 'Created Date',
                'constraint_type': 'greater than',
                'value': f"{date_start}T00:00:00.000Z"
            })
        if date_end:
            constraints.append({
                'key': 'Created Date',
                'constraint_type': 'less than',
                'value': f"{date_end}T23:59:59.999Z"
            })
        
        # Prepare params
        params = {'sort_field': 'Created Date', 'descending': 'true'}
        if constraints:
            params['constraints'] = json.dumps(constraints)
        
        # Fetch data
        conversations = fetch_all('conversation', params)
        
        # Get supporting data for names
        courses = fetch_all_cached('course')
        assignments = fetch_all_cached('assignment')
        users = fetch_all_cached('user')
        
        # Create mappings
        course_map = map_course_names(courses)
        assignment_map = map_assignment_names(assignments)
        
        # Create user email map
        user_email_map = {}
        for user in users:
            user_id = user.get('_id')
            email = extract_user_email(user)
            if user_id and email:
                user_email_map[user_id] = email
        
        # Process conversations
        result = []
        for conv in conversations:
            # Get user email
            user_email = extract_user_email(conv, user_email_map)
            
            # Skip excluded emails
            if is_excluded_email(user_email):
                continue
            
            # Get names
            course_id = get_conversation_course_id(conv)
            course_name = course_map.get(course_id, 'Unknown Course') if course_id else 'Unknown Course'
            
            assignment_id = get_conversation_assignment_id(conv)
            assignment_name = assignment_map.get(assignment_id, 'Unknown Assignment') if assignment_id else 'Unknown Assignment'
            
            result.append({
                '_id': conv.get('_id'),
                'Created Date': conv.get('Created Date'),
                'user': conv.get('user', conv.get('user_id')),
                'user_email': user_email,
                'assignment': assignment_name,
                'assignment_id': assignment_id,
                'course': course_name,
                'course_id': course_id,
                'course_number': conv.get('course_number_text', ''),
                'message_count': conv.get('message_count', 0),
                'status': conv.get('status', 'active'),
                'last_message': conv.get('last_message', '')
            })
        
        app.logger.info(f"Returning {len(result)} conversations")
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error in /api/conversations: {str(e)}")
        return jsonify([])

@app.route('/api/chart/sessions-by-date')
def api_chart_sessions_by_date():
    """Optimized date chart endpoint"""
    try:
        days = int(request.args.get('days', 30))
        grouping = request.args.get('grouping', 'days')
        
        # Use cached data
        conversations = fetch_all_cached('conversation')
        users = fetch_all_cached('user')
        
        # Create user email map for filtering
        user_email_map = {}
        for user in users:
            user_id = user.get('_id')
            email = extract_user_email(user)
            if user_id and email:
                user_email_map[user_id] = email
        
        # Filter and process conversations
        from collections import defaultdict
        date_counts = defaultdict(int)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        for conv in conversations:
            # Filter excluded emails
            user_email = extract_user_email(conv, user_email_map)
            if is_excluded_email(user_email):
                continue
            
            # Parse date
            created_date = parse_iso_datetime(conv.get('Created Date'))
            if not created_date:
                continue
            
            # Check date range
            if not (start_date <= created_date <= end_date):
                continue
            
            # Group by specified interval
            if grouping == 'days':
                date_key = created_date.strftime('%Y-%m-%d')
            elif grouping == 'weeks':
                week_start = created_date - timedelta(days=created_date.weekday())
                date_key = week_start.strftime('%Y-%m-%d')
            elif grouping == 'months':
                date_key = created_date.strftime('%Y-%m')
            else:
                date_key = created_date.strftime('%Y-%m-%d')
            
            date_counts[date_key] += 1
        
        # Generate complete date range
        labels = []
        data = []
        
        if grouping == 'days':
            current = start_date
            while current <= end_date:
                date_key = current.strftime('%Y-%m-%d')
                labels.append(date_key)
                data.append(date_counts.get(date_key, 0))
                current += timedelta(days=1)
        
        elif grouping == 'weeks':
            current = start_date - timedelta(days=start_date.weekday())
            while current <= end_date:
                date_key = current.strftime('%Y-%m-%d')
                week_end = current + timedelta(days=6)
                labels.append(f"{current.strftime('%b %d')} - {week_end.strftime('%b %d')}")
                data.append(date_counts.get(date_key, 0))
                current += timedelta(weeks=1)
        
        elif grouping == 'months':
            current = start_date.replace(day=1)
            while current <= end_date:
                date_key = current.strftime('%Y-%m')
                labels.append(current.strftime('%B %Y'))
                data.append(date_counts.get(date_key, 0))
                
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
        
        return jsonify({
            'labels': labels,
            'data': data,
            'total_sessions': sum(data),
            'grouping': grouping
        })
        
    except Exception as e:
        app.logger.error(f"Error in date chart: {str(e)}")
        return jsonify({'labels': [], 'data': [], 'error': str(e)})

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """Simplified refresh endpoint"""
    try:
        # Clear cache
        for key in cache:
            cache[key] = {'data': None, 'timestamp': 0}
        
        # Try database sync if available
        if database_url:
            from sync_manager import BubbleSyncManager
            sync_manager = BubbleSyncManager()
            
            results = {}
            for data_type in ['users', 'courses', 'assignments', 'conversations']:
                try:
                    method = getattr(sync_manager, f'sync_{data_type}')
                    count = method()
                    results[data_type] = {'count': count, 'success': True}
                except Exception as e:
                    results[data_type] = {'count': 0, 'success': False, 'error': str(e)}
            
            return create_success_response(results, 'Data sync completed')
        
        return create_success_response({}, 'Cache cleared')
        
    except Exception as e:
        app.logger.error(f"Error during refresh: {str(e)}")
        return create_error_response(str(e))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal server error: {error}")
    return create_error_response(str(error))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)