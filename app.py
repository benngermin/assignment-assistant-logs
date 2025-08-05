import os
import logging
import json
import requests
from collections import Counter
from flask import Flask, render_template, jsonify

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

def fetch_bubble_data(data_type, params=None):
    """
    Fetch data from Bubble API
    
    Args:
        data_type (str): The type of data to fetch from the API
        params (dict): Optional query parameters
        
    Returns:
        dict: JSON response from API or error information
    """
    url = f'https://assignmentassistants.theinstituteslab.org/version-test/api/1.1/obj/{data_type}'
    headers = {
        'Authorization': 'Bearer 7c62e2d827655cd29e3f06a971748',
        'Content-Type': 'application/json'
    }
    
    try:
        app.logger.debug(f"Making API request to: {url}")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            json_data = response.json()
            app.logger.debug(f"API response received: {json_data}")
            return json_data.get('response', json_data)
        else:
            app.logger.error(f"API request failed with status {response.status_code}: {response.text}")
            return {
                'error': f'API request failed with status {response.status_code}',
                'details': response.text
            }
            
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Request exception: {str(e)}")
        return {
            'error': 'Failed to connect to Bubble API',
            'details': str(e)
        }
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return {
            'error': 'Unexpected error occurred',
            'details': str(e)
        }

def get_total_count(data_type):
    """
    Get the total count of items for a specific data type from Bubble API
    Using pagination to handle large datasets
    
    Args:
        data_type (str): The type of data to count
        
    Returns:
        int: Total count of items, or 0 if error
    """
    try:
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

@app.route('/api/metrics')
def api_metrics():
    """
    API endpoint to compute and return usage metrics
    Returns comprehensive metrics including counts, averages, and distributions
    """
    try:
        # Get total counts
        total_users = get_total_count('user')
        total_conversations = get_total_count('conversation')
        total_messages = get_total_count('message')
        
        # Initialize metrics dictionary
        metrics = {
            'total_users': total_users,
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'avg_messages_per_conv': 0,
            'convs_per_course': {},
            'convs_per_assignment': {}
        }
        
        # Calculate average messages per conversation
        all_messages = []  # Initialize to avoid unbound variable
        if total_conversations > 0:
            # If we have too many messages, use simple average
            if total_messages > 10000:
                metrics['avg_messages_per_conv'] = round(total_messages / total_conversations, 2)
                app.logger.info(f"Using simple average for messages per conversation: {metrics['avg_messages_per_conv']}")
            else:
                # Fetch all messages and group by conversation
                all_messages = fetch_all('message')
                if all_messages:
                    # Group messages by conversation ID
                    messages_by_conv = Counter()
                    for message in all_messages:
                        conv_id = message.get('conversation', message.get('conversation_id'))
                        if conv_id:
                            messages_by_conv[conv_id] += 1
                    
                    # Calculate average
                    if messages_by_conv:
                        avg = sum(messages_by_conv.values()) / len(messages_by_conv)
                        metrics['avg_messages_per_conv'] = round(avg, 2)
                        app.logger.info(f"Calculated average messages per conversation: {metrics['avg_messages_per_conv']}")
                else:
                    # If fetch failed but we have totals, use simple average
                    metrics['avg_messages_per_conv'] = round(total_messages / total_conversations, 2) if total_conversations > 0 else 0
        
        # Fetch all conversations for grouping by course and assignment
        all_conversations = fetch_all('conversation')
        if all_conversations:
            # Group conversations by course
            course_counter = Counter()
            assignment_counter = Counter()
            
            for conv in all_conversations:
                # Count by course field (assuming it exists as reference ID)
                course_id = conv.get('course', conv.get('course_id', conv.get('Course')))
                if course_id:
                    course_counter[str(course_id)] += 1
                
                # Count by assignment field
                assignment_id = conv.get('assignment', conv.get('assignment_id', conv.get('Assignment')))
                if assignment_id:
                    assignment_counter[str(assignment_id)] += 1
            
            # Convert counters to dictionaries
            metrics['convs_per_course'] = dict(course_counter)
            metrics['convs_per_assignment'] = dict(assignment_counter)
            
            app.logger.info(f"Found {len(course_counter)} unique courses with conversations")
            app.logger.info(f"Found {len(assignment_counter)} unique assignments with conversations")
        
        # Add summary statistics
        metrics['summary'] = {
            'unique_courses': len(metrics['convs_per_course']),
            'unique_assignments': len(metrics['convs_per_assignment']),
            'data_quality': 'complete' if all_conversations or all_messages else 'limited'
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

@app.route('/api/conversations')
def api_conversations():
    """
    API endpoint to fetch all conversations sorted by Created Date
    Returns list of conversation objects with key fields
    Supports filtering by user_id and course_id
    """
    try:
        # Get filter parameters from query string
        user_id = request.args.get('user_id')
        course_id = request.args.get('course_id')
        
        # Build base params
        params = {
            'sort_field': 'Created Date',
            'descending': 'true'
        }
        
        # Build constraints if filters are provided
        constraints = []
        if user_id:
            constraints.append({
                "key": "user",
                "constraint_type": "equals",
                "value": user_id
            })
        if course_id:
            constraints.append({
                "key": "course",
                "constraint_type": "equals", 
                "value": course_id
            })
        
        # Add constraints to params if they exist
        if constraints:
            params['constraints'] = json.dumps(constraints)
        
        # Fetch all conversations with sorting and optional filters
        conversations = fetch_all('conversation', params)
        
        # Extract key fields from each conversation
        result = []
        for conv in conversations:
            result.append({
                '_id': conv.get('_id'),
                'Created Date': conv.get('Created Date'),
                'user': conv.get('user', conv.get('user_id')),
                'assignment': conv.get('assignment', conv.get('assignment_id')),
                'course': conv.get('course', conv.get('course_id')),
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
    """
    try:
        # Create constraint to filter messages by conversation ID
        constraints = [{
            'key': 'conversation',
            'constraint_type': 'equals',
            'value': conv_id
        }]
        
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
        for msg in messages:
            result.append({
                '_id': msg.get('_id'),
                'text': msg.get('text', msg.get('content', '')),
                'role': msg.get('role', msg.get('sender_type', 'user')),
                'Created Date': msg.get('Created Date'),
                'conversation': msg.get('conversation', conv_id),
                'user': msg.get('user', msg.get('user_id'))
            })
        
        app.logger.info(f"Successfully fetched {len(result)} messages for conversation {conv_id}")
        return jsonify({
            'conversation_id': conv_id,
            'message_count': len(result),
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
