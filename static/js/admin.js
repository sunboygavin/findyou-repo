/**
 * Findyou Admin Dashboard
 */
const AdminState = {
  token: localStorage.getItem('fy_token') || '',
  currentSection: 'dashboard',
};

// ─── API ─────────────────────────────────────────────────────────────────────
async function adminGet(url) {
  const headers = {};
  if (AdminState.token) headers['Authorization'] = 'Bearer ' + AdminState.token;
  const res = await fetch(url, { headers });
  if (res.status === 401 || res.status === 403) {
    window.location.href = '/';
    return {};
  }
  return res.json();
}

async function adminPut(url, body) {
  const headers = { 'Content-Type': 'application/json' };
  if (AdminState.token) headers['Authorization'] = 'Bearer ' + AdminState.token;
  const res = await fetch(url, { method: 'PUT', headers, body: JSON.stringify(body) });
  return res.json();
}

// ─── Navigation ──────────────────────────────────────────────────────────────
function switchSection(name) {
  AdminState.currentSection = name;
  document.querySelectorAll('.admin-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.admin-nav li').forEach(l => l.classList.remove('active'));
  const section = document.getElementById('section-' + name);
  if (section) section.classList.add('active');
  const nav = document.querySelector(`[data-section="${name}"]`);
  if (nav) nav.classList.add('active');

  if (name === 'dashboard') loadDashboard();
  else if (name === 'leads') loadLeads();
  else if (name === 'users') loadUsers();
  else if (name === 'usage') loadUsageAnalytics();
}

// ─── Dashboard ───────────────────────────────────────────────────────────────
let trendChart = null;

async function loadDashboard() {
  const [stats, trends] = await Promise.all([
    adminGet('/api/admin/stats'),
    adminGet('/api/admin/stats/trends?days=7'),
  ]);
  if (!stats.success) return;

  document.getElementById('stat-users').textContent = stats.total_users;
  document.getElementById('stat-convs').textContent = stats.total_conversations;
  document.getElementById('stat-leads').textContent = stats.total_leads;
  document.getElementById('stat-usage').textContent = stats.total_usage;
  document.getElementById('stat-today-users').textContent = '+' + stats.today_users + ' 今日';
  document.getElementById('stat-today-convs').textContent = '+' + stats.today_conversations + ' 今日';
  document.getElementById('stat-today-leads').textContent = '+' + stats.today_leads + ' 今日';
  document.getElementById('stat-today-usage').textContent = '+' + stats.today_usage + ' 今日';

  // Leads by status
  const lbs = stats.leads_by_status || {};
  document.getElementById('leads-status-summary').innerHTML =
    `<span class="badge badge-new">新线索 ${lbs.new || 0}</span>
     <span class="badge badge-contacted">已联系 ${lbs.contacted || 0}</span>
     <span class="badge badge-converted">已转化 ${lbs.converted || 0}</span>
     <span class="badge badge-closed">已关闭 ${lbs.closed || 0}</span>`;

  // Trend chart
  if (trends.success && window.Chart) {
    const days = [];
    const now = new Date();
    for (let i = trends.days - 1; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      days.push(d.toISOString().slice(0, 10));
    }
    const datasets = [
      { label: '注册', data: days.map(d => trends.users[d] || 0), borderColor: '#0071e3', tension: 0.3 },
      { label: '对话', data: days.map(d => trends.conversations[d] || 0), borderColor: '#34c759', tension: 0.3 },
      { label: '线索', data: days.map(d => trends.leads[d] || 0), borderColor: '#ff9500', tension: 0.3 },
      { label: '调用', data: days.map(d => trends.usage[d] || 0), borderColor: '#af52de', tension: 0.3 },
    ];
    datasets.forEach(ds => { ds.fill = false; ds.borderWidth = 2; ds.pointRadius = 3; });

    const ctx = document.getElementById('trend-chart');
    if (trendChart) trendChart.destroy();
    trendChart = new Chart(ctx, {
      type: 'line',
      data: { labels: days.map(d => d.slice(5)), datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom' } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      }
    });
  }
}

// ─── Leads ───────────────────────────────────────────────────────────────────
let leadsPage = 1;
let leadsFilter = '';

async function loadLeads(page, status) {
  if (page !== undefined) leadsPage = page;
  if (status !== undefined) leadsFilter = status;
  let url = '/api/leads?page=' + leadsPage + '&per_page=20';
  if (leadsFilter) url += '&status=' + leadsFilter;
  const res = await adminGet(url);
  if (!res.success) return;

  const tbody = document.getElementById('leads-tbody');
  tbody.innerHTML = res.leads.map(l => `
    <tr>
      <td>${l.id}</td>
      <td><strong>${esc(l.name)}</strong><br><span style="color:#888;font-size:12px">${esc(l.phone)}</span></td>
      <td>${esc(l.company)}</td>
      <td>${esc(l.plan)}</td>
      <td>
        <select onchange="updateLeadStatus(${l.id}, this.value)" style="padding:4px 8px;border:1px solid #e5e5e5;border-radius:6px;font-size:12px">
          ${['new','contacted','converted','closed'].map(s =>
            `<option value="${s}" ${l.status===s?'selected':''}>${{new:'新线索',contacted:'已联系',converted:'已转化',closed:'已关闭'}[s]}</option>`
          ).join('')}
        </select>
      </td>
      <td style="max-width:200px;font-size:12px;color:#666">${esc(l.message).slice(0, 80)}</td>
      <td>
        <textarea class="notes-input" onblur="updateLeadNotes(${l.id}, this.value)" placeholder="添加备注...">${esc(l.notes)}</textarea>
      </td>
      <td style="font-size:12px;color:#888">${new Date(l.created_at).toLocaleDateString('zh-CN')}</td>
    </tr>`).join('');

  document.getElementById('leads-pagination').innerHTML = `
    <button onclick="loadLeads(${leadsPage - 1})" ${leadsPage <= 1 ? 'disabled' : ''}>上一页</button>
    <span>第 ${res.page} / ${res.pages} 页 (共 ${res.total} 条)</span>
    <button onclick="loadLeads(${leadsPage + 1})" ${leadsPage >= res.pages ? 'disabled' : ''}>下一页</button>`;
}

async function updateLeadStatus(id, status) {
  await adminPut('/api/admin/leads/' + id, { status });
}

async function updateLeadNotes(id, notes) {
  await adminPut('/api/admin/leads/' + id, { notes });
}

// ─── Users ───────────────────────────────────────────────────────────────────
let usersPage = 1;
let usersSearch = '';

async function loadUsers(page, search) {
  if (page !== undefined) usersPage = page;
  if (search !== undefined) usersSearch = search;
  let url = '/api/admin/users?page=' + usersPage + '&per_page=20';
  if (usersSearch) url += '&q=' + encodeURIComponent(usersSearch);
  const res = await adminGet(url);
  if (!res.success) return;

  const tbody = document.getElementById('users-tbody');
  tbody.innerHTML = res.users.map(u => `
    <tr>
      <td>${u.id}</td>
      <td><strong>${esc(u.username)}</strong></td>
      <td>${esc(u.email)}</td>
      <td>${esc(u.company || '-')}</td>
      <td><span class="badge ${u.is_active !== false ? 'badge-active' : 'badge-inactive'}">${u.is_active !== false ? '正常' : '禁用'}</span></td>
      <td>${u.is_admin ? '✅' : ''}</td>
      <td style="font-size:12px;color:#888">${new Date(u.created_at).toLocaleDateString('zh-CN')}</td>
      <td>
        <button class="btn-sm" onclick="toggleUserActive(${u.id}, ${u.is_active === false})">${u.is_active !== false ? '禁用' : '启用'}</button>
        <button class="btn-sm" onclick="showUserDetail(${u.id})">详情</button>
      </td>
    </tr>`).join('');

  document.getElementById('users-pagination').innerHTML = `
    <button onclick="loadUsers(${usersPage - 1})" ${usersPage <= 1 ? 'disabled' : ''}>上一页</button>
    <span>第 ${res.page} / ${res.pages} 页 (共 ${res.total} 条)</span>
    <button onclick="loadUsers(${usersPage + 1})" ${usersPage >= res.pages ? 'disabled' : ''}>下一页</button>`;
}

function searchUsers() {
  const q = document.getElementById('users-search-input').value.trim();
  loadUsers(1, q);
}

async function toggleUserActive(uid, activate) {
  await adminPut('/api/admin/users/' + uid, { is_active: activate });
  loadUsers();
}

async function showUserDetail(uid) {
  const res = await adminGet('/api/admin/users/' + uid + '/detail');
  if (!res.success) return;
  const u = res.user;
  const s = res.stats;
  const sub = s.subscription;
  alert(
    `用户: ${u.username}\n邮箱: ${u.email}\n公司: ${u.company || '-'}\n` +
    `对话数: ${s.conversation_count}\n本月调用: ${s.monthly_usage}\n总调用: ${s.total_usage}\n` +
    `套餐: ${sub ? sub.plan.display_name : '无'}`
  );
}

// ─── Usage Analytics ─────────────────────────────────────────────────────────
let usageChart = null;

async function loadUsageAnalytics() {
  const days = document.getElementById('usage-days')?.value || 7;
  const res = await adminGet('/api/admin/usage?days=' + days);
  if (!res.success) return;

  // Employee breakdown
  const empNames = { ada:'财务会计 Ada', max:'数据分析师 Max', shield:'安全顾问 Shield', eva:'行政助理 Eva', kai:'销售顾问 Kai', nova:'内容创作 Nova', lex:'法务顾问 Lex', mia:'HR专员 Mia' };
  const empColors = { ada:'#34c759', max:'#0071e3', shield:'#ff3b30', eva:'#ff9500', kai:'#af52de', nova:'#ff2d55', lex:'#5856d6', mia:'#ff6b35' };

  const byEmp = res.by_employee || {};
  const empLabels = Object.keys(byEmp).map(k => empNames[k] || k);
  const empData = Object.values(byEmp);
  const empColorArr = Object.keys(byEmp).map(k => empColors[k] || '#888');

  const ctx = document.getElementById('usage-chart');
  if (usageChart) usageChart.destroy();
  if (empData.length > 0 && window.Chart) {
    usageChart = new Chart(ctx, {
      type: 'doughnut',
      data: { labels: empLabels, datasets: [{ data: empData, backgroundColor: empColorArr }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
    });
  }

  // Top users
  const topEl = document.getElementById('usage-top-users');
  topEl.innerHTML = (res.top_users || []).map((item, i) => `
    <tr>
      <td>${i + 1}</td>
      <td>${esc(item.user.username)}</td>
      <td>${esc(item.user.email)}</td>
      <td><strong>${item.calls}</strong></td>
    </tr>`).join('') || '<tr><td colspan="4" style="text-align:center;color:#888;padding:20px">暂无数据</td></tr>';
}

// ─── Utility ─────────────────────────────────────────────────────────────────
function esc(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ─── Init ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  switchSection('dashboard');
});
