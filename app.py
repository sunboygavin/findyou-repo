import sys
import os
sys.path.insert(0, os.path.join(os.path.expanduser('~'), '.local/lib/python3.11/site-packages'))

import os
import json
import re
import html as html_mod
import logging
import threading
import jwt
import bcrypt
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from openai import OpenAI
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

from config import Config
from models import db, User, Conversation, Lead, Plan, Subscription, UsageLog, EmployeeConfig

app = Flask(__name__)
limiter = Limiter(
    get_remote_address,
    app=None,
    default_limits=[],
    storage_uri="memory://"
)
app.config.from_object(Config)
db.init_app(app)
limiter.init_app(app)

with app.app_context():
    db.create_all()
    # Seed default plans
    if Plan.query.count() == 0:
        for p in Config.DEFAULT_PLANS:
            plan = Plan(
                name=p['name'],
                display_name=p['display_name'],
                price_monthly=p['price_monthly'],
                max_employees=p['max_employees'],
                max_calls_monthly=p['max_calls_monthly'],
                model_tier=p['model_tier'],
                features_json=json.dumps(p['features'], ensure_ascii=False),
                sort_order=p['sort_order'],
            )
            db.session.add(plan)
        db.session.commit()
        logger.info("Seeded default plans")



# ─── Request logging ─────────────────────────────────────────────────────────
@app.before_request
def log_request():
    logger.info(f"{request.method} {request.path} from {request.remote_addr}")

# ─── Error handlers ──────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': '接口不存在'}), 404
    return render_template('index.html', user=''), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"500 error: {e}")
    return jsonify({'error': '服务器内部错误'}), 500

# ─── DeepSeek client ────────────────────────────────────────────────────────
if Config.DEEPSEEK_API_KEY:
    ai_client = OpenAI(
        api_key=Config.DEEPSEEK_API_KEY,
        base_url=Config.DEEPSEEK_BASE_URL
    )
else:
    ai_client = None
    logger.warning("DEEPSEEK_API_KEY not set, AI chat will be unavailable")

# ─── Employee system prompts ─────────────────────────────────────────────────
EMPLOYEE_PROMPTS = {
    'ada': """你是财务会计 Ada，Findyou 平台的 AI 数字员工。
性格：严谨细致、合规优先、主动预警、专业可靠。
专业能力：财务报表分析、税务申报、成本核算、发票审核、预算管理、现金流分析。
说话风格：专业、条理清晰，使用财务专业术语，善于用数据说话，会主动指出风险点。
你的目标是帮助企业做好财务管理，确保合规，降低财务风险。""",

    'max': """你是数据分析师 Max，Findyou 平台的 AI 数字员工。
性格：逻辑严谨、善于解读数据、数据驱动决策、思维敏锐。
专业能力：数据挖掘、统计分析、可视化方案设计、趋势预测、用户画像、A/B测试、BI报表。
说话风格：用数据和图表说话，善于把复杂数据转化为简单洞察，经常给出可执行的建议。
你的目标是帮助企业从数据中发现商业机会和风险。""",

    'shield': """你是安全顾问 Shield，Findyou 平台的 AI 数字员工。
性格：冷静果断、零信任原则、全天候警觉、谨慎严密。
专业能力：网络安全、漏洞扫描、风险评估、合规建议、应急响应、日志分析、威胁情报。
说话风格：简洁有力，以安全为第一优先级，会详细解释风险等级和修复优先级。
你的目标是保护企业的数字资产安全，防范网络威胁。""",

    'eva': """你是行政助理 Eva，Findyou 平台的 AI 数字员工。
性格：贴心周到、条理清晰、高效执行、温暖体贴。
专业能力：日程管理、会议安排、文件整理、行政采购、差旅预订、考勤管理、通知发布。
说话风格：亲切友好、有条理，善于整理和规划，会主动提醒重要事项。
你的目标是让管理者从繁琐的行政事务中解放出来，专注于核心业务。""",

    'kai': """你是销售顾问 Kai，Findyou 平台的 AI 数字员工。
性格：热情主动、目标导向、客户至上、善于沟通。
专业能力：客户关系管理、销售漏斗分析、话术设计、竞品分析、线索跟进、合同跟踪、业绩分析。
说话风格：热情有活力，善用销售技巧，会分析客户心理，提供具体可行的销售策略。
你的目标是帮助销售团队提升效率，扩大销售业绩。""",

    'nova': """你是内容创作 Nova，Findyou 平台的 AI 数字员工。
性格：创意丰富、文风多变、热点敏锐、充满灵感。
专业能力：品牌文案、营销内容、SEO优化、社媒运营、短视频脚本、内容日历规划、多平台适配。
说话风格：充满创意和活力，善于把握热点，文字灵动有感染力，善于根据不同平台调整风格。
你的目标是帮助品牌建立强大的内容矩阵，提升品牌影响力。""",

    'lex': """你是法务顾问 Lex，Findyou 平台的 AI 数字员工。
性格：严谨审慎、法规精通、风险敏锐、公正客观。
专业能力：合同审查、法律咨询、风险评估、合规建议、知识产权保护、劳动法务、政策解读。
说话风格：严谨专业，引用法规条款，会明确区分法律风险等级，给出具体修改建议。
重要提示：你提供的是参考性法律信息，重大法律事务建议咨询持牌律师。
你的目标是帮助企业规避法律风险，确保合规经营。""",

    'mia': """你是HR专员 Mia，Findyou 平台的 AI 数字员工。
性格：慧眼识才、温暖沟通、公正客观、高效执行。
专业能力：招聘管理、简历筛选、绩效评估、员工关系、薪酬分析、培训规划、考勤管理。
说话风格：温暖有亲和力，既专业又人性化，善于在效率和人文关怀之间找到平衡。
你的目标是帮助企业吸引、留住和发展优秀人才，构建良好的组织文化。"""
}

EMPLOYEE_NAMES = {
    'ada': '财务会计 Ada',
    'max': '数据分析师 Max',
    'shield': '安全顾问 Shield',
    'eva': '行政助理 Eva',
    'kai': '销售顾问 Kai',
    'nova': '内容创作 Nova',
    'lex': '法务顾问 Lex',
    'mia': 'HR专员 Mia'
}

# ─── JWT helpers ──────────────────────────────────────────────────────────────
def create_token(user_id, username):
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': datetime.now(timezone.utc) + timedelta(hours=Config.JWT_EXPIRY_HOURS)
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')

def decode_token(token):
    try:
        return jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
    except Exception:
        return None

def get_current_user():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = request.cookies.get('token', '')
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    return User.query.get(payload.get('user_id'))

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': '未授权，请先登录'}), 401
        return f(user, *args, **kwargs)
    return decorated

# ─── Email helper ─────────────────────────────────────────────────────────────
def _send_email_sync(subject, body):
    try:
        if not Config.SMTP_USER or not Config.SMTP_PASS:
            logger.warning("SMTP not configured, skipping email")
            return False
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = Config.SMTP_USER
        msg['To'] = Config.NOTIFY_EMAIL
        msg.attach(MIMEText(body, 'html', 'utf-8'))
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT, context=context, timeout=10) as server:
            server.login(Config.SMTP_USER, Config.SMTP_PASS)
            server.sendmail(Config.SMTP_USER, Config.NOTIFY_EMAIL, msg.as_string())
        logger.info(f"Email sent: {subject}")
        return True
    except Exception as e:
        logger.error(f'Email error: {e}')
        return False

def send_email(subject, body):
    """Non-blocking email send via thread"""
    t = threading.Thread(target=_send_email_sync, args=(subject, body), daemon=True)
    t.start()
    return True

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route('/robots.txt')
def robots():
    from flask import send_from_directory
    return send_from_directory(app.static_folder, 'robots.txt')

@app.route('/sitemap.xml')
def sitemap():
    from flask import send_from_directory
    return send_from_directory(app.static_folder, 'sitemap.xml')

@app.route('/findyou.jpg')
def favicon():
    from flask import send_from_directory
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'findyou.jpg')

@app.route('/')
def index():
    user = get_current_user()
    return render_template('index.html', user=user.username if user else '')

# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    data = request.json or {}
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({'success': False, 'message': '请填写所有必填字段'}), 400
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        return jsonify({'success': False, 'message': '用户名需3-20位字母数字下划线'}), 400
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return jsonify({'success': False, 'message': '邮箱格式不正确'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'message': '密码至少6位'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': '用户名已存在'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': '邮箱已被注册'}), 400

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = User(username=username, email=email, password_hash=pw_hash)
    db.session.add(user)
    db.session.commit()

    token = create_token(user.id, user.username)
    return jsonify({'success': True, 'token': token, 'user': user.to_dict()})


@app.route('/api/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'message': '请输入用户名和密码'}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
    if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

    token = create_token(user.id, user.username)
    return jsonify({'success': True, 'token': token, 'user': user.to_dict()})


@app.route('/api/me', methods=['GET'])
@login_required
def me(user):
    return jsonify({'success': True, 'user': user.to_dict()})


# ── Mock chat responses (演示模式，当 AI 服务未配置时使用) ─────────────────────
def _mock_chat_response(employee_type, message, history, conv_id, user):
    """提供模拟的 AI 回复，用于演示或 API 不可用时"""
    import random
    from datetime import timezone

    # 根据数字员工类型定义不同的回复
    MOCK_RESPONSES = {
        'ada': [
            "您好！我是财务会计 Ada。根据您描述的情况，我建议您可以：\\n\\n1. **整理原始凭证** — 确保所有收支都有对应单据\\n2. **建立科目表** — 按照企业会计准则设置\\n3. **定期核对账目** — 月度/季度进行账实核对\\n\\n如果您有更具体的财务问题，比如税务申报、成本核算等，欢迎继续提问！",
            "收到您的咨询。作为财务顾问，我建议关注以下几个合规要点：\\n\\n- ✅ 发票管理要规范，避免虚开发票风险\\n- ✅ 收入确认按时点，符合会计准则\\n- ✅ 费用报销需真实，保留完整审批链\\n\\n需要我详细说明其中任何一点吗？",
            "明白您的需求。我可以帮您处理：\\n\\n| 服务项 | 说明 |\\n|--------|------|\\n| 财务报表 | 资产负债表、利润表、现金流量表 |\\n| 税务申报 | 增值税、企业所得税、个税等 |\\n| 成本分析 | 产品成本、部门费用、项目核算 |\\n\\n请问您目前最需要哪方面的支持？"
        ],
        'max': [
            "嗨！我是数据分析师 Max。从数据角度来看，我建议您可以先明确 **分析目标**：\\n\\n1. 是想要优化现有业务流程？\\n2. 还是希望发现新的增长机会？\\n3. 或者是监控关键指标预警？\\n\\n目标清晰后，我们才能设计最有效的数据采集和分析方案。",
            "数据分析的关键在于 **从数据到洞察**。我可以帮您：\\n\\n- 📊 搭建 BI 报表看板\\n- 📈 进行趋势预测和异常检测\\n- 🎯 用户画像和分群分析\\n- 🧪 A/B 测试设计与效果评估\\n\\n您手上有哪些数据想先分析看看？",
            "收到！这里有一个数据驱动决策的框架供您参考：\\n\\n```\\n数据收集 → 清洗处理 → 探索分析 → 建模预测 → 可视化呈现 → 决策建议\\n```\\n\\n每个环节我都可以协助您。目前您处于哪个阶段呢？"
        ],
        'shield': [
            "您好，我是安全顾问 Shield。安全是企业的生命线，我建议从以下几个维度评估：\\n\\n**🔴 高风险项（立即处理）：**\\n- 弱密码/默认密码未修改\\n- 敏感端口暴露公网\\n- 缺乏多因素认证\\n\\n**🟡 中风险项（尽快完善）：**\\n- 日志审计不完整\\n- 访问权限过于宽松\\n\\n您希望我帮您进行哪方面的安全评估？",
            "安全无小事。根据行业最佳实践，建议建立 **纵深防御体系**：\\n\\n| 层级 | 措施 |\\n|------|------|\\n| 网络层 | 防火墙、WAF、DDoS 防护 |\\n| 主机层 | 漏洞扫描、基线检查、EDR |\\n| 应用层 | 代码审计、渗透测试 |\\n| 数据层 | 加密存储、访问控制、备份 |\\n\\n需要我针对某一层做详细方案吗？",
            "收到您的安全咨询。请先回答几个问题，便于我评估您的安全成熟度：\\n\\n1. 是否定期进行漏洞扫描？\\n2. 员工是否接受过安全意识培训？\\n3. 是否有应急响应预案？\\n\\n您可以先回复了解程度，我会给出针对性建议。"
        ],
        'eva': [
            "您好！我是行政助理 Eva。让我来帮您梳理一下行政工作的优化方案：\\n\\n**📅 日程管理**\\n- 智能排期，避免时间冲突\\n- 会议提醒，提前准备材料\\n\\n**📋 会议支持**\\n- 预订会议室、发送邀请\\n- 准备议程、记录纪要\\n\\n**📦 采购管理**\\n- 供应商比价、采购申请审批\\n- 资产台账管理\\n\\n哪方面是您目前最想优化的？",
            "明白！行政工作看似琐碎，实则影响团队效率。我可以帮您：\\n\\n1. **建立标准化流程** — 让重复性工作有章可循\\n2. **数字化文档管理** — 合同、证照、档案一目了然\\n3. **员工服务优化** — 考勤、差旅、福利一站式处理\\n\\n请告诉我您团队目前的人数和主要痛点？",
            "好的，我为您准备了一份行政工作检查清单：\\n\\n- [ ] 办公环境整洁有序\\n- [ ] 办公用品库存充足\\n- [ ] 本月重要日程已标注\\n- [ ] 员工考勤异常已处理\\n- [ ] 待签合同跟进中\\n- [ ] 访客接待流程已确认\\n\\n需要我帮您制定更详细的周/月计划吗？"
        ],
        'kai': [
            "嘿！我是销售顾问 Kai。让我们来看看如何提升业绩！首先，请告诉我：\\n\\n1. 您目前的销售漏斗各阶段转化率是多少？\\n2. 主要获客渠道有哪些？\\n3. 客单价和平均成单周期？\\n\\n有了这些数据，我可以帮您找到增长瓶颈和突破点！",
            "销售是一门科学！我建议采用 **SPIN 销售法**：\\n\\n- **S**ituation（现状）— 了解客户当前情况\\n- **P**roblem（问题）— 挖掘痛点\\n- **I**mplication（暗示）— 放大问题影响\\n- **N**eed-payoff（需求确认）— 呈现解决方案价值\\n\\n想让我帮您设计针对特定客户的话术吗？",
            "收到！这里有一个提升成单率的实战技巧：\\n\\n**跟进节奏黄金法则**\\n\\n| 阶段 | 动作 | 时间 |\\n|------|------|------|\\n| 初次接触 | 发送资料 | 当天 |\\n| 需求确认 | 方案演示 | 1-3天 |\\n| 方案提交 | 报价跟进 | 3-7天 |\\n| 异议处理 | 案例分享 | 7-14天 |\\n| 临门一脚 | 限时优惠 | 14-21天 |\\n\\n需要我针对您的具体客户分析一下吗？"
        ],
        'nova': [
            "你好！我是内容创作 Nova。创意灵感正在涌现 ✨ 根据您的品牌调性，我建议：\\n\\n**内容矩阵规划：**\\n\\n- 品牌故事（建立情感连接）\\n- 产品种草（场景化展示价值）\\n- 行业洞察（建立专业权威）\\n- 用户UGC（增强信任背书）\\n\\n您目前最想加强哪个板块的内容？",
            "创意是我的超能力！给您几个当下热门的内容选题方向：\\n\\n1. **反常识观点** — 「为什么 X 不是你想的那样」\\n2. **对比类内容** — 「Before vs After 的惊人变化」\\n3. **干货教程** — 「3 步教你搞定 XX」\\n4. **幕后故事** — 「我们花了 X 个月，只为...」\\n\\n需要我为您的具体产品/服务创作一篇样稿吗？",
            "明白！内容创作要兼顾 **创意** 和 **转化**。一个完整的内容策略包括：\\n\\n```\\n选题策划 → 脚本撰写 → 视觉设计 → 发布排期 → 数据复盘\\n```\\n\\n我可以负责从策划到撰写的全流程。请告诉我：\\n\\n- 您的目标受众是谁？\\n- 主要发布平台有哪些？\\n- 期望的发布频率？"
        ],
        'lex': [
            "您好，我是法务顾问 Lex。请描述您遇到的具体法律问题，我将从以下角度分析：\\n\\n**我的服务范围：**\\n\\n- 合同审查与起草\\n- 劳动用工合规\\n- 知识产权保护\\n- 数据隐私合规\\n- 股权架构设计\\n\\n⚠️ *温馨提示：我提供的是参考性法律信息，重大法律事务建议咨询持牌律师。*\\n\\n您想先了解哪个领域？",
            "收到您的咨询。在处理法律事务时，我建议遵循 **RISC 原则**：\\n\\n- **R**isk（风险识别）— 明确潜在法律风险点\\n- **I**mpact（影响评估）— 评估风险发生的概率和损失\\n- **S**trategy（应对策略）— 制定风险规避/转移/承担方案\\n- **C**ompliance（合规落地）— 确保措施符合法律法规\\n\\n请告诉我您目前的具体情况，我来帮您分析。",
            "明白。以下是一份常见合同审查要点清单，供您参考：\\n\\n| 审查项 | 注意要点 |\\n|--------|----------|\\n| 主体资格 | 签约方是否有履约能力 |\\n| 标的条款 | 明确、可执行、无歧义 |\\n| 价款支付 | 金额、时间、方式、发票 |\\n| 违约责任 | 对等、可执行、上限合理 |\\n| 争议解决 | 管辖法院/仲裁机构明确 |\\n| 生效条件 | 签字盖章、审批流程完成 |\\n\\n需要我帮您审查具体合同吗？"
        ],
        'mia': [
            "你好！我是 HR 专员 Mia。人才是企业最大的资产，让我来帮您！请告诉我：\\n\\n1. 您目前最紧迫的 HR 挑战是什么？（招聘/绩效/培训/员工关系）\\n2. 团队目前的规模和结构？\\n3. 您希望达到什么样的目标？\\n\\n了解情况后，我可以给出针对性的解决方案。",
            "收到！HR 工作既要专业又要有人情味。我可以协助您：\\n\\n**招聘管理**\\n- 职位描述优化、简历筛选、面试评估\\n\\n**绩效管理**\\n- KPI/OKR 设计、绩效面谈、改进计划\\n\\n**培训发展**\\n- 新人入职培训、管理能力提升、职业规划\\n\\n**员工关系**\\n- 满意度调研、离职面谈、企业文化\\n\\n您最想先优化哪个模块？",
            "好的！这里有一个实用的招聘面试问题库供参考：\\n\\n**能力评估类：**\\n- 请描述一次你解决复杂问题的经历\\n- 当团队意见不一致时，你会怎么处理？\\n\\n**文化匹配类：**\\n- 你理想的工作环境是什么样的？\\n- 什么样的管理方式最能激发你的潜力？\\n\\n**动机探索类：**\\n- 为什么选择离开现在的公司？\\n- 未来 3 年你的职业规划是什么？\\n\\n需要我为特定岗位定制面试题库吗？"
        ]
    }

    def generate_mock():
        """模拟流式响应"""
        responses = MOCK_RESPONSES.get(employee_type, MOCK_RESPONSES['ada'])
        # 根据消息内容选择或随机选择回复
        full_response = random.choice(responses)

        # 模拟流式输出（分块发送）
        words = []
        for para in full_response.split('\\n'):
            words.extend(list(para))
            words.append('\\n')

        chunk_size = 3  # 每次发送3个字符
        for i in range(0, len(words), chunk_size):
            chunk = ''.join(words[i:i+chunk_size])
            yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\\n\\n"
            import time
            time.sleep(0.03)  # 模拟打字延迟

        # 保存对话记录
        try:
            if conv_id:
                conv = Conversation.query.filter_by(
                    id=conv_id,
                    user_id=user.id if user else None
                ).first()
            else:
                conv = None

            if conv is None:
                conv = Conversation(
                    user_id=user.id if user else None,
                    employee_type=employee_type
                )
                db.session.add(conv)

            msgs = conv.messages
            msgs.append({'role': 'user', 'content': message, 'time': datetime.now(timezone.utc).isoformat()})
            msgs.append({'role': 'assistant', 'content': full_response, 'time': datetime.now(timezone.utc).isoformat()})
            conv.messages = msgs
            if not conv.title:
                conv.title = message[:30] + ('...' if len(message) > 30 else '')
            db.session.commit()
            # Log usage
            usage = UsageLog(
                user_id=user.id if user else None,
                employee_type=employee_type,
                conversation_id=conv.id,
                tokens_in=len(message),
                tokens_out=len(full_response),
            )
            db.session.add(usage)
            db.session.commit()
            yield f"data: {json.dumps({'done': True, 'conversation_id': conv.id}, ensure_ascii=False)}\\n\\n"
        except Exception:
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\\n\\n"

    return Response(
        stream_with_context(generate_mock()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


# ── Chat ──────────────────────────────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
@limiter.limit("30 per minute")
def chat():
    data = request.json or {}
    employee_type = data.get('employee_type', 'ada').lower()
    message = data.get('message', '').strip()
    history = data.get('history', [])
    conv_id = data.get('conversation_id')

    if not message:
        return jsonify({'error': '消息不能为空'}), 400
    if len(message) > 2000:
        return jsonify({'error': '消息长度不能超过2000字符'}), 400
    if employee_type not in EMPLOYEE_PROMPTS:
        return jsonify({'error': '未知的员工类型'}), 400
    history = history[:20]  # limit history
    # Limit each history message content length
    history = [
        {**h, 'content': h.get('content', '')[:2000]}
        for h in history
        if h.get('role') in ('user', 'assistant')
    ]

    user = get_current_user()

    # ── Quota check ──
    if user:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_calls = UsageLog.query.filter(
            UsageLog.user_id == user.id,
            UsageLog.created_at >= month_start,
        ).count()
        sub = Subscription.query.filter_by(user_id=user.id, status='active').first()
        max_calls = sub.plan.max_calls_monthly if sub and sub.plan else 10000
        if monthly_calls >= max_calls:
            return jsonify({'error': '本月调用次数已达上限，请升级套餐', 'quota_exceeded': True}), 429
        usage_pct = round(monthly_calls / max_calls * 100, 1) if max_calls > 0 else 0
    else:
        usage_pct = 0

    # ── Build system prompt with personality config ──
    system_prompt = EMPLOYEE_PROMPTS[employee_type]
    if user:
        emp_config = EmployeeConfig.query.filter_by(user_id=user.id, employee_type=employee_type).first()
        if emp_config:
            personality_desc = (
                f"\n\n【个性化调整】请根据以下参数调整你的回复风格（0-100）："
                f"\n- 语气（严肃0↔轻松100）：{emp_config.tone}"
                f"\n- 正式度（正式0↔随意100）：{emp_config.formality}"
                f"\n- 主动性（被动0↔主动100）：{emp_config.proactiveness}"
                f"\n- 共情力（理性0↔感性100）：{emp_config.empathy}"
                f"\n- 创造力（保守0↔创新100）：{emp_config.creativity}"
            )
            if emp_config.custom_instructions:
                personality_desc += f"\n- 用户自定义指令：{emp_config.custom_instructions}"
            system_prompt += personality_desc

    # Build messages for API
    messages = [{'role': 'system', 'content': system_prompt}]
    for h in history[-20:]:
        if h.get('role') in ('user', 'assistant'):
            messages.append({'role': h['role'], 'content': h['content']})
    messages.append({'role': 'user', 'content': message})

    # 如果 AI 服务未配置，使用模拟回复（演示模式）
    if not ai_client:
        return _mock_chat_response(employee_type, message, history, conv_id, user)

    def generate():
        full_response = ''
        try:
            stream = ai_client.chat.completions.create(
                model=Config.DEEPSEEK_MODEL,
                messages=messages,
                stream=True,
                max_tokens=2048,
                temperature=0.7
            )
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    text = delta.content
                    full_response += text
                    yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        # Save conversation to DB
        try:
            if conv_id:
                conv = Conversation.query.filter_by(
                    id=conv_id,
                    user_id=user.id if user else None
                ).first()
            else:
                conv = None

            if conv is None:
                conv = Conversation(
                    user_id=user.id if user else None,
                    employee_type=employee_type
                )
                db.session.add(conv)

            msgs = conv.messages
            msgs.append({'role': 'user', 'content': message, 'time': datetime.now(timezone.utc).isoformat()})
            msgs.append({'role': 'assistant', 'content': full_response, 'time': datetime.now(timezone.utc).isoformat()})
            conv.messages = msgs
            if not conv.title:
                conv.title = message[:30] + ('...' if len(message) > 30 else '')
            db.session.commit()
            # Log usage
            usage = UsageLog(
                user_id=user.id if user else None,
                employee_type=employee_type,
                conversation_id=conv.id,
                tokens_in=len(message),
                tokens_out=len(full_response),
            )
            db.session.add(usage)
            db.session.commit()
            resp_data = {'done': True, 'conversation_id': conv.id}
            if user and usage_pct >= Config.USAGE_WARN_THRESHOLD:
                resp_data['usage_warning'] = f'本月用量已达 {usage_pct}%'
            yield f"data: {json.dumps(resp_data, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'done': True})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/conversations', methods=['GET'])
@login_required
def get_conversations(user):
    convs = Conversation.query.filter_by(user_id=user.id).order_by(
        Conversation.created_at.desc()
    ).limit(50).all()
    return jsonify({'success': True, 'conversations': [c.to_dict() for c in convs]})


@app.route('/api/conversations/<int:conv_id>', methods=['GET'])
@login_required
def get_conversation(user, conv_id):
    conv = Conversation.query.filter_by(id=conv_id, user_id=user.id).first()
    if not conv:
        return jsonify({'error': '未找到对话记录'}), 404
    return jsonify({'success': True, 'conversation': conv.to_dict()})


# ── Leads / Contact ────────────────────────────────────────────────────────────
@app.route('/api/contact', methods=['POST'])
@limiter.limit("5 per minute")
def contact():
    data = request.json or {}
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    company = data.get('company', '')
    plan = data.get('plan', '')
    message = data.get('msg', '')

    if not name or not phone:
        return jsonify({'success': False, 'message': '姓名和电话为必填项'}), 400
    # 支持手机号、固话、400电话等常见格式
    if not re.match(r'^[\d\-\+\(\)\s]{7,20}$', phone):
        return jsonify({'success': False, 'message': '请输入有效的联系电话'}), 400

    lead = Lead(name=name, phone=phone, company=company, plan=plan, message=message)
    db.session.add(lead)
    db.session.commit()

    # Send email notification
    # XSS protection: escape user input in email HTML
    s_name = html_mod.escape(name)
    s_phone = html_mod.escape(phone)
    s_company = html_mod.escape(company or '未填写')
    s_plan = html_mod.escape(plan or '未选择')
    s_message = html_mod.escape(message or '无')
    email_body = f"""
    <html><body style="font-family:Arial,sans-serif;color:#333">
    <h2 style="color:#0071e3">新咨询线索 — Findyou</h2>
    <table cellpadding="8" cellspacing="0" border="1" style="border-collapse:collapse;width:100%;max-width:500px">
    <tr><td><b>姓名</b></td><td>{s_name}</td></tr>
    <tr><td><b>电话</b></td><td>{s_phone}</td></tr>
    <tr><td><b>公司</b></td><td>{s_company}</td></tr>
    <tr><td><b>方案</b></td><td>{s_plan}</td></tr>
    <tr><td><b>需求描述</b></td><td>{s_message}</td></tr>
    <tr><td><b>提交时间</b></td><td>{lead.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC</td></tr>
    </table>
    <p style="margin-top:16px;color:#666">请尽快跟进此线索。</p>
    </body></html>
    """
    send_email(f'【Findyou】新咨询线索：{name} - {company}', email_body)

    return jsonify({'success': True, 'message': '提交成功，我们将在24小时内联系您'})


# ── User Profile ─────────────────────────────────────────────────────────────
@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile(user):
    sub = Subscription.query.filter_by(user_id=user.id, status='active').first()
    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'subscription': sub.to_dict() if sub else None,
    })


@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile(user):
    data = request.get_json(silent=True) or {}
    allowed = ['phone', 'company', 'bio']
    for field in allowed:
        if field in data:
            val = str(data[field]).strip()[:500]
            setattr(user, field, val)
    db.session.commit()
    return jsonify({'success': True, 'user': user.to_dict()})


@app.route('/api/password', methods=['PUT'])
@login_required
def change_password(user):
    data = request.get_json(silent=True) or {}
    old_pw = data.get('old_password', '')
    new_pw = data.get('new_password', '')
    if not old_pw or not new_pw:
        return jsonify({'error': '请填写旧密码和新密码'}), 400
    if len(new_pw) < 6:
        return jsonify({'error': '新密码至少6位'}), 400
    if not bcrypt.checkpw(old_pw.encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({'error': '旧密码不正确'}), 400
    user.password_hash = bcrypt.hashpw(new_pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.session.commit()
    return jsonify({'success': True, 'message': '密码修改成功'})


# ── Employee Config ──────────────────────────────────────────────────────────
@app.route('/api/employee-config/<emp_type>', methods=['GET'])
@login_required
def get_employee_config(user, emp_type):
    if emp_type not in EMPLOYEE_PROMPTS:
        return jsonify({'error': '无效的员工类型'}), 400
    config = EmployeeConfig.query.filter_by(user_id=user.id, employee_type=emp_type).first()
    if config:
        return jsonify({'success': True, 'config': config.to_dict()})
    return jsonify({'success': True, 'config': {
        'employee_type': emp_type, 'tone': 50, 'formality': 50,
        'proactiveness': 50, 'empathy': 50, 'creativity': 50,
        'custom_instructions': '',
    }})


@app.route('/api/employee-config/<emp_type>', methods=['PUT'])
@login_required
def update_employee_config(user, emp_type):
    if emp_type not in EMPLOYEE_PROMPTS:
        return jsonify({'error': '无效的员工类型'}), 400
    data = request.get_json(silent=True) or {}
    config = EmployeeConfig.query.filter_by(user_id=user.id, employee_type=emp_type).first()
    if not config:
        config = EmployeeConfig(user_id=user.id, employee_type=emp_type)
        db.session.add(config)
    for field in ['tone', 'formality', 'proactiveness', 'empathy', 'creativity']:
        if field in data:
            setattr(config, field, max(0, min(100, int(data[field]))))
    if 'custom_instructions' in data:
        config.custom_instructions = str(data['custom_instructions']).strip()[:1000]
    db.session.commit()
    return jsonify({'success': True, 'config': config.to_dict()})


# ── Conversation Enhancements ────────────────────────────────────────────────
@app.route('/api/conversations/<int:conv_id>', methods=['DELETE'])
@login_required
def delete_conversation(user, conv_id):
    conv = Conversation.query.get(conv_id)
    if not conv or conv.user_id != user.id:
        return jsonify({'error': '对话不存在'}), 404
    db.session.delete(conv)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/conversations/<int:conv_id>/export', methods=['GET'])
@login_required
def export_conversation(user, conv_id):
    conv = Conversation.query.get(conv_id)
    if not conv or conv.user_id != user.id:
        return jsonify({'error': '对话不存在'}), 404
    fmt = request.args.get('format', 'json')
    if fmt == 'md':
        lines = [f'# {conv.title or "对话记录"}\n']
        lines.append(f'员工类型: {conv.employee_type}\n')
        lines.append(f'创建时间: {conv.created_at}\n\n---\n')
        for msg in conv.messages:
            role = '🧑 用户' if msg.get('role') == 'user' else '🤖 AI'
            lines.append(f'\n### {role}\n\n{msg.get("content", "")}\n')
        content = '\n'.join(lines)
        return Response(content, mimetype='text/markdown',
                        headers={'Content-Disposition': f'attachment; filename=conversation_{conv_id}.md'})
    return jsonify(conv.to_dict())


@app.route('/api/conversations/search', methods=['GET'])
@login_required
def search_conversations(user):
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify({'error': '搜索关键词至少2个字符'}), 400
    convs = Conversation.query.filter(
        Conversation.user_id == user.id,
        db.or_(
            Conversation.title.contains(q),
            Conversation.messages_json.contains(q),
        )
    ).order_by(Conversation.updated_at.desc()).limit(50).all()
    return jsonify({'success': True, 'conversations': [c.to_summary() for c in convs]})


# ── Subscription & Plans ─────────────────────────────────────────────────────
@app.route('/api/plans', methods=['GET'])
def get_plans():
    plans = Plan.query.filter_by(is_active=True).order_by(Plan.sort_order).all()
    return jsonify({'success': True, 'plans': [p.to_dict() for p in plans]})


@app.route('/api/subscription', methods=['GET'])
@login_required
def get_subscription(user):
    sub = Subscription.query.filter_by(user_id=user.id, status='active').first()
    return jsonify({'success': True, 'subscription': sub.to_dict() if sub else None})


@app.route('/api/subscription', methods=['POST'])
@login_required
def create_subscription(user):
    data = request.get_json(silent=True) or {}
    plan_name = data.get('plan', '')
    plan = Plan.query.filter_by(name=plan_name, is_active=True).first()
    if not plan:
        return jsonify({'error': '无效的套餐'}), 400
    # Cancel existing active subscription
    Subscription.query.filter_by(user_id=user.id, status='active').update({'status': 'cancelled'})
    sub = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        status='active',
        started_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.session.add(sub)
    db.session.commit()
    return jsonify({'success': True, 'subscription': sub.to_dict()})


@app.route('/api/usage', methods=['GET'])
@login_required
def get_usage(user):
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total_calls = UsageLog.query.filter(
        UsageLog.user_id == user.id,
        UsageLog.created_at >= month_start,
    ).count()
    # Per-employee breakdown
    from sqlalchemy import func
    breakdown = db.session.query(
        UsageLog.employee_type, func.count(UsageLog.id)
    ).filter(
        UsageLog.user_id == user.id,
        UsageLog.created_at >= month_start,
    ).group_by(UsageLog.employee_type).all()
    sub = Subscription.query.filter_by(user_id=user.id, status='active').first()
    max_calls = sub.plan.max_calls_monthly if sub and sub.plan else 10000
    return jsonify({
        'success': True,
        'total_calls': total_calls,
        'max_calls': max_calls,
        'percentage': round(total_calls / max_calls * 100, 1) if max_calls > 0 else 0,
        'breakdown': {row[0]: row[1] for row in breakdown},
    })


# ── Admin ──────────────────────────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(user, *args, **kwargs):
        if user.username not in Config.ADMIN_USERS and not user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403
        return f(user, *args, **kwargs)
    return decorated


@app.route('/admin')
@login_required
def admin_page(user):
    if user.username not in Config.ADMIN_USERS and not user.is_admin:
        return render_template('index.html', user=user.username), 403
    return render_template('admin.html', user=user.username)


@app.route('/api/leads', methods=['GET'])
@admin_required
def get_leads(user):
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    status_filter = request.args.get('status', '')
    q = Lead.query
    if status_filter:
        q = q.filter_by(status=status_filter)
    pagination = q.order_by(Lead.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'success': True,
        'leads': [l.to_dict() for l in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    })


@app.route('/api/admin/leads/<int:lead_id>', methods=['PUT'])
@admin_required
def update_lead(user, lead_id):
    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify({'error': '线索不存在'}), 404
    data = request.get_json(silent=True) or {}
    if 'status' in data and data['status'] in ('new', 'contacted', 'converted', 'closed'):
        lead.status = data['status']
    if 'notes' in data:
        lead.notes = str(data['notes']).strip()[:2000]
    if 'contacted_by' in data:
        lead.contacted_by = str(data['contacted_by']).strip()[:80]
    db.session.commit()
    return jsonify({'success': True, 'lead': lead.to_dict()})


@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats(user):
    from sqlalchemy import func
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return jsonify({
        'success': True,
        'total_users': User.query.count(),
        'total_conversations': Conversation.query.count(),
        'total_leads': Lead.query.count(),
        'total_usage': UsageLog.query.count(),
        'today_users': User.query.filter(User.created_at >= today_start).count(),
        'today_conversations': Conversation.query.filter(Conversation.created_at >= today_start).count(),
        'today_leads': Lead.query.filter(Lead.created_at >= today_start).count(),
        'today_usage': UsageLog.query.filter(UsageLog.created_at >= today_start).count(),
        'leads_by_status': dict(db.session.query(Lead.status, func.count(Lead.id)).group_by(Lead.status).all()),
    })


@app.route('/api/admin/stats/trends', methods=['GET'])
@admin_required
def admin_trends(user):
    from sqlalchemy import func, cast, Date
    days = min(request.args.get('days', 7, type=int), 90)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    def daily_counts(model):
        rows = db.session.query(
            func.date(model.created_at), func.count(model.id)
        ).filter(model.created_at >= start).group_by(func.date(model.created_at)).all()
        return {str(r[0]): r[1] for r in rows}

    return jsonify({
        'success': True,
        'days': days,
        'users': daily_counts(User),
        'conversations': daily_counts(Conversation),
        'leads': daily_counts(Lead),
        'usage': daily_counts(UsageLog),
    })


@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_users(user):
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    search = request.args.get('q', '').strip()
    q = User.query
    if search:
        q = q.filter(db.or_(
            User.username.contains(search),
            User.email.contains(search),
            User.company.contains(search),
        ))
    pagination = q.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'success': True,
        'users': [u.to_dict() for u in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    })


@app.route('/api/admin/users/<int:uid>', methods=['PUT'])
@admin_required
def admin_update_user(user, uid):
    target = User.query.get(uid)
    if not target:
        return jsonify({'error': '用户不存在'}), 404
    data = request.get_json(silent=True) or {}
    if 'is_active' in data:
        target.is_active = bool(data['is_active'])
    if 'is_admin' in data:
        target.is_admin = bool(data['is_admin'])
    db.session.commit()
    return jsonify({'success': True, 'user': target.to_dict()})


@app.route('/api/admin/users/<int:uid>/detail', methods=['GET'])
@admin_required
def admin_user_detail(user, uid):
    from sqlalchemy import func
    target = User.query.get(uid)
    if not target:
        return jsonify({'error': '用户不存在'}), 404
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    conv_count = Conversation.query.filter_by(user_id=uid).count()
    monthly_usage = UsageLog.query.filter(UsageLog.user_id == uid, UsageLog.created_at >= month_start).count()
    total_usage = UsageLog.query.filter_by(user_id=uid).count()
    sub = Subscription.query.filter_by(user_id=uid, status='active').first()
    return jsonify({
        'success': True,
        'user': target.to_dict(),
        'stats': {
            'conversation_count': conv_count,
            'monthly_usage': monthly_usage,
            'total_usage': total_usage,
            'subscription': sub.to_dict() if sub else None,
        }
    })


@app.route('/api/admin/usage', methods=['GET'])
@admin_required
def admin_usage(user):
    from sqlalchemy import func
    now = datetime.now(timezone.utc)
    days = min(request.args.get('days', 7, type=int), 90)
    start = now - timedelta(days=days)
    # By employee type
    by_employee = dict(db.session.query(
        UsageLog.employee_type, func.count(UsageLog.id)
    ).filter(UsageLog.created_at >= start).group_by(UsageLog.employee_type).all())
    # Top users
    top_users = db.session.query(
        UsageLog.user_id, func.count(UsageLog.id).label('cnt')
    ).filter(UsageLog.created_at >= start, UsageLog.user_id.isnot(None)
    ).group_by(UsageLog.user_id).order_by(func.count(UsageLog.id).desc()).limit(20).all()
    top_user_data = []
    for uid, cnt in top_users:
        u = User.query.get(uid)
        if u:
            top_user_data.append({'user': u.to_dict(), 'calls': cnt})
    return jsonify({
        'success': True,
        'by_employee': by_employee,
        'top_users': top_user_data,
    })


@app.route('/api/logout', methods=['POST'])
def logout():
    return jsonify({'success': True})


@app.route('/logout')
def logout_get():
    from flask import redirect, url_for
    resp = redirect('/')
    resp.delete_cookie('token')
    return resp


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
