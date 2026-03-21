/**
 * Findyou — Chat & Auth Module
 * 负责：登录/注册弹窗、AI对话窗口（SSE流式）、对话历史
 */

// ─── State ───────────────────────────────────────────────────────────────────
const State = {
  token: localStorage.getItem('fy_token') || '',
  user: JSON.parse(localStorage.getItem('fy_user') || 'null'),
  currentEmployee: null,
  currentConvId: null,
  history: [],   // [{role, content}]
  streaming: false,
};

function saveAuth(token, user) {
  State.token = token;
  State.user = user;
  localStorage.setItem('fy_token', token);
  localStorage.setItem('fy_user', JSON.stringify(user));
}

function clearAuth() {
  State.token = '';
  State.user = null;
  localStorage.removeItem('fy_token');
  localStorage.removeItem('fy_user');
}

// ─── Employee meta ────────────────────────────────────────────────────────────
const EMPLOYEES = {
  ada:    { name: '财务会计 Ada',   emoji: '📊', color: '#34c759', intro: '您好！我是 Ada，您的专属财务顾问。请问有什么财务问题需要帮忙？' },
  max:    { name: '数据分析师 Max', emoji: '📈', color: '#0071e3', intro: '嗨！我是 Max，数据就是我的语言。把你的数据难题告诉我吧！' },
  shield: { name: '安全顾问 Shield',emoji: '🛡️', color: '#ff3b30', intro: '你好，我是 Shield。安全无小事，请描述您的安全问题或需求。' },
  eva:    { name: '行政助理 Eva',   emoji: '📅', color: '#ff9500', intro: '您好！我是 Eva，让我来帮您处理行政事务，释放您的时间！' },
  kai:    { name: '销售顾问 Kai',   emoji: '🚀', color: '#af52de', intro: '嘿！我是 Kai，让我们一起把业绩推上去！有什么销售挑战吗？' },
  nova:   { name: '内容创作 Nova',  emoji: '✍️', color: '#ff2d55', intro: '你好！我是 Nova，创意是我的超能力。说说你需要什么内容？' },
  lex:    { name: '法务顾问 Lex',   emoji: '⚖️', color: '#5856d6', intro: '您好，我是 Lex。请描述您的法律问题，我将提供专业参考意见。' },
  mia:    { name: 'HR专员 Mia',     emoji: '👥', color: '#ff6b35', intro: '你好！我是 Mia，人才是企业最大的资产。有什么HR问题？' },
};

// ─── API helpers ──────────────────────────────────────────────────────────────
async function apiPost(url, body) {
  const headers = { 'Content-Type': 'application/json' };
  if (State.token) headers['Authorization'] = 'Bearer ' + State.token;
  const res = await fetch(url, { method: 'POST', headers, body: JSON.stringify(body) });
  return res.json();
}

async function apiGet(url) {
  const headers = {};
  if (State.token) headers['Authorization'] = 'Bearer ' + State.token;
  const res = await fetch(url, { headers });
  return res.json();
}

// ─── Auth UI ──────────────────────────────────────────────────────────────────
function renderNavUser() {
  const navRight = document.getElementById('nav-right');
  if (!navRight) return;
  if (State.user) {
    navRight.innerHTML = `
      <span class="nav-username">👤 ${State.user.username}</span>
      <button class="btn-pill btn-outline" onclick="showHistory()">对话记录</button>
      <button class="btn-pill btn-dark" onclick="doLogout()">退出</button>`;
  } else {
    navRight.innerHTML = `
      <button class="btn-pill btn-outline" onclick="showAuthModal('login')">登录</button>
      <button class="btn-pill btn-primary" onclick="showAuthModal('register')">免费注册</button>`;
  }
}

function showAuthModal(tab = 'login') {
  let modal = document.getElementById('auth-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'auth-modal';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }
  modal.innerHTML = `
    <div class="modal-box auth-box">
      <button class="modal-close" onclick="closeModal('auth-modal')">✕</button>
      <div class="auth-tabs">
        <button id="tab-login" class="auth-tab ${tab==='login'?'active':''}" onclick="switchTab('login')">登录</button>
        <button id="tab-register" class="auth-tab ${tab==='register'?'active':''}" onclick="switchTab('register')">注册</button>
      </div>
      <div id="auth-form-area"></div>
    </div>`;
  modal.style.display = 'flex';
  renderAuthForm(tab);
}

function switchTab(tab) {
  document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  renderAuthForm(tab);
}

function renderAuthForm(tab) {
  const area = document.getElementById('auth-form-area');
  if (!area) return;
  if (tab === 'login') {
    area.innerHTML = `
      <form onsubmit="doLogin(event)">
        <div class="form-group"><label>用户名</label><input id="login-username" type="text" placeholder="请输入用户名" required></div>
        <div class="form-group"><label>密码</label><input id="login-password" type="password" placeholder="请输入密码" required></div>
        <div id="auth-error" class="auth-error"></div>
        <button type="submit" class="btn-pill btn-primary btn-full">登录</button>
        <p class="auth-switch">还没有账号？<a href="#" onclick="switchTab('register')">立即注册</a></p>
      </form>`;
  } else {
    area.innerHTML = `
      <form onsubmit="doRegister(event)">
        <div class="form-group"><label>用户名</label><input id="reg-username" type="text" placeholder="3-20位字母数字" required></div>
        <div class="form-group"><label>邮箱</label><input id="reg-email" type="email" placeholder="your@email.com" required></div>
        <div class="form-group"><label>密码</label><input id="reg-password" type="password" placeholder="至少6位" required></div>
        <div id="auth-error" class="auth-error"></div>
        <button type="submit" class="btn-pill btn-primary btn-full">注册并体验</button>
        <p class="auth-switch">已有账号？<a href="#" onclick="switchTab('login')">直接登录</a></p>
      </form>`;
  }
}

async function doLogin(e) {
  e.preventDefault();
  const username = document.getElementById('login-username').value;
  const password = document.getElementById('login-password').value;
  const errEl = document.getElementById('auth-error');
  errEl.textContent = '登录中...';
  const res = await apiPost('/api/login', { username, password });
  if (res.success) {
    saveAuth(res.token, res.user);
    closeModal('auth-modal');
    renderNavUser();
    showToast('登录成功，欢迎回来 ' + res.user.username + ' 👋');
  } else {
    errEl.textContent = res.message || '登录失败';
  }
}

async function doRegister(e) {
  e.preventDefault();
  const username = document.getElementById('reg-username').value;
  const email = document.getElementById('reg-email').value;
  const password = document.getElementById('reg-password').value;
  const errEl = document.getElementById('auth-error');
  errEl.textContent = '注册中...';
  const res = await apiPost('/api/register', { username, email, password });
  if (res.success) {
    saveAuth(res.token, res.user);
    closeModal('auth-modal');
    renderNavUser();
    showToast('注册成功！欢迎加入 Findyou 🎉');
  } else {
    errEl.textContent = res.message || '注册失败';
  }
}

function doLogout() {
  clearAuth();
  renderNavUser();
  showToast('已退出登录');
}

// ─── Chat Modal ───────────────────────────────────────────────────────────────
function openChat(employeeType) {
  State.currentEmployee = employeeType;
  State.currentConvId = null;
  State.history = [];
  const emp = EMPLOYEES[employeeType];

  let modal = document.getElementById('chat-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'chat-modal';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }

  modal.innerHTML = `
    <div class="modal-box chat-box">
      <div class="chat-header" style="border-bottom:2px solid ${emp.color}20">
        <div class="chat-header-info">
          <span class="chat-emp-emoji">${emp.emoji}</span>
          <div>
            <div class="chat-emp-name">${emp.name}</div>
            <div class="chat-emp-status"><span class="status-dot" style="background:${emp.color}"></span>在线</div>
          </div>
        </div>
        <button class="chat-clear-btn" onclick="clearChat()" title="新对话">🔄</button>
        <button class="modal-close" onclick="closeModal('chat-modal')">✕</button>
      </div>
      <div class="chat-messages" id="chat-messages">
        <div class="msg msg-ai">
          <span class="msg-avatar">${emp.emoji}</span>
          <div class="msg-content"><div class="msg-bubble">${emp.intro}</div></div>
        </div>
      </div>
      <div class="chat-input-area">
        <textarea id="chat-input" placeholder="输入消息，Shift+Enter 换行，Enter 发送..." rows="2" onkeydown="handleChatKey(event)"></textarea>
        <button class="chat-send-btn" onclick="sendMessage()" style="background:${emp.color}" id="send-btn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
        </button>
      </div>
    </div>`;
  modal.style.display = 'flex';
  document.getElementById('chat-input').focus();
}

function handleChatKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
  // Auto-resize textarea
  setTimeout(() => {
    const ta = document.getElementById('chat-input');
    if (ta) { ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, 120) + 'px'; }
  }, 0);
}

async function sendMessage() {
  if (State.streaming) return;
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;
  input.value = '';

  appendMessage('user', message);
  State.history.push({ role: 'user', content: message });

  const empType = State.currentEmployee;
  const emp = EMPLOYEES[empType];

  // 创建AI回复气泡（带光标）
  const aiMsgId = 'ai-msg-' + Date.now();
  appendMessage('ai', '<span class="typing-cursor"></span>', aiMsgId);

  State.streaming = true;
  document.getElementById('send-btn').disabled = true;

  let fullText = '';

  try {
    const headers = { 'Content-Type': 'application/json' };
    if (State.token) headers['Authorization'] = 'Bearer ' + State.token;

    const res = await fetch('/api/chat', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        employee_type: empType,
        message,
        history: State.history.slice(-20),
        conversation_id: State.currentConvId
      })
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    const bubbleEl = document.getElementById(aiMsgId);

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.text) {
            fullText += data.text;
            if (bubbleEl) bubbleEl.innerHTML = formatText(fullText) + '<span class="typing-cursor"></span>';
            scrollToBottom();
          }
          if (data.done) {
            if (data.conversation_id) State.currentConvId = data.conversation_id;
            if (bubbleEl) bubbleEl.innerHTML = formatText(fullText);
          }
          if (data.error) {
            if (bubbleEl) bubbleEl.innerHTML = '⚠️ 出错了：' + data.error;
          }
        } catch (_) {}
      }
    }
  } catch (err) {
    const bubbleEl = document.getElementById(aiMsgId);
    if (bubbleEl) bubbleEl.innerHTML = '⚠️ 连接失败 <button class="retry-btn" onclick="retryLast()">重试</button>';
  }

  if (fullText) State.history.push({ role: 'assistant', content: fullText });
  State.streaming = false;
  document.getElementById('send-btn').disabled = false;
  document.getElementById('chat-input').focus();
}

function appendMessage(role, html, id) {
  const container = document.getElementById('chat-messages');
  if (!container) return;
  const empType = State.currentEmployee;
  const emp = EMPLOYEES[empType] || {};
  const div = document.createElement('div');
  div.className = 'msg msg-' + role;
  var now = new Date();
  var timeStr = now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
  if (role === 'ai') {
    div.innerHTML = `<span class="msg-avatar">${emp.emoji || '🤖'}</span><div class="msg-content"><div class="msg-bubble" ${id ? `id="${id}"` : ''}>${html}</div><span class="msg-time">${timeStr}</span></div>`;
  } else {
    div.innerHTML = `<div class="msg-content"><div class="msg-bubble">${escHtml(html)}</div><span class="msg-time">${timeStr}</span></div><span class="msg-avatar">👤</span>`;
  }
  container.appendChild(div);
  scrollToBottom();
}

function scrollToBottom() {
  const c = document.getElementById('chat-messages');
  if (c) c.scrollTop = c.scrollHeight;
}

function formatText(text) {
  let s = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  // Code blocks (```)
  s = s.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>');
  // Bold
  s = s.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Inline code
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Ordered lists
  s = s.replace(/^(\d+)\.\s+(.+)$/gm, '<li class="ol-item">$2</li>');
  // Unordered lists
  s = s.replace(/^[-•]\s+(.+)$/gm, '<li class="ul-item">$1</li>');
  // Wrap consecutive li
  s = s.replace(/((?:<li class="ol-item">.*<\/li>\n?)+)/g, '<ol>$1</ol>');
  s = s.replace(/((?:<li class="ul-item">.*<\/li>\n?)+)/g, '<ul>$1</ul>');
  // Newlines (outside of pre/ol/ul)
  s = s.replace(/\n/g, '<br>');
  // Clean up double <br> inside lists
  s = s.replace(/<br><\/?(ol|ul|li|pre)>/g, '</$1>');
  return s;
}

function escHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
}

// ─── History Modal ────────────────────────────────────────────────────────────
async function showHistory() {
  if (!State.user) { showAuthModal('login'); return; }
  const data = await apiGet('/api/conversations');
  const convs = data.conversations || [];

  let modal = document.getElementById('history-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'history-modal';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }

  const items = convs.length === 0
    ? '<p class="empty-hint">暂无对话记录</p>'
    : convs.map(c => {
        const emp = EMPLOYEES[c.employee_type] || {};
        const lastMsg = c.messages[c.messages.length - 1];
        const preview = lastMsg ? lastMsg.content.slice(0, 60) + '...' : '无消息';
        return `<div class="history-item" onclick="loadConversation('${c.employee_type}', ${c.id}, ${JSON.stringify(c.messages).replace(/"/g, '&quot;')})">
          <span class="history-emp">${emp.emoji || '🤖'} ${emp.name || c.employee_type}</span>
          <span class="history-preview">${escHtml(preview)}</span>
          <span class="history-time">${new Date(c.created_at).toLocaleDateString('zh-CN')}</span>
        </div>`;
      }).join('');

  modal.innerHTML = `
    <div class="modal-box history-box">
      <div class="modal-header">
        <h3>对话记录</h3>
        <button class="modal-close" onclick="closeModal('history-modal')">✕</button>
      </div>
      <div class="history-list">${items}</div>
    </div>`;
  modal.style.display = 'flex';
}

function loadConversation(employeeType, convId, messages) {
  closeModal('history-modal');
  State.currentEmployee = employeeType;
  State.currentConvId = convId;
  State.history = messages;
  openChat(employeeType);

  // 填充历史消息
  setTimeout(() => {
    const container = document.getElementById('chat-messages');
    if (!container) return;
    container.innerHTML = '';
    messages.forEach(m => appendMessage(m.role === 'user' ? 'user' : 'ai', m.role === 'user' ? m.content : formatText(m.content)));
    scrollToBottom();
  }, 100);
}

// ─── Utility ──────────────────────────────────────────────────────────────────
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = 'none';
}

function showToast(msg) {
  let t = document.getElementById('toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'toast';
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.className = 'toast show';
  setTimeout(() => t.className = 'toast', 2500);
}

// 点击遮罩关闭
document.addEventListener('click', e => {
  ['auth-modal','chat-modal','history-modal'].forEach(id => {
    const el = document.getElementById(id);
    if (el && e.target === el) closeModal(id);
  });
});



// Auto handle 401 (token expired)
async function apiPostSafe(url, body) {
  const res = await apiPost(url, body);
  if (res.error === '未授权，请先登录') {
    clearAuth();
    renderNavUser();
    showAuthModal('login');
    showToast('登录已过期，请重新登录');
  }
  return res;
}

function retryLast() {
  if (State.history.length > 0) {
    const lastUserMsg = [...State.history].reverse().find(m => m.role === 'user');
    if (lastUserMsg) {
      // Remove failed AI response
      const container = document.getElementById('chat-messages');
      if (container && container.lastChild) container.removeChild(container.lastChild);
      State.history = State.history.filter((m, i) => i < State.history.length - 1);
      document.getElementById('chat-input').value = lastUserMsg.content;
      State.history.pop(); // remove user msg too, sendMessage will re-add
      sendMessage();
    }
  }
}

// New conversation button
function clearChat() {
  if (!State.currentEmployee) return;
  State.currentConvId = null;
  State.history = [];
  const emp = EMPLOYEES[State.currentEmployee];
  const container = document.getElementById('chat-messages');
  if (container) {
    container.innerHTML = '<div class="msg msg-ai"><span class="msg-avatar">' + emp.emoji + '</span><div class="msg-bubble">' + emp.intro + '</div></div>';
  }
  showToast('已开启新对话');
}

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  renderNavUser();
});
