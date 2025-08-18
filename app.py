"""
Assignment Assistant Dashboard - Flask Application
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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database base class
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "assignment-assistant-secret-key-2025")

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
        try:
            import models
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
else:
    logger.warning("No DATABASE_URL found, running without database")

# Simple cache
cache = {
    'conversations': {'data': None, 'timestamp': 0},
    'users': {'data': None, 'timestamp': 0},
    'courses': {'data': None, 'timestamp': 0},
    'assignments': {'data': None, 'timestamp': 0},
    'conversation_starters': {'data': None, 'timestamp': 0},
    'messages': {'data': None, 'timestamp': 0}
}

CACHE_TTL_SECONDS = 600  # 10 minutes
MAX_API_ITEMS = 2000

def fetch_bubble_data(data_type, params=None):
    """Fetch data from Bubble API with error handling"""
    api_key = os.environ.get("BUBBLE_API_KEY_LIVE")
    if not api_key:
        logger.error("No BUBBLE_API_KEY_LIVE found in environment")
        return {
            'error': 'Missing API key',
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
            logger.error(f"Bubble API error for {data_type}: {response.status_code}")
            return {
                'error': f'API request failed',
                'results': [],
                'count': 0,
                'remaining': 0
            }
            
    except Exception as e:
        logger.error(f"Exception fetching {data_type}: {str(e)}")
        return {'error': 'Request failed', 'results': [], 'count': 0, 'remaining': 0}

def get_total_count(data_type):
    """Get total count for a data type"""
    try:
        params = {'limit': 1, 'cursor': 0}
        data = fetch_bubble_data(data_type, params)
        
        if 'error' in data:
            return 0
            
        return int(data.get('count', 0)) + int(data.get('remaining', 0))
        
    except Exception as e:
        logger.error(f"Exception in get_total_count for {data_type}: {str(e)}")
        return 0

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index template: {e}")
        return f"<h1>Assignment Assistant Dashboard</h1><p>Error loading template: {e}</p>", 500

@app.route('/api/stats')
def api_stats():
    """Basic statistics endpoint"""
    try:
        # Try database first if available
        if database_url:
            try:
                from database_queries import get_statistics
                stats = get_statistics()
                
                # Use API fallback if database is empty
                if stats['users'] == 0:
                    logger.info("Database empty, using API fallback for stats")
                    stats = {
                        'users': get_total_count('user'),
                        'conversations': get_total_count('conversation'),
                        'messages': get_total_count('message'),
                        'users_error': None,
                        'conversations_error': None,
                        'messages_error': None
                    }
                
                logger.info(f"Stats API response: {stats}")
                return jsonify(stats)
                
            except Exception as db_error:
                logger.error(f"Database error, falling back to API: {db_error}")
        
        # API fallback
        stats = {
            'users': get_total_count('user'),
            'conversations': get_total_count('conversation'),
            'messages': get_total_count('message'),
            'users_error': None,
            'conversations_error': None,
            'messages_error': None
        }
        
        logger.info(f"Stats API response: {stats}")
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error in /api/stats: {str(e)}")
        return jsonify({
            'users': 0,
            'conversations': 0,
            'messages': 0,
            'users_error': str(e),
            'conversations_error': str(e),
            'messages_error': str(e)
        })

@app.route('/api/metrics')
def api_metrics():
    """Comprehensive metrics endpoint"""
    try:
        # Basic counts
        metrics = {
            'total_users': get_total_count('user'),
            'total_conversations': get_total_count('conversation'),
            'total_messages': get_total_count('message'),
            'user_messages': 0,
            'unique_courses': 0,
            'unique_assignments': 0,
            'quiz_count': 0,
            'review_count': 0,
            'takeaway_count': 0,
            'simplify_count': 0,
            'study_count': 0,
            'motivate_count': 0
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error in /api/metrics: {str(e)}")
        return jsonify({
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
        })

@app.route('/api/conversations')
def api_conversations():
    """Get conversations list"""
    try:
        # Return empty list for now - can be enhanced later
        return jsonify([])
        
    except Exception as e:
        logger.error(f"Error in /api/conversations: {str(e)}")
        return jsonify([])

@app.route('/api/chart/sessions-by-date')
def api_chart_sessions_by_date():
    """Chart data for sessions by date"""
    try:
        days = int(request.args.get('days', 30))
        
        # Generate empty chart data for now
        labels = []
        data = []
        
        # Generate date labels
        end_date = datetime.now()
        for i in range(days):
            date = end_date - timedelta(days=days-1-i)
            labels.append(date.strftime('%Y-%m-%d'))
            data.append(0)  # No data for now
        
        return jsonify({
            'labels': labels,
            'data': data,
            'total': 0
        })
        
    except Exception as e:
        logger.error(f"Error in date chart: {str(e)}")
        return jsonify({'labels': [], 'data': [], 'total': 0, 'error': str(e)})

@app.route('/api/chart/sessions-by-course')
def api_chart_sessions_by_course():
    """Chart data for sessions by course"""
    try:
        return jsonify({
            'labels': [],
            'data': [],
            'total': 0
        })
        
    except Exception as e:
        logger.error(f"Error in course chart: {str(e)}")
        return jsonify({'labels': [], 'data': [], 'total': 0, 'error': str(e)})

@app.route('/api/chart/sessions-by-activity')
def api_chart_sessions_by_activity():
    """Chart data for sessions by activity"""
    try:
        return jsonify({
            'labels': [],
            'data': [],
            'total': 0
        })
        
    except Exception as e:
        logger.error(f"Error in activity chart: {str(e)}")
        return jsonify({'labels': [], 'data': [], 'total': 0, 'error': str(e)})

@app.route('/api/conversation/<conversation_id>')
def api_conversation_messages(conversation_id):
    """Get messages for a specific conversation"""
    try:
        return jsonify({
            'conversation_id': conversation_id,
            'messages': []
        })
        
    except Exception as e:
        logger.error(f"Error getting conversation messages: {str(e)}")
        return jsonify({'messages': [], 'error': str(e)})

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'connected' if database_url else 'not configured'
    })

@app.errorhandler(404)
def not_found_error(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# Import additional modules if they exist
try:
    import batch_refresh
    import incremental_sync
    import simple_refresh
    import sequential_sync
    logger.info("Additional sync modules loaded")
except ImportError as e:
    logger.info(f"Some sync modules not available: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)