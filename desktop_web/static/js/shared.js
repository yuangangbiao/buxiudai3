/* shared.js - 5001 Web 全局公共函数
 * 复用于 orders/kanban/production/material/quality 等所有页面
 * v1.0 (2026-06-22) — 由悲观审计沉淀, 抽离 DRY 重复
 */

// ── 认证 ──
function getToken() {
  return localStorage.getItem('dispatch_token') || sessionStorage.getItem('dispatch_token') || '';
}

function getUser() {
  try { return JSON.parse(localStorage.getItem('dispatch_user') || 'null'); }
  catch (e) { return null; }
}

function setToken(token, user) {
  if (token) localStorage.setItem('dispatch_token', token);
  if (user) localStorage.setItem('dispatch_user', JSON.stringify(user));
}

function getCsrfToken() {
  return localStorage.getItem('csrf_token') || sessionStorage.getItem('csrf_token') || '';
}

function setCsrfToken(token) {
  if (token) localStorage.setItem('csrf_token', token);
}

function clearToken() {
  localStorage.removeItem('dispatch_token');
  localStorage.removeItem('dispatch_user');
  localStorage.removeItem('csrf_token');
  sessionStorage.clear();
}

function requireAuth() {
  if (!getToken()) {
    window.location.href = '/login';
    return false;
  }
  return true;
}

// ── 用户显示 ──
function showUser(elementId) {
  const user = getUser();
  const el = document.getElementById(elementId);
  if (el && user) el.textContent = '👤 ' + user.name;
}

// ── 错误提示 ──
function showError(elementId, msg, duration = 5000) {
  const box = document.getElementById(elementId);
  if (!box) return;
  box.textContent = msg;
  box.style.display = 'block';
  if (box._errorTimer) clearTimeout(box._errorTimer);
  box._errorTimer = setTimeout(() => { box.style.display = 'none'; }, duration);
}

function hideError(elementId) {
  const box = document.getElementById(elementId);
  if (box) box.style.display = 'none';
}

// ── XSS 转义 (必须用于所有 innerHTML 拼接) ──
function escapeHtml(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ── 安全 fetch (401 自动跳登录, CSRF 保护) ──
async function apiFetch(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers['X-Dispatch-Token'] = token;
  const method = (options.method || 'GET').toUpperCase();
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
    const csrfToken = getCsrfToken();
    if (csrfToken) headers['X-CSRF-Token'] = csrfToken;
  }
  options.headers = headers;

  try {
    const r = await fetch(url, options);
    if (r.status === 401) {
      window.location.href = '/login';
      return null;
    }
    return r;
  } catch (e) {
    console.error('apiFetch error:', e);
    throw e;
  }
}

// ── 自动刷新管理 (解决 setInterval 泄漏) ──
class AutoRefresh {
  constructor(callback, intervalMs = 30000, buttonId = null) {
    this.callback = callback;
    this.intervalMs = intervalMs;
    this.buttonId = buttonId;
    this.timer = null;
    this.countdown = intervalMs / 1000;
    this.countdownTimer = null;
    this.bindUnload();
  }

  start() {
    if (this.timer) return;
    this.tick();
    this.timer = setInterval(() => this.tick(), this.intervalMs);
    this.countdownTimer = setInterval(() => this.updateCountdown(), 1000);
    if (this.buttonId) this.updateButton(true);
  }

  stop() {
    if (this.timer) clearInterval(this.timer);
    if (this.countdownTimer) clearInterval(this.countdownTimer);
    this.timer = null;
    this.countdownTimer = null;
    if (this.buttonId) this.updateButton(false);
  }

  toggle() {
    if (this.timer) this.stop();
    else this.start();
  }

  tick() {
    this.countdown = this.intervalMs / 1000;
    if (typeof this.callback === 'function') this.callback();
  }

  updateCountdown() {
    if (!this.timer) return;
    this.countdown--;
    if (this.countdown < 0) this.countdown = 0;
    if (this.buttonId) {
      const btn = document.getElementById(this.buttonId);
      if (btn) {
        const icon = this.timer ? '⏸️' : '▶️';
        const text = this.timer ? `暂停 (${this.countdown}s)` : '开启自动刷新';
        btn.textContent = `${icon} ${text}`;
      }
    }
  }

  updateButton(active) {
    if (!this.buttonId) return;
    const btn = document.getElementById(this.buttonId);
    if (btn) btn.textContent = active ? `⏸️ 暂停 (${this.intervalMs / 1000}s)` : '▶️ 开启自动刷新';
  }

  bindUnload() {
    window.addEventListener('pagehide', () => this.stop());
    window.addEventListener('beforeunload', () => this.stop());
  }
}

// ── 退出登录 ──
function logout() {
  clearToken();
  window.location.href = '/login';
}

// ── 工具: 数字转字符串 (带 0 fallback) ──
function numOr(value, fallback = 0) {
  const n = Number(value);
  return isNaN(n) ? fallback : n;
}

// ── 工具: 截断字符串 (带省略号) ──
function truncate(s, maxLen, suffix = '…') {
  if (!s) return '';
  s = String(s);
  return s.length > maxLen ? s.substring(0, maxLen - 1) + suffix : s;
}

// ── 统一导航 (8 页面共享) ──
const NAV_ITEMS = [
  { id: 'home',         label: '🏠 首页',        href: '/' },
  { id: 'dashboard',    label: '📊 Dashboard',   href: '/dashboard' },
  { id: 'orders',       label: '📋 订单',        href: '/orders' },
  { id: 'order_query',  label: '🔍 订单查询',    href: '/order-query' },
  { id: 'order_import', label: '📥 批量导入',    href: '/order-import' },
  { id: 'kanban',       label: '📊 看板',        href: '/kanban' },
  { id: 'production',       label: '🏭 生产看板',     href: '/production' },
  { id: 'production_admin', label: '🏭 生产排单',     href: '/production-admin' },
  { id: 'material',        label: '📦 物料看板',    href: '/material' },
  { id: 'material_admin',  label: '📦 物料备料',    href: '/material-admin' },
  { id: 'shipment',         label: '🚚 发货',        href: '/shipment' },
  { id: 'shipment_admin',  label: '🚚 发货管理',    href: '/shipment-admin' },
  { id: 'process_track',    label: '🏭 工序追踪',    href: '/process-track' },
  { id: 'process_admin', label: '🔧 工序管理',    href: '/process-admin' },
  { id: 'quality',      label: '✅ 质检',        href: '/quality' },
  { id: 'quality_admin', label: '🔍 质检管理',    href: '/quality-admin' },
  { id: 'work_reports', label: '📝 报工',        href: '/work-reports' },
  { id: 'operators',    label: '👥 操作员',       href: '/operators' },
];

function renderNav(currentId, titleText) {
  const container = document.getElementById('appNav');
  if (!container) return;
  const user = getUser();
  const navLinks = NAV_ITEMS.map(item => {
    const isCurrent = item.id === currentId;
    const style = isCurrent
      ? 'background: rgba(255,255,255,0.3); border-color: rgba(255,255,255,0.6); font-weight: 600;'
      : '';
    return `<a href="${item.href}" style="${style}">${item.label}</a>`;
  }).join('');

  container.innerHTML = `
    <div class="navbar" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; padding: 12px 24px; display: flex; align-items: center; justify-content: space-between;">
      <h1 style="font-size: 18px; margin: 0;">${titleText || ''}</h1>
      <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
        <span style="font-size: 14px;">${user ? '👤 ' + escapeHtml(user.name) : ''}</span>
        ${navLinks}
        <button onclick="logout()" style="padding: 6px 12px; color: #fff; text-decoration: none; border: 1px solid rgba(255,255,255,0.3); border-radius: 4px; font-size: 13px; background: rgba(255,255,255,0.1); cursor: pointer;">退出登录</button>
      </div>
    </div>
  `;
}
