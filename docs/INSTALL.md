# Findyou 安装部署手册

> 适用版本：Findyou v2.0+  
> 最后更新：2026-03-20

---

## 目录

1. [环境要求](#1-环境要求)
2. [本地开发部署](#2-本地开发部署)
3. [Linux 服务器部署](#3-linux-服务器部署)
4. [配置说明](#4-配置说明)
5. [获取 API Key](#5-获取-api-key)
6. [邮件配置](#6-邮件配置)
7. [常见问题](#7-常见问题)

---

## 1. 环境要求

| 项目 | 最低要求 | 推荐 |
|------|---------|------|
| 操作系统 | Linux / macOS / Windows | Ubuntu 22.04 LTS |
| Python | 3.9+ | 3.11+ |
| 内存 | 512MB | 1GB+ |
| 磁盘 | 200MB | 1GB+ |
| 网络 | 需能访问 api.deepseek.com | — |

---

## 2. 本地开发部署

### Step 1：克隆代码

```bash
git clone https://github.com/sunboygavin/findyou-repo.git
cd findyou-repo
```

### Step 2：创建虚拟环境（推荐）

```bash
python3 -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### Step 3：安装依赖

```bash
pip install -r requirements.txt
```

### Step 4：配置 API Key

编辑 `config.py`，填入你的 DeepSeek API Key：

```python
DEEPSEEK_API_KEY = 'sk-xxxxxxxxxxxxxxxx'
```

### Step 5：启动

```bash
python3 app.py
```

打开浏览器访问：**http://localhost:5001**

---

## 3. Linux 服务器部署

### 3.1 安装 Python 及依赖

```bash
# Ubuntu / Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

# CentOS / RHEL
sudo yum install -y python3 python3-pip git
```

### 3.2 克隆并配置

```bash
git clone https://github.com/sunboygavin/findyou-repo.git /opt/findyou
cd /opt/findyou
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3.3 设置环境变量（生产必须）

```bash
# 编辑 /etc/environment 或在启动脚本中设置
export SECRET_KEY="换成随机32位字符串"
export JWT_SECRET="换成另一个随机32位字符串"
```

生成随机密钥方法：
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3.4 使用 Gunicorn 启动（推荐生产）

```bash
pip install gunicorn

# 启动（4个worker）
gunicorn -w 4 -b 127.0.0.1:5001 app:app --daemon \
  --access-logfile /var/log/findyou-access.log \
  --error-logfile /var/log/findyou-error.log
```

### 3.5 配置 Nginx 反向代理

```bash
sudo apt install -y nginx
sudo nano /etc/nginx/sites-available/findyou
```

填入以下内容：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 改成你的域名或IP

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # SSE（流式对话）必须关闭缓冲
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/findyou /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3.6 配置 systemd 开机自启

```bash
sudo nano /etc/systemd/system/findyou.service
```

```ini
[Unit]
Description=Findyou AI Digital Employee Platform
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/findyou
Environment="SECRET_KEY=your-secret-key"
Environment="JWT_SECRET=your-jwt-secret"
ExecStart=/opt/findyou/venv/bin/gunicorn -w 4 -b 127.0.0.1:5001 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable findyou
sudo systemctl start findyou
sudo systemctl status findyou
```

### 3.7 配置 HTTPS（Let's Encrypt）

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 4. 配置说明

所有配置集中在 `config.py`：

```python
class Config:
    # 应用安全
    SECRET_KEY = '...'          # Flask session 密钥（生产必改）
    JWT_SECRET = '...'          # JWT签名密钥（生产必改）
    JWT_EXPIRY_HOURS = 24       # Token有效期（小时）

    # 数据库（默认SQLite，可改为PostgreSQL）
    SQLALCHEMY_DATABASE_URI = 'sqlite:///findyou.db'
    # PostgreSQL示例：
    # SQLALCHEMY_DATABASE_URI = 'postgresql://user:pass@localhost/findyou'

    # DeepSeek AI
    DEEPSEEK_API_KEY = 'sk-xxx'
    DEEPSEEK_BASE_URL = 'https://api.deepseek.com/v1'
    DEEPSEEK_MODEL = 'deepseek-chat'

    # 邮件通知
    SMTP_HOST = 'smtp.126.com'  # 邮件服务商
    SMTP_PORT = 465             # SSL端口
    SMTP_USER = 'xxx@126.com'   # 发件邮箱
    SMTP_PASS = 'xxx'           # SMTP授权码（非登录密码）
    NOTIFY_EMAIL = 'xxx@qq.com' # 线索通知收件箱
```

---

## 5. 获取 API Key

### DeepSeek API Key

1. 访问 [platform.deepseek.com](https://platform.deepseek.com)
2. 注册/登录账号
3. 进入「API Keys」页面
4. 点击「创建 API Key」
5. 复制 Key 填入 `config.py` 的 `DEEPSEEK_API_KEY`

> 💡 DeepSeek 按 token 计费，价格极低，100万 token 约 ¥1。

---

## 6. 邮件配置

### 使用 126 邮箱（推荐）

1. 登录 [mail.126.com](https://mail.126.com)
2. 设置 → POP3/SMTP/IMAP
3. 开启「SMTP服务」
4. 生成「授权码」（非登录密码）
5. 填入 `config.py`：
   ```python
   SMTP_HOST = 'smtp.126.com'
   SMTP_PORT = 465
   SMTP_USER = 'your@126.com'
   SMTP_PASS = '授权码'
   ```

### 使用 QQ 邮箱

```python
SMTP_HOST = 'smtp.qq.com'
SMTP_PORT = 465
SMTP_USER = 'your@qq.com'
SMTP_PASS = 'QQ邮箱授权码'  # 在QQ邮箱设置→账户→生成授权码
```

### 使用 Gmail

```python
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = 'your@gmail.com'
SMTP_PASS = 'App Password'  # Google账号→安全性→应用密码
```

---

## 7. 常见问题

### Q: 启动后访问空白/报错？

```bash
# 查看错误日志
python3 app.py  # 直接运行看错误信息
```

常见原因：
- 依赖未安装：`pip install -r requirements.txt`
- Python版本过低：需要 3.9+

---

### Q: AI对话没有回复？

检查 DeepSeek API Key 是否正确：
```bash
python3 -c "
from openai import OpenAI
client = OpenAI(api_key='your-key', base_url='https://api.deepseek.com/v1')
r = client.chat.completions.create(model='deepseek-chat', messages=[{'role':'user','content':'hi'}])
print(r.choices[0].message.content)
"
```

---

### Q: 邮件发送失败？

1. 确认使用的是**授权码**，不是登录密码
2. 确认 SMTP 服务已在邮箱设置中开启
3. 检查防火墙是否放通 465 端口

---

### Q: 如何迁移数据库？

```bash
# 备份
cp findyou.db findyou.db.bak

# 查看数据
python3 -c "
import sqlite3
conn = sqlite3.connect('findyou.db')
print('Users:', conn.execute('SELECT count(*) FROM users').fetchone()[0])
print('Leads:', conn.execute('SELECT count(*) FROM leads').fetchone()[0])
conn.close()
"
```

---

### Q: 如何更新代码？

```bash
cd /opt/findyou
git pull origin main
sudo systemctl restart findyou
```

---

## 📞 技术支持

- GitHub Issues：https://github.com/sunboygavin/findyou-repo/issues
- 邮件：contact@findyou.ai
