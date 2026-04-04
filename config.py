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

    # Usage quota warning thresholds (percentage)
    USAGE_WARN_THRESHOLD = 80
    USAGE_CRITICAL_THRESHOLD = 90

    # Default plans seed data (price in fen/cents)
    DEFAULT_PLANS = [
        {
            'name': 'starter',
            'display_name': '入门版',
            'price_monthly': 29900,
            'max_employees': 1,
            'max_calls_monthly': 10000,
            'model_tier': 'basic',
            'features': ['单个数字员工', '基础模型', '邮件支持', '标准SLA'],
            'sort_order': 1,
        },
        {
            'name': 'professional',
            'display_name': '专业版',
            'price_monthly': 89900,
            'max_employees': 3,
            'max_calls_monthly': 50000,
            'model_tier': 'mid',
            'features': ['3个数字员工', '中级模型', '优先支持', '高级SLA', '个性化定制'],
            'sort_order': 2,
        },
        {
            'name': 'enterprise',
            'display_name': '企业版',
            'price_monthly': 299900,
            'max_employees': 10,
            'max_calls_monthly': 200000,
            'model_tier': 'premium',
            'features': ['10个数字员工', '高级模型', '专属客服', '企业SLA', '深度定制', 'API接入'],
            'sort_order': 3,
        },
        {
            'name': 'flagship',
            'display_name': '旗舰版',
            'price_monthly': 0,  # 定制报价
            'max_employees': 99,
            'max_calls_monthly': 999999,
            'model_tier': 'all',
            'features': ['无限数字员工', '全部模型', '7×24专属支持', '定制SLA', '私有化部署', '全量API'],
            'sort_order': 4,
        },
    ]
