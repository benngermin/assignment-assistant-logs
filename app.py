import os
import logging
import requests
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
        count = data.get('count', 0)
        remaining = data.get('remaining', 0)
        total = count + remaining
        
        app.logger.debug(f"Total count for {data_type}: {total} (count: {count}, remaining: {remaining})")
        return total
        
    except Exception as e:
        app.logger.error(f"Exception in get_total_count for {data_type}: {str(e)}")
        return 0

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
