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
