import os
import logging
import json
import requests
from collections import Counter
from flask import Flask, render_template, jsonify, request, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timedelta
import time

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
        db.create_all()
else:
    app.logger.warning("No DATABASE_URL found, running without database")

# Simple in-memory cache with all data types
cache = {
    'conversations': {'data': None, 'timestamp': 0},
    'users': {'data': None, 'timestamp': 0},
    'courses': {'data': None, 'timestamp': 0},
    'assignments': {'data': None, 'timestamp': 0},
    'conversation_starters': {'data': None, 'timestamp': 0},
    'conversation': {'data': None, 'timestamp': 0},
    'user': {'data': None, 'timestamp': 0},
    'course': {'data': None, 'timestamp': 0},
    'conversation_starter': {'data': None, 'timestamp': 0},
    'message': {'data': None, 'timestamp': 0}
}
CACHE_TTL = 600  # Cache for 10 minutes for better performance

def fetch_bubble_data(data_type, params=None):
    """
    Fetch data from Bubble API
    
    Args:
        data_type (str): The type of data to fetch from the API
        params (dict): Optional query parameters
        
    Returns:
        dict: API response data or error information
    """
    # Get API key from environment
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
    
    # Build API URL
    base_url = "https://assignmentassistants.theinstituteslab.org/api/1.1/obj"
    url = f"{base_url}/{data_type}"
    
    # Set up headers
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Make API request
        app.logger.debug(f"Fetching {data_type} from Bubble API: {url}")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Handle Bubble API response structure
            if 'response' in response_data:
                bubble_response = response_data['response']
                results = bubble_response.get('results', [])
                cursor = bubble_response.get('cursor', 0)
                remaining = bubble_response.get('remaining', 0)
                
                # Format data to match expected structure
                data = {
                    'results': results,
                    'count': len(results),
                    'cursor': cursor,
                    'remaining': remaining
                }
                app.logger.debug(f"Successfully fetched {data_type}: {len(results)} items (cursor: {cursor}, remaining: {remaining})")
                return data
            else:
                # Fallback for other API response formats
                app.logger.debug(f"Successfully fetched {data_type}: {response_data.get('count', 0)} items")
                return response_data
        else:
            app.logger.error(f"Bubble API error for {data_type}: {response.status_code} - {response.text}")
            return {
                'error': f'API request failed',
                'details': f'Status: {response.status_code}, Response: {response.text}',
                'results': [],
                'count': 0,
                'remaining': 0
            }
            
    except requests.exceptions.Timeout:
        app.logger.error(f"Timeout fetching {data_type} from Bubble API")
        return {
            'error': 'Request timeout',
            'details': 'API request timed out after 30 seconds',
            'results': [],
            'count': 0,
            'remaining': 0
        }
    except Exception as e:
        app.logger.error(f"Exception fetching {data_type} from Bubble API: {str(e)}")
        return {
            'error': 'Request failed',
            'details': str(e),
            'results': [],
            'count': 0,
            'remaining': 0
        }

def get_total_count(data_type, filter_user_messages=False):
    """
    Get the total count of items for a specific data type from Bubble API
    Using pagination to handle large datasets
    
    Args:
        data_type (str): The type of data to count
        filter_user_messages (bool): If True and data_type is 'message', count only user messages
        
    Returns:
        int: Total count of items, or 0 if error
    """
    try:
        # For messages with user filter, use separate queries for each constraint
        # and combine the results (this is much faster than fetching all messages)
        if data_type == 'message' and filter_user_messages:
            try:
                # Count messages with new field role_option_message_role = 'user'
                new_role_constraints = [{
                    'key': 'role_option_message_role',
                    'constraint_type': 'equals',
                    'value': 'user'
                }]
                new_role_params = {
                    'constraints': json.dumps(new_role_constraints),
                    'limit': 1,
                    'cursor': 0
                }
                new_role_data = fetch_bubble_data(data_type, new_role_params)
                new_role_count = 0
                if 'error' not in new_role_data:
                    new_role_count = int(new_role_data.get('count', 0)) + int(new_role_data.get('remaining', 0))
                
                # Count messages with legacy field role = 'user'
                legacy_user_constraints = [{
                    'key': 'role',
                    'constraint_type': 'equals',
                    'value': 'user'
                }]
                legacy_user_params = {
                    'constraints': json.dumps(legacy_user_constraints),
                    'limit': 1,
                    'cursor': 0
                }
                legacy_user_data = fetch_bubble_data(data_type, legacy_user_params)
                legacy_user_count = 0
                if 'error' not in legacy_user_data:
                    legacy_user_count = int(legacy_user_data.get('count', 0)) + int(legacy_user_data.get('remaining', 0))
                
                # Estimate total user messages (this may have some overlap but gives us a good approximation)
                # For now, let's take the higher count as it's likely more accurate
                total_user_messages = max(new_role_count, legacy_user_count)
                
                app.logger.debug(f"New role field user messages: {new_role_count}, Legacy role field user messages: {legacy_user_count}")
                app.logger.debug(f"Using count: {total_user_messages}")
                return total_user_messages
                
            except Exception as e:
                app.logger.warning(f"Error in optimized user message counting, falling back to simple count: {str(e)}")
                # Fall back to total message count if filtering fails
                return get_total_count('message', filter_user_messages=False)
        else:
            # Make initial call with limit=1 to get count and remaining
            params = {'limit': 1, 'cursor': 0}
        
        data = fetch_bubble_data(data_type, params)
        
        if 'error' in data:
            app.logger.error(f"Error getting count for {data_type}: {data}")
            return 0
        
        # Total = count (items in current page) + remaining (items left)
        count = int(data.get('count', 0))
        remaining = int(data.get('remaining', 0))
        total = count + remaining
        
        app.logger.debug(f"Total count for {data_type}: {total} (count: {count}, remaining: {remaining})")
        return total
        
    except Exception as e:
        app.logger.error(f"Exception in get_total_count for {data_type}: {str(e)}")
        return 0

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

def fetch_all(data_type, custom_params=None):
    """
    Fetch all items of a specific data type from Bubble API using pagination
    
    Args:
        data_type (str): The type of data to fetch
        custom_params (dict): Optional custom parameters like constraints or sorting
        
    Returns:
        list: All results from the API, or empty list if error
    """
    all_results = []
    cursor = 0
    limit = 100
    max_items = 2000  # Reduced limit to prevent timeouts
    
    try:
        while True:
            params = {'cursor': cursor, 'limit': limit}
            # Add custom parameters if provided
            if custom_params:
                params.update(custom_params)
            
            data = fetch_bubble_data(data_type, params)
            
            if 'error' in data:
                app.logger.error(f"Error fetching all {data_type}: {data}")
                return []
            
            # Get results from response
            results = data.get('results', [])
            all_results.extend(results)
            
            # Check if we've reached the maximum
            if len(all_results) >= max_items:
                app.logger.info(f"Reached maximum items limit ({max_items}) for {data_type}")
                all_results = all_results[:max_items]  # Trim to max
                break
            
            # Check if there are more items
            remaining = data.get('remaining', 0)
            if remaining == 0:
                break
                
            # Update cursor for next batch
            cursor += limit
            
            app.logger.debug(f"Fetched {len(results)} {data_type} items, total so far: {len(all_results)}")
        
        app.logger.info(f"Successfully fetched {len(all_results)} total {data_type} items")
        return all_results
        
    except Exception as e:
        app.logger.error(f"Exception in fetch_all for {data_type}: {str(e)}")
        return []

def fetch_all_cached(data_type, custom_params=None):
    """
    Fetch all items with caching to improve performance
    
    Args:
        data_type (str): The type of data to fetch
        custom_params (dict): Optional custom parameters
        
    Returns:
        list: All results from the API cache or fresh fetch
    """
    current_time = time.time()
    
    # Check if we have valid cache for this data type
    if data_type in cache:
        cache_entry = cache[data_type]
        if (cache_entry['data'] is not None and 
            current_time - cache_entry['timestamp'] < CACHE_TTL):
            cache_age = int(current_time - cache_entry['timestamp'])
            app.logger.info(f"Using cached data for {data_type} (age: {cache_age}s, items: {len(cache_entry['data'])})")
            return cache_entry['data']
    
    # Fetch fresh data
    app.logger.info(f"Fetching fresh data for {data_type} (cache miss or expired)")
    start_time = time.time()
    data = fetch_all(data_type, custom_params)
    fetch_time = time.time() - start_time
    
    # Update cache
    if data_type in cache:
        cache[data_type] = {
            'data': data,
            'timestamp': current_time
        }
        app.logger.info(f"Cached {len(data)} items for {data_type} (fetch took {fetch_time:.2f}s)")
    
    return data

@app.route('/')
def index():
    """
    Main dashboard route - serves the index.html template
    """
    return render_template('index.html')

@app.route('/test')
def test_api():
    """
    Test route to verify API connectivity
    Returns JSON response from Bubble API
    """
    try:
        result = fetch_bubble_data('user')
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Test route error: {str(e)}")
        return jsonify({
            'error': 'Test route failed',
            'details': str(e)
        }), 500

@app.route('/api/total_users')
def api_total_users():
    """
    API endpoint to get total count of users
    Returns: JSON with total_users count
    """
    try:
        total = get_total_count('user')
        return jsonify({'total_users': total})
    except Exception as e:
        app.logger.error(f"Error in /api/total_users: {str(e)}")
        return jsonify({'total_users': 0, 'error': str(e)}), 500

@app.route('/api/total_conversations')
def api_total_conversations():
    """
    API endpoint to get total count of conversations
    Returns: JSON with total_conversations count
    """
    try:
        total = get_total_count('conversation')
        return jsonify({'total_conversations': total})
    except Exception as e:
        app.logger.error(f"Error in /api/total_conversations: {str(e)}")
        return jsonify({'total_conversations': 0, 'error': str(e)}), 500

@app.route('/api/total_messages')
def api_total_messages():
    """
    API endpoint to get total count of messages
    Returns: JSON with total_messages count
    """
    try:
        total = get_total_count('message')
        return jsonify({'total_messages': total})
    except Exception as e:
        app.logger.error(f"Error in /api/total_messages: {str(e)}")
        return jsonify({'total_messages': 0, 'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """
    API endpoint to get basic statistics for the dashboard
    Returns: JSON with users, conversations, messages counts and any API errors
    """
    try:
        from database_queries import get_statistics
        
        # Try to get stats from database first
        stats = get_statistics()
        
        # If database is empty, fall back to API
        if stats['users'] == 0 and stats['conversations'] == 0:
            app.logger.info("Database empty, using API fallback for stats")
            # Initialize response with default values
            stats = {
                'users': 0,
                'conversations': 0,
                'messages': 0,
                'users_error': None,
                'conversations_error': None,
                'messages_error': None
            }
            
            # Get user count
            try:
                stats['users'] = get_total_count('user')
            except Exception as e:
                app.logger.error(f"Error getting user count: {str(e)}")
                stats['users_error'] = str(e)
            
            # Get conversation count
            try:
                stats['conversations'] = get_total_count('conversation')
            except Exception as e:
                app.logger.error(f"Error getting conversation count: {str(e)}")
                stats['conversations_error'] = str(e)
            
            # Get message count (only user messages)
            try:
                stats['messages'] = get_total_count('message', filter_user_messages=True)
            except Exception as e:
                app.logger.error(f"Error getting message count: {str(e)}")
                stats['messages_error'] = str(e)
        
        app.logger.info(f"Stats API response: {stats}")
        return jsonify(stats)
        
    except Exception as e:
        app.logger.error(f"Error in /api/stats: {str(e)}")
        return jsonify({
            'users': 0,
            'conversations': 0,
            'messages': 0,
            'users_error': str(e),
            'conversations_error': str(e),
            'messages_error': str(e)
        }), 500

@app.route('/api/metrics')
def api_metrics_with_db():
    """
    API endpoint to compute and return usage metrics
    Returns comprehensive metrics including counts, averages, and distributions
    """
    try:
        # Get total counts
        total_users = get_total_count('user')
        total_conversations = get_total_count('conversation')
        total_messages = get_total_count('message', filter_user_messages=True)  # Only count user messages
        
        # Initialize metrics dictionary
        metrics = {
            'total_users': total_users,
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'avg_messages_per_conv': 0,
            'convs_per_course': {},
            'convs_per_assignment': {},
            # Feature counts
            'quiz_count': 0,
            'review_count': 0,
            'takeaway_count': 0,
            'simplify_count': 0,
            'study_count': 0,
            'motivate_count': 0
        }
        
        # Calculate average messages per conversation
        all_messages = []  # Initialize to avoid unbound variable
        if total_conversations > 0:
            # If we have too many messages, use simple average
            if total_messages > 10000:
                metrics['avg_messages_per_conv'] = round(total_messages / total_conversations, 2)
                app.logger.info(f"Using simple average for messages per conversation: {metrics['avg_messages_per_conv']}")
            else:
                # Fetch all messages (we'll filter manually for both legacy and new fields)
                try:
                    all_messages = fetch_all('message')
                    if all_messages:
                        # Filter for user messages using both legacy and new fields
                        # then group by conversation ID
                        messages_by_conv = Counter()
                        for message in all_messages:
                            # Check new field (role_option_message_role = 'user')
                            new_role = message.get('role_option_message_role')
                            # Check legacy field (role = 'user' or role != 'assistant')
                            legacy_role = message.get('role')
                            
                            # Count if new field is 'user' OR legacy field is 'user' OR legacy field is not 'assistant'
                            if new_role == 'user' or legacy_role == 'user' or (legacy_role and legacy_role != 'assistant'):
                                conv_id = message.get('conversation', message.get('conversation_id'))
                                if conv_id:
                                    messages_by_conv[conv_id] += 1
                        
                        # Calculate average
                        if messages_by_conv:
                            avg = sum(messages_by_conv.values()) / len(messages_by_conv)
                            metrics['avg_messages_per_conv'] = round(avg, 2)
                            app.logger.info(f"Calculated average messages per conversation: {metrics['avg_messages_per_conv']}")
                        else:
                            metrics['avg_messages_per_conv'] = 0
                    else:
                        # If fetch failed but we have totals, use simple average
                        metrics['avg_messages_per_conv'] = round(total_messages / total_conversations, 2) if total_conversations > 0 else 0
                except Exception as e:
                    app.logger.warning(f"Error fetching messages for average calculation: {str(e)}")
                    metrics['avg_messages_per_conv'] = round(total_messages / total_conversations, 2) if total_conversations > 0 else 0
        
        # Fetch all conversations for grouping by course and assignment
        all_conversations = fetch_all('conversation')
        if all_conversations:
            # Group conversations by course
            course_counter = Counter()
            assignment_counter = Counter()
            
            # Initialize feature counters
            feature_counters = {
                'quiz_count': 0,
                'review_count': 0,
                'takeaway_count': 0,
                'simplify_count': 0,
                'study_count': 0,
                'motivate_count': 0
            }
            
            # Get conversation starter data to identify activity types
            conversation_starters = fetch_all('conversation_starter')
            starter_activity_map = {}
            
            if conversation_starters:
                for starter in conversation_starters:
                    starter_id = starter.get('_id')
                    title_text = starter.get('title_text', '').lower()
                    
                    if starter_id and title_text:
                        starter_activity_map[starter_id] = title_text
                        
            app.logger.info(f"Found {len(starter_activity_map)} conversation starters with activity mappings")
            
            # Fetch course data for proper naming in metrics
            all_courses = fetch_all('course')
            course_name_map = {}
            
            if all_courses:
                for course in all_courses:
                    course_id = course.get('_id')
                    # Use course number (name_text) as primary identifier
                    # This will show like "CPCU 551" instead of "Managing Commercial Property Risk"
                    course_name = (course.get('name_text') or 
                                 course.get('course_name') or 
                                 course.get('full_name_text') or 
                                 course.get('name') or 
                                 course.get('title') or 
                                 f'Course {course_id[:8]}' if course_id else 'Unknown Course')
                    if course_id:
                        course_name_map[course_id] = course_name
            
            # Fetch assignment data for proper naming in metrics
            all_assignments = fetch_all('assignment')
            assignment_name_map = {}
            
            if all_assignments:
                for assignment in all_assignments:
                    assignment_id = assignment.get('_id')
                    # Priority order: assignment_name_text > name_text > assignment_name > name > title > fallback
                    assignment_name = (assignment.get('assignment_name_text') or 
                                     assignment.get('name_text') or 
                                     assignment.get('assignment_name') or 
                                     assignment.get('name') or 
                                     assignment.get('title') or 
                                     f'Assignment {assignment_id[:8]}' if assignment_id else 'Unknown Assignment')
                    if assignment_id:
                        assignment_name_map[assignment_id] = assignment_name
            
            for conv in all_conversations:
                # Count by course field (using course_custom_variable_parent as primary field)
                course_id = conv.get('course_custom_variable_parent', 
                                   conv.get('course', 
                                          conv.get('course_id', 
                                                 conv.get('Course'))))
                if course_id:
                    course_name = course_name_map.get(course_id, f'Course {course_id[:8]}')
                    course_counter[course_name] += 1
                
                # Count by assignment field (using assignment_custom_variable_parent as primary field)
                assignment_id = conv.get('assignment_custom_variable_parent',
                                       conv.get('assignment', 
                                              conv.get('assignment_id', 
                                                     conv.get('Assignment'))))
                if assignment_id:
                    assignment_name = assignment_name_map.get(assignment_id, f'Assignment {assignment_id[:8]}')
                    assignment_counter[assignment_name] += 1
                
                # Count by activity type based on conversation starter
                starter_id = conv.get('conversation_starter_custom_conversation_starter', 
                                   conv.get('conversation_starter', 
                                          conv.get('starter_id')))
                
                if starter_id and starter_id in starter_activity_map:
                    activity = starter_activity_map[starter_id]
                    
                    # Map activity names to counter keys based on title_text
                    if activity == 'quiz me':
                        feature_counters['quiz_count'] += 1
                    elif activity == 'review terms':
                        feature_counters['review_count'] += 1
                    elif activity == 'key takeaways':
                        feature_counters['takeaway_count'] += 1
                    elif activity == 'simplify a concept':
                        feature_counters['simplify_count'] += 1
                    elif activity == 'study hacks':
                        feature_counters['study_count'] += 1
                    elif activity == 'motivate me':
                        feature_counters['motivate_count'] += 1
                    else:
                        app.logger.debug(f"Unknown activity type: {activity}")
            
            # Update metrics with feature counts
            metrics.update(feature_counters)
            
            # Convert counters to dictionaries
            metrics['convs_per_course'] = dict(course_counter)
            metrics['convs_per_assignment'] = dict(assignment_counter)
            
            app.logger.info(f"Found {len(course_counter)} unique courses with conversations")
            app.logger.info(f"Found {len(assignment_counter)} unique assignments with conversations")
            app.logger.info(f"Feature counts: {feature_counters}")
        
        # Add summary statistics
        metrics['summary'] = {
            'unique_courses': len(metrics['convs_per_course']),
            'unique_assignments': len(metrics['convs_per_assignment']),
            'data_quality': 'complete' if all_conversations else 'limited'
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        app.logger.error(f"Error in /api/metrics: {str(e)}")
        # Return gracefully formatted error response
        return jsonify({
            'total_users': 0,
            'total_conversations': 0,
            'total_messages': 0,
            'avg_messages_per_conv': 0,
            'convs_per_course': {},
            'convs_per_assignment': {},
            'error': str(e),
            'summary': {'data_quality': 'error'}
        }), 500

@app.route('/api/chart/sessions-by-date-db')
def api_chart_sessions_by_date_db():
    """Database version of sessions by date chart"""
    try:
        from database_queries import get_date_chart_data
        
        # Get query parameters
        days = request.args.get('days', default=30, type=int)
        grouping = request.args.get('grouping', default='days', type=str)
        
        data = get_date_chart_data(days, grouping)
        
        app.logger.info(f"Generated date chart data: {len(data['labels'])} days, {data['total']} total sessions")
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Error in /api/chart/sessions-by-date-db: {str(e)}")
        return jsonify({'labels': [], 'data': [], 'error': str(e)}), 500

@app.route('/api/chart/sessions-by-date')
def api_chart_sessions_by_date():
    """
    API endpoint to get sessions grouped by date for line chart
    Supports date range filtering: 7, 30, or 90 days
    Supports grouping by: days, weeks, months
    """
    try:
        # Get parameters
        days = int(request.args.get('days', 30))
        grouping = request.args.get('grouping', 'days')  # days, weeks, months
        
        # Fetch all conversations with caching
        all_conversations = fetch_all_cached('conversation')
        if not all_conversations:
            return jsonify({'labels': [], 'data': []})
        
        # Fetch user data to filter out excluded emails with caching
        all_users = fetch_all_cached('user')
        user_email_map = {}
        
        if all_users:
            for user in all_users:
                user_id = user.get('_id')
                user_email = user.get('email', user.get('authentication', {}).get('email', {}).get('email', ''))
                if user_id and user_email:
                    user_email_map[user_id] = user_email
        
        # Filter conversations to exclude certain email domains
        filtered_conversations = []
        for conv in all_conversations:
            user_id = conv.get('user', conv.get('user_id'))
            user_email = conv.get('user_email_text', user_email_map.get(user_id, ''))
            
            if not is_excluded_email(user_email):
                filtered_conversations.append(conv)
        
        all_conversations = filtered_conversations
        
        from datetime import datetime, timedelta
        from collections import defaultdict
        import calendar
        
        # Calculate start date
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Group conversations by date with specified grouping
        date_counts = defaultdict(int)
        
        for conv in all_conversations:
            created_date_str = conv.get('Created Date')
            if created_date_str:
                try:
                    # Parse the date (assuming ISO format like 2025-08-05T19:11:20.107Z)
                    created_date = datetime.fromisoformat(created_date_str.replace('Z', '+00:00'))
                    created_date = created_date.replace(tzinfo=None)  # Remove timezone for comparison
                    
                    # Only include dates within range
                    if start_date <= created_date <= end_date:
                        if grouping == 'days':
                            date_key = created_date.strftime('%Y-%m-%d')
                        elif grouping == 'weeks':
                            # Get Monday of the week (ISO week)
                            week_start = created_date - timedelta(days=created_date.weekday())
                            date_key = week_start.strftime('%Y-%m-%d')
                        elif grouping == 'months':
                            date_key = created_date.strftime('%Y-%m')
                        else:
                            date_key = created_date.strftime('%Y-%m-%d')  # fallback to days
                        
                        date_counts[date_key] += 1
                except (ValueError, TypeError) as e:
                    app.logger.debug(f"Failed to parse date {created_date_str}: {e}")
                    continue
        
        # Generate complete date range with appropriate intervals
        labels = []
        data = []
        
        if grouping == 'days':
            current_date = start_date
            while current_date <= end_date:
                date_key = current_date.strftime('%Y-%m-%d')
                labels.append(date_key)
                data.append(date_counts.get(date_key, 0))
                current_date += timedelta(days=1)
                
        elif grouping == 'weeks':
            # Start from Monday of start_date week
            current_date = start_date - timedelta(days=start_date.weekday())
            while current_date <= end_date:
                date_key = current_date.strftime('%Y-%m-%d')
                week_end = current_date + timedelta(days=6)
                if current_date >= start_date:  # Only include weeks that overlap with our range
                    labels.append(f"{current_date.strftime('%b %d')} - {week_end.strftime('%b %d')}")
                    data.append(date_counts.get(date_key, 0))
                current_date += timedelta(weeks=1)
                
        elif grouping == 'months':
            current_date = start_date.replace(day=1)  # Start from first day of month
            while current_date <= end_date:
                date_key = current_date.strftime('%Y-%m')
                labels.append(current_date.strftime('%B %Y'))
                data.append(date_counts.get(date_key, 0))
                
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
        
        app.logger.info(f"Generated date chart data: {len(labels)} {grouping}, {sum(data)} total sessions")
        return jsonify({
            'labels': labels,
            'data': data,
            'total_sessions': sum(data),
            'grouping': grouping
        })
        
    except Exception as e:
        app.logger.error(f"Error in /api/chart/sessions-by-date: {str(e)}")
        return jsonify({'labels': [], 'data': [], 'error': str(e)}), 500

@app.route('/api/chart/sessions-by-course')
def api_chart_sessions_by_course():
    """
    API endpoint to get sessions grouped by course for bar chart
    """
    try:
        # Fetch all conversations with caching
        all_conversations = fetch_all_cached('conversation')
        if not all_conversations:
            return jsonify({'labels': [], 'data': []})
        
        # Fetch user data to filter out excluded emails with caching
        all_users = fetch_all_cached('user')
        user_email_map = {}
        
        if all_users:
            for user in all_users:
                user_id = user.get('_id')
                user_email = user.get('email', user.get('authentication', {}).get('email', {}).get('email', ''))
                if user_id and user_email:
                    user_email_map[user_id] = user_email
        
        # Filter conversations to exclude certain email domains
        filtered_conversations = []
        for conv in all_conversations:
            user_id = conv.get('user', conv.get('user_id'))
            user_email = conv.get('user_email_text', user_email_map.get(user_id, ''))
            
            if not is_excluded_email(user_email):
                filtered_conversations.append(conv)
        
        all_conversations = filtered_conversations
        
        # Fetch course data to get course names with caching
        all_courses = fetch_all_cached('course')
        course_name_map = {}
        
        if all_courses:
            for course in all_courses:
                course_id = course.get('_id')
                # Use course number (name_text) instead of full name for charts
                # This will show like "CPCU 551" instead of "Managing Commercial Property Risk"
                course_name = (course.get('name_text') or 
                             course.get('course_name') or 
                             course.get('full_name_text') or 
                             course.get('name') or 
                             course.get('title') or 
                             f'Course {course_id[:8]}' if course_id else 'Unknown Course')
                if course_id:
                    course_name_map[course_id] = course_name
        
        # Group conversations by course
        from collections import Counter
        course_counter = Counter()
        
        for conv in all_conversations:
            course_id = conv.get('course_custom_variable_parent', 
                              conv.get('course', 
                                     conv.get('course_id')))
            if course_id:
                course_name = course_name_map.get(course_id, f'Course {course_id[:8]}')
                course_counter[course_name] += 1
        
        # Sort by count (descending) and limit to top 10
        sorted_courses = course_counter.most_common(10)
        
        labels = [course[0] for course in sorted_courses]
        data = [course[1] for course in sorted_courses]
        
        app.logger.info(f"Generated course chart data: {len(labels)} courses, {sum(data)} total sessions")
        return jsonify({
            'labels': labels,
            'data': data,
            'total_sessions': sum(data)
        })
        
    except Exception as e:
        app.logger.error(f"Error in /api/chart/sessions-by-course: {str(e)}")
        return jsonify({'labels': [], 'data': [], 'error': str(e)}), 500

@app.route('/api/chart/sessions-by-assignment')
def api_chart_sessions_by_assignment():
    """
    API endpoint for Sessions by Assignment chart data.
    Returns assignment names and session counts.
    """
    try:
        # Get all conversations
        all_conversations = fetch_all('conversation')
        if not all_conversations:
            return jsonify({'labels': [], 'data': [], 'total_sessions': 0})
        
        # Fetch assignment data for proper naming
        all_assignments = fetch_all('assignment')
        assignment_name_map = {}
        
        if all_assignments:
            for assignment in all_assignments:
                assignment_id = assignment.get('_id')
                # Priority order: assignment_name_text > name_text > assignment_name > name > title > fallback
                assignment_name = (assignment.get('assignment_name_text') or 
                                 assignment.get('name_text') or 
                                 assignment.get('assignment_name') or 
                                 assignment.get('name') or 
                                 assignment.get('title') or 
                                 f'Assignment {assignment_id[:8]}' if assignment_id else 'Unknown Assignment')
                if assignment_id:
                    assignment_name_map[assignment_id] = assignment_name
        
        # Count conversations by assignment
        assignment_counter = Counter()
        
        for conv in all_conversations:
            # Get assignment ID (using assignment_custom_variable_parent as primary field)
            assignment_id = conv.get('assignment_custom_variable_parent',
                                   conv.get('assignment', 
                                          conv.get('assignment_id', 
                                                 conv.get('Assignment'))))
            if assignment_id:
                assignment_name = assignment_name_map.get(assignment_id, f'Assignment {assignment_id[:8]}')
                assignment_counter[assignment_name] += 1
        
        # Sort by count (descending) and get top assignments
        sorted_assignments = sorted(assignment_counter.items(), key=lambda x: x[1], reverse=True)
        
        # Get labels and data
        labels = [assignment[0] for assignment in sorted_assignments]
        data = [assignment[1] for assignment in sorted_assignments]
        
        app.logger.info(f"Generated assignment chart data: {len(labels)} assignments, {sum(data)} total sessions")
        return jsonify({
            'labels': labels,
            'data': data,
            'total_sessions': sum(data)
        })
        
    except Exception as e:
        app.logger.error(f"Error in /api/chart/sessions-by-assignment: {str(e)}")
        return jsonify({'labels': [], 'data': [], 'error': str(e)}), 500

@app.route('/api/chart/sessions-by-activity')
def api_chart_sessions_by_activity():
    """
    API endpoint to get sessions grouped by activity type for bar chart
    """
    try:
        # Get feature counts from metrics calculation
        # This reuses the logic from /api/metrics
        all_conversations = fetch_all_cached('conversation')
        if not all_conversations:
            return jsonify({'labels': [], 'data': []})
        
        # Fetch user data to filter out excluded emails
        all_users = fetch_all_cached('user')
        user_email_map = {}
        
        if all_users:
            for user in all_users:
                user_id = user.get('_id')
                user_email = user.get('email', user.get('authentication', {}).get('email', {}).get('email', ''))
                if user_id and user_email:
                    user_email_map[user_id] = user_email
        
        # Filter conversations to exclude certain email domains
        filtered_conversations = []
        for conv in all_conversations:
            user_id = conv.get('user', conv.get('user_id'))
            user_email = conv.get('user_email_text', user_email_map.get(user_id, ''))
            
            if not is_excluded_email(user_email):
                filtered_conversations.append(conv)
        
        all_conversations = filtered_conversations
        
        # Get conversation starter data with caching
        conversation_starters = fetch_all_cached('conversation_starter')
        starter_activity_map = {}
        
        if conversation_starters:
            for starter in conversation_starters:
                starter_id = starter.get('_id')
                title_text = starter.get('title_text', '').lower()
                
                if starter_id and title_text:
                    starter_activity_map[starter_id] = title_text
        
        # Initialize feature counters
        feature_counters = {
            'Quiz Me': 0,
            'Review Terms': 0,
            'Key Takeaways': 0,
            'Simplify a Concept': 0,
            'Study Hacks': 0,
            'Motivate Me': 0
        }
        
        # Count by activity type
        for conv in all_conversations:
            starter_id = conv.get('conversation_starter_custom_conversation_starter', 
                               conv.get('conversation_starter', 
                                      conv.get('starter_id')))
            
            if starter_id and starter_id in starter_activity_map:
                activity = starter_activity_map[starter_id]
                
                # Map activity names to display names
                if activity == 'quiz me':
                    feature_counters['Quiz Me'] += 1
                elif activity == 'review terms':
                    feature_counters['Review Terms'] += 1
                elif activity == 'key takeaways':
                    feature_counters['Key Takeaways'] += 1
                elif activity == 'simplify a concept':
                    feature_counters['Simplify a Concept'] += 1
                elif activity == 'study hacks':
                    feature_counters['Study Hacks'] += 1
                elif activity == 'motivate me':
                    feature_counters['Motivate Me'] += 1
        
        # Sort by count (descending)
        sorted_activities = sorted(feature_counters.items(), key=lambda x: x[1], reverse=True)
        
        labels = [activity[0] for activity in sorted_activities]
        data = [activity[1] for activity in sorted_activities]
        
        app.logger.info(f"Generated activity chart data: {len(labels)} activities, {sum(data)} total sessions")
        return jsonify({
            'labels': labels,
            'data': data,
            'total_sessions': sum(data)
        })
        
    except Exception as e:
        app.logger.error(f"Error in /api/chart/sessions-by-activity: {str(e)}")
        return jsonify({'labels': [], 'data': [], 'error': str(e)}), 500

@app.route('/api/conversations')
def api_conversations_with_db():
    """
    API endpoint to fetch all conversations sorted by Created Date
    Returns list of conversation objects with key fields
    Supports filtering by email, course_number, and date range
    """
    try:
        # Get filter parameters from query string
        email = request.args.get('email')
        course_number = request.args.get('course_number')
        date_start = request.args.get('date_start')
        date_end = request.args.get('date_end')
        
        # Build base params
        params = {
            'sort_field': 'Created Date',
            'descending': 'true'
        }
        
        # Build constraints if filters are provided
        constraints = []
        
        # Email filter - will need to match against user field
        if email:
            constraints.append({
                "key": "user_email_text",
                "constraint_type": "text contains",
                "value": email
            })
        
        # Course number filter
        if course_number:
            constraints.append({
                "key": "course_number_text",
                "constraint_type": "text contains", 
                "value": course_number
            })
        
        # Date range filters
        if date_start:
            constraints.append({
                "key": "Created Date",
                "constraint_type": "greater than",
                "value": f"{date_start}T00:00:00.000Z"
            })
        
        if date_end:
            constraints.append({
                "key": "Created Date",
                "constraint_type": "less than",
                "value": f"{date_end}T23:59:59.999Z"
            })
        
        # Add constraints to params if they exist
        if constraints:
            params['constraints'] = json.dumps(constraints)
        
        # Fetch all conversations with sorting and optional filters
        conversations = fetch_all('conversation', params)
        
        # Fetch course data for proper naming in conversation list
        all_courses = fetch_all('course')
        course_name_map = {}
        
        if all_courses:
            for course in all_courses:
                course_id = course.get('_id')
                # Priority order: full_name_text > course_name > name_text > name > title > fallback
                course_name = (course.get('full_name_text') or 
                             course.get('course_name') or 
                             course.get('name_text') or 
                             course.get('name') or 
                             course.get('title') or 
                             f'Course {course_id[:8]}' if course_id else 'Unknown Course')
                if course_id:
                    course_name_map[course_id] = course_name
        
        # Fetch assignment data for proper naming in conversation list
        all_assignments = fetch_all('assignment')
        assignment_name_map = {}
        
        if all_assignments:
            for assignment in all_assignments:
                assignment_id = assignment.get('_id')
                # Priority order: assignment_name_text > name_text > assignment_name > name > title > fallback
                assignment_name = (assignment.get('assignment_name_text') or 
                                 assignment.get('name_text') or 
                                 assignment.get('assignment_name') or 
                                 assignment.get('name') or 
                                 assignment.get('title') or 
                                 f'Assignment {assignment_id[:8]}' if assignment_id else 'Unknown Assignment')
                if assignment_id:
                    assignment_name_map[assignment_id] = assignment_name
        
        # Fetch user data to get email addresses
        all_users = fetch_all('user')
        user_email_map = {}
        
        if all_users:
            for user in all_users:
                user_id = user.get('_id')
                user_email = user.get('email', user.get('authentication', {}).get('email', {}).get('email', ''))
                if user_id and user_email:
                    user_email_map[user_id] = user_email
        
        # Extract key fields from each conversation
        result = []
        for conv in conversations:
            # Get user ID and email
            user_id = conv.get('user', conv.get('user_id'))
            user_email = conv.get('user_email_text', user_email_map.get(user_id, ''))
            
            # Filter out entries from excluded domains
            if is_excluded_email(user_email):
                app.logger.debug(f"Filtering out conversation from {user_email}")
                continue
            
            # Get course ID and map it to proper course name
            course_id = conv.get('course_custom_variable_parent', 
                               conv.get('course', 
                                      conv.get('course_id')))
            course_name = course_name_map.get(course_id, f'Course {course_id[:8]}' if course_id else 'Unknown Course')
            
            # Get course number if available
            course_number = conv.get('course_number_text', '')
            if not course_number and course_id in all_courses:
                for course in all_courses:
                    if course.get('_id') == course_id:
                        course_number = course.get('course_number', course.get('number', ''))
                        break
            
            # Get assignment ID and map it to proper assignment name
            assignment_id = conv.get('assignment_custom_variable_parent',
                                   conv.get('assignment', 
                                          conv.get('assignment_id')))
            assignment_name = assignment_name_map.get(assignment_id, f'Assignment {assignment_id[:8]}' if assignment_id else 'Unknown Assignment')
            
            # Get message count (this would need to be fetched separately if not in conversation)
            message_count = conv.get('message_count', conv.get('messages_count', 0))
            
            result.append({
                '_id': conv.get('_id'),
                'Created Date': conv.get('Created Date'),
                'user': user_id,
                'user_email': user_email,
                'assignment': assignment_name,  # Use assignment name instead of ID
                'assignment_id': assignment_id,  # Keep original ID for reference
                'course': course_name,  # Use course name instead of ID
                'course_id': course_id,  # Keep original ID for reference
                'course_number': course_number,
                'message_count': message_count,
                'status': conv.get('status', 'active'),
                'last_message': conv.get('last_message', '')
            })
        
        app.logger.info(f"Successfully fetched {len(result)} conversations (filtered: {bool(constraints)})")
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error in /api/conversations: {str(e)}")
        # Return empty list instead of error to avoid frontend crashes
        return jsonify([])

@app.route('/api/conversation/<conv_id>')
def api_conversation_messages(conv_id):
    """
    API endpoint to fetch messages for a specific conversation
    Returns list of messages sorted by Created Date
    Optionally filter for user messages only with ?user_only=true
    """
    try:
        # Check if we should filter for user messages only
        user_only = request.args.get('user_only', '').lower() == 'true'
        
        # Create constraint to filter messages by conversation ID
        constraints = [{
            'key': 'conversation',
            'constraint_type': 'equals',
            'value': conv_id
        }]
        
        # Add role filter if user_only is requested
        if user_only:
            constraints.append({
                'key': 'role',
                'constraint_type': 'equals',
                'value': 'user'
            })
        
        # Convert constraints to JSON string
        params = {
            'constraints': json.dumps(constraints),
            'sort_field': 'Created Date',
            'descending': 'false'  # Ascending order for messages (oldest first)
        }
        
        # Fetch all messages for this conversation
        messages = fetch_all('message', params)
        
        # Extract key fields from each message
        result = []
        user_message_count = 0
        for msg in messages:
            role = msg.get('role', msg.get('sender_type', 'user'))
            if role == 'user':
                user_message_count += 1
            result.append({
                '_id': msg.get('_id'),
                'text': msg.get('text', msg.get('content', '')),
                'role': role,
                'Created Date': msg.get('Created Date'),
                'conversation': msg.get('conversation', conv_id),
                'user': msg.get('user', msg.get('user_id'))
            })
        
        app.logger.info(f"Successfully fetched {len(result)} messages for conversation {conv_id} (user_only={user_only})")
        return jsonify({
            'conversation_id': conv_id,
            'message_count': len(result),
            'user_message_count': user_message_count,
            'messages': result
        })
        
    except Exception as e:
        app.logger.error(f"Error in /api/conversation/{conv_id}: {str(e)}")
        # Return empty messages list instead of error to avoid frontend crashes
        return jsonify({
            'conversation_id': conv_id,
            'message_count': 0,
            'messages': []
        })

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """Endpoint to trigger a data refresh from Bubble API and sync to database"""
    try:
        from sync_manager import BubbleSyncManager
        from models import SyncStatus
        
        # Check if this is the first sync (no data in database)
        sync_statuses = SyncStatus.query.all()
        is_first_sync = len(sync_statuses) == 0 or all(s.last_sync_date is None for s in sync_statuses)
        
        # Create sync manager
        sync_manager = BubbleSyncManager()
        
        # Perform full sync if first time, otherwise incremental
        if is_first_sync:
            app.logger.info("Performing initial full sync")
            results = sync_manager.perform_full_sync()
        else:
            app.logger.info("Performing incremental sync")
            results = sync_manager.perform_incremental_sync()
        
        # Clear the old cache since we're using database now
        cache.clear()
        
        # Count total synced records
        total_synced = sum(r.get('count', 0) for r in results.values() if r.get('success'))
        
        app.logger.info(f"Sync completed: {results}")
        
        # Return success response
        return jsonify({
            'success': True,
            'message': f'Data sync completed. {"Initial sync" if is_first_sync else "Incremental sync"} - {total_synced} records processed',
            'results': results,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        app.logger.error(f"Error during refresh: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sync-status')
def get_sync_status():
    """Get the current sync status for all data types"""
    try:
        from database_queries import get_sync_status_all
        status = get_sync_status_all()
        return jsonify(status)
    except Exception as e:
        app.logger.error(f"Error getting sync status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    app.logger.error(f"Internal server error: {error}")
    return jsonify({
        'error': 'Internal server error',
        'details': str(error)
    }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
