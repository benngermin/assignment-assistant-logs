"""
Simple refresh endpoint that just clears cache and returns success
to avoid database connection issues during sync
"""
from app import app, db
from flask import jsonify
import logging

@app.route('/api/simple-refresh', methods=['POST'])
def simple_refresh():
    """Simple refresh that just clears cache without heavy sync operations"""
    try:
        # Clear any caches
        from app import cache
        cache.clear()
        
        # Get current stats quickly
        from models import User, Course, Conversation
        
        users_count = User.query.count()
        courses_count = Course.query.count()
        conversations_count = Conversation.query.count()
        
        app.logger.info(f"Simple refresh - Users: {users_count}, Courses: {courses_count}, Conversations: {conversations_count}")
        
        return jsonify({
            'success': True,
            'message': f'Dashboard refreshed - {users_count} users, {courses_count} courses, {conversations_count} conversations',
            'counts': {
                'users': users_count,
                'courses': courses_count,
                'conversations': conversations_count
            }
        })
        
    except Exception as e:
        app.logger.error(f"Error in simple refresh: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500