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

// ─── Typewriter Queue ─────────────────────────────────────────────────────────
const TypeWriter = {
  queue: '',
  timer: null,
  targetId: null,
  fullAccum: '',
  speed: 18, // ms per char
  start(id) {
    this.queue = '';
    this.fullAccum = '';
    this.targetId = id;
    this.timer = null;
  },
  push(text) {
    this.queue += text;
    if (!this.timer) this._tick();
  },
  _tick() {
    if (!this.queue.length) { this.timer = null; return; }
    const ch = this.queue[0];
    this.queue = this.queue.slice(1);
    this.fullAccum += ch;
    const el = document.getElementById(this.targetId);
    if (el) {
      el.innerHTML = formatText(this.fullAccum) + '<span class="typing-cursor"></span>';
      scrollToBottom();
    }
    this.timer = setTimeout(() => this._tick(), this.speed);
  },
  finish() {
    // flush remaining
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    if (this.queue.length) {
      this.fullAccum += this.queue;
      this.queue = '';
    }
    const el = document.getElementById(this.targetId);
    if (el) el.innerHTML = formatText(this.fullAccum);
    return this.fullAccum;
  }
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
      <span class="nav-username" onclick="showProfileModal()" style="cursor:pointer" title="个人资料">👤 ${State.user.username}</span>
      <button class="btn-pill btn-outline" onclick="showUsageModal()">用量</button>
      <button class="btn-pill btn-outline" onclick="showHistory()">对话记录</button>
      ${State.user.is_admin ? '<a href="/admin" class="btn-pill btn-outline">管理后台</a>' : ''}
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
        <button class="chat-clear-btn" onclick="showEmployeeConfig('${employeeType}')" title="个性化设置">⚙️</button>
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
  TypeWriter.start(aiMsgId);

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
            TypeWriter.push(data.text);
          }
          if (data.done) {
            if (data.conversation_id) State.currentConvId = data.conversation_id;
            if (data.usage_warning) showToast('⚠️ ' + data.usage_warning, 5000);
            if (data.quota_exceeded) showToast('❌ 本月用量已达上限，请升级套餐', 5000);
            fullText = TypeWriter.finish();
          }
          if (data.error) {
            const bubbleEl = document.getElementById(aiMsgId);
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
    div.innerHTML = `<span class="msg-avatar">${emp.emoji || '🤖'}</span><div class="msg-content"><div class="msg-bubble" ${id ? `id="${id}"` : ''} ondblclick="copyMsg(this)" title="双击复制">${html}</div><span class="msg-time">${timeStr}</span></div>`;
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
  // Tables
  s = s.replace(/\|(.+)\|\n\|[-| :]+\|\n((?:\|.+\|\n?)*)/g, (match, header, body) => {
    const ths = header.split('|').filter(c => c.trim()).map(c => `<th>${c.trim()}</th>`).join('');
    const rows = body.trim().split('\n').map(row => {
      const tds = row.split('|').filter(c => c.trim()).map(c => `<td>${c.trim()}</td>`).join('');
      return `<tr>${tds}</tr>`;
    }).join('');
    return `<div class="msg-table-wrap"><table class="msg-table"><thead><tr>${ths}</tr></thead><tbody>${rows}</tbody></table></div>`;
  });
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
  let modal = document.getElementById('history-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'history-modal';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }
  modal.innerHTML = `<div class="modal-box history-box"><div class="modal-header"><h3>对话记录</h3><button class="modal-close" onclick="closeModal('history-modal')">✕</button></div><div class="history-list"><p style="text-align:center;color:#888;padding:32px">加载中...</p></div></div>`;
  modal.style.display = 'flex';
  await renderHistoryList(modal);
}

async function renderHistoryList(modal, searchQuery) {
  let res;
  if (searchQuery) {
    res = await apiGet('/api/conversations/search?q=' + encodeURIComponent(searchQuery));
  } else {
    res = await apiGet('/api/conversations');
  }
  const convs = res.conversations || [];
  const items = convs.length === 0
    ? `<div class="history-empty"><p>${searchQuery ? '未找到匹配的对话' : '暂无对话记录'}</p></div>`
    : convs.map(c => {
        const emp = EMPLOYEES[c.employee_type] || {};
        const preview = c.preview || c.title || '无消息';
        return `<div class="history-item">
          <div class="history-item-main" onclick="loadConvById('${c.employee_type}', ${c.id})">
            <span class="history-emp">${emp.emoji || '🤖'} ${emp.name || c.employee_type}</span>
            <span class="history-preview">${escHtml(preview.slice(0, 60))}</span>
            <span class="history-time">${new Date(c.created_at).toLocaleDateString('zh-CN')}</span>
          </div>
          <div class="history-item-actions">
            <button onclick="exportConv(${c.id}, 'md')" title="导出Markdown">📄</button>
            <button onclick="exportConv(${c.id}, 'json')" title="导出JSON">📋</button>
            <button onclick="deleteConv(${c.id})" title="删除">🗑️</button>
          </div>
        </div>`;
      }).join('');

  const box = modal.querySelector('.modal-box') || modal;
  box.innerHTML = `
    <div class="modal-header">
      <h3>对话记录</h3>
      <button class="modal-close" onclick="closeModal('history-modal')">✕</button>
    </div>
    <div class="history-search">
      <input type="text" id="history-search-input" placeholder="搜索对话内容..." value="${escHtml(searchQuery || '')}" onkeydown="if(event.key==='Enter')searchHistory()">
      <button onclick="searchHistory()">🔍</button>
    </div>
    <div class="history-list">${items}</div>`;
}

function searchHistory() {
  const q = document.getElementById('history-search-input')?.value?.trim();
  const modal = document.getElementById('history-modal');
  if (modal) renderHistoryList(modal, q || '');
}

async function loadConvById(employeeType, convId) {
  const res = await apiGet('/api/conversations/' + convId);
  if (res.messages) {
    closeModal('history-modal');
    State.currentEmployee = employeeType;
    State.currentConvId = convId;
    State.history = res.messages;
    openChat(employeeType);
    setTimeout(() => {
      const container = document.getElementById('chat-messages');
      if (!container) return;
      container.innerHTML = '';
      res.messages.forEach(m => appendMessage(m.role === 'user' ? 'user' : 'ai', m.role === 'user' ? m.content : formatText(m.content)));
      scrollToBottom();
    }, 100);
  }
}

async function deleteConv(convId) {
  if (!confirm('确定删除这条对话记录？')) return;
  const headers = {};
  if (State.token) headers['Authorization'] = 'Bearer ' + State.token;
  await fetch('/api/conversations/' + convId, { method: 'DELETE', headers });
  showToast('已删除');
  const modal = document.getElementById('history-modal');
  if (modal) renderHistoryList(modal);
}

function exportConv(convId, format) {
  const headers = {};
  if (State.token) headers['Authorization'] = 'Bearer ' + State.token;
  fetch('/api/conversations/' + convId + '/export?format=' + format, { headers }).then(res => {
    if (format === 'md') {
      res.blob().then(blob => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'conversation_' + convId + '.md';
        a.click();
      });
    } else {
      res.json().then(data => {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'conversation_' + convId + '.json';
        a.click();
      });
    }
  });
  showToast('正在导出...');
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

function copyMsg(el) {
  const text = el.innerText || el.textContent;
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => showToast('已复制到剪贴板 ✓'));
  } else {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    showToast('已复制到剪贴板 ✓');
  }
}

// ─── API helpers (extended) ──────────────────────────────────────────────────
async function apiPut(url, body) {
  const headers = { 'Content-Type': 'application/json' };
  if (State.token) headers['Authorization'] = 'Bearer ' + State.token;
  const res = await fetch(url, { method: 'PUT', headers, body: JSON.stringify(body) });
  return res.json();
}

// ─── Profile Modal ───────────────────────────────────────────────────────────
async function showProfileModal() {
  if (!State.user) { showAuthModal('login'); return; }
  const res = await apiGet('/api/profile');
  if (!res.success) return;
  const u = res.user;
  const sub = res.subscription;

  let modal = document.getElementById('profile-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'profile-modal';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }
  modal.innerHTML = `
    <div class="modal-box" style="max-width:480px">
      <div class="modal-header">
        <h3>个人资料</h3>
        <button class="modal-close" onclick="closeModal('profile-modal')">✕</button>
      </div>
      <div style="padding:20px">
        <div class="form-group"><label>用户名</label><input value="${escHtml(u.username)}" disabled style="opacity:0.6"></div>
        <div class="form-group"><label>邮箱</label><input value="${escHtml(u.email)}" disabled style="opacity:0.6"></div>
        <div class="form-group"><label>手机</label><input id="prof-phone" value="${escHtml(u.phone || '')}" placeholder="选填"></div>
        <div class="form-group"><label>公司</label><input id="prof-company" value="${escHtml(u.company || '')}" placeholder="选填"></div>
        <div class="form-group"><label>简介</label><textarea id="prof-bio" rows="2" placeholder="选填">${escHtml(u.bio || '')}</textarea></div>
        <button class="btn-pill btn-primary btn-full" onclick="saveProfile()">保存资料</button>
        <hr style="margin:20px 0;border:none;border-top:1px solid #eee">
        <h4 style="margin-bottom:12px">修改密码</h4>
        <div class="form-group"><label>旧密码</label><input id="pw-old" type="password"></div>
        <div class="form-group"><label>新密码</label><input id="pw-new" type="password" placeholder="至少6位"></div>
        <div id="pw-msg" style="color:#ff3b30;font-size:13px;margin-bottom:8px"></div>
        <button class="btn-pill btn-outline btn-full" onclick="changePassword()">修改密码</button>
        ${sub ? `<div style="margin-top:16px;padding:12px;background:#f5f5f7;border-radius:8px;font-size:13px">
          <strong>当前套餐：</strong>${escHtml(sub.plan?.display_name || '免费')}<br>
          <strong>到期时间：</strong>${sub.expires_at ? new Date(sub.expires_at).toLocaleDateString('zh-CN') : '无'}
        </div>` : ''}
      </div>
    </div>`;
  modal.style.display = 'flex';
}

async function saveProfile() {
  const res = await apiPut('/api/profile', {
    phone: document.getElementById('prof-phone').value,
    company: document.getElementById('prof-company').value,
    bio: document.getElementById('prof-bio').value,
  });
  if (res.success) {
    State.user = res.user;
    localStorage.setItem('fy_user', JSON.stringify(res.user));
    showToast('资料已保存');
    closeModal('profile-modal');
  } else {
    showToast(res.error || '保存失败');
  }
}

async function changePassword() {
  const msgEl = document.getElementById('pw-msg');
  const res = await apiPut('/api/password', {
    old_password: document.getElementById('pw-old').value,
    new_password: document.getElementById('pw-new').value,
  });
  if (res.success) {
    showToast('密码修改成功');
    document.getElementById('pw-old').value = '';
    document.getElementById('pw-new').value = '';
    msgEl.textContent = '';
  } else {
    msgEl.textContent = res.error || '修改失败';
  }
}

// ─── Usage Modal ─────────────────────────────────────────────────────────────
async function showUsageModal() {
  if (!State.user) { showAuthModal('login'); return; }
  const res = await apiGet('/api/usage');
  if (!res.success) return;

  let modal = document.getElementById('usage-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'usage-modal';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }

  const pct = res.percentage || 0;
  const barColor = pct >= 90 ? '#ff3b30' : pct >= 80 ? '#ff9500' : '#34c759';
  const breakdownHtml = Object.keys(res.breakdown || {}).map(k => {
    const emp = EMPLOYEES[k] || {};
    return `<div style="display:flex;justify-content:space-between;padding:4px 0"><span>${emp.emoji || ''} ${emp.name || k}</span><span>${res.breakdown[k]} 次</span></div>`;
  }).join('') || '<p style="color:#888">暂无使用记录</p>';

  modal.innerHTML = `
    <div class="modal-box" style="max-width:420px">
      <div class="modal-header">
        <h3>本月用量</h3>
        <button class="modal-close" onclick="closeModal('usage-modal')">✕</button>
      </div>
      <div style="padding:20px">
        <div style="text-align:center;margin-bottom:20px">
          <div style="font-size:36px;font-weight:700">${res.total_calls}</div>
          <div style="color:#888;font-size:14px">/ ${res.max_calls} 次</div>
          <div style="background:#f0f0f0;border-radius:8px;height:8px;margin-top:12px;overflow:hidden">
            <div style="background:${barColor};height:100%;width:${Math.min(pct, 100)}%;border-radius:8px;transition:width 0.3s"></div>
          </div>
          <div style="font-size:13px;color:${barColor};margin-top:4px">${pct}%</div>
        </div>
        <h4 style="margin-bottom:8px">按员工分布</h4>
        ${breakdownHtml}
        <button class="btn-pill btn-primary btn-full" style="margin-top:20px" onclick="closeModal('usage-modal');showSubscriptionModal()">升级套餐</button>
      </div>
    </div>`;
  modal.style.display = 'flex';
}

// ─── Subscription Modal ──────────────────────────────────────────────────────
async function showSubscriptionModal() {
  if (!State.user) { showAuthModal('login'); return; }
  const [plansRes, subRes] = await Promise.all([apiGet('/api/plans'), apiGet('/api/subscription')]);
  const plans = plansRes.plans || [];
  const currentSub = subRes.subscription;
  const currentPlan = currentSub?.plan?.name || '';

  let modal = document.getElementById('sub-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'sub-modal';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }

  const planCards = plans.map(p => {
    const isCurrent = p.name === currentPlan;
    const price = p.price_monthly === 0 ? '定制报价' : '¥' + (p.price_monthly / 100) + '/月';
    return `<div class="plan-card ${isCurrent ? 'plan-current' : ''}" style="border:2px solid ${isCurrent ? '#0071e3' : '#e5e5e5'};border-radius:12px;padding:16px;margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <strong>${escHtml(p.display_name)}</strong>
          ${isCurrent ? '<span style="color:#0071e3;font-size:12px;margin-left:8px">当前</span>' : ''}
          <div style="color:#888;font-size:13px;margin-top:4px">${price} · ${p.max_employees}个员工 · ${p.max_calls_monthly.toLocaleString()}次/月</div>
        </div>
        ${isCurrent ? '' : `<button class="btn-pill btn-primary" onclick="subscribePlan('${p.name}')">选择</button>`}
      </div>
    </div>`;
  }).join('');

  modal.innerHTML = `
    <div class="modal-box" style="max-width:480px">
      <div class="modal-header">
        <h3>选择套餐</h3>
        <button class="modal-close" onclick="closeModal('sub-modal')">✕</button>
      </div>
      <div style="padding:20px">${planCards}</div>
    </div>`;
  modal.style.display = 'flex';
}

async function subscribePlan(planName) {
  const res = await apiPost('/api/subscription', { plan: planName });
  if (res.success) {
    showToast('套餐已激活 🎉');
    closeModal('sub-modal');
  } else {
    showToast(res.error || '操作失败');
  }
}

// ─── Employee Config (Personality) ───────────────────────────────────────────
async function showEmployeeConfig(empType) {
  if (!State.user) { showAuthModal('login'); return; }
  const emp = EMPLOYEES[empType];
  if (!emp) return;
  const res = await apiGet('/api/employee-config/' + empType);
  const cfg = res.config || {};

  let modal = document.getElementById('empconfig-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'empconfig-modal';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }

  const sliders = [
    { key: 'tone', label: '语气', left: '严肃', right: '轻松' },
    { key: 'formality', label: '正式度', left: '正式', right: '随意' },
    { key: 'proactiveness', label: '主动性', left: '被动', right: '主动' },
    { key: 'empathy', label: '共情力', left: '理性', right: '感性' },
    { key: 'creativity', label: '创造力', left: '保守', right: '创新' },
  ].map(s => `
    <div style="margin-bottom:16px">
      <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">
        <span>${s.left}</span><strong>${s.label}</strong><span>${s.right}</span>
      </div>
      <input type="range" min="0" max="100" value="${cfg[s.key] ?? 50}" id="ec-${s.key}" style="width:100%">
    </div>`).join('');

  modal.innerHTML = `
    <div class="modal-box" style="max-width:440px">
      <div class="modal-header">
        <h3>${emp.emoji} ${emp.name} — 个性化设置</h3>
        <button class="modal-close" onclick="closeModal('empconfig-modal')">✕</button>
      </div>
      <div style="padding:20px">
        ${sliders}
        <div class="form-group"><label>自定义指令</label><textarea id="ec-instructions" rows="3" placeholder="例如：回复时多用表格，语言简洁...">${escHtml(cfg.custom_instructions || '')}</textarea></div>
        <button class="btn-pill btn-primary btn-full" onclick="saveEmployeeConfig('${empType}')">保存设置</button>
      </div>
    </div>`;
  modal.style.display = 'flex';
}

async function saveEmployeeConfig(empType) {
  const res = await apiPut('/api/employee-config/' + empType, {
    tone: +document.getElementById('ec-tone').value,
    formality: +document.getElementById('ec-formality').value,
    proactiveness: +document.getElementById('ec-proactiveness').value,
    empathy: +document.getElementById('ec-empathy').value,
    creativity: +document.getElementById('ec-creativity').value,
    custom_instructions: document.getElementById('ec-instructions').value,
  });
  if (res.success) {
    showToast('个性化设置已保存');
    closeModal('empconfig-modal');
  } else {
    showToast(res.error || '保存失败');
  }
}

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  renderNavUser();
});
