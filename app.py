from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

# 默认账号
USERS = {
    'admin': 'findyou2026',
    'demo': 'demo123'
}

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username', '')
    password = data.get('password', '')
    if username in USERS and USERS[username] == password:
        session['user'] = username
        return jsonify({'success': True, 'user': username})
    return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html', user=session.get('user', ''))

@app.route('/api/contact', methods=['POST'])
def contact():
    data = request.json
    print(f"[咨询] {data.get('name')} | {data.get('phone')} | {data.get('company')} | {data.get('plan')}")
    return jsonify({'success': True, 'message': '提交成功'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
