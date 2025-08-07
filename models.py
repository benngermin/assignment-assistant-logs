from app import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(100), primary_key=True)  # Bubble ID
    email = db.Column(db.String(255))
    user_signed_up = db.Column(db.Boolean, default=False)
    role_option_roles = db.Column(db.String(100))
    is_company_opted_out = db.Column(db.Boolean, default=False)
    has_seen_tooltip_tour = db.Column(db.Boolean, default=False)
    created_date = db.Column(db.DateTime)
    modified_date = db.Column(db.DateTime)
    raw_data = db.Column(db.JSON)  # Store complete Bubble response
    last_synced = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.email}>'

class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.String(100), primary_key=True)  # Bubble ID
    name = db.Column(db.String(500))
    name_text = db.Column(db.String(500))
    title = db.Column(db.String(500))
    created_date = db.Column(db.DateTime)
    modified_date = db.Column(db.DateTime)
    raw_data = db.Column(db.JSON)
    last_synced = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Course {self.name or self.title}>'

class Assignment(db.Model):
    __tablename__ = 'assignments'
    
    id = db.Column(db.String(100), primary_key=True)  # Bubble ID
    name = db.Column(db.String(500))
    name_text = db.Column(db.String(500))
    assignment_name = db.Column(db.String(500))
    assignment_name_text = db.Column(db.String(500))
    title = db.Column(db.String(500))
    course_id = db.Column(db.String(100))
    created_date = db.Column(db.DateTime)
    modified_date = db.Column(db.DateTime)
    raw_data = db.Column(db.JSON)
    last_synced = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Assignment {self.name or self.title}>'

class Conversation(db.Model):
    __tablename__ = 'conversations'
    
    id = db.Column(db.String(100), primary_key=True)  # Bubble ID
    user_id = db.Column(db.String(100))
    user_email = db.Column(db.String(255))
    course_id = db.Column(db.String(100))
    course_name = db.Column(db.String(500))
    assignment_id = db.Column(db.String(100))
    assignment_name = db.Column(db.String(500))
    conversation_starter_id = db.Column(db.String(100))
    conversation_starter_name = db.Column(db.String(500))
    message_count = db.Column(db.Integer, default=0)
    created_date = db.Column(db.DateTime)
    modified_date = db.Column(db.DateTime)
    raw_data = db.Column(db.JSON)
    last_synced = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Conversation {self.id}>'

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.String(100), primary_key=True)  # Bubble ID
    conversation_id = db.Column(db.String(100))
    role = db.Column(db.String(50))  # 'user' or 'assistant'
    role_option_message_role = db.Column(db.String(50))
    text = db.Column(db.Text)
    created_date = db.Column(db.DateTime)
    modified_date = db.Column(db.DateTime)
    raw_data = db.Column(db.JSON)
    last_synced = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Message {self.id} - {self.role}>'

class ConversationStarter(db.Model):
    __tablename__ = 'conversation_starters'
    
    id = db.Column(db.String(100), primary_key=True)  # Bubble ID
    name = db.Column(db.String(500))
    name_text = db.Column(db.String(500))
    activity_type = db.Column(db.String(100))
    created_date = db.Column(db.DateTime)
    modified_date = db.Column(db.DateTime)
    raw_data = db.Column(db.JSON)
    last_synced = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ConversationStarter {self.name}>'

class SyncStatus(db.Model):
    """Track the last sync for each data type"""
    __tablename__ = 'sync_status'
    
    id = db.Column(db.Integer, primary_key=True)
    data_type = db.Column(db.String(50), unique=True, nullable=False)
    last_sync_date = db.Column(db.DateTime)
    last_modified_date = db.Column(db.DateTime)  # Track the latest modified date we've seen
    total_records = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='pending')  # pending, syncing, completed, failed
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SyncStatus {self.data_type} - {self.status}>'