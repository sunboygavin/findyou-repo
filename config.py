import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'findyou-secret-key-2026-change-in-prod')
    JWT_SECRET = os.environ.get('JWT_SECRET', 'findyou-jwt-secret-2026')
    JWT_EXPIRY_HOURS = 24

    # Database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'findyou.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # DeepSeek AI
    DEEPSEEK_API_KEY = 'sk-877f8575ed964461a1a87b87f9328c92'
    DEEPSEEK_BASE_URL = 'https://api.deepseek.com/v1'
    DEEPSEEK_MODEL = 'deepseek-chat'

    # Email (SMTP)
    SMTP_HOST = 'smtp.126.com'
    SMTP_PORT = 465
    SMTP_USER = 'sunboygavin@126.com'
    SMTP_PASS = 'LRZgafVkqTs22MRa'
    NOTIFY_EMAIL = '44490661@qq.com'
