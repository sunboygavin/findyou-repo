import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Use environment variables for secrets. 
    # Removing the hardcoded fallbacks ensures the app fails safely if keys are missing.
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET = os.environ.get('JWT_SECRET')
    JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', 24))

    # Database
    # It is okay to keep a local SQLite fallback for development purposes
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'findyou.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # DeepSeek AI - Replaced the hardcoded key
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
    DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
    DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')

    # Email (SMTP) - Replaced all hardcoded credentials
    SMTP_HOST = os.environ.get('SMTP_HOST')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))
    SMTP_USER = os.environ.get('SMTP_USER')
    SMTP_PASS = os.environ.get('SMTP_PASS')
    NOTIFY_EMAIL = os.environ.get('NOTIFY_EMAIL')
