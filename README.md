# Findyou — 企业级 AI 数字员工平台

> 8大岗位AI数字员工，云上SaaS + 内网私有化双轨部署，成本仅为真人十分之一。

---

## ✨ 功能特性

- 🤖 **8大AI数字员工**：财务会计 Ada、数据分析师 Max、安全顾问 Shield、行政助理 Eva、销售顾问 Kai、内容创作 Nova、法务顾问 Lex、HR专员 Mia
- 💬 **真实AI对话**：接入 DeepSeek，流式逐字输出，每位员工独立人格
- 👤 **用户系统**：注册/登录（bcrypt加密 + JWT认证）、对话历史云端保存
- 📋 **线索管理**：咨询表单自动入库 + 邮件实时通知
- 📱 **移动端适配**：Apple风格响应式设计
- 🔒 **数据安全**：SQLite本地存储，支持私有化部署

---

## 🚀 快速开始

### 环境要求

- Python 3.9+
- pip

### 1. 克隆项目

```bash
git clone https://github.com/sunboygavin/findyou-repo.git
cd findyou-repo
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量（可选）

复制并编辑配置：

```bash
cp config.py config.local.py  # 可选，直接编辑 config.py 也可
```

关键配置项（`config.py`）：

```python
DEEPSEEK_API_KEY = 'your-deepseek-api-key'  # DeepSeek API Key
SMTP_USER = 'your@email.com'                 # 发件邮箱
SMTP_PASS = 'your-smtp-auth-code'            # SMTP授权码
NOTIFY_EMAIL = 'notify@email.com'            # 线索通知收件邮箱
```

### 4. 启动服务

```bash
python3 app.py
```

服务默认运行在 `http://localhost:5001`

---

## 📁 项目结构

```
findyou-repo/
├── app.py              # Flask 主应用（API路由、AI对话、邮件）
├── models.py           # 数据库模型（users/conversations/leads）
├── config.py           # 全局配置
├── requirements.txt    # Python 依赖
├── start.sh            # 一键启动脚本
├── stop.sh             # 停止服务脚本
├── templates/
│   ├── index.html      # 主页（Apple风格，含对话/登录/注册）
│   └── login.html      # 独立登录页
├── static/
│   ├── css/
│   │   └── chat.css    # 对话/弹窗/认证样式
│   └── js/
│       └── chat.js     # AI对话逻辑（SSE流式）
└── docs/
    ├── BUSINESS_PLAN.md        # 基础商业企划
    ├── FULL_BUSINESS_PLAN.md   # 完整详细企划
    └── 企划方案.md             # 早期方案
```

---

## 🔌 API 接口

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/register` | 注册（username/email/password） |
| POST | `/api/login` | 登录（username/password） |
| GET  | `/api/me` | 获取当前用户信息（需Token） |

### AI 对话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | SSE流式对话（employee_type/message/history） |
| GET  | `/api/conversations` | 获取对话历史列表（需Token） |
| GET  | `/api/conversations/:id` | 获取单条对话详情（需Token） |

**employee_type 可选值：**`ada` / `max` / `shield` / `eva` / `kai` / `nova` / `lex` / `mia`

### 线索

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/contact` | 提交咨询（name/phone/company/plan/msg） |
| GET  | `/api/leads` | 查看所有线索（需Token） |

---

## 🛠️ 生产部署

### 使用 Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

### 使用 Nginx 反代（推荐）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # SSE 必须关闭缓冲
        proxy_buffering off;
        proxy_cache off;
    }
}
```

### 环境变量（生产必改）

```bash
export SECRET_KEY="your-random-secret-key-32chars"
export JWT_SECRET="your-random-jwt-secret-32chars"
```

---

## 📦 依赖说明

| 包 | 版本 | 用途 |
|----|------|------|
| flask | ≥3.0 | Web框架 |
| flask-sqlalchemy | ≥3.1 | ORM数据库 |
| bcrypt | ≥5.0 | 密码加密 |
| pyjwt | ≥2.8 | JWT认证 |
| openai | ≥1.0 | DeepSeek API客户端 |

---

## 📄 License

MIT License — 自由使用、修改、分发。

---

## 📬 联系我们

- GitHub Issues：[提交问题](https://github.com/sunboygavin/findyou-repo/issues)
- 商务合作：contact@findyou.ai
