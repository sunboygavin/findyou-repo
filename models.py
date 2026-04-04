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
    is_active = db.Column(db.Boolean, default=True)
    phone = db.Column(db.String(20), default='')
    company = db.Column(db.String(200), default='')
    bio = db.Column(db.Text, default='')
    last_login_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    conversations = db.relationship('Conversation', backref='user', lazy='dynamic')
    subscriptions = db.relationship('Subscription', backref='user', lazy='dynamic')
    employee_configs = db.relationship('EmployeeConfig', backref='user', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'phone': self.phone or '',
            'company': self.company or '',
            'bio': self.bio or '',
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
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
    notes = db.Column(db.Text, default='')
    contacted_by = db.Column(db.String(80), default='')
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
            'notes': self.notes or '',
            'contacted_by': self.contacted_by or '',
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Plan(db.Model):
    __tablename__ = 'plans'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # starter/professional/enterprise/flagship
    display_name = db.Column(db.String(100), nullable=False)
    price_monthly = db.Column(db.Integer, default=0)  # 单位：分
    max_employees = db.Column(db.Integer, default=1)
    max_calls_monthly = db.Column(db.Integer, default=10000)
    model_tier = db.Column(db.String(50), default='basic')  # basic/mid/premium/all
    features_json = db.Column(db.Text, default='[]')
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)

    subscriptions = db.relationship('Subscription', backref='plan', lazy='dynamic')

    @property
    def features(self):
        try:
            return json.loads(self.features_json or '[]')
        except json.JSONDecodeError:
            return []

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'price_monthly': self.price_monthly,
            'max_employees': self.max_employees,
            'max_calls_monthly': self.max_calls_monthly,
            'model_tier': self.model_tier,
            'features': self.features,
            'is_active': self.is_active,
        }


class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=False)
    status = db.Column(db.String(20), default='active', index=True)  # active/expired/cancelled
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plan': self.plan.to_dict() if self.plan else None,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }


class UsageLog(db.Model):
    __tablename__ = 'usage_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    employee_type = db.Column(db.String(50), nullable=False, index=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=True)
    tokens_in = db.Column(db.Integer, default=0)
    tokens_out = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'employee_type': self.employee_type,
            'conversation_id': self.conversation_id,
            'tokens_in': self.tokens_in,
            'tokens_out': self.tokens_out,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class EmployeeConfig(db.Model):
    __tablename__ = 'employee_configs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    employee_type = db.Column(db.String(50), nullable=False)
    tone = db.Column(db.Integer, default=50)          # 0-100 语气：严肃↔轻松
    formality = db.Column(db.Integer, default=50)      # 0-100 正式↔随意
    proactiveness = db.Column(db.Integer, default=50)   # 0-100 被动↔主动
    empathy = db.Column(db.Integer, default=50)         # 0-100 理性↔感性
    creativity = db.Column(db.Integer, default=50)      # 0-100 保守↔创新
    custom_instructions = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'employee_type', name='uq_user_employee'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'employee_type': self.employee_type,
            'tone': self.tone,
            'formality': self.formality,
            'proactiveness': self.proactiveness,
            'empathy': self.empathy,
            'creativity': self.creativity,
            'custom_instructions': self.custom_instructions or '',
        }
