import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'findyou-dev-secret-change-in-production-2026!@#$')
    JWT_SECRET = os.environ.get('JWT_SECRET', 'findyou-jwt-dev-secret-2026-min32chars!@#$')
    JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', '24'))

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(basedir, 'findyou.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # DeepSeek AI
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
    DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
    DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')

    # Email (SMTP)
    SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.126.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '465'))
    SMTP_USER = os.environ.get('SMTP_USER', '')
    SMTP_PASS = os.environ.get('SMTP_PASS', '')
    NOTIFY_EMAIL = os.environ.get('NOTIFY_EMAIL', '')

    # Rate limiting
    CHAT_RATE_LIMIT = int(os.environ.get('CHAT_RATE_LIMIT', '30'))  # per minute
    REGISTER_RATE_LIMIT = int(os.environ.get('REGISTER_RATE_LIMIT', '5'))  # per hour

    # Admin
    ADMIN_USERS = os.environ.get('ADMIN_USERS', 'admin').split(',')
