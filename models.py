import sys
import os
sys.path.insert(0, os.path.join(os.path.expanduser('~'), '.local/lib/python3.11/site-packages'))

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import json

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    conversations = db.relationship('Conversation', backref='user', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Conversation(db.Model):
    __tablename__ = 'conversations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    employee_type = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(200), default='')
    messages_json = db.Column(db.Text, default='[]')
    message_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    @property
    def messages(self):
        try:
            return json.loads(self.messages_json or '[]')
        except json.JSONDecodeError:
            return []

    @messages.setter
    def messages(self, value):
        self.messages_json = json.dumps(value, ensure_ascii=False)
        self.message_count = len(value)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'employee_type': self.employee_type,
            'title': self.title,
            'messages': self.messages,
            'message_count': self.message_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def to_summary(self):
        """轻量摘要（列表用，不含完整消息）"""
        msgs = self.messages
        preview = ''
        if msgs:
            last = msgs[-1]
            preview = last.get('content', '')[:80]
        return {
            'id': self.id,
            'employee_type': self.employee_type,
            'title': self.title or preview,
            'message_count': self.message_count,
            'preview': preview,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Lead(db.Model):
    __tablename__ = 'leads'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    company = db.Column(db.String(200), default='')
    plan = db.Column(db.String(100), default='')
    message = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='new', index=True)  # new/contacted/converted/closed
    source = db.Column(db.String(50), default='website')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'company': self.company,
            'plan': self.plan,
            'message': self.message,
            'status': self.status,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
