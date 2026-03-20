import sys
sys.path.insert(0, '/home/node/.local/lib/python3.11/site-packages')

import os
import json
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

from config import Config
from models import db, User, Conversation, Lead

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    db.create_all()

# ─── DeepSeek client ────────────────────────────────────────────────────────
ai_client = OpenAI(
    api_key=Config.DEEPSEEK_API_KEY,
    base_url=Config.DEEPSEEK_BASE_URL
)

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
def send_email(subject, body):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = Config.SMTP_USER
        msg['To'] = Config.NOTIFY_EMAIL
        msg.attach(MIMEText(body, 'html', 'utf-8'))
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT, context=context) as server:
            server.login(Config.SMTP_USER, Config.SMTP_PASS)
            server.sendmail(Config.SMTP_USER, Config.NOTIFY_EMAIL, msg.as_string())
        return True
    except Exception as e:
        print(f'[Email Error] {e}')
        return False

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    user = get_current_user()
    return render_template('index.html', user=user.username if user else '')

# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({'success': False, 'message': '请填写所有必填字段'}), 400
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


# ── Chat ──────────────────────────────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    employee_type = data.get('employee_type', 'ada').lower()
    message = data.get('message', '').strip()
    history = data.get('history', [])
    conv_id = data.get('conversation_id')

    if not message:
        return jsonify({'error': '消息不能为空'}), 400
    if employee_type not in EMPLOYEE_PROMPTS:
        return jsonify({'error': '未知的员工类型'}), 400

    user = get_current_user()

    # Build messages for API
    system_prompt = EMPLOYEE_PROMPTS[employee_type]
    messages = [{'role': 'system', 'content': system_prompt}]
    for h in history[-20:]:
        if h.get('role') in ('user', 'assistant'):
            messages.append({'role': h['role'], 'content': h['content']})
    messages.append({'role': 'user', 'content': message})

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
                conv = Conversation.query.get(conv_id)
            else:
                conv = None

            if conv is None:
                conv = Conversation(
                    user_id=user.id if user else None,
                    employee_type=employee_type
                )
                db.session.add(conv)

            msgs = conv.messages
            msgs.append({'role': 'user', 'content': message, 'time': datetime.utcnow().isoformat()})
            msgs.append({'role': 'assistant', 'content': full_response, 'time': datetime.utcnow().isoformat()})
            conv.messages = msgs
            db.session.commit()
            yield f"data: {json.dumps({'done': True, 'conversation_id': conv.id})}\n\n"
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
def contact():
    data = request.json or {}
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    company = data.get('company', '')
    plan = data.get('plan', '')
    message = data.get('msg', '')

    if not name or not phone:
        return jsonify({'success': False, 'message': '姓名和电话为必填项'}), 400

    lead = Lead(name=name, phone=phone, company=company, plan=plan, message=message)
    db.session.add(lead)
    db.session.commit()

    # Send email notification
    email_body = f"""
    <html><body style="font-family:Arial,sans-serif;color:#333">
    <h2 style="color:#0071e3">新咨询线索 — Findyou</h2>
    <table cellpadding="8" cellspacing="0" border="1" style="border-collapse:collapse;width:100%;max-width:500px">
    <tr><td><b>姓名</b></td><td>{name}</td></tr>
    <tr><td><b>电话</b></td><td>{phone}</td></tr>
    <tr><td><b>公司</b></td><td>{company or '未填写'}</td></tr>
    <tr><td><b>方案</b></td><td>{plan or '未选择'}</td></tr>
    <tr><td><b>需求描述</b></td><td>{message or '无'}</td></tr>
    <tr><td><b>提交时间</b></td><td>{lead.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC</td></tr>
    </table>
    <p style="margin-top:16px;color:#666">请尽快跟进此线索。</p>
    </body></html>
    """
    send_email(f'【Findyou】新咨询线索：{name} - {company}', email_body)

    return jsonify({'success': True, 'message': '提交成功，我们将在24小时内联系您'})


# ── Admin ──────────────────────────────────────────────────────────────────────
@app.route('/api/leads', methods=['GET'])
@login_required
def get_leads(user):
    leads = Lead.query.order_by(Lead.created_at.desc()).all()
    return jsonify({'success': True, 'leads': [l.to_dict() for l in leads]})


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
