const API_PATH = '/api/dispatch-center';
var CONN = window.CONN || { activeBase: '' };
CONN.activeBase = '';
var CONTAINER_CENTER_BASE = (window.__CONN_CONFIG__ && window.__CONN_CONFIG__.containerCenterBase) || 'http://127.0.0.1:5002';
const CONFIG = {
    API_PREFIX: 'dc_api_',
    CACHE_TTL: 30,
    AUTO_REFRESH_MS: 60000,
    PROCESS_REFRESH_MS: 30000,
    SLOW_REQUEST_MS: 1000
};

let _loadingCount = 0;

function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (!overlay) return;
    if (show) {
        _loadingCount++;
        if (_loadingCount === 1) {
            overlay.style.display = 'flex';
        }
    } else {
        _loadingCount = Math.max(0, _loadingCount - 1);
        if (_loadingCount === 0) {
            overlay.style.display = 'none';
        }
    }
}

// ── XSS 防御 ──────────────────────────────────────────────
function escHtml(str) {
  if (typeof str !== 'string') return String(str || '');
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

// ── API 缓存工具 (localStorage + TTL + 容量控制) ──────────────
var CACHE_PREFIX = CONFIG.API_PREFIX;
var MAX_STORAGE_BYTES = parseInt(localStorage.getItem('_max_storage_bytes') || (2 * 1024 * 1024));

function apiCacheKey(path, opts) {
  return CACHE_PREFIX + path + (opts?.method ? '_' + opts.method : '_GET');
}
function _getStorageUsage() {
  var total = 0;
  for (var i = 0; i < localStorage.length; i++) {
    var k = localStorage.key(i);
    if (k && k.startsWith(CACHE_PREFIX)) {
      total += (k.length + (localStorage.getItem(k) || '').length) * 2;
    }
  }
  return total;
}
function _evictOldestCache() {
  var entries = [];
  for (var i = 0; i < localStorage.length; i++) {
    var k = localStorage.key(i);
    if (k && k.startsWith(CACHE_PREFIX)) {
      try {
        var raw = localStorage.getItem(k);
        var parsed = JSON.parse(raw);
        entries.push({ key: k, time: parsed.t || 0 });
      } catch { entries.push({ key: k, time: 0 }); }
    }
  }
  entries.sort(function(a, b) { return a.time - b.time; });
  var removeCount = Math.max(1, Math.floor(entries.length / 3));
  for (var j = 0; j < removeCount && j < entries.length; j++) {
    localStorage.removeItem(entries[j].key);
  }
}
function apiCacheGet(path, opts, ttlSec) {
  const k = apiCacheKey(path, opts);
  const raw = localStorage.getItem(k);
  if (!raw) return null;
  try {
    const { v, t } = JSON.parse(raw);
    if (Date.now() - t < ttlSec * 1000) return v;
    localStorage.removeItem(k);
  } catch {}
  return null;
}
function apiCacheSet(path, opts, data) {
  const k = apiCacheKey(path, opts);
  var value = JSON.stringify({ v: data, t: Date.now() });
  if (_getStorageUsage() > MAX_STORAGE_BYTES) {
    console.warn('[API Cache] 缓存接近上限，清理旧缓存');
    _evictOldestCache();
  }
  try {
    localStorage.setItem(k, value);
  } catch (e) {
    if (e.name === 'QuotaExceededError') {
      console.warn('[API Cache] localStorage已满，深度清理');
      _evictOldestCache();
      try {
        localStorage.setItem(k, value);
      } catch (e2) {
        if (e2.name === 'QuotaExceededError') {
          localStorage.clear();
          try { localStorage.setItem(k, value); } catch {}
        }
      }
    }
  }
}
function apiCacheDel(prefix) {
  const keys = [];
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i);
    if (k?.startsWith(prefix || CACHE_PREFIX)) keys.push(k);
  }
  keys.forEach(k => localStorage.removeItem(k));
}

function toast(msg, type) {
  const t = document.createElement('div');
  t.className = `toast ${type || 'info'}`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (id === 'template-modal' && modal) {
    const modalEl = modal.querySelector('.modal');
    if (modalEl) {
      const rect = modalEl.getBoundingClientRect();
      localStorage.setItem('tmpl-modal-width', rect.width);
      localStorage.setItem('tmpl-modal-height', rect.height);
    }
  }
  modal?.classList.remove('show');
}

function openModal(id) {
  const modal = document.getElementById(id);
  if (id === 'template-modal' && modal) {
    const savedWidth = localStorage.getItem('tmpl-modal-width');
    const savedHeight = localStorage.getItem('tmpl-modal-height');
    const modalEl = modal.querySelector('.modal');
    if (modalEl && savedWidth && savedHeight) {
      modalEl.style.width = savedWidth + 'px';
      modalEl.style.height = savedHeight + 'px';
    }
  }
  modal?.classList.add('show');
}

function api(path, opts = {}) {
  const startTime = performance.now();
  const url = API_PATH + path;
  const isGet = !opts?.method || opts.method === 'GET';
  const config = { headers: { 'Content-Type': 'application/json' }, ...opts };
  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }

  if (isGet) {
    const cached = apiCacheGet(path, opts, CONFIG.CACHE_TTL);
    if (cached) return Promise.resolve(cached);
  }

  const traceId = sessionStorage.getItem('trace_id') || '';

  return fetch(url, config)
    .then(async r => {
      if (!r.ok) {
        let errMsg = `HTTP ${r.status}: ${r.statusText}`;
        try {
          const errBody = await r.json();
          if (errBody?.message) errMsg = errBody.message;
        } catch (_) {}
        throw new Error(errMsg);
      }
      const traceIdHeader = r.headers.get('X-Trace-ID');
      if (traceIdHeader) sessionStorage.setItem('trace_id', traceIdHeader);
      return r.json();
    })
    .then(data => {
      const duration = performance.now() - startTime;
      if (duration > CONFIG.SLOW_REQUEST_MS) {
        console.warn(`[API] 慢请求: ${path} 耗时 ${duration.toFixed(0)}ms`);
      }

      if (data?.code !== 0) {
        throw new Error(data?.message || '请求失败');
      }

      if (isGet && data?.code === 0) apiCacheSet(path, opts, data);
      if (!isGet && data?.code === 0) setTimeout(refreshCurrentTab, 500);
      return data;
    })
    .catch(err => {
      // 网络错误自动重试一次
      if (!opts._retried && (err.name === 'TypeError' || err.message === 'Failed to fetch' || err.message === 'NetworkError')) {
        opts._retried = true;
        return api(path, opts);
      }
      if (path !== '/status' && path !== '/cloud/poll-data') {
        console.error(`[API] 请求失败: ${path}`, err);
        toast('请求失败: ' + (err.message || '网络错误'), 'error');
      }
      return { code: -1, message: err.message || '请求失败' };
    });
}

let cloudStatusTimer = null;
let processTabTimer = null;

function switchTab(name) {
  sessionStorage.setItem('dc_active_tab', name);
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  const items = document.querySelectorAll('.sidebar-item');
  const idx = ['overview', 'operators', 'tasks', 'messages', 'processes', 'rules', 'process-config', 'monitor', 'cloud', 'repairs', 'outsource', 'warehousing', 'feedback', 'quality-inspect', 'report-records', 'quality-regression', 'material-regression', 'outsource-regression', 'schedule-regression', 'schedule', 'material-dc', 'servers', 'system-config', 'sync-queue'].indexOf(name);
  if (items[idx]) items[idx].classList.add('active');
  apiCacheDel();
  if (name === 'overview') loadOverview();
  if (name === 'operators') { refreshOperators(); }
  if (name === 'tasks') loadOperators();
  if (name === 'messages') loadTemplates();
  if (name === 'processes') { document.getElementById('process-search').value = ''; loadProcesses(); }
  if (name === 'rules') { loadRules(); loadFlowMatchingRules(); }
  if (name === 'process-config') { loadProcessConfig(); }
  if (name === 'quality-inspect') { if(typeof loadQualityTab==='function') loadQualityTab(); }
  if (name === 'report-records') { if(typeof loadReportRecords==='function') loadReportRecords(); }
  if (name === 'quality-regression') { if(typeof loadQualityRegression==='function') loadQualityRegression(); }
  if (name === 'material-regression') { if(typeof loadMaterialRegression==='function') loadMaterialRegression(); }
  if (name === 'outsource-regression') { if(typeof loadOutsourceRegression==='function') loadOutsourceRegression(); }
  if (name === 'schedule-regression') { if(typeof loadScheduleRegression==='function') loadScheduleRegression(); }
  if (name === 'schedule') { if(typeof loadScheduleTab==='function') loadScheduleTab(); }
  if (name === 'material-dc') { if(typeof loadMaterialDc==='function') loadMaterialDc(); }
  if (name === 'monitor') { loadAlerts(); loadDispatchLog(); }
  if (name === 'sync-queue') { if(typeof loadSyncQueue==='function') loadSyncQueue(); }
  if (name === 'processes') {
    startProcessTabRefresh();
  } else {
    stopProcessTabRefresh();
  }
  if (name === 'cloud') {
    loadCloudConfig();
    startCloudStatusRefresh();
  } else {
    stopCloudStatusRefresh();
  }
  if (name === 'repairs') { loadRepairCategories(); loadRepairRecords(); }
  if (name === 'system-config') renderConfigCenter();
  if (name === 'servers') refreshServers();
  if (name === 'warehousing') loadWarehousing();
  if (name === 'feedback') loadFeedbackList();
}

function _startPollingWithBackoff(getTimer, setTimer, fn, baseInterval, maxInterval) {
  if (getTimer()) return;
  let failCount = 0;

  function schedule() {
    const interval = Math.min(baseInterval * Math.pow(2, failCount), maxInterval);
    const id = setTimeout(() => {
      try {
        const result = fn();
        if (result && typeof result.then === 'function') {
          result.then(() => { failCount = 0; }).catch(() => { failCount++; });
        } else {
          failCount = 0;
        }
      } catch (e) {
        failCount++;
      }
      schedule();
    }, interval);
    setTimer(id);
  }

  schedule();
}

function _stopPolling(getTimer, setTimer) {
  const id = getTimer();
  if (id !== null) {
    clearTimeout(id);
    setTimer(null);
  }
}

function startCloudStatusRefresh() {
  _startPollingWithBackoff(
    () => cloudStatusTimer,
    (id) => { cloudStatusTimer = id; },
    () => refreshCloudStatus(),
    5000, 30000
  );
}

function stopCloudStatusRefresh() {
  _stopPolling(() => cloudStatusTimer, (id) => { cloudStatusTimer = id; });
}

function startProcessTabRefresh() {
  _startPollingWithBackoff(
    () => processTabTimer,
    (id) => { processTabTimer = id; },
    () => loadProcesses(),
    30000, 120000
  );
}

function stopProcessTabRefresh() {
  _stopPolling(() => processTabTimer, (id) => { processTabTimer = id; });
}

// ── 流程详情弹窗自动刷新 ──────────────────
const _processDetailTimers = {};

function _startProcessDetailRefresh(processId) {
  _stopProcessDetailRefresh(processId);
  _processDetailTimers[processId] = setInterval(async () => {
    const overlay = document.querySelector(`.modal-overlay[data-process-id="${processId}"]`);
    if (!overlay) { _stopProcessDetailRefresh(processId); return; }
    const body = overlay.querySelector('.modal-body');
    if (!body) { _stopProcessDetailRefresh(processId); return; }
    _stopProcessDetailRefresh(processId);
    body.innerHTML = '<div style="text-align:center;padding:20px;color:#999;">同步刷新中...</div>';
    await viewProcess(processId);
  }, 30000);
}

function _stopProcessDetailRefresh(processId) {
  if (_processDetailTimers[processId]) {
    clearInterval(_processDetailTimers[processId]);
    delete _processDetailTimers[processId];
  }
}

// ── 全局自动刷新 ──────────────────────────
let autoRefreshTimer = null;
let _dispatchMode = 'all';

async function toggleDispatchMode() {
  if (_dispatchMode === 'all') {
    _dispatchMode = 'department';
  } else if (_dispatchMode === 'department') {
    _dispatchMode = 'specific';
  } else {
    _dispatchMode = 'all';
  }
  const btn = document.getElementById('btn-dispatch-mode');
  const label = document.getElementById('dispatch-mode-label');
  const deptSelect = document.getElementById('dispatch-dept-select');
  const auto_send = _dispatchMode !== 'specific';
  const default_to_all = _dispatchMode === 'all';
  if (_dispatchMode === 'all') {
    btn.textContent = '✅ 全员派发';
    btn.className = 'btn btn-sm btn-success';
    label.textContent = '任务自动对全体工人可见';
    if (deptSelect) deptSelect.style.display = 'none';
  } else if (_dispatchMode === 'department') {
    btn.textContent = '🏭 按部门派发';
    btn.className = 'btn btn-sm btn-warning';
    label.textContent = '仅派发到指定部门';
    if (deptSelect) deptSelect.style.display = 'inline-block';
  } else {
    btn.textContent = '🔗 工序绑定';
    btn.className = 'btn btn-sm btn-primary';
    label.textContent = '按工序→部门绑定自动派发';
    if (deptSelect) deptSelect.style.display = 'none';
  }
  const body = { auto_send, default_to_all, dispatch_mode: _dispatchMode };
  await api('/global-config', { method: 'POST', body });
  refreshTasks();
}

async function saveDeptFilter() {
  const dept = document.getElementById('dispatch-dept-select').value;
  await api('/global-config', { method: 'POST', body: { dispatch_dept: dept } });
}

const TAB_LOAD_FUNCS = {
  overview:    () => loadOverview(),
  tasks:       () => loadOperators(),
  messages:    () => loadTemplates(),
  processes:   () => loadProcesses(),
  rules:       () => loadRules(),
  'process-config': () => loadProcessConfig(),
  monitor:     () => { loadAlerts(); loadDispatchLog(); loadSchedulerStatus(); },
  cloud:       () => loadCloudConfig(),
  repairs:     () => { loadRepairCategories(); loadRepairRecords(); },
  outsource:   () => { loadOutsourceRecords(); loadOutsourceConfig(); },
  feedback:    () => loadFeedback(),
  'system-config': () => renderConfigCenter(),
  'sync-queue': () => loadSyncQueue(),
};

function refreshCurrentTab() {
  const name = sessionStorage.getItem('dc_active_tab') || 'overview';
  const fn = TAB_LOAD_FUNCS[name];
  if (fn) { apiCacheDel(); fn(); }
}

function startAutoRefresh() {
  _startPollingWithBackoff(
    () => autoRefreshTimer,
    (id) => { autoRefreshTimer = id; },
    () => refreshCurrentTab(),
    30000, 120000
  );
}

function stopAutoRefresh() {
  _stopPolling(() => autoRefreshTimer, (id) => { autoRefreshTimer = id; });
}

async function acknowledgeTask(workOrderNo, taskId, btn) {
  try {
    if (!confirm('确认收到该派工任务？')) return;
    btn.disabled = true;
    btn.textContent = '确认中...';
    const res = await api(`/workorder/${workOrderNo}/acknowledge`, {
      method: 'POST',
      body: { task_id: taskId }
    });
    if (res.code === 0) {
      toast('已确认收到派工', 'success');
      viewWorkorderDetail(workOrderNo);
    } else {
      toast(res.message || '确认失败', 'error');
      btn.disabled = false;
      btn.textContent = '📥 收到派工';
    }
  } catch (e) {
    toast('操作异常: ' + e.message, 'error');
    btn.disabled = false;
    btn.textContent = '📥 收到派工';
  }
}

async function refreshWorkorderStatus(workOrderNo, btn) {
  btn.disabled = true;
  btn.textContent = '刷新中...';
  const res = await api(`/workorder/${workOrderNo}/refresh`, { method: 'POST' });
  if (res.code === 0) {
    toast('工单状态已刷新', 'success');
    viewWorkorderDetail(workOrderNo);
    loadWorkorderStats();
  } else {
    toast(res.message || '刷新失败', 'error');
  }
  btn.disabled = false;
  btn.textContent = '🔄 刷新状态';
}

// === 概览 ===
async function loadOverview() {
  try {
    const [res, ctRes] = await Promise.all([
      api('/status'),
      fetch(CONTAINER_CENTER_BASE + '/container/api/stats').then(r => r.json()).catch(() => ({ code: -1 }))
    ]);
    if (res.code === 0) {
      const d = res.data;
      document.getElementById('ov-pending').textContent = d.summary.pending + d.summary.dispatched;
      document.getElementById('ov-in-progress').textContent = d.summary.in_progress;
      document.getElementById('ov-completed').textContent = d.summary.completed;
      document.getElementById('ov-overdue').textContent = d.summary.overdue;
      document.getElementById('ov-rate').textContent = d.summary.completion_rate + '%';
      document.getElementById('ov-processes').textContent = d.active_processes;
      document.getElementById('ov-pending-warehousing').textContent = d.pending_warehousing ?? 0;

      const ops = d.operators;
      let html = '<table><thead><tr><th>操作员</th><th>角色</th><th>活跃任务</th><th>今日完成</th></tr></thead><tbody>';
      if (ops.length === 0) {
        html += '<tr><td colspan="4" style="text-align:center;color:#999;">暂无操作员数据</td></tr>';
      } else {
        for (const op of ops) {
          html += `<tr><td>${escHtml(op.name)}</td><td>${escHtml(op.role || '-')}</td><td>${op.active_tasks || 0}</td><td>${op.completed_today || 0}</td></tr>`;
        }
      }
      html += '</tbody></table>';
      document.getElementById('operator-load').innerHTML = html;
    }
    if (ctRes.code === 0) {
      const ct = ctRes.data;
      document.getElementById('ct-pending').textContent = ct.pending ?? '-';
      document.getElementById('ct-distributed').textContent = ct.distributed ?? '-';
      document.getElementById('ct-acknowledged').textContent = ct.acknowledged ?? '-';
      document.getElementById('ct-completed').textContent = ct.completed ?? '-';
      document.getElementById('ct-expired').textContent = ct.expired ?? '-';
      document.getElementById('ct-total').textContent = ct.total ?? '-';
    }
  } catch (e) {
    console.error('[Overview] 加载概览数据异常:', e);
  }
}

/**
 * 显示待入库工单列表弹窗
 * 调用 /pending-warehousing 接口获取待入库工单列表，生成弹窗HTML
 */
async function showPendingWarehousing() {
  const res = await api('/pending-warehousing');
  if (res.code !== 0) { toast(res.message || '获取待入库列表失败', 'error'); return; }
  const list = res.data || [];

  let bodyHtml = '';
  if (list.length === 0) {
    bodyHtml = '<div style="text-align:center;padding:40px 0;color:#999;">暂无待入库工单</div>';
  } else {
    bodyHtml = '<table><thead><tr><th>工单号</th><th>产品名称</th><th>数量</th><th>客户</th><th>操作</th></tr></thead><tbody>';
    for (const item of list) {
      const qty = item.quantity || 0;
      const unit = item.unit || '米';
      bodyHtml += '<tr>' +
        '<td>' + escHtml(item.order_no || '-') + '</td>' +
        '<td>' + escHtml(item.product_name || '-') + '</td>' +
        '<td>' + qty + ' ' + unit + '</td>' +
        '<td>' + escHtml(item.customer_name || '-') + '</td>' +
        '<td><button class="btn btn-sm btn-success" onclick="confirmWarehousing(\'' + item.order_no + '\',\'' + escHtml(item.order_no || '') + '\')">确认入库</button></td>' +
        '</tr>';
    }
    bodyHtml += '</tbody></table>';
  }

  const modal = document.createElement('div');
  modal.className = 'modal-overlay show';
  modal.style.display = 'flex';
  modal.innerHTML = '<div class="modal" style="width:720px;max-width:95vw;">' +
    '<div class="modal-header"><h3>待入库工单</h3>' +
    '<button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove()">&times;</button></div>' +
    '<div class="modal-body">' + bodyHtml + '</div></div>';
  document.body.appendChild(modal);
}

/**
 * 加载待入库工单列表
 * 调用 /pending-warehousing 接口获取待入库数据并渲染表格
 */
async function loadWarehousing() {
  const container = document.getElementById('warehousing-list');
  if (!container) return;
  container.innerHTML = '<div class="loading">加载中...</div>';
  const res = await api('/pending-warehousing');
  if (res.code !== 0) {
    container.innerHTML = '<div style="text-align:center;padding:40px;color:#999;">获取数据失败</div>';
    return;
  }
  const list = res.data || [];
  if (list.length === 0) {
    container.innerHTML = '<div style="text-align:center;padding:40px;color:#999;">暂无待入库工单</div>';
    return;
  }
  let html = '<table><thead><tr><th>工单号</th><th>产品名称</th><th>数量</th><th>客户</th><th>创建时间</th><th>操作</th></tr></thead><tbody>';
  for (const item of list) {
    const createTime = item.created_at ? item.created_at.replace('T', ' ').substring(0, 16) : '';
    const qty = item.quantity || 0;
    const unit = item.unit || '米';
    html += '<tr>' +
      '<td>' + (item.order_no || item.order_no || '-') + '</td>' +
      '<td>' + (item.product_name || '-') + '</td>' +
      '<td>' + qty + ' ' + unit + '</td>' +
      '<td>' + (item.customer_name || '-') + '</td>' +
      '<td>' + createTime + '</td>' +
      '<td><button class="btn btn-sm btn-success" onclick="showWarehousingConfirm(\'' + item.order_no + '\',\'' + (item.order_no || item.order_no || '') + '\')">确认入库</button></td>' +
      '</tr>';
  }
  html += '</tbody></table>';
  container.innerHTML = html;
}

/**
 * 显示入库确认对话框
 */
function showWarehousingConfirm(processId, orderNo) {
  if (!confirm('确认工单 ' + (orderNo || '') + ' 已完成入库？')) return;
  confirmWarehousing(processId, orderNo);
}

/**
 * 确认入库操作
 * 调用 /processes/<order_no>/confirm 接口完成入库确认，然后刷新列表
 */
async function confirmWarehousing(processId, orderNo) {
  if (!processId) { toast('流程ID无效', 'error'); return; }
  const res = await api('/processes/' + processId + '/confirm', {
    method: 'POST',
    body: { operator_name: '调度中心' }
  });
  if (res.code !== 0) { toast(res.message || '入库确认失败', 'error'); return; }
  toast('工单 ' + (orderNo || '') + ' 已确认入库', 'success');
  loadWarehousing();
  loadOverview();
}

// === 反馈管理 ===
async function loadFeedbackList() {
  const container = document.getElementById('feedback-list');
  if (!container) return;
  container.innerHTML = '<div class="loading">加载中...</div>';
  try {
    const res = await api('/outsource-records?page_size=100');
    if (res.code !== 0) {
      container.innerHTML = '<div class="empty-state"><p>加载失败</p></div>';
      return;
    }
    const records = res.data || [];
    if (records.length === 0) {
      container.innerHTML = '<div class="empty-state"><p>暂无反馈记录</p><p style="color:#999;font-size:13px;">外协反馈将在外协工单完成后显示</p></div>';
      return;
    }
    let html = '<table><thead><tr><th>外协单号</th><th>供应商</th><th>承诺天数</th><th>实际天数</th><th>状态</th><th>反馈</th><th>时间</th></tr></thead><tbody>';
    for (const r of records) {
      const feedback = r.feedback || '-';
      html += '<tr>' +
        '<td>' + escHtml(r.order_no || '-') + '</td>' +
        '<td>' + escHtml(r.supplier || '-') + '</td>' +
        '<td>' + (r.promised_days ?? '-') + '</td>' +
        '<td>' + (r.actual_days ?? '-') + '</td>' +
        '<td>' + escHtml(r.status || '-') + '</td>' +
        '<td>' + escHtml(feedback) + '</td>' +
        '<td>' + (r.created_at || '').slice(0,10) + '</td>' +
        '</tr>';
    }
    html += '</tbody></table>';
    container.innerHTML = html;
  } catch(e) {
    container.innerHTML = '<div class="empty-state"><p>加载失败</p></div>';
    console.error('[Feedback]', e);
  }
}

// === 任务调度 ===
async function refreshTasks() {
  const status = document.getElementById('task-status-filter').value;
  const operator = document.getElementById('task-operator-filter').value;
  const type = document.getElementById('task-type-filter').value;
  const params = new URLSearchParams({ page: 1, page_size: 50 });
  if (status) params.set('status', status);
  if (operator) params.set('operator', operator);
  if (type) params.set('type', type);

  const [res, opsRes] = await Promise.all([
    api('/tasks?' + params.toString()),
    api('/operators'),
  ]);
  if (res.code !== 0) return;
  const tasks = res.data.tasks;
  const operators = opsRes.code === 0 ? opsRes.data : [];

  let html = '<table><thead><tr><th>任务</th><th>类型</th><th>状态</th><th>工单</th><th>操作员</th><th>派发</th><th>时间</th><th>操作</th></tr></thead><tbody>';
  if (tasks.length === 0) {
    html += '<tr><td colspan="8" style="text-align:center;color:#999;">暂无任务</td></tr>';
  } else {
    for (const t of tasks) {
      const statusCls = t.status;
      const created = t.created_at ? t.created_at.slice(0, 16) : '-';

      let assignOps = operators.map(o =>
        `<a href="#" class="btn btn-sm btn-outline" onclick="event.preventDefault();assignTask('${t.id}','${o.id}')">${escHtml(o.name)}</a>`
      ).join(' ');

      const displayOperator = escHtml(t.operator || (_dispatchMode === 'all' ? '全员' : '-'));

      if (t.status === 'completed') {
        html += `<tr>
          <td>${escHtml(t.title || '-')}</td>
          <td>${LABELS.t(t.type) || escHtml(t.type)}</td>
          <td><span class="status-badge ${statusCls}">${LABELS.s(t.status) || escHtml(t.status)}</span></td>
          <td>${escHtml(t.order_no || t.related_order || '-')}</td>
          <td>${displayOperator}</td>
          <td>${escHtml(t.dispatched_to || '-')}</td>
          <td>${created}</td>
          <td><span style="color:#999;">已完成</span></td>
        </tr>`;
      } else {
        const actionButtons = [];
        const isDistributed = t.status === 'distributed';
        if (_dispatchMode === 'specific') {
          if (t.operator && !isDistributed) {
            actionButtons.push(`<button class="btn btn-sm btn-warning" onclick="reassignTask('${t.id}')">转派</button>`);
          } else if (isDistributed) {
            actionButtons.push(`<button class="btn btn-sm" style="background:#ccc;cursor:not-allowed" disabled>已派发</button>`);
          } else {
            actionButtons.push(`<div class="btn-group">${assignOps}</div>`);
          }
        } else {
          if (t.operator && !isDistributed) {
            actionButtons.push(`<button class="btn btn-sm btn-warning" onclick="reassignTask('${t.id}')">转派</button>`);
            actionButtons.push(`<button class="btn btn-sm btn-info" onclick="assignToAll('${t.id}')">设为全员</button>`);
          } else if (isDistributed) {
            actionButtons.push(`<button class="btn btn-sm" style="background:#ccc;cursor:not-allowed" disabled>已派发</button>`);
          }
        }
        if (!isDistributed) {
          actionButtons.push(`<button class="btn btn-sm btn-danger" onclick="cancelTask('${t.id}', ${!!t.operator})">取消</button>`);
        }

        html += `<tr>
          <td>${escHtml(t.title || '-')}</td>
          <td>${LABELS.t(t.type) || escHtml(t.type)}</td>
          <td><span class="status-badge ${statusCls}">${LABELS.s(t.status) || escHtml(t.status)}</span></td>
          <td>${escHtml(t.order_no || '-')}</td>
          <td>${displayOperator}</td>
          <td>${escHtml(t.dispatched_to || '-')}</td>
          <td>${created}</td>
          <td><div class="btn-group">${actionButtons.join('')}</div></td>
        </tr>`;
      }
    }
  }
  html += '</tbody></table>';
  document.getElementById('task-list').innerHTML = html;
}

async function loadOperators() {
  try {
    const res = await api('/operators');
    if (res.code !== 0) return;
    const sel = document.getElementById('task-operator-filter');
    sel.innerHTML = '<option value="">全部操作员</option>' + res.data.map(o => `<option value="${escHtml(o.id)}">${escHtml(o.name)}</option>`).join('');

    const configRes = await api('/global-config');
    if (configRes?.code === 0) {
      const cfg = configRes.data;
      const isAll = cfg.default_to_all !== false;
      _dispatchMode = isAll ? 'all' : 'specific';
      const btn = document.getElementById('btn-dispatch-mode');
      const label = document.getElementById('dispatch-mode-label');
      if (btn && label) {
        if (isAll) {
          btn.textContent = '✅ 全员派发';
          btn.className = 'btn btn-sm btn-success';
          label.textContent = '任务自动对全体工人可见';
        } else {
          btn.textContent = '👤 指定人员';
          btn.className = 'btn btn-sm btn-primary';
          label.textContent = '需手动选择操作员分配任务';
        }
      }
    }

    refreshTasks();
  } catch (e) {
    console.error('[Operators] 加载操作员异常:', e);
  }
}

async function refreshOperators() {
  const res = await api('/operators?include_disabled=1');
  if (res.code !== 0) {
    toast('加载操作员失败', 'error');
    return;
  }
  const operators = res.data || [];

  if (operators.length === 0) {
    document.getElementById('operator-list').innerHTML = '<div class="empty-state">暂无操作员，点击右上角添加</div>';
  } else {
    const html = `
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>微信ID</th>
            <th>姓名</th>
            <th>角色</th>
            <th>部门</th>
            <th>微信权限</th>
            <th>创建时间</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          ${operators.map(op => {
            return `
            <tr>
              <td>${escHtml(op.id)}</td>
              <td>${escHtml(op.wechat_userid) || '<span style="color:#999;">-</span>'}</td>
              <td>${escHtml(op.name)}</td>
              <td>${escHtml(op.role || '-')}</td>
              <td>${escHtml(op.department) || '<span style="color:#999;">未分配</span>'}</td>
              <td style="font-size:11px;">${(op.can_receive_wechat ? '📥收' : '') + (op.can_send_wechat ? ' 📤发' : '') || '<span style="color:#999;">--</span>'}</td>
              <td style="font-size:11px;">${op.created_at ? op.created_at.substring(0,10) : '-'}</td>
              <td>${op.enabled ? '<span class="status-badge in_progress">启用</span>' : '<span class="status-badge cancelled">已离职</span>'}</td>
              <td>
                <div class="btn-group">
                  <button class="btn btn-sm btn-warning" onclick="editOperator('${op.id}')">编辑</button>
                  <button class="btn btn-sm ${op.enabled ? 'btn-outline' : 'btn-success'}" onclick="toggleOperator('${op.id}', ${!op.enabled})">${op.enabled ? '禁用' : '启用'}</button>
                  <button class="btn btn-sm btn-danger" onclick="deleteOperator('${op.id}')">删除</button>
                </div>
              </td>
            </tr>
          `;}).join('')}
        </tbody>
      </table>
    `;
    document.getElementById('operator-list').innerHTML = html;
  }

}

function renderDeptTree(nodes, depth = 0) {
  return nodes.map(node => {
    const hasChildren = node.children && node.children.length > 0;
    const indent = depth * 20;
    let html = `
      <div class="dept-tree-node" style="margin-left:${indent}px">
        <div class="dept-tree-header" onclick="toggleDeptTree(this)">
          <span class="dept-tree-toggle">${hasChildren ? '▶' : '◉'}</span>
          <span class="dept-name">${escHtml(node.name)}</span>
          <span class="dept-count-badge">${node.members.length} 人</span>
        </div>
        <div class="dept-tree-body" style="${depth > 0 ? 'display:none' : ''}">
          ${node.members.length > 0 ? `
          <div class="dept-members" style="padding:6px 0 6px 24px">
            ${node.members.map(m => `
              <span class="member-tag">${escHtml(m.name)}<small>(${escHtml(m.userid)})</small></span>
            `).join('')}
          </div>` : ''}
          ${hasChildren ? renderDeptTree(node.children, depth + 1) : ''}
        </div>
      </div>
    `;
    return html;
  }).join('');
}

function toggleDeptTree(el) {
  const body = el.nextElementSibling;
  if (!body) return;
  const isHidden = body.style.display === 'none';
  body.style.display = isHidden ? 'block' : 'none';
  const toggle = el.querySelector('.dept-tree-toggle');
  if (toggle) toggle.textContent = isHidden ? '▼' : '▶';
}

// ── 企业微信部门架构：请求合并 + 缓存复用 ──
let _wechatDeptCacheData = null;
let _wechatDeptCacheTime = 0;
let _wechatDeptPendingPromise = null;
const WECHAT_DEPT_CACHE_TTL = 60000;

async function fetchWechatDepartments(forceCloud) {
  const now = Date.now();
  if (!forceCloud) {
    if (_wechatDeptCacheData && (now - _wechatDeptCacheTime) < WECHAT_DEPT_CACHE_TTL) {
      return _wechatDeptCacheData;
    }
    if (_wechatDeptPendingPromise) {
      return _wechatDeptPendingPromise;
    }
    const promise = api('/operators/wechat-departments').then(res => {
      _wechatDeptPendingPromise = null;
      if (res.code === 0) {
        _wechatDeptCacheData = res;
        _wechatDeptCacheTime = Date.now();
      }
      return res;
    }).catch(err => {
      _wechatDeptPendingPromise = null;
      throw err;
    });
    _wechatDeptPendingPromise = promise;
    return promise;
  }
  return api('/operators/wechat-departments?force_cloud=1');
}

function clearWechatDeptCache() {
  _wechatDeptCacheData = null;
  _wechatDeptCacheTime = 0;
}

async function loadWechatDepartments() {
  const container = document.getElementById('department-list');

  const res = await fetchWechatDepartments(false);
  if (res.code !== 0) {
    container.innerHTML = `<div class="empty-state"><p>❌ ${escHtml(res.message || '获取失败')}</p></div>`;
    return;
  }

  const departments = res.data.departments || [];
  const flatCount = res.data.flat_count || 0;
  let totalMembers = 0;
  const countMembers = (nodes) => { nodes.forEach(n => { totalMembers += n.members.length; countMembers(n.children || []); }); };
  countMembers(departments);

  let html = `
    <div class="dept-stats-bar">
      <span>
        企业微信部门架构：共 <strong>${flatCount}</strong> 个部门，<strong>${totalMembers}</strong> 人
        <span style="margin-left:12px;font-size:12px;color:#999;">（点击部门展开/折叠子部门）</span>
      </span>
      <span style="margin-left:auto;">
        <button class="btn btn-sm btn-outline" onclick="syncWechatDepartments()">☁️ 从云端同步</button>
      </span>
    </div>
    <div class="dept-tree">${renderDeptTree(departments)}</div>
  `;
  container.innerHTML = html;
}

async function syncWechatDepartments() {
  const container = document.getElementById('department-list');
  container.innerHTML = '<div class="loading"><span style="font-size:24px;">⏳</span><br>正在从云端同步企业微信部门架构...</div>';

  clearWechatDeptCache();
  const res = await fetchWechatDepartments(true);
  if (res.code !== 0) {
    container.innerHTML = `<div class="empty-state"><p>❌ ${escHtml(res.message || '同步失败')}</p></div>`;
    return;
  }

  const departments = res.data.departments || [];
  const flatCount = res.data.flat_count || 0;
  let totalMembers = 0;
  const countMembers = (nodes) => { nodes.forEach(n => { totalMembers += n.members.length; countMembers(n.children || []); }); };
  countMembers(departments);

  let html = `
    <div class="dept-stats-bar">
      <span>
        企业微信部门架构：共 <strong>${flatCount}</strong> 个部门，<strong>${totalMembers}</strong> 人
        <span style="margin-left:12px;font-size:12px;color:#999;">（已从云端同步）</span>
      </span>
      <span style="margin-left:auto;">
        <button class="btn btn-sm btn-outline" onclick="syncWechatDepartments()">☁️ 从云端同步</button>
      </span>
    </div>
    <div class="dept-tree">${renderDeptTree(departments)}</div>
  `;
  container.innerHTML = html;
}

// ═══════════════════════════════════════
// 操作员表单数据缓存
// ═══════════════════════════════════════
let _formDeptData = [];  // [{name, users:[{userid,name}], user_count}]
let _formRoles = [];
let _formNextId = '';

async function loadFormData() {
  try {
    const res = await api('/operators/wechat-form-data');
    if (res.code === 0) {
      _formDeptData = res.data.departments || [];
      _formRoles = res.data.roles || [];
      _formNextId = res.data.next_auto_id || 'OP001';
    }
  } catch(e) {
    console.warn('加载表单数据失败:', e);
  }
}

async function showAddOperatorModal(op = null) {
  const isEdit = op != null;
  // 确保数据已加载
  if (!_formDeptData.length) {
    await loadFormData();
    if (!_formDeptData.length) {
      toast('无法加载部门数据', 'error');
      return;
    }
  }
  if (isEdit && !_formDeptData.length) return; // 编辑时也需要数据

  const deptOptions = _formDeptData.map(d =>
    `<option value="${escHtml(d.name)}" ${op?.department === d.name ? 'selected' : ''}>${escHtml(d.name)} (${d.user_count}人)</option>`
  ).join('');

  const currentDeptUsers = isEdit ? [] :
    (_formDeptData.find(d => d.name === (op?.department || ''))?.users || []);

  // 编辑时：显示所有部门可选，姓名显示该部门下所有人员
  const nameOptions = isEdit
    ? ((_formDeptData.find(d => d.name === (op?.department || ''))?.users || [])).map(u =>
        `<option value="${escHtml(u.userid)}" ${u.userid === (op?.wechat_userid||'') ? 'selected' : ''}>${escHtml(u.name)}</option>`
      ).join('')
    : currentDeptUsers.map(u =>
        `<option value="${escHtml(u.userid)}">${escHtml(u.name)} (${escHtml(u.userid)})</option>`
      ).join('');

  const roleOptions = _formRoles.map(r =>
    `<option value="${escHtml(r)}" ${op?.role === r ? 'selected' : (!isEdit && r === '操作员' ? 'selected' : '')}>${escHtml(r)}</option>`
  ).join('');

  _renderOperatorModal(op, isEdit, deptOptions, nameOptions, roleOptions);
}

function _renderOperatorModal(op, isEdit, deptOptions, nameOptions, roleOptions) {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay show';
  modal.innerHTML = `
    <div class="modal" style="width: 480px;">
      <div class="modal-header">
        <h3>${isEdit ? '编辑操作员' : '新增操作员'}</h3>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
      </div>
      <div style="padding: 20px;">
        <!-- 系统自增ID（锁定） -->
        <div class="form-group">
          <label>系统ID <span style="color:#999;font-size:12px;">（系统自增，不可修改）</span></label>
          <input id="op-sysid" value="${escHtml(op?.id || _formNextId)}" readonly style="background:#f0f0f0;color:#666;">
        </div>

        <!-- 操作员ID = 企业微信userid（下拉选择） -->
        <div class="form-group">
          <label>操作员ID * <span style="color:#999;font-size:12px;">（从企业微信同步）</span></label>
          ${isEdit
            ? `<input id="op-id" value="${escHtml(op?.id || '')}" readonly style="background:#f0f0f0;color:#666;">`
            : `<select id="op-id" onchange="onOpIdChange(this.value)" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:4px;">
                 <option value="">-- 请选择 --</option>
                 ${(_formDeptData.flatMap(d => d.users).map(u =>
                   `<option value="${escHtml(u.userid)}">${escHtml(u.name)} - ${escHtml(u.userid)}</option>`
                 )).join('')}
               </select>`
          }
        </div>

        <!-- 部门 -->
        <div class="form-group">
          <label>部门 *</label>
          <select id="op-dept" onchange="onDeptChange(this.value)" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:4px;">
            <option value="">-- 请选择部门 --</option>
            ${deptOptions || ''}
          </select>
        </div>

        <!-- 姓名 -->
        <div class="form-group">
          <label>姓名 * <span style="color:#999;font-size:12px;">${isEdit ? '（人员锁定不可变更）' : ''}</span></label>
          ${isEdit
            ? (() => {
                // 从企业架构中查找真实姓名
                let realName = op?.name || '';
                if (op?.wechat_userid) {
                  for (const dept of _formDeptData) {
                    const u = dept.users.find(u => u.userid === op.wechat_userid);
                    if (u) { realName = u.name; break; }
                  }
                }
                return `<input id="op-name" value="${escHtml(realName)}" readonly style="background:#f0f0f0;color:#666;">`;
              })()
            : `<select id="op-name" onchange="onNameChange(this.value)" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:4px;">
                 <option value="">-- 请选择 --</option>
                 ${nameOptions || ''}
               </select>`
          }
        </div>

        <!-- 角色 -->
        <div class="form-group">
          <label>角色</label>
          <select id="op-role" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:4px;">
            ${roleOptions || '<option value="操作员">操作员</option>'}
          </select>
        </div>

        <!-- 手机号 -->
        <div class="form-group">
          <label>手机号</label>
          <input id="op-phone" value="${escHtml(op?.phone || '')}" placeholder="选填" style="width:100%;">
        </div>

        <!-- 最大任务数 -->
        <div class="form-group">
          <label>最大任务数</label>
          <input id="op-max" type="number" value="${escHtml(String(op?.max_tasks || 10))}" min="1" max="99" style="width:100%;">
        </div>

        <!-- 启用开关（控制权限和登录） -->
        <div class="form-group" style="display:flex;align-items:center;gap:12px;">
          <label style="margin:0;">启用</label>
          <input type="checkbox" id="op-enabled" ${op?.enabled !== false ? 'checked' : ''}
                 onchange="document.getElementById('op-enabled-hint').textContent=this.checked?'已授权 - 可登录和操作':'已禁用 - 不可登录和操作'">
          <span id="op-enabled-hint" style="color:${op?.enabled !== false ? '#22c55e' : '#ef4444'};font-size:12px;">
            ${op?.enabled !== false ? '已授权 - 可登录和操作' : '已禁用 - 不可登录和操作'}
          </span>
        </div>

        <!-- 微信消息权限 -->
        <div class="form-section" style="margin-top:8px;padding:10px 0;border-top:1px solid #eee;">
          <label style="display:block;margin-bottom:8px;font-weight:bold;color:#333;">📨 微信消息授权</label>
          <div class="form-group" style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <input type="checkbox" id="op-recv-wechat" ${op?.can_receive_wechat ? 'checked' : ''}>
            <label style="margin:0;">接收微信消息</label>
            <span style="color:#999;font-size:11px;">（接收任务通知、报工提醒）</span>
          </div>
          <div class="form-group" style="display:flex;align-items:center;gap:8px;">
            <input type="checkbox" id="op-send-wechat" ${op?.can_send_wechat ? 'checked' : ''}>
            <label style="margin:0;">发送微信消息</label>
            <span style="color:#999;font-size:11px;">（通过微信报工、回复查询）</span>
          </div>
        </div>

        <div style="display:flex;gap:10px;margin-top:20px;">
          <button class="btn btn-primary" style="flex:1" onclick="saveOperator('${isEdit ? (op?.id || '') : ''}')">保存</button>
          <button class="btn btn-outline" style="flex:1" onclick="this.closest('.modal-overlay').remove()">取消</button>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
}

function onDeptChange(deptName) {
  const dept = _formDeptData.find(d => d.name === deptName);
  const nameSel = document.getElementById('op-name');
  if (!nameSel || !dept) return;
  nameSel.innerHTML = '<option value="">-- 请选择 --</option>' +
    dept.users.map(u =>
      `<option value="${escHtml(u.userid)}">${escHtml(u.name)}</option>`
    ).join('');
}

function onNameChange(userid) {
  const idInput = document.getElementById('op-id');
  if (idInput && idInput.tagName === 'SELECT') {
    idInput.value = userid;
  }
}

function onOpIdChange(userid) {
  // 找到该用户所在的部门并自动选中
  for (const dept of _formDeptData) {
    const u = dept.users.find(u => u.userid === userid);
    if (u) {
      const deptSel = document.getElementById('op-dept');
      if (deptSel) deptSel.value = dept.name;
      onDeptChange(dept.name);
      const nameSel = document.getElementById('op-name');
      if (nameSel) nameSel.value = userid;
      break;
    }
  }
}

async function saveOperator(existId) {
  try {
    const sysId = document.getElementById('op-sysid').value.trim();
    const opId = document.getElementById('op-id').value.trim();
    const nameEl = document.getElementById('op-name');
    const name = nameEl?.tagName === 'SELECT'
      ? (nameEl.selectedOptions[0]?.textContent || '').trim()
      : (nameEl?.value || '').trim();
    const role = document.getElementById('op-role').value.trim();
    const phone = document.getElementById('op-phone')?.value.trim() || '';
    const department = document.getElementById('op-dept').value.trim();
    const max_tasks = parseInt(document.getElementById('op-max').value) || 10;
    const enabled = document.getElementById('op-enabled').checked;
    const can_receive_wechat = document.getElementById('op-recv-wechat')?.checked || false;
    const can_send_wechat = document.getElementById('op-send-wechat')?.checked || false;

    const id = existId || sysId;

    if (!id || !name) {
      toast('操作员ID和姓名不能为空', 'error');
      return;
    }

    // 从 enterprise_structure 查找 wechat_userid
    let wechat_userid = '';
    if (!existId && opId) {
      wechat_userid = opId;  // 新增时操作员ID就是wechat_userid
    }

    const data = {
      name, role, phone, department, max_tasks, enabled,
      can_receive_wechat, can_send_wechat,
      wechat_userid: wechat_userid || (opId || '')
    };

    let res;
    if (existId) {
      res = await api(`/operators/${existId}`, { method: 'PUT', body: data });
      toast(res.message || (res.code === 0 ? '更新成功' : '更新失败'), res.code === 0 ? 'success' : 'error');
    } else {
      res = await api('/operators', { method: 'POST', body: { id, ...data } });
      toast(res.message || (res.code === 0 ? '添加成功' : '添加失败'), res.code === 0 ? 'success' : 'error');
    }

    if (res.code === 0) {
      document.querySelector('.modal-overlay.show')?.remove();
      refreshOperators();
    }
  } catch(e) {
    toast('操作异常: ' + e.message, 'error');
  }
}

async function editOperator(id) {
  const res = await api('/operators');
  if (res.code !== 0) return;
  const op = res.data?.find(o => o.id === id);
  if (op) showAddOperatorModal(op);
}

async function toggleOperator(id, enable) {
  try {
    const res = await api(`/operators/${id}`, { method: 'PUT', body: { enabled: enable } });
    toast(res.message || (res.code === 0 ? '更新成功' : '更新失败'), res.code === 0 ? 'success' : 'error');
    if (res.code === 0) refreshOperators();
  } catch(e) {
    toast('操作异常: ' + e.message, 'error');
  }
}

async function deleteOperator(id) {
  try {
    if (!confirm(`确认删除操作员 ${id}？`)) return;
    const res = await api(`/operators/${id}`, { method: 'DELETE' });
    toast(res.message || (res.code === 0 ? '删除成功' : '删除失败'), res.code === 0 ? 'success' : 'error');
    if (res.code === 0) refreshOperators();
  } catch(e) {
    toast('操作异常: ' + e.message, 'error');
  }
}

async function assignTask(taskId, operatorId) {
  if (!confirm('确认分配该任务？')) return;
  const res = await api(`/tasks/${taskId}/assign`, { method: 'POST', body: { operator_id: operatorId } });
  toast(res.message, res.code === 0 ? 'success' : 'error');
  if (res.code === 0) refreshTasks();
}

async function reassignTask(taskId) {
  const opRes = await api('/operators');
  if (opRes.code !== 0) return;
  const ops = opRes.data.map(o => `${o.id}:${o.name}`).join('\n');
  const input = await showPrompt('选择转派的操作员', '', '请输入操作员ID', `操作员列表:\n${ops}`);
  if (!input) return;
  const reason = await showPrompt('转派原因（可选）', '人工转派', '转派原因') || '人工转派';
  const res = await api(`/tasks/${taskId}/reassign`, { method: 'POST', body: { operator_id: input.trim(), reason } });
  toast(res.message, res.code === 0 ? 'success' : 'error');
  if (res.code === 0) refreshTasks();
}

async function cancelTask(taskId, hasOperator = false) {
  const msg = hasOperator
    ? '该任务已派发，取消后会自动发送微信通知已派发人员，确认取消？'
    : '该任务未派发，确认直接删除？';
  if (!confirm(msg)) return;
  const res = await api(`/tasks/${taskId}/cancel`, { method: 'POST', body: { has_operator: !!hasOperator } });
  toast(res.message, res.code === 0 ? 'success' : 'error');
  if (res.code === 0) refreshTasks();
}

async function assignToAll(taskId) {
  if (!confirm('确认将该任务设为全员派发？')) return;
  const res = await api(`/tasks/${taskId}/assign-all`, { method: 'POST' });
  toast(res.message, res.code === 0 ? 'success' : 'error');
  if (res.code === 0) refreshTasks();
}

async function convertAllToPublic() {
  if (!confirm('确认将所有已分配任务转为全员派发？\n现有操作员分配将被清除，所有工人可见。')) return;
  if (!confirm('⚠️ 二次确认：此操作不可撤销，是否继续？')) return;
  const res = await api('/tasks/convert-all-to-public', { method: 'POST' });
  toast(res.message, res.code === 0 ? 'success' : 'error');
  if (res.code === 0) refreshTasks();
}

// === 消息调度 - 模板管理 ===
const CATEGORY_LABELS = {
  task: '📋 任务类', process: '🔧 流程类', alert: '⚠️ 告警类',
  material: '📦 物料类', schedule: '📅 排产类', other: '📂 其他'
};
const CATEGORY_COLORS = {
  task: '#667eea', process: '#52c41a', alert: '#ff4d4f',
  material: '#fa8c16', schedule: '#722ed1', other: '#888'
};

let _allTemplates = [];
let _defaultTemplateIds = [];
let _currentTemplateCategory = 'all';
let _templatePreference = {};

async function loadTemplates() {
  try {
    const res = await api('/messages/templates');
    if (res.code !== 0) return;
    _allTemplates = res.data;

    const defaultTmpls = await api('/messages/templates/defaults');
    _defaultTemplateIds = (defaultTmpls.code === 0 ? defaultTmpls.data : []).map(t => t.id);

    const prefRes = await api('/messages/templates/preference');
    if (prefRes.code === 0) {
      _templatePreference = prefRes.data || {};
    }

    const sel = document.getElementById('send-template-select');
    const grouped = {};
    for (const t of _allTemplates) {
      const cat = t.category || 'other';
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(t);
    }

    const catOrder = ['task', 'process', 'alert', 'material', 'schedule', 'other'];
    let selHtml = '<option value="">— 选择模板发送（推荐）—</option>';
    for (const cat of catOrder) {
      if (grouped[cat]) {
        selHtml += `<optgroup label="${CATEGORY_LABELS[cat] || cat}">`;
        for (const t of grouped[cat]) {
          selHtml += `<option value="${t.id}">${t.name}</option>`;
        }
        selHtml += '</optgroup>';
      }
    }
    sel.innerHTML = selHtml;

    renderTemplateList(_currentTemplateCategory);
    renderQuickTemplateSelector();
    initDragAndDrop();
  } catch (e) {
    console.error('[Templates] 加载模板异常:', e);
  }
}

function initDragAndDrop() {
  document.querySelectorAll('.template-cards').forEach(container => {
    container.addEventListener('dragstart', handleDragStart);
    container.addEventListener('dragend', handleDragEnd);
    container.addEventListener('dragover', handleDragOver);
    container.addEventListener('dragleave', handleDragLeave);
    container.addEventListener('drop', handleDrop);
  });
}

let _draggedCard = null;
let _draggedCategory = null;

function handleDragStart(e) {
  const card = e.target.closest('.template-card');
  if (!card) return;
  _draggedCard = card;
  _draggedCategory = card.dataset.category;
  card.classList.add('dragging');
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', card.dataset.id);
}

function handleDragEnd(e) {
  const card = e.target.closest('.template-card');
  if (card) card.classList.remove('dragging');
  document.querySelectorAll('.template-card').forEach(c => c.classList.remove('drag-over'));
  _draggedCard = null;
  _draggedCategory = null;
}

function handleDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  const card = e.target.closest('.template-card');
  if (card && card !== _draggedCard) {
    card.classList.add('drag-over');
  }
}

function handleDragLeave(e) {
  const card = e.target.closest('.template-card');
  if (card) card.classList.remove('drag-over');
}

function handleDrop(e) {
  e.preventDefault();
  const targetCard = e.target.closest('.template-card');
  if (!targetCard || targetCard === _draggedCard || targetCard.dataset.category !== _draggedCategory) {
    if (targetCard) targetCard.classList.remove('drag-over');
    return;
  }

  const container = targetCard.closest('.template-cards');
  const draggedRect = _draggedCard.getBoundingClientRect();
  const targetRect = targetCard.getBoundingClientRect();

  if (draggedRect.top < targetRect.top) {
    container.insertBefore(_draggedCard, targetCard.nextSibling);
  } else {
    container.insertBefore(_draggedCard, targetCard);
  }

  targetCard.classList.remove('drag-over');
  saveTemplateOrder();
}

async function saveTemplateOrder() {
  try {
    const category = _currentTemplateCategory;
    const catOrder = ['task', 'process', 'alert', 'material', 'schedule', 'other'];
    let newOrder = [];

    if (category === 'all') {
      for (const cat of catOrder) {
        const container = document.querySelector(`.template-cards[data-category="${cat}"]`);
        if (container) {
          container.querySelectorAll('.template-card').forEach(card => {
            newOrder.push(card.dataset.id);
          });
        }
      }
      const otherCats = document.querySelectorAll('.template-cards');
      otherCats.forEach(c => {
        if (!catOrder.includes(c.dataset.category)) {
          c.querySelectorAll('.template-card').forEach(card => {
            if (!newOrder.includes(card.dataset.id)) newOrder.push(card.dataset.id);
          });
        }
      });
    } else {
      const container = document.querySelector(`.template-cards[data-category="${category}"]`);
      if (container) {
        container.querySelectorAll('.template-card').forEach(card => {
          newOrder.push(card.dataset.id);
        });
      }
    }

    if (newOrder.length > 0) {
      const res = await api('/messages/templates/order', {
        method: 'POST',
        body: JSON.stringify({ order: newOrder })
      });
      if (res.code === 0) loadTemplates();
    }
  } catch(e) {
    toast('操作异常: ' + e.message, 'error');
  }
}

function switchTemplateTab(category) {
  _currentTemplateCategory = category;
  document.querySelectorAll('.template-tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.category === category);
  });
  renderTemplateList(category);
}

function renderTemplateList(category) {
  const templates = category === 'all'
    ? _allTemplates
    : _allTemplates.filter(t => (t.category || 'other') === category);

  const catOrder = ['task', 'process', 'alert', 'material', 'schedule', 'other'];

  if (templates.length === 0) {
    document.getElementById('template-list').innerHTML =
      '<div class="empty-state"><div class="icon">📋</div><p>该分类暂无模板</p></div>';
    return;
  }

  let html = '';
  if (category === 'all') {
    for (const cat of catOrder) {
      const items = templates.filter(t => (t.category || 'other') === cat);
      if (items.length === 0) continue;
      html += renderTemplateCategory(cat, items);
    }
  } else {
    html = renderTemplateCategory(category, templates);
  }

  document.getElementById('template-list').innerHTML = html;
}

function renderTemplateCategory(cat, items) {
  const catColor = CATEGORY_COLORS[cat] || '#888';
  const catLabel = CATEGORY_LABELS[cat] || cat;

  let html = `<div class="template-panel" style="border-left: 3px solid ${catColor}; margin-bottom: 16px;">
    <div class="template-panel-header" style="display:flex;align-items:center;gap:8px;margin-bottom:12px;font-size:14px;font-weight:600;color:${catColor};">
      <span>${catLabel}</span>
      <span style="font-size:12px;font-weight:400;color:#999;">(${items.length}个模板)</span>
    </div>
    <div class="template-cards" data-category="${cat}">`;

  for (const t of items) {
    const isDefault = _defaultTemplateIds.includes(t.id);
    const channels = (t.channels || []).map(c =>
      `<span class="channel-tag ${c}">${c === 'wechat_group' ? '💬群聊' : c === 'wechat_app' ? '🤖应用' : '🖥桌面'}</span>`
    ).join(' ');
    const desc = t.description || (t.content || '').slice(0, 80);

    html += `<div class="template-card" draggable="true" data-id="${t.id}" data-category="${cat}">
      <div class="template-card-header">
        <span class="drag-handle" title="拖拽排序">⋮⋮</span>
        <strong>${escHtml(t.name)}</strong>
        ${isDefault ? '<span class="default-badge">默认</span>' : ''}
      </div>
      <div class="template-card-channels">${channels}</div>
      <div class="template-card-desc">${escHtml(desc)}</div>
      <div class="template-card-actions">
        <button class="btn btn-sm btn-outline" onclick="editTemplate('${t.id}')">编辑</button>
        <button class="btn btn-sm btn-outline" onclick="cloneTemplate('${t.id}')" title="另存为副本">📋 另存</button>
        <button class="btn btn-sm ${isDefault ? 'btn-warning' : 'btn-danger'}" onclick="deleteTemplate('${t.id}')">${isDefault ? '重置' : '删除'}</button>
      </div>
    </div>`;
  }

  html += '</div></div>';
  return html;
}

let _quickTemplateCategory = 'task';
let _selectedQuickTemplateId = null;

function switchQuickTemplate(category) {
  _quickTemplateCategory = category;
  document.querySelectorAll('.quick-tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.category === category);
  });
  renderQuickTemplateSelector();
  const savedTemplateId = _templatePreference[category];
  if (savedTemplateId) {
    const tmpl = _allTemplates.find(t => t.id === savedTemplateId);
    if (tmpl) {
      selectQuickTemplate(savedTemplateId);
      return;
    }
  }
  _selectedQuickTemplateId = null;
}

function renderQuickTemplateSelector() {
  const grid = document.getElementById('template-selector-grid');
  const templates = _allTemplates.filter(t => (t.category || 'other') === _quickTemplateCategory);

  if (templates.length === 0) {
    grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:20px;color:#999;">该分类暂无模板</div>';
    return;
  }

  let html = '';
  for (const t of templates) {
    const isSelected = _selectedQuickTemplateId === t.id;
    const channels = (t.channels || []).map(c =>
      c === 'wechat_group' ? '💬' : c === 'wechat_app' ? '🤖' : '🖥'
    ).join(' ');
    html += `<div class="template-selector-card ${isSelected ? 'selected' : ''}" onclick="selectQuickTemplate('${t.id}')">
      <div class="selector-name">${t.name}</div>
      <div class="selector-channels">${channels}</div>
    </div>`;
  }
  grid.innerHTML = html;
}

function selectQuickTemplate(templateId) {
  _selectedQuickTemplateId = templateId;
  renderQuickTemplateSelector();

  const tmpl = _allTemplates.find(t => t.id === templateId);
  if (!tmpl) return;

  document.getElementById('send-template-select').value = templateId;
  document.getElementById('send-content').value = tmpl.content || '';

  const hint = document.getElementById('template-variable-hint');
  const hintList = document.getElementById('var-hint-list');
  const vars = (tmpl.content || '').match(/\{([^}]+)\}/g) || [];
  const uniqueVars = [...new Set(vars.map(v => v.replace(/[{}]/g, '')))];
  if (uniqueVars.length > 0) {
    hintList.innerHTML = uniqueVars.map(v => `<code style="background:#e8e8e8;padding:1px 5px;border-radius:3px;margin:0 2px;">{${v}}</code>`).join(' ');
    hint.style.display = 'block';
  } else {
    hint.style.display = 'none';
  }

  const cat = tmpl.category || 'other';
  if (_templatePreference[cat] !== templateId) {
    _templatePreference[cat] = templateId;
    api('/messages/templates/preference', {
      method: 'POST',
      body: JSON.stringify({ category: cat, template_id: templateId })
    });
  }
}

let _availableVars = [];

async function loadAvailableVars(category) {
  const cat = category || 'all';
  const res = await api('/messages/templates/variables?category=' + cat);
  if (res.code === 0) {
    _availableVars = res.data || [];
  }
  return _availableVars;
}

function showTemplateModal() {
  var titleEl = document.getElementById('template-modal-title');
  var idEl = document.getElementById('tmpl-edit-id');
  var nameEl = document.getElementById('tmpl-name');
  var catEl = document.getElementById('tmpl-category');
  var descEl = document.getElementById('tmpl-description');
  var contentEl = document.getElementById('tmpl-content');
  var missing = [];
  if (!titleEl) missing.push('template-modal-title');
  if (!idEl) missing.push('tmpl-edit-id');
  if (!nameEl) missing.push('tmpl-name');
  if (!catEl) missing.push('tmpl-category');
  if (!descEl) missing.push('tmpl-description');
  if (!contentEl) missing.push('tmpl-content');
  if (missing.length) {
    console.error('template modal fields not found:', missing.join(', '));
    toast('模板编辑框加载失败，请尝试 Ctrl+F5 强制刷新页面', 'error');
    return;
  }
  titleEl.textContent = '新建消息模板';
  idEl.value = '';
  nameEl.value = '';
  catEl.value = 'task';
  descEl.value = '';
  contentEl.value = '';
  document.querySelectorAll('#template-modal input[type="checkbox"]').forEach(c => c.checked = false);
  var defaultCb = document.querySelector('#template-modal input[value="wechat_group"]');
  if (defaultCb) defaultCb.checked = true;
  _previewVarValues = {};
  _tmplSelectedOperatorIds = new Set();
  _tmplSelectedDeptIds = new Set();
  var sendAllCb = document.getElementById('tmpl-send-all-checkbox');
  if (sendAllCb) sendAllCb.checked = false;
  var wechatAppCb = document.querySelector('#template-modal input[value="wechat_app"]');
  var receiverSelector = document.getElementById('tmpl-receiver-selector');
  if (wechatAppCb && wechatAppCb.checked) {
    receiverSelector.style.display = 'block';
    if (!_tmplDeptTreeCache) {
      loadTmplReceiverDeptTree();
    } else {
      document.getElementById('tmpl-dept-receiver-list').innerHTML = renderTmplReceiverDeptTree(_tmplDeptTreeCache);
      document.getElementById('tmpl-operator-receiver-list').innerHTML = '';
      updateTmplReceiverCount([]);
    }
  } else {
    receiverSelector.style.display = 'none';
  }
  loadAvailableVars('task').then(() => { buildVarPanel(); updatePreview(); });
  openModal('template-modal');
}

async function editTemplate(id) {
  const res = await api('/messages/templates');
  if (res.code !== 0) return;
  const tmpl = res.data.find(t => t.id === id);
  if (!tmpl) { toast('模板不存在', 'error'); return; }
  var titleEl = document.getElementById('template-modal-title');
  var idEl = document.getElementById('tmpl-edit-id');
  var nameEl = document.getElementById('tmpl-name');
  var catEl = document.getElementById('tmpl-category');
  var descEl = document.getElementById('tmpl-description');
  var contentEl = document.getElementById('tmpl-content');
  var missing = [];
  if (!titleEl) missing.push('template-modal-title');
  if (!idEl) missing.push('tmpl-edit-id');
  if (!nameEl) missing.push('tmpl-name');
  if (!catEl) missing.push('tmpl-category');
  if (!descEl) missing.push('tmpl-description');
  if (!contentEl) missing.push('tmpl-content');
  if (missing.length) {
    console.error('template modal fields not found:', missing.join(', '));
    toast('模板编辑框加载失败，请尝试 Ctrl+F5 强制刷新页面', 'error');
    return;
  }
  titleEl.textContent = '编辑模板';
  idEl.value = id;
  nameEl.value = tmpl.name || '';
  catEl.value = tmpl.category || 'other';
  descEl.value = tmpl.description || '';
  contentEl.value = tmpl.content || '';
  document.querySelectorAll('#template-modal input[type="checkbox"]').forEach(c => {
    c.checked = (tmpl.channels || []).includes(c.value);
  });
  _tmplSelectedOperatorIds = new Set();
  _tmplSelectedDeptIds = new Set();
  var sendAllCb = document.getElementById('tmpl-send-all-checkbox');
  var wechatAppCb = document.querySelector('#template-modal input[value="wechat_app"]');
  var receiverSelector = document.getElementById('tmpl-receiver-selector');
  const tmplReceivers = tmpl.receivers || {};
  if (tmplReceivers.send_all) {
    sendAllCb.checked = true;
  } else {
    sendAllCb.checked = false;
    (tmplReceivers.operator_ids || []).forEach(oid => _tmplSelectedOperatorIds.add(oid));
    (tmplReceivers.department_ids || []).forEach(did => _tmplSelectedDeptIds.add(did));
  }
  if (wechatAppCb && wechatAppCb.checked) {
    receiverSelector.style.display = 'block';
    if (!_tmplDeptTreeCache) {
      loadTmplReceiverDeptTree();
    } else {
      document.getElementById('tmpl-dept-receiver-list').innerHTML = renderTmplReceiverDeptTree(_tmplDeptTreeCache);
      _tmplSelectedDeptIds.forEach(did => {
        var cb = document.querySelector(`#tmpl-dept-receiver-list input[value="${did}"]`);
        if (cb) cb.checked = true;
      });
      renderTmplOperatorReceivers();
      updateTmplReceiverCount(getTmplSelectedReceivers());
    }
  } else {
    receiverSelector.style.display = 'none';
  }
  _previewVarValues = {};
  loadAvailableVars(tmpl.category || 'task').then(() => { buildVarPanel(); updatePreview(); });
  openModal('template-modal');
}

async function saveTemplate() {
  try {
    const idEl = document.getElementById('tmpl-edit-id');
    const nameEl = document.getElementById('tmpl-name');
    const catEl = document.getElementById('tmpl-category');
    const descEl = document.getElementById('tmpl-description');
    const contentEl = document.getElementById('tmpl-content');
    if (!idEl || !nameEl || !catEl || !descEl || !contentEl) {
      toast('模板编辑框状态异常，请关闭后重试', 'error');
      return;
    }
    const id = idEl.value;
    const name = nameEl.value.trim();
    const category = catEl.value;
    const description = descEl.value.trim();
    const content = contentEl.value.trim();
    if (!name || !content) { toast('请填写模板名称和内容', 'error'); return; }
    const channels = Array.from(document.querySelectorAll('#template-modal input[type="checkbox"]:checked')).map(c => c.value);

    const body = { name, category, description, content, channels };
    const wechatAppChecked = channels.includes('wechat_app');
    if (wechatAppChecked) {
      const receivers = {};
      const selectedIds = getTmplSelectedReceivers();
      if (selectedIds[0] === '@all') {
        receivers.send_all = true;
      } else {
        const allMembers = collectAllTmplMembers(_tmplDeptTreeCache || []);
        const allMemberIds = new Set(allMembers.map(m => m.userid));
        const operatorIds = [];
        const departmentIds = [];
        for (const opId of selectedIds) {
          if (allMemberIds.has(opId)) {
            operatorIds.push(opId);
          }
        }
        receivers.operator_ids = operatorIds;
        receivers.department_ids = Array.from(_tmplSelectedDeptIds);
        if (operatorIds.length === 0 && departmentIds.length === 0) {
          receivers.send_all = true;
        }
      }
      body.receivers = receivers;
    }
    let res;
    if (id) {
      res = await api(`/messages/templates/${id}`, { method: 'PUT', body });
    } else {
      res = await api('/messages/templates', { method: 'POST', body });
    }
    toast(res.message, res.code === 0 ? 'success' : 'error');
    if (res.code === 0) {
      closeModal('template-modal');
      loadTemplates();
    }
  } catch(e) {
    toast('操作异常: ' + e.message, 'error');
  }
}

async function deleteTemplate(id) {
  if (!confirm('确认删除该模板？')) return;
  const res = await api(`/messages/templates/${id}`, { method: 'DELETE' });
  toast(res.message, res.code === 0 ? 'success' : 'error');
  if (res.code === 0) loadTemplates();
}

async function resetDefaultTemplates() {
  if (!confirm('重置为默认模板？\n\n自定义模板将被保留，默认模板会恢复到初始状态。')) return;
  const res = await api('/messages/templates/defaults/reset', { method: 'POST' });
  if (res.code === 0) {
    toast('已重置为默认模板，共 ' + res.data.length + ' 个模板', 'success');
    loadTemplates();
  } else {
    toast(res.message || '重置失败', 'error');
  }
}

// ── 实时预览 + 变量工具栏 ──────────────────────────
const COMMON_VARS = [
  { key: '工单号', label: '工单号' },
  { key: '任务标题', label: '任务标题' },
  { key: '数量', label: '数量' },
  { key: '截止时间', label: '截止时间' },
  { key: '优先级', label: '优先级' },
  { key: '已用分钟', label: '已用时间(分钟)' },
  { key: '提醒次数', label: '提醒次数' },
  { key: '超时分钟', label: '超时分钟' },
  { key: '逾期天数', label: '逾期天数' },
  { key: '延期原因', label: '延期原因' },
  { key: '原截止时间', label: '原截止时间' },
  { key: '新截止时间', label: '新截止时间' },
  { key: '操作员', label: '操作员' },
  { key: '工序', label: '工序' },
  { key: '原负责人', label: '原负责人' },
  { key: '新负责人', label: '新负责人' },
  { key: '执行人', label: '执行人' },
  { key: '完成时间', label: '完成时间' },
  { key: '流程名称', label: '流程名称' },
  { key: '当前步骤', label: '当前步骤' },
  { key: '下一步骤', label: '下一步骤' },
  { key: '产品', label: '产品' },
  { key: '客户', label: '客户' },
  { key: '发起人', label: '发起人' },
  { key: '质量问题', label: '质量问题' },
  { key: '检测环节', label: '检测环节' },
  { key: '质检员', label: '质检员' },
  { key: '物料名称', label: '物料名称' },
  { key: '短缺数量', label: '短缺数量' },
  { key: '单位', label: '单位' },
  { key: '影响描述', label: '影响描述' },
  { key: '到货数量', label: '到货数量' },
  { key: '到货时间', label: '到货时间' },
  { key: '供应商', label: '供应商' },
  { key: '当前库存', label: '当前库存' },
  { key: '安全库存', label: '安全库存' },
  { key: '可用天数', label: '可用天数' },
  { key: '原排产计划', label: '原排产计划' },
  { key: '新排产计划', label: '新排产计划' },
  { key: '变更原因', label: '变更原因' },
  { key: '外协单号', label: '外协单号' },
  { key: '发出时间', label: '发出时间' },
  { key: '预计返回', label: '预计返回' },
  { key: '实收数量', label: '实收数量' },
  { key: '收货时间', label: '收货时间' },
  { key: '质检结果', label: '质检结果' },
  { key: '设备名称', label: '设备名称' },
  { key: '报修人', label: '报修人' },
  { key: '报修时间', label: '报修时间' },
  { key: '故障描述', label: '故障描述' },
  { key: '紧急程度', label: '紧急程度' },
  { key: '维修人', label: '维修人' },
  { key: '维修结果', label: '维修结果' },
  { key: '耗时(小时)', label: '耗时(小时)' },
  { key: '求助人', label: '求助人' },
  { key: '问题描述', label: '问题描述' },
  { key: '协助人', label: '协助人' },
  { key: '解决时间', label: '解决时间' },
  { key: '解决方案', label: '解决方案' },
];

function buildVarPanel() {
  const content = document.getElementById('tmpl-content').value;
  const headerEl = document.getElementById('var-panel-header');
  const bodyEl = document.getElementById('var-panel-body');
  const countEl = document.getElementById('var-count');

  const varNames = [...new Set(
    (content.match(/\{([^}]+)\}/g) || []).map(v => v.replace(/[{}]/g, ''))
  )];

  if (varNames.length === 0) {
    headerEl.style.display = 'none';
    bodyEl.innerHTML = '<span id="var-panel-empty" style="color:#bbb;font-size:12px;">输入 <code style="background:#f0f0f0;padding:1px 4px;border-radius:2px;">{变量名}</code> 后将在此显示可拖拽的变量卡片</span>';
  } else {
    headerEl.style.display = 'block';
    countEl.textContent = '(' + varNames.length + '个)';

    const countMap = {};
    const allVars = content.match(/\{([^}]+)\}/g) || [];
    allVars.forEach(function(v) {
      const name = v.replace(/[{}]/g, '');
      countMap[name] = (countMap[name] || 0) + 1;
    });

    var html = '';
    for (var i = 0; i < varNames.length; i++) {
      var vName = varNames[i];
      var count = countMap[vName] || 1;
      html += '<div draggable="true" class="var-chip" data-var="' + vName + '"'
        + ' title="拖拽或点击插入 · 出现 ' + count + ' 次"'
        + ' style="display:inline-flex;align-items:center;gap:4px;padding:4px 10px;background:#fff;border:1px solid #d0d0ff;border-radius:16px;cursor:grab;font-size:12px;color:#667eea;user-select:none;transition:all 0.15s;"'
        + ' onmouseover="this.style.background=\'#667eea\';this.style.color=\'#fff\';this.style.borderColor=\'#667eea\'"'
        + ' onmouseout="this.style.background=\'#fff\';this.style.color=\'#667eea\';this.style.borderColor=\'#d0d0ff\'"'
        + ' ondragstart="onVarDragStart(event)"'
        + ' ondragend="onVarDragEnd(event)"'
        + ' onclick="onVarClick(this)">'
        + '<span>{' + vName + '}</span>'
        + '<span style="font-size:10px;opacity:0.6;">\u00d7' + count + '</span>'
        + '</div>';
    }
    bodyEl.innerHTML = html;
  }

  var availEl = document.getElementById('available-vars-panel');
  if (availEl) {
    var usedSet = new Set(varNames);
    var availHtml = '<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">'
      + '<span style="font-size:12px;font-weight:600;color:#888;">📎 可用变量</span>'
      + '<input id="var-search-input" type="text" placeholder="搜索变量（中/英文）…" '
      + 'oninput="filterAvailableVars()" '
      + 'style="flex:1;padding:4px 8px;border:1px solid #d9d9d9;border-radius:6px;font-size:11px;outline:none;transition:border-color 0.2s;" '
      + 'onfocus="this.style.borderColor=\'#667eea\'" onblur="this.style.borderColor=\'#d9d9d9\'">'
      + '</div>';
    availHtml += '<div id="avail-vars-list" style="display:flex;flex-wrap:wrap;gap:4px;">';
    for (var j = 0; j < _availableVars.length; j++) {
      var av = _availableVars[j];
      var isUsed = usedSet.has(av.cn);
      var chipStyle = isUsed
        ? 'background:#f0f0f0;border:1px solid #ddd;color:#aaa;cursor:default;'
        : 'background:#fff;border:1px solid #b7e4c7;color:#2d6a4f;cursor:pointer;';
      availHtml += '<div class="avail-var-chip" data-cn="' + av.cn + '" data-en="' + av.en + '"'
        + ' title="' + av.cn + ' → ' + av.en + '"'
        + ' style="display:inline-flex;align-items:center;gap:3px;padding:3px 8px;border-radius:12px;font-size:11px;user-select:none;transition:all 0.15s;' + chipStyle + '"'
        + (isUsed ? '' : ' onclick="insertAvailableVar(\'' + av.cn + '\')"'
          + ' onmouseover="this.style.background=\'#2d6a4f\';this.style.color=\'#fff\';this.style.borderColor=\'#2d6a4f\'"'
          + ' onmouseout="this.style.background=\'#fff\';this.style.color=\'#2d6a4f\';this.style.borderColor=\'#b7e4c7\'"')
        + '>'
        + '<span>{' + av.cn + '}</span>'
        + '<span style="font-size:9px;opacity:0.5;">' + av.en + '</span>'
        + (isUsed ? '<span style="font-size:9px;color:#52c41a;">✓</span>' : '')
        + '</div>';
    }
    availHtml += '</div>';
    availEl.innerHTML = availHtml;
  }
}

function insertAvailableVar(cnName) {
  var ta = document.getElementById('tmpl-content');
  var start = ta.selectionStart;
  var end = ta.selectionEnd;
  var text = ta.value;
  var insert = '{' + cnName + '}';
  ta.value = text.slice(0, start) + insert + text.slice(end);
  ta.focus();
  ta.selectionStart = ta.selectionEnd = start + insert.length;
  updatePreview();
}

function onCategoryChange() {
  var cat = document.getElementById('tmpl-category').value;
  loadAvailableVars(cat).then(function() { buildVarPanel(); });
  updatePreview();
}

function filterAvailableVars() {
  var input = document.getElementById('var-search-input');
  if (!input) return;
  var keyword = input.value.trim().toLowerCase();
  var chips = document.querySelectorAll('#avail-vars-list .avail-var-chip');
  var visibleCount = 0;
  chips.forEach(function(chip) {
    var cn = (chip.getAttribute('data-cn') || '').toLowerCase();
    var en = (chip.getAttribute('data-en') || '').toLowerCase();
    var match = !keyword || cn.indexOf(keyword) !== -1 || en.indexOf(keyword) !== -1;
    chip.style.display = match ? '' : 'none';
    if (match) visibleCount++;
  });
  var emptyHint = document.getElementById('var-search-empty');
  if (visibleCount === 0 && keyword) {
    if (!emptyHint) {
      var list = document.getElementById('avail-vars-list');
      var hint = document.createElement('span');
      hint.id = 'var-search-empty';
      hint.style.cssText = 'color:#bbb;font-size:11px;padding:4px 0;';
      hint.textContent = '未找到匹配的变量';
      list.appendChild(hint);
    }
  } else if (emptyHint) {
    emptyHint.remove();
  }
}

function onVarDragStart(e) {
  var vName = e.target.getAttribute('data-var');
  e.dataTransfer.setData('text/plain', vName);
  e.dataTransfer.effectAllowed = 'copy';
  e.target.style.opacity = '0.5';
  var ta = document.getElementById('tmpl-content');
  ta.style.borderColor = '#667eea';
  ta.style.boxShadow = '0 0 0 2px rgba(102,126,234,0.2)';
}

function onVarDragEnd(e) {
  e.target.style.opacity = '1';
  var ta = document.getElementById('tmpl-content');
  ta.style.borderColor = '';
  ta.style.boxShadow = '';
}

function onVarClick(el) {
  var vName = el.getAttribute('data-var');
  var ta = document.getElementById('tmpl-content');
  var start = ta.selectionStart;
  var end = ta.selectionEnd;
  var text = ta.value;
  ta.value = text.slice(0, start) + '{' + vName + '}' + text.slice(end);
  ta.focus();
  ta.selectionStart = ta.selectionEnd = start + vName.length + 2;
  updatePreview();
}

document.addEventListener('DOMContentLoaded', function() {
  var ta = document.getElementById('tmpl-content');
  if (!ta) return;
  ta.addEventListener('dragover', function(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  });
  ta.addEventListener('drop', function(e) {
    e.preventDefault();
    var vName = e.dataTransfer.getData('text/plain');
    if (!vName) return;
    var start = ta.selectionStart;
    var text = ta.value;
    ta.value = text.slice(0, start) + '{' + vName + '}' + text.slice(start);
    ta.focus();
    ta.selectionStart = ta.selectionEnd = start + vName.length + 2;
    ta.style.borderColor = '';
    ta.style.boxShadow = '';
    updatePreview();
  });
});

let _previewVarValues = {};

function updatePreview() {
  buildVarPanel();
  const content = document.getElementById('tmpl-content').value;
  const titleEl = document.getElementById('preview-title');
  const bodyEl = document.getElementById('preview-body');
  const varInputsEl = document.getElementById('preview-var-inputs');
  const channelTag = document.getElementById('preview-channel-tag');

  const checkedChannels = Array.from(
    document.querySelectorAll('#template-modal input[type="checkbox"]:checked')
  ).map(c => c.value);
  const channelLabels = { wechat_group: '💬群聊', wechat_app: '🤖应用', desktop: '🖥桌面' };
  channelTag.textContent = checkedChannels.map(c => channelLabels[c] || c).join(' / ') || '未选择';

  if (!content.trim()) {
    bodyEl.innerHTML = '<div style="color:#999;text-align:center;padding:40px 0;">编辑左侧内容后自动预览</div>';
    varInputsEl.innerHTML = '';
    return;
  }

  const varNames = [...new Set(
    (content.match(/\{([^}]+)\}/g) || []).map(v => v.replace(/[{}]/g, ''))
  )];

  let varHtml = '';
  for (const vName of varNames) {
    if (_previewVarValues[vName] === undefined) {
      _previewVarValues[vName] = vName;
    }
    const varInfo = COMMON_VARS.find(cv => cv.key === vName);
    const label = varInfo ? `${vName} (${varInfo.label})` : vName;
    varHtml += `<span style="display:inline-flex;align-items:center;gap:4px;background:#fff;border:1px solid #e0e0e0;border-radius:4px;padding:2px 6px;">
      <span style="color:#888;font-size:11px;">${label}</span>
      <input type="text" value="${_previewVarValues[vName]}"
        oninput="_previewVarValues['${vName}']=this.value;renderPreviewContent()"
        style="width:70px;padding:2px 4px;border:1px solid #d0d0ff;border-radius:2px;font-size:12px;">
    </span>`;
  }
  varInputsEl.innerHTML = varHtml || '<span style="color:#ccc;">无变量</span>';

  titleEl.textContent = document.getElementById('tmpl-name').value.trim() || '消息预览';
  renderPreviewContent();
}

function renderPreviewContent() {
  let content = document.getElementById('tmpl-content').value;
  const bodyEl = document.getElementById('preview-body');
  content = content.replace(/\{([^}]+)\}/g, (match, vName) => {
    const val = _previewVarValues[vName];
    return val !== undefined ? `<span style="color:#667eea;font-weight:500;">${val}</span>` : match;
  });
  content = content.replace(/\n/g, '<br>');
  bodyEl.innerHTML = content || '<div style="color:#999;text-align:center;padding:40px 0;">编辑左侧内容后自动预览</div>';
}

// ── 另存为 ──────────────────────────
async function cloneTemplate(id) {
  const res = await api('/messages/templates');
  if (res.code !== 0) return;
  const tmpl = res.data.find(t => t.id === id);
  if (!tmpl) { toast('模板不存在', 'error'); return; }
  showTemplateModal();
  document.getElementById('template-modal-title').textContent = '另存为模板副本';
  document.getElementById('tmpl-edit-id').value = '';
  document.getElementById('tmpl-name').value = tmpl.name + ' (副本)';
  document.getElementById('tmpl-category').value = tmpl.category || 'other';
  document.getElementById('tmpl-description').value = tmpl.description || '';
  document.getElementById('tmpl-content').value = tmpl.content || '';
  document.querySelectorAll('#template-modal input[type="checkbox"]').forEach(c => {
    c.checked = (tmpl.channels || []).includes(c.value);
  });
  buildVarPanel();
  _previewVarValues = {};
  updatePreview();
}

// === 消息发送 ===
async function onSendTemplateChange() {
  const sel = document.getElementById('send-template-select');
  const hint = document.getElementById('template-variable-hint');
  const hintList = document.getElementById('var-hint-list');

  if (!sel.value) {
    hint.style.display = 'none';
    document.getElementById('send-content').value = '';
    return;
  }

  const res = await api('/messages/templates');
  if (res.code !== 0) return;
  const tmpl = res.data.find(t => t.id === sel.value);
  if (!tmpl) return;

  // 提取变量提示
  const vars = tmpl.content.match(/\{([^}]+)\}/g) || [];
  const uniqueVars = [...new Set(vars.map(v => v.replace(/[{}]/g, '')))];
  if (uniqueVars.length > 0) {
    hintList.innerHTML = uniqueVars.map(v => `<code style="background:#e8e8e8;padding:1px 5px;border-radius:3px;margin:0 2px;">{${v}}</code>`).join(' ');
    hint.style.display = 'block';
  } else {
    hint.style.display = 'none';
  }

  // 尝试用已有变量替换
  let content = tmpl.content;
  const varsStr = document.getElementById('send-variables').value.trim();
  if (varsStr) {
    try {
      const parsed = JSON.parse(varsStr);
      for (const [k, v] of Object.entries(parsed)) {
        content = content.replace(new RegExp('\\{' + k + '\\}', 'g'), v);
      }
    } catch (e) { /* ignore parse error */ }
  }
  document.getElementById('send-content').value = content;
}

function showTemplatePreview() {
  const sel = document.getElementById('send-template-select');
  if (!sel.value) {
    toast('请先选择一个模板', 'info');
    return;
  }
  api('/messages/templates').then(res => {
    if (res.code !== 0) return;
    const tmpl = res.data.find(t => t.id === sel.value);
    if (!tmpl) return;
    const catLabel = CATEGORY_LABELS[tmpl.category] || tmpl.category || '未分类';
    const channels = (tmpl.channels || []).map(c =>
      c === 'wechat_group' ? '💬群聊' : c === 'wechat_app' ? '🤖应用' : '🖥桌面'
    ).join(', ') || '未配置';

    let rendered = tmpl.content;
    const varsStr = document.getElementById('send-variables').value.trim();
    if (varsStr) {
      try {
        const parsed = JSON.parse(varsStr);
        for (const [k, v] of Object.entries(parsed)) {
          rendered = rendered.replace(new RegExp('\\{' + k + '\\}', 'g'), v);
        }
      } catch (e) {}
    }

    const previewHtml = `
      <div style="margin-bottom:12px;">
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:8px;">
          <span style="font-size:12px;color:#888;">📌 名称: <strong>${tmpl.name}</strong></span>
          <span style="font-size:12px;color:#888;">🏷 分类: ${catLabel}</span>
          <span style="font-size:12px;color:#888;">📡 渠道: ${channels}</span>
        </div>
        ${tmpl.description ? `<div style="font-size:12px;color:#666;margin-bottom:8px;">📝 描述: ${tmpl.description}</div>` : ''}
        <div style="background:#f5f5f5;border:1px solid #e8e8e8;border-radius:6px;padding:16px;white-space:pre-wrap;font-size:13px;line-height:1.6;max-height:300px;overflow-y:auto;">${rendered}</div>
      </div>
    `;

    // 用 toast 形式展示预览
    const previewDiv = document.createElement('div');
    previewDiv.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:3000;background:#fff;border-radius:8px;box-shadow:0 8px 40px rgba(0,0,0,0.2);width:600px;max-width:90vw;max-height:80vh;overflow-y:auto;';
    previewDiv.innerHTML = `
      <div style="padding:16px 20px;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between;align-items:center;">
        <h3 style="font-size:16px;">👁 模板预览</h3>
        <button onclick="this.parentElement.parentElement.remove()" style="background:none;border:none;font-size:20px;cursor:pointer;color:#999;">&times;</button>
      </div>
      <div style="padding:20px;">${previewHtml}</div>
      <div style="padding:12px 20px;border-top:1px solid #f0f0f0;text-align:right;">
        <button class="btn btn-outline" onclick="this.parentElement.parentElement.remove()">关闭</button>
      </div>
    `;
    document.body.appendChild(previewDiv);
  });
}

let _deptTreeCache = null;

function toggleReceiverSelector() {
  const wechatAppChecked = document.querySelector('#tab-messages input[value="wechat_app"]').checked;
  const selector = document.getElementById('receiver-selector');
  if (wechatAppChecked) {
    selector.style.display = 'block';
    if (!_deptTreeCache) {
      loadReceiverDeptTree();
    }
  } else {
    selector.style.display = 'none';
  }
}

function toggleSendAll() {
  const sendAllChecked = document.getElementById('send-all-checkbox').checked;
  const deptList = document.getElementById('dept-receiver-list');
  const opList = document.getElementById('operator-receiver-list');
  if (sendAllChecked) {
    deptList.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
    opList.innerHTML = '';
    updateReceiverCount(['@all']);
  } else {
    updateReceiverCount(getSelectedReceivers());
  }
}

async function loadReceiverDeptTree() {
  const container = document.getElementById('dept-receiver-list');
  const res = await fetchWechatDepartments(false);
  if (res.code !== 0) {
    container.innerHTML = `<div style="color:#ff4d4f;text-align:center;padding:10px;">❌ ${escHtml(res.message || '获取部门失败')}</div>`;
    return;
  }
  _deptTreeCache = res.data.departments || [];
  container.innerHTML = renderReceiverDeptTree(_deptTreeCache);
  document.getElementById('operator-receiver-list').innerHTML = '';
  updateReceiverCount([]);
}

function renderReceiverDeptTree(nodes, depth = 0) {
  return nodes.map(node => {
    const hasChildren = node.children && node.children.length > 0;
    const indent = depth * 16;
    const members = node.members || [];
    return `
      <div class="dept-tree-node" style="margin-left:${indent}px;margin-bottom:4px;">
        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">
          <input type="checkbox" value="${node.id}" data-type="dept" onchange="onReceiverDeptChange(this)">
          <span>${escHtml(node.name)}</span>
          <span style="color:#999;font-size:11px;">(${members.length}人)</span>
        </label>
        ${hasChildren ? `<div style="margin-left:20px;">${renderReceiverDeptTree(node.children, depth + 1)}</div>` : ''}
      </div>
    `;
  }).join('');
}

function onReceiverDeptChange(checkbox) {
  const deptId = checkbox.value;
  const checked = checkbox.checked;
  const deptNode = findDeptNode(_deptTreeCache, parseInt(deptId));
  if (!deptNode) return;

  if (checked) {
    addDeptMembersAsReceivers(deptNode);
  } else {
    removeDeptMembersFromReceivers(deptNode);
  }
  renderOperatorReceivers();
  updateReceiverCount(getSelectedReceivers());
}

function findDeptNode(nodes, deptId) {
  for (const node of nodes) {
    if (node.id === deptId) return node;
    if (node.children) {
      const found = findDeptNode(node.children, deptId);
      if (found) return found;
    }
  }
  return null;
}

function getAllMemberIds(node) {
  let ids = (node.members || []).map(m => m.userid);
  if (node.children) {
    for (const child of node.children) {
      ids = ids.concat(getAllMemberIds(child));
    }
  }
  return ids;
}

let _selectedOperatorIds = new Set();
let _selectedDeptIds = new Set();

function addDeptMembersAsReceivers(deptNode) {
  _selectedDeptIds.add(deptNode.id);
  const memberIds = getAllMemberIds(deptNode);
  memberIds.forEach(id => _selectedOperatorIds.add(id));
}

function removeDeptMembersFromReceivers(deptNode) {
  _selectedDeptIds.delete(deptNode.id);
  const memberIds = getAllMemberIds(deptNode);
  memberIds.forEach(id => {
    for (const deptId of _selectedDeptIds) {
      const dNode = findDeptNode(_deptTreeCache, deptId);
      if (dNode && getAllMemberIds(dNode).includes(id)) {
        return;
      }
    }
    _selectedOperatorIds.delete(id);
  });
}

function renderOperatorReceivers() {
  const container = document.getElementById('operator-receiver-list');
  if (_selectedOperatorIds.size === 0) {
    container.innerHTML = '';
    return;
  }
  const allMembers = collectAllMembers(_deptTreeCache);
  const selectedMembers = allMembers.filter(m => _selectedOperatorIds.has(m.userid));
  const deptsMap = {};
  _deptTreeCache.forEach(d => buildDeptNameMap(d, deptsMap));

  container.innerHTML = `
    <div style="font-size:12px;color:#666;margin-bottom:4px;">已选操作员：</div>
    <div style="display:flex;flex-wrap:wrap;gap:4px;">
      ${selectedMembers.map(m => `
        <span class="member-tag" style="background:#e6f7ff;border:1px solid #91d5ff;padding:2px 8px;border-radius:4px;font-size:12px;">
          ${m.name}
          <small style="color:#999;">(${deptsMap[m.userid] || '未知部门'})</small>
          <a href="#" onclick="removeReceiver('${m.userid}');return false;" style="color:#ff4d4f;margin-left:4px;">×</a>
        </span>
      `).join('')}
    </div>
  `;
}

function buildDeptNameMap(node, map) {
  (node.members || []).forEach(m => {
    map[m.userid] = node.name;
  });
  (node.children || []).forEach(c => buildDeptNameMap(c, map));
}

function collectAllMembers(nodes) {
  let members = [];
  nodes.forEach(n => {
    members = members.concat(n.members || []);
    if (n.children) members = members.concat(collectAllMembers(n.children));
  });
  return members;
}

function removeReceiver(userId) {
  _selectedOperatorIds.delete(userId);
  for (const deptId of _selectedDeptIds) {
    const dNode = findDeptNode(_deptTreeCache, deptId);
    if (dNode && getAllMemberIds(dNode).includes(userId)) {
      _selectedDeptIds.delete(deptId);
      const memberIds = getAllMemberIds(dNode);
      memberIds.forEach(id => {
        for (const dId of _selectedDeptIds) {
          if (dId !== deptId) {
            const otherNode = findDeptNode(_deptTreeCache, dId);
            if (otherNode && getAllMemberIds(otherNode).includes(id)) {
              _selectedOperatorIds.add(id);
              break;
            }
          }
        }
      });
      break;
    }
  }
  renderOperatorReceivers();
  updateReceiverCount(getSelectedReceivers());
}

function getSelectedReceivers() {
  if (document.getElementById('send-all-checkbox').checked) {
    return ['@all'];
  }
  return Array.from(_selectedOperatorIds);
}

function updateReceiverCount(ids) {
  const count = ids[0] === '@all' ? '全部' : ids.length;
  document.getElementById('selected-receiver-count').textContent = count;
}

let _tmplDeptTreeCache = null;
let _tmplSelectedOperatorIds = new Set();
let _tmplSelectedDeptIds = new Set();

function toggleTmplReceiverSelector() {
  const wechatAppChecked = document.querySelector('#template-modal input[value="wechat_app"]').checked;
  const selector = document.getElementById('tmpl-receiver-selector');
  if (wechatAppChecked) {
    selector.style.display = 'block';
    if (!_tmplDeptTreeCache) {
      loadTmplReceiverDeptTree();
    }
  } else {
    selector.style.display = 'none';
  }
}

function toggleTmplSendAll() {
  const sendAllChecked = document.getElementById('tmpl-send-all-checkbox').checked;
  const deptList = document.getElementById('tmpl-dept-receiver-list');
  const opList = document.getElementById('tmpl-operator-receiver-list');
  if (sendAllChecked) {
    deptList.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
    opList.innerHTML = '';
    updateTmplReceiverCount(['@all']);
  } else {
    updateTmplReceiverCount(getTmplSelectedReceivers());
  }
}

async function loadTmplReceiverDeptTree() {
  const container = document.getElementById('tmpl-dept-receiver-list');
  const res = await fetchWechatDepartments(false);
  if (res.code !== 0) {
    container.innerHTML = `<div style="color:#ff4d4f;text-align:center;padding:10px;">❌ ${escHtml(res.message || '获取部门失败')}</div>`;
    return;
  }
  _tmplDeptTreeCache = res.data.departments || [];
  container.innerHTML = renderTmplReceiverDeptTree(_tmplDeptTreeCache);
  document.getElementById('tmpl-operator-receiver-list').innerHTML = '';
  updateTmplReceiverCount([]);
}

function renderTmplReceiverDeptTree(nodes, depth = 0) {
  return nodes.map(node => {
    const hasChildren = node.children && node.children.length > 0;
    const indent = depth * 16;
    const members = node.members || [];
    return `
      <div class="dept-tree-node" style="margin-left:${indent}px;margin-bottom:4px;">
        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">
          <input type="checkbox" value="${node.id}" data-type="dept" onchange="onTmplReceiverDeptChange(this)">
          <span>${escHtml(node.name)}</span>
          <span style="color:#999;font-size:11px;">(${members.length}人)</span>
        </label>
        ${hasChildren ? `<div style="margin-left:20px;">${renderTmplReceiverDeptTree(node.children, depth + 1)}</div>` : ''}
      </div>
    `;
  }).join('');
}

function onTmplReceiverDeptChange(checkbox) {
  const deptId = checkbox.value;
  const checked = checkbox.checked;
  const deptNode = findTmplDeptNode(_tmplDeptTreeCache, parseInt(deptId));
  if (!deptNode) return;

  if (checked) {
    addTmplDeptMembersAsReceivers(deptNode);
  } else {
    removeTmplDeptMembersFromReceivers(deptNode);
  }
  renderTmplOperatorReceivers();
  updateTmplReceiverCount(getTmplSelectedReceivers());
}

function findTmplDeptNode(nodes, deptId) {
  for (const node of nodes) {
    if (node.id === deptId) return node;
    if (node.children) {
      const found = findTmplDeptNode(node.children, deptId);
      if (found) return found;
    }
  }
  return null;
}

function getAllTmplMemberIds(node) {
  let ids = (node.members || []).map(m => m.userid);
  if (node.children) {
    for (const child of node.children) {
      ids = ids.concat(getAllTmplMemberIds(child));
    }
  }
  return ids;
}

function addTmplDeptMembersAsReceivers(deptNode) {
  _tmplSelectedDeptIds.add(deptNode.id);
  const memberIds = getAllTmplMemberIds(deptNode);
  memberIds.forEach(id => _tmplSelectedOperatorIds.add(id));
}

function removeTmplDeptMembersFromReceivers(deptNode) {
  _tmplSelectedDeptIds.delete(deptNode.id);
  const memberIds = getAllTmplMemberIds(deptNode);
  memberIds.forEach(id => {
    for (const dId of _tmplSelectedDeptIds) {
      const otherNode = findTmplDeptNode(_tmplDeptTreeCache, dId);
      if (otherNode && getAllTmplMemberIds(otherNode).includes(id)) {
        return;
      }
    }
    _tmplSelectedOperatorIds.delete(id);
  });
}

function renderTmplOperatorReceivers() {
  const container = document.getElementById('tmpl-operator-receiver-list');
  if (_tmplSelectedOperatorIds.size === 0) {
    container.innerHTML = '';
    return;
  }
  const allMembers = collectAllTmplMembers(_tmplDeptTreeCache);
  const selectedMembers = allMembers.filter(m => _tmplSelectedOperatorIds.has(m.userid));
  const deptsMap = {};
  _tmplDeptTreeCache.forEach(d => buildTmplDeptNameMap(d, deptsMap));

  container.innerHTML = `
    <div style="font-size:12px;color:#666;margin-bottom:4px;">已选操作员：</div>
    <div style="display:flex;flex-wrap:wrap;gap:4px;">
      ${selectedMembers.map(m => `
        <span class="member-tag" style="background:#e6f7ff;border:1px solid #91d5ff;padding:2px 8px;border-radius:4px;font-size:12px;">
          ${m.name}
          <small style="color:#999;">(${deptsMap[m.userid] || '未知部门'})</small>
          <a href="#" onclick="removeTmplReceiver('${m.userid}');return false;" style="color:#ff4d4f;margin-left:4px;">×</a>
        </span>
      `).join('')}
    </div>
  `;
}

function buildTmplDeptNameMap(node, map) {
  (node.members || []).forEach(m => {
    map[m.userid] = node.name;
  });
  (node.children || []).forEach(c => buildTmplDeptNameMap(c, map));
}

function collectAllTmplMembers(nodes) {
  let members = [];
  nodes.forEach(n => {
    members = members.concat(n.members || []);
    if (n.children) members = members.concat(collectAllTmplMembers(n.children));
  });
  return members;
}

function removeTmplReceiver(userId) {
  _tmplSelectedOperatorIds.delete(userId);
  for (const deptId of _tmplSelectedDeptIds) {
    const dNode = findTmplDeptNode(_tmplDeptTreeCache, deptId);
    if (dNode && getAllTmplMemberIds(dNode).includes(userId)) {
      _tmplSelectedDeptIds.delete(deptId);
      const memberIds = getAllTmplMemberIds(dNode);
      memberIds.forEach(id => {
        for (const dId of _tmplSelectedDeptIds) {
          if (dId !== deptId) {
            const otherNode = findTmplDeptNode(_tmplDeptTreeCache, dId);
            if (otherNode && getAllTmplMemberIds(otherNode).includes(id)) {
              _tmplSelectedOperatorIds.add(id);
              break;
            }
          }
        }
      });
      break;
    }
  }
  renderTmplOperatorReceivers();
  updateTmplReceiverCount(getTmplSelectedReceivers());
}

function getTmplSelectedReceivers() {
  if (document.getElementById('tmpl-send-all-checkbox').checked) {
    return ['@all'];
  }
  return Array.from(_tmplSelectedOperatorIds);
}

function updateTmplReceiverCount(ids) {
  const count = ids[0] === '@all' ? '全部' : ids.length;
  document.getElementById('tmpl-selected-receiver-count').textContent = count;
}

async function sendMessage() {
  try {
    const templateId = document.getElementById('send-template-select').value || null;
    const content = document.getElementById('send-content').value.trim();
    const variables = document.getElementById('send-variables').value.trim();
    const channels = Array.from(document.querySelectorAll('#tab-messages input[type="checkbox"]:checked')).map(c => c.value);

    if (!content && !templateId) { toast('请选择模板或输入消息内容', 'error'); return; }

    const wechatAppChecked = channels.includes('wechat_app');
    const receivers = {};
    if (wechatAppChecked) {
      const selectedIds = getSelectedReceivers();
      if (selectedIds[0] === '@all') {
        receivers.send_all = true;
      } else {
        const allMembers = collectAllMembers(_deptTreeCache || []);
        const allMemberIds = new Set(allMembers.map(m => m.userid));
        const operatorIds = [];
        const departmentIds = [];
        for (const id of selectedIds) {
          if (allMemberIds.has(id)) {
            operatorIds.push(id);
          }
        }
        receivers.operator_ids = operatorIds;
        receivers.department_ids = Array.from(_selectedDeptIds);
        if (operatorIds.length === 0 && departmentIds.length === 0) {
          receivers.send_all = true;
        }
      }
    }

    const body = { template_id: templateId, content, channels };
    if (Object.keys(receivers).length > 0) {
      body.receivers = receivers;
    }
    if (variables) {
      try { body.variables = JSON.parse(variables); } catch (e) { toast('变量格式错误，需要JSON格式', 'error'); return; }
    }

    const res = await api('/messages/send', { method: 'POST', body });
    toast(res.message, res.code === 0 ? 'success' : 'error');
    if (res.code === 0) {
      loadTemplates();
    }
  } catch (e) {
    toast('发送异常: ' + e.message, 'error');
  }
}

// === 流程编排 ===
let _procDebounceTimer = null;
function debounceProcessSearch() {
  clearTimeout(_procDebounceTimer);
  _procDebounceTimer = setTimeout(loadProcesses, 300);
}

async function loadProcesses() {
  try {
    loadWorkorderStats();
    const typeFilter = document.getElementById('process-type-filter')?.value || '';
    const statusFilter = document.getElementById('process-status-filter')?.value || '';
    const searchText = document.getElementById('process-search')?.value?.trim().toLowerCase() || '';
    let url = '/processes';
    const params = [`_t=${Date.now()}`];
    if (typeFilter) params.push(`type=${typeFilter}`);
    if (statusFilter) params.push(`status=${statusFilter}`);
    url += '?' + params.join('&');

    const res = await api(url);
    if (res.code !== 0) return;
    let processes = res.data || [];

    if (searchText) {
      processes = processes.filter(p =>
        (p.order_no || '').toLowerCase().includes(searchText) ||
        (p.order_no || '').toLowerCase().includes(searchText) ||
        (p.customer_name || '').toLowerCase().includes(searchText) ||
        (p.product_name || '').toLowerCase().includes(searchText)
      );
    }

    _renderProcessList(processes);
  } catch (e) {
    console.error('[Processes] 加载流程异常:', e);
  }
}

function _renderProcessList(processes) {
  let html = '';
  if (processes.length === 0) {
    html = '<div class="empty-state"><div class="icon">📋</div><p>暂无活跃流程</p></div>';
  } else {
    html = '<table><thead><tr><th>工单号</th><th>客户</th><th>产品</th><th>数量</th><th>流程类型</th><th>状态</th><th>进度</th><th>任务</th><th>创建时间</th><th>操作</th></tr></thead><tbody>';
    for (const p of processes) {
      const totalSteps = (p.steps || []).length || 7;
      const current = p.current_step || 0;
      const progress = totalSteps > 0 ? Math.round(current / totalSteps * 100) : 0;
      const orderDisplay = p.order_no || '-';
      const taskDisplay = p.task_count ? `${p.completed_task_count || 0}/${p.task_count}` : '-';
      const hasWorkorder = !!p.order_no;
      const createdDate = (p.created_at || '').slice(0, 10);
      const awaitingConfirm = p.awaiting_confirmation;
      const awaitingStepName = p.awaiting_step_status ? LABELS.s(p.awaiting_step_status) : '';
      const statusClass = awaitingConfirm ? 'awaiting-confirm' : (p.status === 'completed' ? 'completed' : (p.status === 'created' || p.status === 'published' ? 'pending' : 'in_progress'));
      const statusLabel = awaitingConfirm ? `等待确认${awaitingStepName ? '(' + awaitingStepName + ')' : ''}` : (LABELS.s(p.status) || p.status);
      html += `<tr>
        <td><strong>${escHtml(orderDisplay)}</strong></td>
        <td>${escHtml(p.customer_name || '-')}</td>
        <td>${escHtml(p.product_name || '-')}</td>
        <td>${p.quantity || 0}${p.unit ? ' ' + p.unit : ''}</td>
        <td>${LABELS.f(p.flow_type) || p.flow_type || '生产流程'}</td>
        <td><span class="status-badge ${statusClass}">${statusLabel}</span></td>
        <td>
          <div style="display:flex;align-items:center;gap:8px;min-width:100px;">
            <div style="flex:1;height:6px;background:#f0f0f0;border-radius:3px;">
              <div style="height:100%;background:${progress >= 100 ? '#52c41a' : '#667eea'};border-radius:3px;width:${progress}%;"></div>
            </div>
            <span style="font-size:12px;color:#666;">${progress}%</span>
          </div>
        </td>
        <td><span style="font-size:12px;">${taskDisplay}</span></td>
        <td style="font-size:11px;color:#888;">${createdDate}</td>
        <td>
          <div class="btn-group">
            ${hasWorkorder ? `<button class="btn btn-sm btn-primary" onclick="viewWorkorderDetail('${p.order_no}')">工单</button>` : ''}
            ${hasWorkorder ? `<button class="btn btn-sm btn-danger" onclick="deleteWorkorder('${p.order_no}')">删工单</button>` : ''}
            <button class="btn btn-sm btn-outline" onclick="viewProcess('${p.id}')">详情</button>
            ${awaitingConfirm ? `<button class="btn btn-sm btn-success" onclick="confirmProcess('${p.id}')">确认</button>` : ''}
            <button class="btn btn-sm btn-danger" onclick="deleteProcess('${p.id}')">删除</button>
          </div>
        </td>
      </tr>`;
    }
    html += '</tbody></table>';
  }
  document.getElementById('process-list').innerHTML = html;
}

async function loadWorkorderStats() {
  const res = await api('/workorder/stats');
  if (res.code !== 0) return;
  const d = res.data;
  document.getElementById('wo-total').textContent = d.total_orders || 0;
  document.getElementById('wo-in-progress').textContent = d.in_progress || 0;
  document.getElementById('wo-completed').textContent = d.completed || 0;
  document.getElementById('wo-tasks').textContent = d.total_tasks || 0;
  document.getElementById('wo-done-tasks').textContent = d.completed_tasks || 0;
}

async function viewWorkorderDetail(workOrderNo) {
  const res = await api(`/workorder/${workOrderNo}`);
  if (res.code !== 0) {
    toast('获取工单详情失败', 'error');
    return;
  }
  const d = res.data;
  const p = d.process;

  let flowHtml = '<div class="progress-flow">';
  for (let i = 0; i < d.steps.length; i++) {
    const s = d.steps[i];
    const cls = s.status === 'completed' ? 'completed' : (s.status === 'active' ? 'active' : '');
    const stepName = s.name;
    flowHtml += `<div class="progress-step ${cls}">
      <div class="step-circle">${s.status === 'completed' ? '✓' : (i + 1)}</div>
      <div class="step-label">${escHtml(stepName)}
        <span class="step-send-btn" onclick="event.stopPropagation();sendStepNotify('${p && p.id || workOrderNo}','${escHtml(stepName)}')" title="手动发送工序通知">📤</span>
      </div>
      <div class="step-role">${s.role}</div>
    </div>`;
    if (i < d.steps.length - 1) {
      flowHtml += `<div class="progress-connector ${s.status === 'completed' ? 'completed' : ''}"></div>`;
    }
  }
  flowHtml += '</div>';

  function renderTaskTable(tasks, typeLabel, workOrderNo) {
    if (!tasks || tasks.length === 0) {
      return `<div style="padding:16px;text-align:center;color:#999;">暂无${typeLabel}任务</div>`;
    }
    let html = '<table style="font-size:12px;"><thead><tr><th>工序</th><th>数量</th><th>已完成</th><th>操作员</th><th>状态</th><th>创建时间</th><th>操作</th></tr></thead><tbody>';
    for (const t of tasks) {
      const tStatus = t.display_status || t.status || '-';
      let statusCls = 'pending';
      if (t.status === 'completed') statusCls = 'completed';
      else if (t.status === 'distributed' || t.status === 'acknowledged') statusCls = 'in_progress';
      const createdTime = (t.created_at || '').slice(0, 16) || '-';
      const canAck = t.status === 'pending' || t.status === 'distributed';
      html += `<tr>
        <td><strong>${t.related_process || t.title || '-'}</strong></td>
        <td>${t.planned_qty || '-'}</td>
        <td>${t.completed_qty != null ? t.completed_qty : 0}</td>
        <td>${t.status === 'distributed' ? '全员' : (t.operator_name || t.target_operator || '-')}</td>
        <td><span class="status-badge ${statusCls}" style="font-size:11px;">${tStatus}</span></td>
        <td style="font-size:11px;">${createdTime}</td>
        <td></td>
      </tr>`;
    }
    html += '</tbody></table>';
    return html;
  }

  // 流程步骤专用表格(系统自动生成,无操作员)
  function renderFlowStepTable(flowSteps, flowProduction, workOrderNo) {
    const total = (flowSteps ? flowSteps.length : 0) + (flowProduction ? flowProduction.length : 0);
    if (total === 0) {
      return `<div style="padding:16px;text-align:center;color:#999;">暂无流程步骤记录<br><span style="font-size:11px;color:#bbb;">流程步骤由工单发布时系统自动生成</span></div>`;
    }
    let html = '<div style="font-size:11px;color:#888;padding:4px 8px;background:#f0f5ff;border-radius:4px;margin-bottom:8px;">📊 流程步骤为系统自动生成,无操作员分配,仅作进度跟踪</div>';
    html += '<table style="font-size:12px;"><thead><tr><th>步骤</th><th>类型</th><th>状态</th><th>创建时间</th></tr></thead><tbody>';
    // 排产发布放最前
    const all = [];
    for (const f of (flowProduction || [])) {
      all.push({ name: f.related_process || '排产发布', type: '排产发布', status: f.status, created_at: f.created_at });
    }
    for (const s of (flowSteps || [])) {
      all.push({ name: s.related_process || '-', type: '流程步骤', status: s.status, created_at: s.created_at });
    }
    for (const item of all) {
      let statusCls = 'pending';
      const st = item.status || 'pending';
      if (st === 'completed') statusCls = 'completed';
      else if (st === 'in_progress' || st === 'active') statusCls = 'in_progress';
      const createdTime = (item.created_at || '').slice(0, 16) || '-';
      html += `<tr>
        <td><strong>${item.name}</strong></td>
        <td><span style="padding:1px 6px;background:#e6f0ff;color:#1890ff;border-radius:3px;font-size:11px;">${item.type}</span></td>
        <td><span class="status-badge ${statusCls}" style="font-size:11px;">${LABELS.s(st) || st}</span></td>
        <td style="font-size:11px;">${createdTime}</td>
      </tr>`;
    }
    html += '</tbody></table>';
    return html;
  }

  const materialHtml = renderTaskTable(d.material_tasks, '物料', workOrderNo);
  const processHtml = renderTaskTable(d.process_tasks, '工序报工', workOrderNo);
  const flowHtml2 = renderFlowStepTable(d.flow_steps || [], d.flow_production || [], workOrderNo);
  const qualityHtml = renderTaskTable(d.quality_tasks, '质检', workOrderNo);
  const repairHtml = renderTaskTable(d.repair_tasks, '维修', workOrderNo);
  const outsourceHtml = renderTaskTable(d.outsource_tasks, '外协', workOrderNo);

  const basicInfoHtml = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px;">
      <div><strong>工单号：</strong>${p.order_no || p.order_no || '-'}</div>
      <div><strong>客户：</strong>${p.customer_name || '-'}</div>
      <div><strong>客户群：</strong>${p.customer_group || '-'}</div>
      <div><strong>产品：</strong>${p.product_name || '-'}</div>
      <div><strong>数量：</strong>${p.quantity || 0} ${p.unit || ''}</div>
      <div><strong>交期：</strong>${(p.delivery_date || '').slice(0, 10) || '-'}</div>
      <div><strong>优先级：</strong>${p.priority === 'urgent' ? '紧急' : (p.priority === 'high' ? '高' : '普通')}</div>
      <div><strong>状态：</strong><span class="status-badge ${p.status === 'completed' ? 'completed' : (p.status === 'created' ? 'pending' : 'in_progress')}">${LABELS.s(p.status) || p.status}</span></div>
    </div>
  `;

  const taskSummaryHtml = `
    <div class="cards" style="margin-top:12px;">
      <div class="card"><div class="label">物料任务</div><div class="value primary">${d.material_tasks ? d.material_tasks.length : 0}</div></div>
      <div class="card"><div class="label">工序报工</div><div class="value primary">${d.process_tasks ? d.process_tasks.length : 0}</div></div>
      <div class="card"><div class="label">流程进度</div><div class="value info">${(d.flow_steps ? d.flow_steps.length : 0) + (d.flow_production ? d.flow_production.length : 0)}</div></div>
      <div class="card"><div class="label">质检任务</div><div class="value primary">${d.quality_tasks ? d.quality_tasks.length : 0}</div></div>
      <div class="card"><div class="label">维修任务</div><div class="value primary">${d.repair_tasks ? d.repair_tasks.length : 0}</div></div>
      <div class="card"><div class="label">外协任务</div><div class="value primary">${d.outsource_tasks ? d.outsource_tasks.length : 0}</div></div>
      <div class="card"><div class="label">完成进度</div><div class="value success">${d.stats ? (d.stats.completed_tasks || 0) + '/' + (d.stats.total_tasks || 0) : '0/0'}</div></div>
    </div>
  `;

  const modalHtml = `
    <div class="modal" style="width:800px;max-width:95vw;max-height:90vh;">
      <div class="modal-header">
        <h3>工单详情 - ${p.order_no || p.order_no || workOrderNo}</h3>
        <div style="display:flex;gap:8px;">
          <button class="btn btn-sm btn-outline" onclick="refreshWorkorderStatus('${workOrderNo}', this)">🔄 刷新状态</button>
          <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
        </div>
      </div>
      <div class="modal-body" style="max-height:calc(90vh - 60px);overflow-y:auto;">
        <h4 style="margin-bottom:12px;font-size:14px;color:#555;">基本信息</h4>
        ${basicInfoHtml}
        <h4 style="margin:16px 0 12px;font-size:14px;color:#555;">流程进度</h4>
        ${flowHtml}
        ${taskSummaryHtml}
        <h4 style="margin:16px 0 12px;font-size:14px;color:#555;">任务列表</h4>
        <div style="border-bottom:1px solid #f0f0f0;display:flex;gap:0;margin-bottom:12px;flex-wrap:wrap;">
          <button class="wo-tab-btn active" style="padding:8px 16px;border:none;background:#667eea;color:#fff;cursor:pointer;border-radius:4px 4px 0 0;font-size:13px;" onclick="switchWoTab(this, 'material')">📦 物料任务 (${d.material_tasks ? d.material_tasks.length : 0})</button>
          <button class="wo-tab-btn" style="padding:8px 16px;border:none;background:#f0f0f0;color:#555;cursor:pointer;border-radius:4px 4px 0 0;font-size:13px;" onclick="switchWoTab(this, 'process')">⚙️ 工序报工 (${d.process_tasks ? d.process_tasks.length : 0})</button>
          <button class="wo-tab-btn" style="padding:8px 16px;border:none;background:#f0f0f0;color:#555;cursor:pointer;border-radius:4px 4px 0 0;font-size:13px;" onclick="switchWoTab(this, 'flow')">📊 流程进度 (${(d.flow_steps ? d.flow_steps.length : 0) + (d.flow_production ? d.flow_production.length : 0)})</button>
          <button class="wo-tab-btn" style="padding:8px 16px;border:none;background:#f0f0f0;color:#555;cursor:pointer;border-radius:4px 4px 0 0;font-size:13px;" onclick="switchWoTab(this, 'quality')">🔍 质检任务 (${d.quality_tasks ? d.quality_tasks.length : 0})</button>
          <button class="wo-tab-btn" style="padding:8px 16px;border:none;background:#f0f0f0;color:#555;cursor:pointer;border-radius:4px 4px 0 0;font-size:13px;" onclick="switchWoTab(this, 'repair')">🔧 维修任务 (${d.repair_tasks ? d.repair_tasks.length : 0})</button>
          <button class="wo-tab-btn" style="padding:8px 16px;border:none;background:#f0f0f0;color:#555;cursor:pointer;border-radius:4px 4px 0 0;font-size:13px;" onclick="switchWoTab(this, 'outsource')">🏭 外协任务 (${d.outsource_tasks ? d.outsource_tasks.length : 0})</button>
        </div>
        <div id="wo-tab-material">${materialHtml}</div>
        <div id="wo-tab-process" style="display:none;">${processHtml}</div>
        <div id="wo-tab-flow" style="display:none;">${flowHtml2}</div>
        <div id="wo-tab-quality" style="display:none;">${qualityHtml}</div>
        <div id="wo-tab-repair" style="display:none;">${repairHtml}</div>
        <div id="wo-tab-outsource" style="display:none;">${outsourceHtml}</div>
      </div>
    </div>
  `;

  const modal = document.createElement('div');
  modal.className = 'modal-overlay show';
  modal.style.display = 'flex';
  modal.innerHTML = modalHtml;
  document.body.appendChild(modal);
}

function switchWoTab(btn, tabName) {
  document.querySelectorAll('.wo-tab-btn').forEach(b => {
    b.style.background = '#f0f0f0';
    b.style.color = '#555';
  });
  btn.style.background = '#667eea';
  btn.style.color = '#fff';
  ['material', 'process', 'flow', 'quality', 'repair', 'outsource'].forEach(name => {
    const el = document.getElementById('wo-tab-' + name);
    if (el) el.style.display = name === tabName ? 'block' : 'none';
  });
}

async function viewProcess(id) {
  const [processRes, stepsRes] = await Promise.all([
    api(`/processes/${id}`),
    api(`/process_sub_steps/${id}`)
  ]);
  if (processRes.code !== 0) { toast('获取流程详情失败', 'error'); return; }
  const d = processRes.data;
  const p = d.process;
  const steps = d.steps || [];
  const subSteps = stepsRes.code === 0 ? (stepsRes.data || []) : [];

  function getStepQty(stepName) {
    return subSteps.filter(function(s) { return s.step_name === stepName; })
      .reduce(function(sum, s) { return sum + (parseFloat(s.quantity) || 0); }, 0);
  }

  const totalQty = parseFloat(p.quantity) || 0;

  let timelineHtml = '<div class="process-timeline" style="margin-bottom:16px;">';
  steps.forEach(function(step, i) {
    const isComplete = step.status === 'completed';
    const isActive = step.status === 'active';
    const dotBg = isComplete ? '#52c41a' : (isActive ? '#1890ff' : '#e8e8e8');
    const dotColor = isComplete || isActive ? '#fff' : '#999';
    const dotText = isComplete ? '✓' : (i + 1);
    const statusText = isComplete ? '已完成' : (isActive ? '进行中' : '待处理');
    const completedQty = getStepQty(step.name);
    const pct = totalQty > 0 ? Math.min(100, Math.round(completedQty / totalQty * 100)) : 0;

    timelineHtml += '<div class="process-item" style="margin-bottom:12px;display:flex;gap:10px;">';
    timelineHtml += '<div style="display:flex;flex-direction:column;align-items:center;min-width:28px;">';
    timelineHtml += '<div style="width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:bold;background:' + dotBg + ';color:' + dotColor + ';">' + dotText + '</div>';
    if (i < steps.length - 1) {
      timelineHtml += '<div style="width:2px;flex:1;background:' + (isComplete ? '#52c41a' : '#e8e8e8') + ';margin:4px 0;"></div>';
    }
    timelineHtml += '</div>';
    timelineHtml += '<div style="flex:1;padding-bottom:' + (i < steps.length - 1 ? '16px' : '0') + ';">';
    timelineHtml += '<div style="font-weight:600;font-size:14px;">' + (step.name || '') + '</div>';
    if (step.role) {
      timelineHtml += '<div style="font-size:12px;color:#888;">' + step.role + '</div>';
    }
    timelineHtml += '<div class="progress-bar" style="margin:4px 0;height:8px;background:#e8e8e8;border-radius:4px;overflow:hidden;">';
    timelineHtml += '<div style="width:' + pct + '%;height:100%;background:' + (isComplete ? '#52c41a' : '#1890ff') + ';border-radius:4px;transition:width 0.3s;"></div>';
    timelineHtml += '</div>';
    timelineHtml += '<div style="font-size:12px;color:#666;">完成: ' + completedQty + ' / ' + totalQty + '（' + pct + '%）</div>';
    timelineHtml += '<div style="margin-top:4px;display:flex;gap:6px;align-items:center;flex-wrap:wrap;">';
    timelineHtml += '<span style="font-size:11px;padding:1px 6px;border-radius:3px;background:' + (isComplete ? '#e6f7e6' : (isActive ? '#e6f0ff' : '#f5f5f5')) + ';color:' + (isComplete ? '#52c41a' : (isActive ? '#1890ff' : '#999')) + ';">' + statusText + '</span>';
    if (!isComplete) {
      const escStepName = (step.name || '').replace(/"/g, '&quot;');
      timelineHtml += '<button class="btn btn-sm btn-report-step" style="padding:2px 10px;font-size:12px;" data-process-id="' + id + '" data-order-no="' + (p.order_no || p.order_no || '') + '" data-step-name="' + escStepName + '">📝 报工</button>';
    }
    timelineHtml += '</div></div></div>';
  });
  timelineHtml += '</div>';

  let recordsHtml = '';
  if (subSteps.length > 0) {
    recordsHtml = '<div style="padding:12px;background:#f6f8fa;border-radius:6px;border:1px solid #e8e8e8;">';
    recordsHtml += '<div style="font-weight:600;margin-bottom:8px;font-size:13px;">📋 报工记录</div>';
    recordsHtml += '<table style="font-size:12px;width:100%;"><thead><tr><th>工序</th><th>批次号</th><th>数量</th><th>合格数量</th><th>操作人</th><th>设备</th><th>工时</th><th>时间</th><th>备注</th></tr></thead><tbody>';
    for (var si = 0; si < subSteps.length; si++) {
      var s = subSteps[si];
      var qqty = (s.qualified_qty !== undefined && s.qualified_qty !== null) ? s.qualified_qty : s.quantity;
      recordsHtml += '<tr><td>' + (s.step_name || '-') + '</td><td style="font-size:11px;">' + (s.batch_no || '-') + '</td><td><strong>' + s.quantity + '</strong></td><td><strong>' + qqty + '</strong></td><td>' + (s.operator || '-') + '</td><td style="font-size:11px;">' + (s.equipment_name || '-') + '</td><td style="font-size:11px;">' + ((s.overtime_hours !== undefined && s.overtime_hours !== null && s.overtime_hours > 0) ? s.overtime_hours + '小时' : '-') + '</td><td style="font-size:11px;">' + ((s.created_at || '').slice(0, 16).replace('T', ' ')) + '</td><td style="font-size:11px;color:#888;">' + (s.remark || '-') + '</td></tr>';
    }
    recordsHtml += '</tbody></table></div>';
  }

  const detailHtml = '<div class="process-detail-info" style="margin-bottom:16px;">' +
   '<p><strong>工单：</strong>' + (p.order_no || '-') + ' &nbsp; <strong>产品：</strong>' + (p.product_name || '-') + ' &nbsp; <strong>数量：</strong>' + (p.quantity || 0) + '</p>' +
    '<p><strong>状态：</strong><span class="process-status-value">' + (LABELS.s(p.status) || p.status) + '</span></p></div>' +
    timelineHtml +
    '<div id="sub-step-area-' + id + '">' + recordsHtml + '</div>' +
    '<div style="margin-top:16px;display:flex;gap:8px;">' +
    '<button class="btn btn-success btn-sm" onclick="advanceProcess(\'' + id + '\')">推进下一步</button>' +
    '<button class="btn btn-warning btn-sm" onclick="rejectProcess(\'' + id + '\')">退回上一步</button>' +
    '<button class="btn btn-outline btn-sm" onclick="showTemplateBindingsModal(\'' + id + '\')">消息模板</button></div>';

  const modal = document.createElement('div');
  modal.className = 'modal-overlay show';
  modal.style.display = 'flex';
  modal.setAttribute('data-process-id', id);
  modal.innerHTML = '<div class="modal" style="width:750px;max-width:95vw;">' +
    '<div class="modal-header"><h3>工序报工 - ' + (p.order_no || id) + '</h3>' +
    '<button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove(); _stopProcessDetailRefresh(\'' + id + '\')">&times;</button></div>' +
    '<div class="modal-body">' + detailHtml + '</div></div>';
  document.body.appendChild(modal);

  modal.querySelectorAll('.btn-report-step').forEach(function(btn) {
    btn.addEventListener('click', function() {
      showStepReportForm(btn.getAttribute('data-process-id'), btn.getAttribute('data-order-no'), btn.getAttribute('data-step-name'));
    });
  });

  _startProcessDetailRefresh(id);
}

async function showStepReportForm(processId, orderNo, stepName) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay show';
  overlay.style.display = 'flex';
  overlay.innerHTML = '<div class="modal" style="width:420px;">' +
    '<div class="modal-header"><h3>' + stepName + ' - 报工</h3>' +
    '<button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove()">&times;</button></div>' +
    '<div class="modal-body">' +
    '<div style="margin-bottom:12px;"><label style="font-size:13px;font-weight:500;display:block;margin-bottom:4px;">报工数量 <span style="color:red;">*</span></label>' +
    '<input type="number" id="report-qty" min="0" step="0.1" placeholder="请输入完成数量" style="width:100%;padding:8px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;box-sizing:border-box;"></div>' +
    '<div style="margin-bottom:12px;"><label style="font-size:13px;font-weight:500;display:block;margin-bottom:4px;">合格数量 <span style="color:red;">*</span></label>' +
    '<input type="number" id="report-qualified-qty" min="0" step="0.1" placeholder="请输入合格数量" style="width:100%;padding:8px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;box-sizing:border-box;"></div>' +
    '<div style="margin-bottom:12px;"><label style="font-size:13px;font-weight:500;display:block;margin-bottom:4px;">操作人</label>' +
    '<input type="text" id="report-operator" placeholder="操作人姓名" style="width:100%;padding:8px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;box-sizing:border-box;"></div>' +
    '<div style="margin-bottom:12px;"><label style="font-size:13px;font-weight:500;display:block;margin-bottom:4px;">设备名称</label>' +
    '<input type="text" id="report-equipment" placeholder="设备名称（可选）" style="width:100%;padding:8px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;box-sizing:border-box;"></div>' +
    '<div style="margin-bottom:12px;"><label style="font-size:13px;font-weight:500;display:block;margin-bottom:4px;">工时(小时)</label>' +
    '<input type="number" id="report-overtime-hours" min="0" step="0.1" placeholder="工时（可选）" style="width:100%;padding:8px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;box-sizing:border-box;"></div>' +
    '<div style="margin-bottom:12px;"><label style="font-size:13px;font-weight:500;display:block;margin-bottom:4px;">备注</label>' +
    '<textarea id="report-remark" placeholder="备注（可选）" rows="2" style="width:100%;padding:8px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;box-sizing:border-box;resize:vertical;"></textarea></div>' +
    '</div>' +
    '<div class="modal-footer" style="display:flex;gap:8px;justify-content:flex-end;padding:12px 16px;border-top:1px solid #e8e8e8;">' +
    '<button class="btn btn-outline" onclick="this.closest(\'.modal-overlay\').remove()">取消</button>' +
    '<button class="btn" id="btn-submit-report" data-process-id="' + processId + '" data-order-no="' + orderNo + '" data-step-name="' + stepName.replace(/"/g, '&quot;') + '">提交报工</button></div></div>';
  document.body.appendChild(overlay);

  setTimeout(function() { var el = document.getElementById('report-qty'); if (el) el.focus(); }, 100);

  document.getElementById('btn-submit-report').addEventListener('click', function() {
    submitStepReport(processId, orderNo, stepName);
  });
}

async function submitStepReport(processId, orderNo, stepName) {
  var qty = document.getElementById('report-qty');
  var qualifiedQty = document.getElementById('report-qualified-qty');
  var operator = document.getElementById('report-operator');
  var equipment = document.getElementById('report-equipment');
  var remark = document.getElementById('report-remark');
  var overtimeHours = document.getElementById('report-overtime-hours');
  if (!qty) { toast('表单异常，请重试', 'error'); return; }
  var qtyVal = qty.value;
  var qualifiedQtyVal = qualifiedQty ? qualifiedQty.value : '';
  var operatorVal = operator ? operator.value : '';
  var equipmentVal = equipment ? equipment.value : '';
  var remarkVal = remark ? remark.value : '';
  var overtimeHoursVal = overtimeHours ? parseFloat(overtimeHours.value) || 0 : 0;

  if (!qtyVal || parseFloat(qtyVal) <= 0) {
    toast('请输入有效的报工数量', 'error');
    qty.focus();
    return;
  }

  if (!qualifiedQtyVal || parseFloat(qualifiedQtyVal) <= 0) {
    toast('请输入有效的合格数量', 'error');
    if (qualifiedQty) qualifiedQty.focus();
    return;
  }

  if (parseFloat(qualifiedQtyVal) > parseFloat(qtyVal)) {
    toast('合格数量不能大于报工数量', 'error');
    if (qualifiedQty) qualifiedQty.focus();
    return;
  }

  var wechatUserid = '';
  if (operatorVal) {
    try {
      var opsRes = await fetch('/dispatch-center/operators');
      var opsData = await opsRes.json();
      if (opsData && opsData.code === 0 && opsData.data) {
        var found = opsData.data.find(function(o) { return o.name === operatorVal; });
        if (found) {
          wechatUserid = found.wechat_userid || '';
        }
      }
    } catch (e) { console.warn('获取操作员微信ID失败:', e); }
  }

  var res = await api('/process_sub_step', {
    method: 'POST',
    body: {
      order_no: processId,
      order_no: orderNo,
      step_name: stepName,
      quantity: parseFloat(qtyVal),
      qualified_qty: parseFloat(qualifiedQtyVal),
      operator: operatorVal || '未知',
      wechat_userid: wechatUserid,
      equipment_name: equipmentVal,
      remark: remarkVal,
      overtime_hours: overtimeHoursVal
    }
  });

  if (res.code !== 0) {
    toast(res.message || '报工失败', 'error');
    return;
  }

  toast('报工成功！', 'success');

  var formModal = document.querySelector('.modal-overlay:last-child');
  if (formModal) formModal.remove();

  var overlay = document.querySelector('.modal-overlay[data-process-id="' + processId + '"]');
  if (overlay) {
    var body = overlay.querySelector('.modal-body');
    if (body) body.innerHTML = '<div style="text-align:center;padding:20px;color:#999;">刷新中...</div>';
    _stopProcessDetailRefresh(processId);
    await viewProcess(processId);
  }
}

async function sendStepNotify(processId, stepName) {
  if (!confirm(`确定发送工序"${stepName}"的通知？`)) return;
  const res = await api(`/processes/${processId}/step-notify`, {
    method: 'POST',
    body: { step_name: stepName }
  });
  toast(res.message, res.code === 0 ? 'success' : 'error');
}

async function loadProcessSubSteps(processId) {
  const [summaryRes, stepsRes] = await Promise.all([
    api(`/process_sub_step_summary/${processId}`),
    api(`/process_sub_steps/${processId}`)
  ]);
  const area = document.getElementById(`sub-step-area-${processId}`);
  if (!area) return;

  let html = '';
  if (summaryRes.code === 0) {
    const s = summaryRes.data;
    if (s.order_qty > 0) {
      const completedPct = s.order_qty > 0 ? Math.min(100, Math.round(s.completed_qty / s.order_qty * 100)) : 0;
      const shippedPct = s.order_qty > 0 ? Math.min(100, Math.round(s.shipped_qty / s.order_qty * 100)) : 0;
      html += '<div style="padding:12px;background:#f6f8fa;border-radius:6px;border:1px solid #e8e8e8;">';
      html += '<div style="font-weight:600;margin-bottom:8px;font-size:13px;">📦 出入库进度</div>';
      html += renderProgressBar('完工入库', s.completed_qty, s.order_qty, completedPct, '#52c41a');
      html += renderProgressBar('发货', s.shipped_qty, s.order_qty, shippedPct, '#1890ff');
      html += '</div>';
    }
  }

  if (stepsRes.code === 0 && stepsRes.data && stepsRes.data.length > 0) {
    html += '<div style="margin-top:8px;padding:12px;background:#f6f8fa;border-radius:6px;border:1px solid #e8e8e8;">';
    html += '<div style="font-weight:600;margin-bottom:8px;font-size:13px;">📋 分批记录</div>';
    html += '<table style="font-size:12px;width:100%;"><thead><tr><th>类型</th><th>批次号</th><th>数量</th><th>操作人</th><th>时间</th><th>设备名称</th><th>备注</th></tr></thead><tbody>';
    for (const step of stepsRes.data) {
      const typeLabel = step.step_name === '完工入库' ? '📥 入库' : (step.step_name === '发货' ? '📤 发货' : step.step_name);
      html += `<tr>
        <td>${typeLabel}</td>
        <td style="font-size:11px;">${step.batch_no || '-'}</td>
        <td><strong>${step.quantity}</strong></td>
        <td>${step.operator || '-'}</td>
        <td style="font-size:11px;">${(step.created_at || '').slice(0, 16).replace('T', ' ')}</td>
        <td style="font-size:11px;">${step.equipment_name || '-'}</td>
        <td style="font-size:11px;color:#888;">${step.remark || '-'}</td>
      </tr>`;
    }
    html += '</tbody></table></div>';
  }

  area.innerHTML = html || '<div style="color:#999;font-size:12px;text-align:center;padding:8px;">暂无出入库记录</div>';
}

function renderProgressBar(label, current, total, pct, color) {
  return `<div style="margin-bottom:6px;">
    <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:2px;">
      <span>${label}</span>
      <span>${current} / ${total} (${pct}%)</span>
    </div>
    <div style="height:8px;background:#e8e8e8;border-radius:4px;overflow:hidden;">
      <div style="height:100%;width:${pct}%;background:${color};border-radius:4px;transition:width 0.3s;"></div>
    </div>
  </div>`;
}

function showPrompt(title, defaultValue = '', placeholder = '', description = '') {
  return new Promise(_resolve => {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay show';
    modal.style.display = 'flex';
    const descHtml = description ? `<div style="margin-bottom:10px;padding:10px;background:#f6f8fa;border:1px solid #e8e8e8;border-radius:4px;font-size:13px;max-height:200px;overflow-y:auto;white-space:pre-wrap;line-height:1.6;">${description}</div>` : '';
    modal.innerHTML = `<div class="modal" style="width:440px;">
      <div class="modal-header"><h3>${title}</h3></div>
      <div class="modal-body">${descHtml}<input type="text" id="prompt-input" value="${defaultValue}" placeholder="${placeholder}" style="width:100%;padding:8px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;box-sizing:border-box;"></div>
      <div class="modal-footer" style="display:flex;gap:8px;justify-content:flex-end;padding:12px 16px;border-top:1px solid #e8e8e8;">
        <button class="btn btn-outline" id="prompt-cancel-btn">取消</button>
        <button class="btn" id="prompt-ok-btn">确定</button>
      </div>
    </div>`;
    document.body.appendChild(modal);
    setTimeout(() => document.getElementById('prompt-input')?.focus(), 100);
    modal.querySelector('#prompt-cancel-btn').addEventListener('click', () => { modal.remove(); _resolve(null); });
    modal.querySelector('#prompt-ok-btn').addEventListener('click', () => { const v = document.getElementById('prompt-input').value; modal.remove(); _resolve(v); });
    modal.querySelector('#prompt-input')?.addEventListener('keydown', e => { if (e.key === 'Enter') { const v = e.target.value; modal.remove(); _resolve(v); } });
    modal.addEventListener('click', e => { if (e.target === modal) { modal.remove(); _resolve(null); } });
  });
}

async function advanceProcess(id) {
  try {
    const name = await showPrompt('操作人名称', '管理员', '请输入操作人名称');
    if (!name) return;
    const res = await api(`/processes/${id}/advance`, { method: 'POST', body: { operator_name: name } });
    toast(res.message, res.code === 0 ? 'success' : 'error');
    document.querySelectorAll('.modal-overlay').forEach(el => el.remove());
    loadProcesses();
  } catch(e) {
    toast('操作异常: ' + e.message, 'error');
  }
}

async function confirmProcess(id) {
  const result = await new Promise(resolve => {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay show';
    modal.style.display = 'flex';
    modal.innerHTML = `<div class="modal" style="width:440px;">
      <div class="modal-header"><h3>确认推进</h3></div>
      <div class="modal-body">
        <div class="form-group">
          <label>确认人名称 <span style="color:#ff4d4f;">*</span></label>
          <input id="cf-operator" type="text" value="管理员" placeholder="请输入确认人名称" style="width:100%;padding:8px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;box-sizing:border-box;">
        </div>
        <div class="form-group" style="margin-top:12px;">
          <label>工期（天）</label>
          <input id="cf-lead-time" type="number" min="1" value="" placeholder="可选，排产确认时填写" style="width:100%;padding:8px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;box-sizing:border-box;">
        </div>
      </div>
      <div class="modal-footer" style="display:flex;gap:8px;justify-content:flex-end;padding:12px 16px;border-top:1px solid #e8e8e8;">
        <button class="btn btn-outline" id="cf-cancel-btn">取消</button>
        <button class="btn" id="cf-ok-btn">确定</button>
      </div>
    </div>`;
    document.body.appendChild(modal);
    setTimeout(() => document.getElementById('cf-operator')?.focus(), 100);
    modal.querySelector('#cf-cancel-btn').addEventListener('click', () => { modal.remove(); resolve(null); });
    modal.querySelector('#cf-ok-btn').addEventListener('click', () => {
      const name = document.getElementById('cf-operator').value.trim();
      const leadTime = document.getElementById('cf-lead-time').value.trim();
      if (!name) { toast('请输入确认人名称', 'warning'); return; }
      modal.remove();
      resolve({ operator_name: name, lead_time: leadTime || null });
    });
    modal.querySelector('#cf-operator')?.addEventListener('keydown', e => {
      if (e.key === 'Enter') document.getElementById('cf-ok-btn')?.click();
    });
    modal.addEventListener('click', e => { if (e.target === modal) { modal.remove(); resolve(null); } });
  });
  if (!result) return;
  const body = { operator_name: result.operator_name };
  if (result.lead_time) body.lead_time = parseInt(result.lead_time);
  const res = await api(`/processes/${id}/confirm`, { method: 'POST', body });
  toast(res.message, res.code === 0 ? 'success' : 'error');
  document.querySelectorAll('.modal-overlay').forEach(el => el.remove());
  loadProcesses();
}

async function rejectProcess(id) {
  try {
    const reason = await showPrompt('退回原因', '需要修改', '请输入退回原因');
    if (!reason) return;
    const name = await showPrompt('操作人名称', '管理员', '请输入操作人名称');
    if (!name) return;
    const res = await api(`/processes/${id}/reject`, { method: 'POST', body: { reason, operator_name: name } });
    toast(res.message, res.code === 0 ? 'success' : 'error');
    document.querySelectorAll('.modal-overlay').forEach(el => el.remove());
    loadProcesses();
  } catch(e) {
    toast('操作异常: ' + e.message, 'error');
  }
}

async function deleteProcess(id) {
  try {
    if (!confirm('确认删除该流程？此操作不可撤销。')) return;
    const res = await api(`/processes/${id}`, { method: 'DELETE' });
    toast(res.message, res.code === 0 ? 'success' : 'error');
    if (res.code === 0) loadProcesses();
  } catch(e) {
    toast('操作异常: ' + e.message, 'error');
  }
}

async function showTemplateBindingsModal(processId) {
  const res = await api(`/processes/${processId}/template-bindings`);
  if (res.code !== 0) { toast('获取模板绑定信息失败', 'error'); return; }
  const { bindings, event_labels, available_templates, defaults } = res.data;

  const modal = document.createElement('div');
  modal.className = 'modal-overlay show';
  modal.style.display = 'flex';

  let rowsHtml = '';
  const eventKeys = Object.keys(event_labels);
  for (const key of eventKeys) {
    const currentId = bindings[key] || defaults[key] || '';
    const label = event_labels[key];
    let optionsHtml = '';
    for (const tpl of available_templates) {
      const selected = tpl.id === currentId ? 'selected' : '';
      optionsHtml += `<option value="${tpl.id}" ${selected}>${tpl.name}</option>`;
    }
    rowsHtml += `<div class="form-group">
      <label>${label}</label>
      <select data-event-key="${key}" class="tpl-binding-select" style="width:100%;padding:8px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;box-sizing:border-box;">
        <option value="">-- 不发送通知 --</option>
        ${optionsHtml}
      </select>
    </div>`;
  }

  modal.innerHTML = `<div class="modal" style="width:520px;">
    <div class="modal-header">
      <h3>消息模板绑定</h3>
      <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
    </div>
    <div class="modal-body">
      <p style="margin-bottom:12px;color:#666;font-size:13px;">为每个流程事件选择对应的消息模板，更换后流程通知将使用新模板发送。</p>
      ${rowsHtml}
      <div id="tpl-bind-result" style="margin-top:8px;"></div>
    </div>
    <div class="modal-footer" style="display:flex;gap:8px;justify-content:space-between;">
      <button class="btn btn-outline btn-sm" onclick="resetTemplateBindings('${processId}')">重置为默认</button>
      <div style="display:flex;gap:8px;">
        <button class="btn btn-outline" onclick="this.closest('.modal-overlay').remove()">取消</button>
        <button class="btn btn-primary" onclick="saveTemplateBindings('${processId}')">保存</button>
      </div>
    </div>
  </div>`;
  document.body.appendChild(modal);
}

async function saveTemplateBindings(processId) {
  try {
    const selects = document.querySelectorAll('.tpl-binding-select');
    const bindings = {};
    selects.forEach(sel => {
      const key = sel.dataset.eventKey;
      const val = sel.value;
      if (val) bindings[key] = val;
    });
    const res = await api(`/processes/${processId}/template-bindings`, {
      method: 'PUT',
      body: { bindings },
    });
    const resultEl = document.getElementById('tpl-bind-result');
    if (res.code === 0) {
      resultEl.innerHTML = '<span style="color:#52c41a;">✓ 消息模板绑定已更新</span>';
      setTimeout(() => document.querySelectorAll('.modal-overlay').forEach(el => el.remove()), 800);
      loadProcesses();
    } else {
      resultEl.innerHTML = `<span style="color:#ff4d4f;">✗ ${escHtml(res.message)}</span>`;
    }
  } catch(e) {
    toast('操作异常: ' + e.message, 'error');
  }
}

async function resetTemplateBindings(processId) {
  try {
    if (!confirm('确认重置为默认模板？')) return;
    const res = await api(`/processes/${processId}/template-bindings/reset`, { method: 'POST' });
    const resultEl = document.getElementById('tpl-bind-result');
    if (res.code === 0) {
      resultEl.innerHTML = '<span style="color:#52c41a;">✓ 已重置为默认模板</span>';
      document.querySelectorAll('.modal-overlay').forEach(el => el.remove());
      showTemplateBindingsModal(processId);
      loadProcesses();
    } else {
      resultEl.innerHTML = `<span style="color:#ff4d4f;">✗ ${escHtml(res.message)}</span>`;
    }
  } catch(e) {
    toast('操作异常: ' + e.message, 'error');
  }
}

async function deleteWorkorder(workOrderNo) {
  try {
    if (!confirm(`确认删除工单 ${workOrderNo} 下的所有子项（物料、工序、质检、维修等）？此操作不可撤销。`)) return;
    const res = await api(`/workorder/${workOrderNo}`, { method: 'DELETE' });
    toast(res.message, res.code === 0 ? 'success' : 'error');
    if (res.code === 0) loadProcesses();
  } catch(e) {
    toast('操作异常: ' + e.message, 'error');
  }
}

function showCreateProcessModal() {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay show';
  modal.innerHTML = `
    <div class="modal" style="width: 480px;">
      <div class="modal-header">
        <h3>新建流程</h3>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label>流程类型 *</label>
          <select id="create-flow-type">
            <option value="production">生产流程</option>
            <option value="material_purchase">物料采购流程</option>
            <option value="quality">质检流程</option>
          </select>
        </div>
        <div class="form-group">
          <label>工单号 *</label>
          <input id="create-order-no" placeholder="请输入工单号(WO-xxx)">
        </div>
        <div class="form-group">
          <label>原始订单号</label>
          <input id="create-work-order-no" placeholder="请输入原始订单号(ORD-xxx)，可选">
        </div>
        <div class="form-group">
          <label>产品名称 *</label>
          <input id="create-product-name" placeholder="请输入产品名称">
        </div>
        <div class="form-group">
          <label>数量</label>
          <input id="create-quantity" type="number" value="1" min="1">
        </div>
        <div class="form-group">
          <label>备注</label>
          <textarea id="create-remark" rows="2" placeholder="可选备注信息"></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-outline" onclick="this.closest('.modal-overlay').remove()">取消</button>
        <button class="btn btn-primary" onclick="createProcess()">创建流程</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
}

async function createProcess() {
  try {
    const flowType = document.getElementById('create-flow-type').value;
    const orderNo = document.getElementById('create-order-no').value.trim();
    const workOrderNo = document.getElementById('create-work-order-no').value.trim();
    const productName = document.getElementById('create-product-name').value.trim();
    const quantity = parseInt(document.getElementById('create-quantity').value) || 1;
    const remark = document.getElementById('create-remark').value.trim();

    if (!orderNo) {
      toast('工单号不能为空', 'error');
      return;
    }
    if (!productName) {
      toast('产品名称不能为空', 'error');
      return;
    }

    const body = { flow_type: flowType, order_no: orderNo, product_name: productName, quantity, remark };
    if (workOrderNo) body.order_no = workOrderNo;
    const res = await api('/processes', { 
      method: 'POST', 
      body
    });
    toast(res.message, res.code === 0 ? 'success' : 'error');
    if (res.code === 0) {
      document.querySelectorAll('.modal-overlay').forEach(el => el.remove());
      loadProcesses();
    }
  } catch(e) {
    toast('操作异常: ' + e.message, 'error');
  }
}

function refreshProcesses() { loadProcesses(); }

async function syncWorkorders() {
  if (!confirm('确认从容器中心同步工单，自动为缺失流程的工单创建流程编排？')) return;
  const btn = document.querySelector('.btn-success');
  const originalText = btn.innerHTML;
  btn.innerHTML = '⏳ 同步中...';
  btn.disabled = true;
  try {
    const res = await fetch((CONN.activeBase || '') + API_PATH + '/processes/backfill', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    if (json.code !== 0) {
      toast(json.message || '同步失败', 'error');
      return;
    }
    toast(json.message || '同步成功', 'success');
    await loadProcesses();
  } catch (e) {
    toast(e.message || '同步失败', 'error');
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

async function repairProcessProducts() {
  if (!confirm('确认从容器中心同步产品名称？将修复流程列表中缺失的产品类型和数量。')) return;
  const btn = document.querySelector('.btn-warning');
  const originalText = btn.innerHTML;
  btn.innerHTML = '⏳ 修复中...';
  btn.disabled = true;
  try {
    const res = await fetch((CONN.activeBase || '') + API_PATH + '/processes/repair-products', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    if (json.code !== 0) {
      toast(json.message || '修复失败', 'error');
      return;
    }
    const detail = json.data?.details || [];
    if (detail.length > 0) {
      toast(`修复成功：已修复 ${detail.length} 条记录`, 'success');
    } else {
      toast('所有记录产品名称已完整，无需修复', 'success');
    }
    await loadProcesses();
  } catch (e) {
    toast(e.message || '修复请求失败', 'error');
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

// === 规则配置 ===
let _rulesData = {};

async function loadRules() {
  const res = await api('/rules');
  if (res.code !== 0) return;
  const rules = res.data;
  let html = '';
  for (const r of rules) {
    html += `<div class="rule-item">
      <div class="rule-label">${r.label}<div class="rule-desc">${r.env_key}</div></div>
      <div class="rule-control">
        ${r.type === 'boolean'
          ? `<input type="checkbox" ${r.value ? 'checked' : ''} onchange="updateRule('${r.key}', this.checked)">`
          : `<input type="number" value="${r.value}" onchange="updateRule('${r.key}', Number(this.value))" min="0">`
        }
      </div>
    </div>`;
  }
  document.getElementById('rules-list').innerHTML = html;
  _rulesData = {};
  for (const r of rules) { _rulesData[r.key] = r.value; }
}

function updateRule(key, value) {
  if (!_rulesData) _rulesData = {};
  _rulesData[key] = value;
}

async function saveRules() {
  try {
    if (!_rulesData) return;
    const res = await api('/rules', { method: 'POST', body: { rules: _rulesData } });
    toast(res.message, res.code === 0 ? 'success' : 'error');
    if (res.code === 0) loadRules();
  } catch(e) {
    toast('操作异常: ' + e.message, 'error');
  }
}

// === 流程匹配规则 ===
let _flowMatchingRules = [];

const FLOW_TYPE_OPTIONS = {
  production: '生产流程',
  material_purchase: '物料采购',
  quality: '质检流程',
};

async function loadFlowMatchingRules() {
  const res = await api('/flow-matching-rules');
  if (res.code !== 0) return;
  _flowMatchingRules = res.data || [];

  let html = '';
  if (_flowMatchingRules.length === 0) {
    html = '<div style="color:#999;padding:12px;">暂无规则，点击上方"+ 新增规则"添加</div>';
  } else {
    html = '<table><thead><tr><th>启用</th><th>规则名称</th><th>匹配字段</th><th>匹配值</th><th>映射流程</th><th>优先级</th><th>操作</th></tr></thead><tbody>';
    for (let i = 0; i < _flowMatchingRules.length; i++) {
      const r = _flowMatchingRules[i];
      const flowLabel = FLOW_TYPE_OPTIONS[r.flow_type] || r.flow_type;
      html += `<tr>
        <td><input type="checkbox" ${r.enabled !== false ? 'checked' : ''} onchange="updateFmr(${i}, 'enabled', this.checked)"></td>
        <td><input class="fmr-input" value="${escHtml(r.name || '')}" onchange="updateFmr(${i}, 'name', this.value)"></td>
        <td><input class="fmr-input" value="${escHtml(r.field || '')}" onchange="updateFmr(${i}, 'field', this.value)"></td>
        <td><input class="fmr-input" value="${escHtml(r.value || '')}" onchange="updateFmr(${i}, 'value', this.value)"></td>
        <td><select class="fmr-select" onchange="updateFmr(${i}, 'flow_type', this.value)">
          ${Object.entries(FLOW_TYPE_OPTIONS).map(([k, v]) => `<option value="${k}" ${r.flow_type === k ? 'selected' : ''}>${v}</option>`).join('')}
        </select></td>
        <td><input class="fmr-input fmr-input-narrow" type="number" value="${r.priority || 10}" onchange="updateFmr(${i}, 'priority', Number(this.value))"></td>
        <td><button class="btn btn-sm btn-danger" onclick="deleteFmr(${i})">删除</button></td>
      </tr>`;
    }
    html += '</tbody></table>';
  }
  document.getElementById('flow-matching-rules-list').innerHTML = html;
}

function updateFmr(index, key, value) {
  if (!_flowMatchingRules) _flowMatchingRules = [];
  if (!_flowMatchingRules[index]) return;
  _flowMatchingRules[index][key] = value;
}

function deleteFmr(index) {
  if (!_flowMatchingRules) return;
  if (!confirm('确定删除该规则？')) return;
  _flowMatchingRules.splice(index, 1);
  renderFmrTable();
}

function addFlowMatchingRule() {
  if (!_flowMatchingRules) _flowMatchingRules = [];
  const usedIds = new Set(_flowMatchingRules.map(r => r.id));
  let idx = 1;
  while (usedIds.has(`fmr_custom_${idx}`)) idx++;
  _flowMatchingRules.push({
    id: `fmr_custom_${idx}`,
    name: '',
    field: 'product_type',
    value: '',
    flow_type: 'production',
    priority: 10,
    enabled: true,
  });
  renderFmrTable();
}

function renderFmrTable() {
  const rules = _flowMatchingRules || [];
  if (rules.length === 0) {
    document.getElementById('flow-matching-rules-list').innerHTML = '<div style="color:#999;padding:12px;">暂无规则，点击上方"+ 新增规则"添加</div>';
    return;
  }
  let html = '<table><thead><tr><th>启用</th><th>规则名称</th><th>匹配字段</th><th>匹配值</th><th>映射流程</th><th>优先级</th><th>操作</th></tr></thead><tbody>';
  for (let i = 0; i < rules.length; i++) {
    const r = rules[i];
    html += `<tr>
      <td><input type="checkbox" ${r.enabled !== false ? 'checked' : ''} onchange="updateFmr(${i}, 'enabled', this.checked)"></td>
      <td><input class="fmr-input" value="${escHtml(r.name || '')}" onchange="updateFmr(${i}, 'name', this.value)"></td>
      <td><input class="fmr-input" value="${escHtml(r.field || '')}" onchange="updateFmr(${i}, 'field', this.value)"></td>
      <td><input class="fmr-input" value="${escHtml(r.value || '')}" onchange="updateFmr(${i}, 'value', this.value)"></td>
      <td><select class="fmr-select" onchange="updateFmr(${i}, 'flow_type', this.value)">
        ${Object.entries(FLOW_TYPE_OPTIONS).map(([k, v]) => `<option value="${k}" ${r.flow_type === k ? 'selected' : ''}>${v}</option>`).join('')}
      </select></td>
      <td><input class="fmr-input fmr-input-narrow" type="number" value="${r.priority || 10}" onchange="updateFmr(${i}, 'priority', Number(this.value))"></td>
      <td><button class="btn btn-sm btn-danger" onclick="deleteFmr(${i})">删除</button></td>
    </tr>`;
  }
  html += '</tbody></table>';
  document.getElementById('flow-matching-rules-list').innerHTML = html;
}

async function saveFlowMatchingRules() {
  try {
    if (!_flowMatchingRules) return;
    const res = await api('/flow-matching-rules', { method: 'POST', body: { rules: _flowMatchingRules } });
    toast(res.message, res.code === 0 ? 'success' : 'error');
    if (res.code === 0) loadFlowMatchingRules();
  } catch(e) {
    toast('操作异常: ' + e.message, 'error');
  }
}

function refreshFlowMatchingRules() {
  loadFlowMatchingRules();
}

// === 监控告警 ===
async function loadAlerts() {
  const res = await api('/alerts?limit=50');
  if (res.code !== 0) return;
  const d = res.data;

  let html = '<table><thead><tr><th>级别</th><th>标题</th><th>消息</th><th>时间</th><th>操作</th></tr></thead><tbody>';
  const alerts = d.alerts || [];
  if (alerts.length === 0 && (d.overdue_tasks || []).length === 0) {
    html += '<tr><td colspan="5" style="text-align:center;color:#999;">暂无告警</td></tr>';
  }
  for (const a of alerts) {
    if (a.dismissed) continue;
    const levelMap = { info: '信息', warning: '警告', critical: '严重' };
    const levelCls = a.level === 'critical' ? 'danger' : (a.level === 'warning' ? 'warning' : 'primary');
    html += `<tr>
      <td><span class="status-badge ${a.level === 'critical' ? 'overdue' : 'pending'}">${levelMap[a.level] || a.level}</span></td>
      <td>${escHtml(a.title)}</td>
      <td>${escHtml(a.message)}</td>
      <td style="font-size:12px;">${(a.created_at || '').slice(0, 16)}</td>
      <td><button class="btn btn-sm btn-outline" onclick="dismissAlert('${a.id}')">忽略</button></td>
    </tr>`;
  }
  for (const t of (d.overdue_tasks || [])) {
    html += `<tr>
      <td><span class="status-badge overdue">严重</span></td>
      <td>任务超时</td>
      <td>${escHtml(t.title || '未知')} 已超时 ${t.elapsed_minutes} 分钟 (操作员: ${escHtml(t.operator || '未分配')})</td>
      <td style="font-size:12px;">-</td>
      <td><span style="color:#999;">系统告警</span></td>
    </tr>`;
  }
  html += '</tbody></table>';
  document.getElementById('alert-list').innerHTML = html;
}

async function dismissAlert(alertId) {
  const res = await api(`/alerts/${alertId}/dismiss`, { method: 'POST' });
  toast(res.message, res.code === 0 ? 'success' : 'error');
  if (res.code === 0) loadAlerts();
}

function refreshAlerts() { loadAlerts(); }

async function loadDispatchLog() {
  const res = await api('/dispatch-log?limit=30');
  if (res.code !== 0) return;
  const logs = res.data;
  let html = '<table><thead><tr><th>类型</th><th>内容</th><th>时间</th></tr></thead><tbody>';
  if (logs.length === 0) {
    html += '<tr><td colspan="3" style="text-align:center;color:#999;">暂无调度日志</td></tr>';
  } else {
    for (const log of logs) {
      let detail = '';
      if (log.type === 'task_assign') detail = `任务:${log.task_id} → 操作员:${log.operator_id}`;
      else if (log.type === 'task_reassign') detail = `任务:${log.task_id} ${log.from_operator||''}→${log.to_operator||''}`;
      else if (log.type === 'batch_assign') detail = `批量:${log.success_count||0}/${log.total||0}`;
      else detail = JSON.stringify(log).slice(0, 60);
      html += `<tr>
        <td>${LABELS.t(log.type) || log.type}</td>
        <td style="font-size:12px;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${detail}</td>
        <td style="font-size:12px;">${(log.timestamp || '').slice(0, 16)}</td>
      </tr>`;
    }
  }
  html += '</tbody></table>';
  document.getElementById('dispatch-log').innerHTML = html;
}

// === 定时任务管理 ===
async function loadSchedulerStatus() {
  const res = await api('/scheduler-manager/status');
  if (res.code !== 0) return;
  const list = res.data || [];
  let html = '';
  for (const s of list) {
    const statusIcon = s.available
      ? (s.running ? '<span style="color:#52c41a;">●</span>' : '<span style="color:#faad14;">●</span>')
      : '<span style="color:#d9d9d9;">○</span>';
    const statusText = s.available ? (s.running ? '运行中' : '已停止') : '不可用';
    const disabled = !s.available ? 'disabled' : '';
    html += `<tr>
      <td><strong>${s.name}</strong></td>
      <td style="font-size:12px;color:#666;">${s.description}</td>
      <td title="${statusText}">${statusIcon} ${statusText}</td>
      <td>
        <input type="number" id="interval-${s.name}" value="${s.interval_seconds}" min="10"
               style="width:60px;padding:2px 4px;font-size:12px;text-align:center;" ${disabled} />
      </td>
      <td>
        <label class="switch" style="margin:0;">
          <input type="checkbox" id="toggle-${s.name}" ${s.enabled ? 'checked' : ''}
                 onchange="toggleScheduler('${s.name}', this.checked)" ${disabled} />
          <span class="switch-slider"></span>
        </label>
      </td>
      <td>
        <button class="btn btn-sm btn-outline" onclick="setSchedulerInterval('${s.name}')" ${disabled}>应用</button>
      </td>
    </tr>`;
  }
  if (list.length === 0) {
    html = '<tr><td colspan="6" style="text-align:center;color:#999;">暂无定时任务</td></tr>';
  }
  document.getElementById('scheduler-status-tbody').innerHTML = html;
}

async function toggleScheduler(name, enabled) {
  const res = await api('/scheduler-manager/toggle', {
    method: 'PUT', body: JSON.stringify({ name, enabled })
  });
  if (res.code !== 0) { toast(res.message || '操作失败', 'error'); return; }
  toast(enabled ? '已启动' : '已停止', 'success');
  loadSchedulerStatus();
}

async function setSchedulerInterval(name) {
  const input = document.getElementById('interval-' + name);
  const seconds = parseInt(input.value, 10);
  if (!seconds || seconds < 10) { toast('间隔不能少于10秒', 'error'); input.value = 10; return; }
  const res = await api('/scheduler-manager/interval', {
    method: 'PUT', body: JSON.stringify({ name, interval_seconds: seconds })
  });
  if (res.code !== 0) { toast(res.message || '操作失败', 'error'); return; }
  toast('间隔已更新', 'success');
  loadSchedulerStatus();
}

// === 报修管理 ===
async function loadRepairCategories() {
  const ret = await api('/repair-categories');
  if (ret.code !== 0) return;
  const cats = ret.data || [];
  let html = '<table class="table"><thead><tr><th>种类ID</th><th>名称</th><th>负责人</th><th>描述</th><th>操作</th></tr></thead><tbody>';
  if (cats.length === 0) {
    html += '<tr><td colspan="5" style="text-align:center;color:#999;">暂无种类配置</td></tr>';
  } else {
    cats.forEach(c => {
      html += `<tr>
        <td>${c.id}</td>
        <td>${c.icon} ${c.name}</td>
        <td>${c.assigned_operator_id}</td>
        <td>${c.description || '-'}</td>
        <td>
          <button class="btn btn-outline btn-sm" onclick="deleteRepairCategory('${c.id}')">删除</button>
        </td>
      </tr>`;
    });
  }
  html += '</tbody></table>';
  document.getElementById('repair-category-list').innerHTML = html;
}

async function showRepairCategoryModal() {
  const name = await showPrompt('种类名称', '', '如：设备故障');
  if (!name) return;
  const operatorId = await showPrompt('负责人ID', '', '如：MG001');
  if (!operatorId) return;
  const description = await showPrompt('描述（可选）', '', '描述信息') || '';
  const ret = await api('/repair-categories', {
    method: 'POST',
    body: {name, assigned_operator_id: operatorId, description}
  });
  toast(ret.message || (ret.code === 0 ? '添加成功' : '添加失败'), ret.code === 0 ? 'success' : 'error');
  refreshRepairs();
}

async function deleteRepairCategory(catId) {
  if (!confirm('确认删除？')) return;
  const ret = await api(`/repair-categories/${catId}`, {method: 'DELETE'});
  toast(ret.message || (ret.code === 0 ? '删除成功' : '删除失败'), ret.code === 0 ? 'success' : 'error');
  refreshRepairs();
}

// ========== 云端配置 ==========
async function loadCloudConfig() {
  try {
    const res = await api('/cloud/config');
    if (res.code !== 0) { toast('获取云端配置失败', 'error'); return; }
    const cfg = res.data;
    const cloudHostEl = document.getElementById('cloud-host');
    const cloudApiKeyEl = document.getElementById('cloud-api-key');
    const cloudEnabledEl = document.getElementById('cloud-enabled');
    const cloudGroupNotifyEl = document.getElementById('cloud-group-notify');
    if (!cloudHostEl || !cloudApiKeyEl || !cloudEnabledEl || !cloudGroupNotifyEl) {
      console.warn('[loadCloudConfig] 云端配置元素未就绪，跳过');
      return;
    }
    cloudHostEl.value = cfg.cloud_host || '';
    cloudApiKeyEl.value = cfg.api_key || '';
    cloudEnabledEl.checked = cfg.enabled || false;
    cloudGroupNotifyEl.checked = cfg.enable_group_notification !== false;
    await refreshCloudStatus();
  } catch (e) {
    toast('加载云端配置异常: ' + e.message, 'error');
  }
}

async function saveCloudConfig() {
  try {
    const cloudHostEl = document.getElementById('cloud-host');
    const cloudApiKeyEl = document.getElementById('cloud-api-key');
    const cloudEnabledEl = document.getElementById('cloud-enabled');
    const cloudGroupNotifyEl = document.getElementById('cloud-group-notify');
    if (!cloudHostEl || !cloudApiKeyEl || !cloudEnabledEl || !cloudGroupNotifyEl) {
      toast('云端配置元素未就绪，无法保存', 'error');
      return;
    }
    const cloud_host = cloudHostEl.value.trim();
    const api_key = cloudApiKeyEl.value.trim();
    const enabled = cloudEnabledEl.checked;
    const enable_group_notification = cloudGroupNotifyEl.checked;

    if (enabled && !cloud_host) {
      toast('启用云端连接时，云端地址不能为空', 'error');
      return;
    }

    const res = await api('/cloud/config', {
      method: 'POST',
      body: JSON.stringify({ cloud_host, api_key, enabled, enable_group_notification })
    });

    if (res.code === 0) {
      toast('云端配置已保存', 'success');
      await loadCloudConfig();
    } else {
      toast('保存失败: ' + (res.message || '未知错误'), 'error');
    }
  } catch(e) {
    toast('操作异常: ' + e.message, 'error');
  }
}

async function testCloudConnection() {
  const statusEl = document.getElementById('cloud-status');
  const textEl = document.getElementById('cloud-status-text');
  statusEl.style.display = 'block';
  statusEl.style.background = '#e6f7ff';
  textEl.innerHTML = '🔄 正在测试连接...';

  const res = await api('/cloud/connection-test');

  if (res.code === 0) {
    statusEl.style.background = '#f6ffed';
    textEl.innerHTML = '✅ ' + escHtml(res.message) + '<br/><span style="font-size:12px;color:#888;">响应: ' + escHtml(JSON.stringify(res.data)) + '</span>';
    toast('连接成功', 'success');
  } else {
    statusEl.style.background = '#fff2f0';
    textEl.innerHTML = '❌ ' + escHtml(res.message);
    toast('连接失败', 'error');
  }

  setTimeout(() => { statusEl.style.display = 'none'; }, 5000);
}

async function refreshCloudStatus() {
  const now = new Date();
  const timeStr = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  
  let statusRes = { code: -1 }, pollRes = { code: -1 };
  try { statusRes = await api('/cloud/status'); } catch (e) { statusRes = { code: -1 }; }
  try { pollRes = await api('/cloud/poll-data'); } catch (e) { pollRes = { code: -1 }; }
  
  if (statusRes.code !== 0 && pollRes.code !== 0) {
    document.getElementById('cloud-refresh-status').textContent = '❌ 刷新失败 @ ' + timeStr;
    return;
  }

  const cloudData = statusRes.data || {};
  const pollData = pollRes.data || {};

  const cloudActive = cloudData.cloud_active || pollData.cloud_enabled || false;
  const connected = cloudActive ? '✅ 已启用' : '⚪ 未启用';
  const connectedColor = cloudActive ? '#52c41a' : '#999';

  document.getElementById('cloud-connected').innerHTML = '<span style="color:' + connectedColor + ';font-weight:500;">' + connected + '</span>';
  document.getElementById('cloud-host-display').textContent = cloudData.cloud_host || pollData.cloud_host || '未配置';
  document.getElementById('cloud-poll-code').textContent = pollData.code === 0 ? '✅ 正常(' + pollData.code + ')' : '❌ 异常(' + pollData.code + ')';
  document.getElementById('cloud-poll-count').textContent = pollData.count !== undefined ? pollData.count + ' 条' : '-';
  document.getElementById('cloud-poll-source').textContent = pollData.source || '-';
  document.getElementById('cloud-poll-time').textContent = pollData.last_poll_time || '-';
  
  const messagesSection = document.getElementById('poll-messages-section');
  const messagesList = document.getElementById('poll-messages-list');
  
  if (pollData.messages && pollData.messages.length > 0) {
    messagesSection.style.display = 'block';
    let html = '<table style="width:100%; font-size:13px;">';
    html += '<tr style="background:#f5f5f5;"><th>ID</th><th>用户</th><th>内容</th><th>类型</th><th>时间</th></tr>';
    pollData.messages.forEach(function(msg) {
      html += '<tr style="border-bottom:1px solid #eee;">';
      html += '<td>' + (msg.id || '-') + '</td>';
      html += '<td>' + (msg.user_id || '-') + '</td>';
      html += '<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;">' + (msg.content || '-') + '</td>';
      html += '<td>' + (msg.type || '-') + '</td>';
      html += '<td>' + (msg.timestamp ? msg.timestamp.substring(11, 19) : '-') + '</td>';
      html += '</tr>';
    });
    html += '</table>';
    messagesList.innerHTML = html;
  } else {
    messagesSection.style.display = 'none';
    messagesList.innerHTML = '<div style="color:#999;text-align:center;padding:20px;">暂无消息</div>';
  }
  
  document.getElementById('cloud-refresh-status').textContent = '🟢 已刷新 @ ' + timeStr;
}

function refreshRepairs() {
  loadRepairCategories();
  loadRepairRecords();
}

async function loadRepairRecords() {
  const ret = await api('/repair-records');
  if (ret.code !== 0) return;
  const records = ret.data || [];
  let html = '<table class="table"><thead><tr><th>时间</th><th>种类</th><th>报修人</th><th>事项</th><th>状态</th><th>操作</th></tr></thead><tbody>';
  if (records.length === 0) {
    html += '<tr><td colspan="6" style="text-align:center;color:#999;">暂无报修记录</td></tr>';
  } else {
    records.forEach(r => {
      html += `<tr>
        <td>${r.created_at || '-'}</td>
        <td>${r.category_name || '-'}</td>
        <td>${r.reporter_id || '-'}</td>
        <td>${(r.description || '-').substring(0, 30)}</td>
        <td><span class="badge badge-${LABELS.repairBadgeClass(r.status)}">${LABELS.r(r.status) || r.status}</span></td>
        <td>
          ${r.status !== 'completed' ? `<button class="btn btn-outline btn-sm" onclick="completeRepairRecord('${r.id}')">完成</button>` : ''}
        </td>
      </tr>`;
    });
  }
  html += '</tbody></table>';
  document.getElementById('repair-list').innerHTML = html;
}

async function completeRepairRecord(recordId) {
  const ret = await api(`/repair-records/${recordId}/complete`, {method: 'POST'});
  toast(ret.message || (ret.code === 0 ? '已标记完成' : '操作失败'), ret.code === 0 ? 'success' : 'error');
  refreshRepairs();
}

// === 外协管理 ===
async function loadOutsourceRecords() {
  const status = document.getElementById('outsource-filter-status')?.value || '';
  const path = status ? `/outsource-records?status=${status}` : '/outsource-records';
  const ret = await api(path);
  if (ret.code !== 0) return;
  const records = ret.data || [];
  let html = '<table class="table"><thead><tr><th>时间</th><th>工单</th><th>工序</th><th>数量</th><th>负责人</th><th>承诺日期</th><th>状态</th><th>操作</th></tr></thead><tbody>';
  if (records.length === 0) {
    html += '<tr><td colspan="8" style="text-align:center;color:#999;">暂无外协任务</td></tr>';
  } else {
    records.forEach(r => {
      const content = r.content || {};
      const badgeClass = LABELS.outsourceBadgeClass(r.status);
      html += `<tr>
        <td>${(r.created_at || '-').substring(0, 16)}</td>
        <td>${r.order_no || '-'}</td>
        <td>${content.process_name || '-'}</td>
        <td>${content.planned_qty || 0}</td>
        <td>${r.target_operator || '-'}</td>
        <td>${r.promised_date ? r.promised_date.substring(0, 10) : '-'}</td>
        <td><span class="badge badge-${badgeClass}">${LABELS.outsourceStatusMap[r.status] || r.status}</span></td>
        <td>
          ${r.status === 'pending' ? `<button class="btn btn-outline btn-sm" onclick="showOutsourceFeedbackModal('${r.id}')">反馈</button> ` : ''}
          ${r.status === 'processing' ? `<button class="btn btn-outline btn-sm" onclick="completeOutsource('${r.id}')">完成</button> ` : ''}
          ${r.status === 'completed' ? `<button class="btn btn-outline btn-sm" onclick="receiveOutsource('${r.id}')">收货</button> ` : ''}
          <button class="btn btn-outline btn-sm" onclick="showOutsourceAssignModal('${r.id}', '${r.target_operator || ''}')">分配</button>
        </td>
      </tr>`;
    });
  }
  html += '</tbody></table>';
  document.getElementById('outsource-list').innerHTML = html;
}

async function showOutsourceCreateModal() {
  const orderNo = await showPrompt('工单号', '', '请输入工单号');
  if (!orderNo) return;
  const processName = await showPrompt('工序名称', '', '请输入工序名称');
  if (!processName) return;
  const processSeq = parseInt(await showPrompt('工序序号', '1', '数字') || '1');
  const plannedQty = parseInt(await showPrompt('计划数量', '0', '请输入数量') || '0') || 0;
  const remark = await showPrompt('备注（可选）', '', '备注信息') || '';
  const ret = await api('/outsource-records', {
    method: 'POST',
    body: {order_no: orderNo, process_name: processName, process_seq: processSeq, planned_qty: plannedQty, outsource_remark: remark}
  });
  toast(ret.message || (ret.code === 0 ? '创建成功' : '创建失败'), ret.code === 0 ? 'success' : 'error');
  loadOutsourceRecords();
}

async function showOutsourceFeedbackModal(recordId) {
  const days = await showPrompt('承诺完成天数', '', '请输入天数');
  if (!days) return;
  const ret = await api(`/outsource-records/${recordId}/feedback`, {
    method: 'POST',
    body: {promised_days: parseInt(days)}
  });
  toast(ret.message || (ret.code === 0 ? '反馈成功' : '反馈失败'), ret.code === 0 ? 'success' : 'error');
  loadOutsourceRecords();
}

async function showOutsourceAssignModal(recordId, currentOp) {
  const operatorId = await showPrompt('分配给（操作员ID）', currentOp || '', '操作员ID');
  if (!operatorId) return;
  const ret = await api(`/outsource-records/${recordId}/assign`, {
    method: 'POST',
    body: {operator_id: operatorId}
  });
  toast(ret.message || (ret.code === 0 ? '已分配' : '操作失败'), ret.code === 0 ? 'success' : 'error');
  loadOutsourceRecords();
}

async function completeOutsource(recordId) {
  const ret = await api(`/outsource-records/${recordId}/complete`, {method: 'POST'});
  toast(ret.message || (ret.code === 0 ? '已标记完成' : '操作失败'), ret.code === 0 ? 'success' : 'error');
  loadOutsourceRecords();
}

async function receiveOutsource(recordId) {
  const ret = await api(`/outsource-records/${recordId}/receive`, {method: 'POST'});
  toast(ret.message || (ret.code === 0 ? '已确认收货' : '操作失败'), ret.code === 0 ? 'success' : 'error');
  loadOutsourceRecords();
}

async function loadOutsourceConfig() {
  const ret = await api('/outsource-config');
  if (ret.code !== 0) return;
  const cfg = ret.data || {};
  let html = '<table class="table"><tbody>';
  html += `<tr><td>默认负责人</td><td>${cfg.default_operator_id || '-'}</td></tr>`;
  html += `<tr><td>提醒天数</td><td>${(cfg.remind_days || []).join(', ')} 天前</td></tr>`;
  html += `<tr><td>逾期提醒时间</td><td>${(cfg.overdue_remind_times || []).join(', ')}</td></tr>`;
  html += `<tr><td>启用状态</td><td>${cfg.enabled ? '启用' : '禁用'}</td></tr>`;
  html += '</tbody></table>';
  html += '<button class="btn btn-outline btn-sm" style="margin-top:10px" onclick="showOutsourceConfigEdit()">编辑配置</button>';
  document.getElementById('outsource-config').innerHTML = html;
}

async function showOutsourceConfigEdit() {
  const defaultOp = await showPrompt('默认负责人ID', '', '负责人ID');
  if (defaultOp === null) return;
  const remindDays = await showPrompt('提醒天数', '3,2,1', '逗号分隔，如3,2,1');
  if (remindDays === null) return;
  const overdueTimes = await showPrompt('逾期提醒时间', '08:00,13:30', '逗号分隔，如08:00,13:30');
  if (overdueTimes === null) return;
  const ret = await api('/outsource-config', {
    method: 'POST',
    body: {
      default_operator_id: defaultOp,
      remind_days: remindDays.split(',').map(s => parseInt(s.trim())).filter(n => n > 0),
      overdue_remind_times: overdueTimes.split(',').map(s => s.trim()).filter(s => s)
    }
  });
  toast(ret.message || (ret.code === 0 ? '配置已更新' : '更新失败'), ret.code === 0 ? 'success' : 'error');
  loadOutsourceConfig();
}

// ─── 反馈管理 ─────────────────────────────────────
function loadFeedback() {
  const status = document.getElementById('fb-status-filter').value;
  const category = document.getElementById('fb-category-filter').value;
  const source = document.getElementById('fb-source-filter').value;
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  if (category) params.set('category', category);
  if (source) params.set('source', source);
  const qs = params.toString();
  api('/feedback' + (qs ? '?' + qs : '')).then(ret => {
    if (ret.code !== 0) return;
    const items = ret.data || [];
    const html = renderFeedbackTable(items);
    document.getElementById('feedback-list').innerHTML = html;
    // 加载统计
    api('/feedback/stats').then(sr => {
      if (sr.code !== 0) return;
      const s = sr.data || {};
      document.getElementById('fb-stats').textContent =
        `共 ${s.total} 条 | 待处理 ${s.open} | 处理中 ${s.in_progress} | 已解决 ${s.resolved} | 自动 ${s.auto}`;
    });
  });
}

function renderFeedbackTable(items) {
  if (!items.length) return '<div class="empty-state">暂无反馈记录</div>';
  let html = '<table class="table"><thead><tr>' +
    '<th style="width:40px;">#</th>' +
    '<th>标题</th>' +
    '<th style="width:80px;">类型</th>' +
    '<th style="width:70px;">优先级</th>' +
    '<th style="width:80px;">状态</th>' +
    '<th style="width:80px;">来源</th>' +
    '<th style="width:80px;">报告人</th>' +
    '<th style="width:100px;">处理人</th>' +
    '<th style="width:150px;">创建时间</th>' +
    '<th style="width:120px;">操作</th>' +
    '</tr></thead><tbody>';
  items.forEach((item, i) => {
    const statusLabel = ({open:'待处理',in_progress:'处理中',resolved:'已解决',closed:'已关闭'})[item.status] || item.status;
    const statusClass = ({open:'badge-danger',in_progress:'badge-warning',resolved:'badge-success',closed:'badge-secondary'})[item.status] || '';
    const priorityLabel = ({low:'🟢 低',medium:'🟡 中',high:'🔴 高'})[item.priority] || item.priority;
    const categoryLabel = ({template:'📋 模板',system:'⚙️ 系统',process:'🔧 流程',data:'📊 数据',other:'📂 其他'})[item.category] || item.category;
    const sourceLabel = item.source === 'auto' ? '🤖 自动' : '👤 人工';
    html += `<tr>
      <td>${i + 1}</td>
      <td><strong>${escHtml(item.title)}</strong>${item.description ? `<br><small style="color:#888;">${escHtml(item.description.substring(0, 80))}${item.description.length > 80 ? '...' : ''}</small>` : ''}</td>
      <td>${categoryLabel}</td>
      <td>${priorityLabel}</td>
      <td><span class="badge ${statusClass}">${statusLabel}</span></td>
      <td>${sourceLabel}</td>
      <td>${item.source === 'auto' ? '🤖 系统检测' : escHtml(item.reporter_name)}</td>
      <td>${item.resolver || '-'}</td>
      <td><small>${formatTime(item.created_at)}</small></td>
      <td>
        <button class="btn btn-sm btn-outline" onclick="editFeedback('${item.id}')">处理</button>
        <button class="btn btn-sm btn-outline" style="color:#ff4d4f;" onclick="deleteFeedback('${item.id}')">删除</button>
      </td>
    </tr>`;
  });
  html += '</tbody></table>';
  return html;
}

function showCreateFeedbackModal() {
  document.getElementById('fb-modal-title').textContent = '提交反馈';
  document.getElementById('fb-edit-id').value = '';
  document.getElementById('fb-title').value = '';
  document.getElementById('fb-description').value = '';
  document.getElementById('fb-category').value = 'other';
  document.getElementById('fb-priority').value = 'medium';
  document.getElementById('fb-status').value = 'open';
  document.getElementById('fb-resolution').value = '';
  document.getElementById('fb-resolver').value = '';
  toggleFeedbackResolveFields();
  document.getElementById('feedback-modal').classList.add('show');
}

function toggleFeedbackResolveFields() {
  const status = document.getElementById('fb-status').value;
  const show = status === 'in_progress' || status === 'resolved' || status === 'closed';
  document.getElementById('fb-resolution-group').style.display = show ? 'block' : 'none';
  document.getElementById('fb-resolver-group').style.display = show ? 'block' : 'none';
}

function editFeedback(id) {
  api('/feedback?status=&category=').then(ret => {
    if (ret.code !== 0) return;
    const item = (ret.data || []).find(f => f.id === id);
    if (!item) { toast('反馈记录不存在', 'error'); return; }
    document.getElementById('fb-modal-title').textContent = '处理反馈';
    document.getElementById('fb-edit-id').value = id;
    document.getElementById('fb-title').value = item.title;
    document.getElementById('fb-description').value = item.description || '';
    document.getElementById('fb-category').value = item.category || 'other';
    document.getElementById('fb-priority').value = item.priority || 'medium';
    document.getElementById('fb-status').value = item.status || 'open';
    document.getElementById('fb-resolution').value = item.resolution || '';
    document.getElementById('fb-resolver').value = item.resolver || '';
    const showResolve = item.status === 'resolved' || item.status === 'closed' || item.status === 'in_progress';
    document.getElementById('fb-resolution-group').style.display = showResolve ? 'block' : 'none';
    document.getElementById('fb-resolver-group').style.display = showResolve ? 'block' : 'none';
    document.getElementById('feedback-modal').classList.add('show');
  });
}

function saveFeedback() {
  const id = document.getElementById('fb-edit-id').value;
  const title = document.getElementById('fb-title').value.trim();
  if (!title) { toast('请输入反馈标题', 'error'); return; }
  const body = {
    title: title,
    description: document.getElementById('fb-description').value.trim(),
    category: document.getElementById('fb-category').value,
    priority: document.getElementById('fb-priority').value,
    status: document.getElementById('fb-status').value,
    resolution: document.getElementById('fb-resolution').value.trim(),
    resolver: document.getElementById('fb-resolver').value.trim(),
  };
  const method = id ? 'PUT' : 'POST';
  const url = id ? `/feedback/${id}` : '/feedback';
  api(url, { method, body }).then(ret => {
    if (ret.code !== 0) { toast(ret.message || '操作失败', 'error'); return; }
    toast(ret.message || '操作成功', 'success');
    closeModal('feedback-modal');
    loadFeedback();
  });
}

function deleteFeedback(id) {
  if (!confirm('确定删除此反馈记录？')) return;
  api(`/feedback/${id}`, { method: 'DELETE' }).then(ret => {
    if (ret.code !== 0) { toast(ret.message || '删除失败', 'error'); return; }
    toast('反馈已删除', 'success');
    loadFeedback();
  });
}

function showCreateWorkorderModal() {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay show';
  modal.style.display = 'flex';
  modal.innerHTML = `
    <div class="modal" style="width:520px;">
      <div class="modal-header">
        <h3>新建工单</h3>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label>流程类型 *</label>
          <select id="wo-create-flow-type">
            <option value="production">生产流程</option>
            <option value="material_purchase">物料采购流程</option>
            <option value="quality">质检流程</option>
          </select>
        </div>
        <div class="form-group">
          <label>工单号 *</label>
          <input id="wo-create-order-no" placeholder="例如：WO20260512001">
        </div>
        <div class="form-group">
          <label>原始工单号（可选）</label>
          <input id="wo-create-original-order-no" placeholder="WO-xxx，留空则与工单号相同">
        </div>
        <div class="form-group">
          <label>客户名称</label>
          <input id="wo-create-customer" placeholder="客户名称">
        </div>
        <div class="form-group">
          <label>产品名称 *</label>
          <input id="wo-create-product" placeholder="请输入产品名称">
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
          <div class="form-group">
            <label>数量</label>
            <input id="wo-create-qty" type="number" value="1" min="1">
          </div>
          <div class="form-group">
            <label>单位</label>
            <select id="wo-create-unit">
              <option value="米">米</option>
              <option value="个">个</option>
              <option value="件">件</option>
              <option value="套">套</option>
              <option value="kg">kg</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label>交期</label>
          <input id="wo-create-delivery" type="date">
        </div>
        <div class="form-group">
          <label>优先级</label>
          <select id="wo-create-priority">
            <option value="normal">普通</option>
            <option value="high">高</option>
            <option value="urgent">紧急</option>
          </select>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-outline" onclick="this.closest('.modal-overlay').remove()">取消</button>
        <button class="btn btn-primary" onclick="createWorkorder()">创建工单</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
}

async function createWorkorder() {
  const flowType = document.getElementById('wo-create-flow-type').value;
  const orderNo = document.getElementById('wo-create-order-no').value.trim();
  const origOrderNo = document.getElementById('wo-create-original-order-no').value.trim();
  const customer = document.getElementById('wo-create-customer').value.trim();
  const product = document.getElementById('wo-create-product').value.trim();
  const qty = parseInt(document.getElementById('wo-create-qty').value) || 1;
  const unit = document.getElementById('wo-create-unit').value;
  const delivery = document.getElementById('wo-create-delivery').value;
  const priority = document.getElementById('wo-create-priority').value;

  if (!orderNo) { toast('请输入工单号', 'error'); return; }
  if (!product) { toast('请输入产品名称', 'error'); return; }

  const res = await api('/workorder/register', {
    method: 'POST',
    body: {
      order_no: orderNo,
      order_no: origOrderNo || orderNo,
      flow_type: flowType,
      customer_name: customer,
      product_name: product,
      quantity: qty,
      unit: unit,
      delivery_date: delivery,
      priority: priority,
    }
  });

  toast(res.message, res.code === 0 ? 'success' : 'error');
  if (res.code === 0) {
    document.querySelectorAll('.modal-overlay').forEach(el => el.remove());
    loadProcesses();
  }
}

// ─── 工具函数 ─────────────────────────────────────
function escHtml(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

function escapeHtml(str) {
  if (!str) return '';
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

function formatTime(iso) {
  if (!iso) return '-';
  try { return iso.replace('T', ' ').substring(0, 16); } catch(e) { return iso; }
}

// ============= 同步队列管理 JS =============
var SQ_API = '/api/sync-queue';
var sqRetryingId = null;

function loadSyncQueue(page){
  if(!page) page = 1;
  var statusEl = document.getElementById('sq-status');
  var status = statusEl ? statusEl.value : 'failed,retry';
  var listBox = document.getElementById('sq-list');
  listBox.innerHTML = '<div style="padding:30px;text-align:center;color:#999;">加载中...</div>';
  fetch(SQ_API+'/list?status='+encodeURIComponent(status)+'&page='+page+'&page_size=50')
    .then(function(r){return r.json();})
    .then(function(ret){
      if(ret.code !== 0){
        listBox.innerHTML = '<div style="padding:30px;text-align:center;color:#e74c3c;">'+(ret.message||'加载失败')+'</div>';
        return;
      }
      var data = ret.data || {};
      var rows = data.list || [];
      document.getElementById('sq-total').innerText = data.total || 0;
      if(!rows.length){
        listBox.innerHTML = '<div style="padding:30px;text-align:center;color:#999;">暂无数据</div>';
        document.getElementById('sq-pagination').innerHTML = '';
        return;
      }
      var html = '<table style="width:100%;border-collapse:collapse;font-size:13px;">';
      html += '<thead><tr style="background:#f8f9fa;">';
      html += '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">ID</th>';
      html += '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">订单号</th>';
      html += '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">工序</th>';
      html += '<th style="padding:10px;text-align:right;border-bottom:1px solid #eee;">数量</th>';
      html += '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">操作员</th>';
      html += '<th style="padding:10px;text-align:center;border-bottom:1px solid #eee;">状态</th>';
      html += '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">重试</th>';
      html += '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">错误</th>';
      html += '<th style="padding:10px;text-align:center;border-bottom:1px solid #eee;">时间</th>';
      html += '<th style="padding:10px;text-align:center;border-bottom:1px solid #eee;">操作</th>';
      html += '</tr></thead><tbody>';
      rows.forEach(function(r){
        var statusMap = {
          'pending': '<span style="color:#f39c12;">待处理</span>',
          'retry': '<span style="color:#e67e22;">待重试</span>',
          'failed': '<span style="color:#e74c3c;">失败</span>',
          'completed': '<span style="color:#27ae60;">已完成</span>'
        };
        var st = statusMap[r.status] || r.status;
        var canRetry = (r.status === 'failed' || r.status === 'retry');
        var errMsg = (r.last_error || '').substring(0, 60);
        html += '<tr style="border-bottom:1px solid #f0f0f0;">';
        html += '<td style="padding:10px;font-size:12px;color:#888;">'+r.id+'</td>';
        html += '<td style="padding:10px;">'+escapeHtml(r.order_no)+'</td>';
        html += '<td style="padding:10px;">'+escapeHtml(r.step_name)+'</td>';
        html += '<td style="padding:10px;text-align:right;font-weight:bold;">'+parseFloat(r.quantity).toFixed(2)+'</td>';
        html += '<td style="padding:10px;">'+escapeHtml(r.operator||'-')+'</td>';
        html += '<td style="padding:10px;text-align:center;">'+st+'</td>';
        html += '<td style="padding:10px;text-align:center;font-size:12px;">'+(r.retry_count||0)+'/'+(r.max_retries||3)+'</td>';
        html += '<td style="padding:10px;font-size:11px;color:#999;max-width:120px;overflow:hidden;text-overflow:ellipsis;">'+(errMsg||'-')+'</td>';
        html += '<td style="padding:10px;font-size:12px;color:#888;">'+formatTime(r.enqueued_at)+'</td>';
        html += '<td style="padding:10px;text-align:center;">';
        if(canRetry){
          html += '<button class="sq-btn-retry" data-id="'+r.id+'" data-order="'+escapeHtml(r.order_no)+'" data-step="'+escapeHtml(r.step_name)+'" data-qty="'+r.quantity+'" data-op="'+escapeHtml(r.operator||'')+'" style="padding:3px 10px;background:#e74c3c;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">重推</button>';
        } else {
          html += '<span style="color:#bbb;font-size:12px;">-</span>';
        }
        html += '</td></tr>';
      });
      html += '</tbody></table>';
      listBox.innerHTML = html;
      // 绑定事件
      listBox.querySelectorAll('.sq-btn-retry').forEach(function(b){
        b.onclick = function(){
          var d = b.dataset;
          openSqRetryModal(d.id, d.order, d.step, d.qty, d.op);
        };
      });
      // 分页
      var total = data.total || 0;
      var ps = data.page_size || 50;
      var totalPages = Math.ceil(total / ps);
      var pagHtml = '';
      if(totalPages > 1){
        for(var i=1;i<=totalPages;i++){
          var active = (i===page) ? 'background:#3498db;color:#fff;' : 'background:#fff;color:#333;';
          pagHtml += '<button onclick="loadSyncQueue('+i+')" style="padding:5px 10px;border:1px solid #ddd;border-radius:4px;cursor:pointer;'+active+'">'+i+'</button>';
        }
      }
      document.getElementById('sq-pagination').innerHTML = pagHtml;
    }).catch(function(e){
      listBox.innerHTML = '<div style="padding:30px;text-align:center;color:#e74c3c;">加载失败: '+e.message+'</div>';
    });
}

function openSqRetryModal(id, orderNo, stepName, qty, operator){
  sqRetryingId = id;
  document.getElementById('sq-retry-body').innerHTML =
    '<p>确定向 8008 重推以下同步记录？</p>'+
    '<table style="width:100%;font-size:13px;">'+
    '<tr><td style="padding:4px 8px;color:#888;">订单号</td><td style="padding:4px 8px;"><strong>'+escapeHtml(orderNo)+'</strong></td></tr>'+
    '<tr><td style="padding:4px 8px;color:#888;">工序</td><td style="padding:4px 8px;"><strong>'+escapeHtml(stepName)+'</strong></td></tr>'+
    '<tr><td style="padding:4px 8px;color:#888;">数量</td><td style="padding:4px 8px;"><strong>'+parseFloat(qty).toFixed(2)+'</strong></td></tr>'+
    '<tr><td style="padding:4px 8px;color:#888;">操作员</td><td style="padding:4px 8px;"><strong>'+escapeHtml(operator||'-')+'</strong></td></tr>'+
    '</table>';
  document.getElementById('sq-retry-modal').style.display = 'flex';
}

function closeSqRetryModal(){
  document.getElementById('sq-retry-modal').style.display = 'none';
  sqRetryingId = null;
}

function confirmSqRetry(){
  if(!sqRetryingId){alert('记录ID缺失');return;}
  fetch(SQ_API+'/retry', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({id: sqRetryingId})
  }).then(function(r){return r.json();}).then(function(ret){
    if(ret.code === 0){
      alert('✅ '+ret.message);
    } else {
      alert('❌ '+ret.message);
    }
    closeSqRetryModal();
    loadSyncQueue();
  }).catch(function(e){
    alert('❌ 请求失败: '+e.message);
    closeSqRetryModal();
  });
}



// ============================================================
// 从 dispatch_center.html 迁移的内联 JS
// 来源: dispatch_center.html L1377~L2114
// 迁移日期: 2026-06-21
// ============================================================

var QI_API = '/api/quality-inspection';
var qiFilterResult = '全部';

function loadQualityTab(){loadQualityRecords();}
function loadQualityRecords(){
  var url = QI_API + '/history?limit=50';
  if(qiFilterResult!=='全部') url += '&result='+encodeURIComponent(qiFilterResult);
  fetch(url).then(function(r){return r.json();}).then(function(d){
    if(d.code!==0){document.getElementById('qi-table-body').innerHTML='<tr><td colspan="8">加载失败</td></tr>';return;}
    var rows=d.data.records||[];
    document.getElementById('qi-stat-total').textContent=rows.length;
    var passed=rows.filter(function(r){return r.result==='合格'}).length;
    document.getElementById('qi-stat-passed').textContent=passed;
    document.getElementById('qi-stat-failed').textContent=rows.length-passed;
    var html='';
    rows.forEach(function(r){
      var reviewBadge=r.review_status==='approved'?'<span style="color:#27ae60;">✅已审</span>':r.review_status==='rejected'?'<span style="color:#e74c3c;">❌退回</span>':'<span style="color:#f39c12;">⏳待审</span>';
      var resultColor=r.result==='合格'?'#27ae60':r.result==='不合格'?'#e74c3c':'#f39c12';
      html+='<tr>'+
        '<td>'+r.id+'</td>'+'<td>'+r.order_no+'</td>'+'<td>'+r.inspection_type+'</td>'+
        '<td>'+r.process_name+'</td>'+'<td>'+r.inspector+'</td>'+
        '<td style="color:'+resultColor+';font-weight:bold;">'+r.result+'</td>'+
        '<td>'+reviewBadge+'</td>'+'<td>'+(r.record_date||'').substring(0,10)+'</td>'+
        '<td>'+
          (r.review_status!=='approved'?'<button onclick="reviewQi('+r.id+',\'approved\')" style="background:#27ae60;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;margin:2px;">通过</button>':'')+
          (r.review_status!=='rejected'?'<button onclick="reviewQi('+r.id+',\'rejected\')" style="background:#e74c3c;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;margin:2px;">退回</button>':'')+
          (r.rework_version?'<button onclick="showQiVersions(\''+r.order_no+'\')" style="background:#3498db;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;margin:2px;">版本</button>':'')+
        '</td></tr>';
    });
    document.getElementById('qi-table-body').innerHTML=html||'<tr><td colspan="9" style="text-align:center;color:#999;">暂无记录</td></tr>';
  });
}
function reviewQi(recordId,action){
  if(!confirm('确认'+(action==='approved'?'通过':'退回')+'此质检记录？')) return;
  fetch(QI_API+'/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record_id:recordId,action:action,reviewer:'调度员'})})
  .then(function(r){return r.json();}).then(function(d){
    if(d.code===0){alert('操作成功');loadQualityRecords();}else{alert('操作失败: '+d.message);}
  });
}
function showQiVersions(orderNo){
  fetch(QI_API+'/versions/'+orderNo).then(function(r){return r.json();}).then(function(d){
    if(d.code!==0) return;
    var msg='质检版本链: '+orderNo+'\n\n';
    (d.data.records||[]).forEach(function(r){msg+=r.rework_version+'版 - '+r.result+' - '+(r.record_date||'')+'\n';});
    alert(msg);
  });
}
function showQiDetail(recordId){
  document.getElementById('qid-id').textContent=recordId;
  document.getElementById('qid-body').innerHTML='<div class="loading">加载中...</div>';
  document.getElementById('qi-detail-modal').classList.add('show');
  fetch(QI_API+'/detail/'+recordId).then(function(r){return r.json();}).then(function(d){
    if(d.code!==0){document.getElementById('qid-body').innerHTML='加载失败';return;}
    var r=d.data.record, html='';
    html+='<table style="width:100%;font-size:13px;margin-bottom:12px;">'+
      '<tr><td style="color:#999;padding:4px;">订单号</td><td style="padding:4px;">'+r.order_no+'</td>'+
      '<td style="color:#999;padding:4px;">类型</td><td style="padding:4px;">'+r.inspection_type+'</td></tr>'+
      '<tr><td style="color:#999;padding:4px;">工序</td><td style="padding:4px;">'+r.process_name+'</td>'+
      '<td style="color:#999;padding:4px;">质检员</td><td style="padding:4px;">'+r.inspector+'</td></tr>'+
      '<tr><td style="color:#999;padding:4px;">结果</td><td style="padding:4px;font-weight:bold;color:'+(r.result==='合格'?'#27ae60':'#e74c3c')+';">'+r.result+'</td>'+
      '<td style="color:#999;padding:4px;">版本</td><td style="padding:4px;">v'+(r.rework_version||1)+'</td></tr>'+
      '<tr><td style="color:#999;padding:4px;">日期</td><td colspan="3" style="padding:4px;">'+r.record_date+'</td></tr>'+
      '</table>';
    html+='<div style="font-weight:bold;margin:10px 0 6px;">📋 检查项明细</div>';
    html+='<table style="width:100%;border-collapse:collapse;font-size:13px;">'+
      '<tr style="background:#f5f5f5;"><th style="padding:6px;text-align:left;">项目</th><th style="padding:6px;">标准值</th><th style="padding:6px;">公差</th><th style="padding:6px;">实测值</th><th style="padding:6px;">判定</th></tr>';
    (d.data.items||[]).forEach(function(it){
      var passedIcon=it.is_passed?'✅':'❌';
      html+='<tr style="border-bottom:1px solid #eee;">'+
        '<td style="padding:6px;">'+it.inspection_item+'</td>'+
        '<td style="padding:6px;text-align:center;">'+it.standard_value+'</td>'+
        '<td style="padding:6px;text-align:center;">'+(it.tolerance||'无')+'</td>'+
        '<td style="padding:6px;text-align:center;font-weight:500;">'+it.measured_value+'</td>'+
        '<td style="padding:6px;text-align:center;">'+passedIcon+'</td></tr>';
    });
    html+='</table>';
    if(r.defect_description){html+='<div style="margin-top:8px;padding:8px;background:#fff3cd;border-radius:4px;font-size:12px;">⚠ '+r.defect_description+'</div>';}
    document.getElementById('qid-body').innerHTML=html;
  });
}
function closeQiModal(){
  document.getElementById('qi-detail-modal').classList.remove('show');
}
function qiChangeFilter(v){
  qiFilterResult=v;
  document.querySelectorAll('#tab-quality-inspect .filter-btn').forEach(function(b){b.classList.remove('active');});
  event.target.classList.add('active');
  loadQualityRecords();
}

// ============= 排产列表 =============
function loadScheduleTab(){
  var container = document.getElementById('sch-list');
  container.innerHTML = '<div style="padding:30px;text-align:center;color:#999;">加载中...</div>';
  fetch('/api/schedule/list').then(function(r){return r.json();}).then(function(ret){
    var list = ret.data||ret||[];
    var filter = (document.getElementById('sch-filter')||{}).value||'';
    if(filter){list = list.filter(function(o){return (o.workOrderNo||o.order_no||'').indexOf(filter)>=0;});}
    if(!list.length){container.innerHTML='<div style="padding:30px;text-align:center;color:#999;">暂无数据</div>';return;}
    var statusMap={'created':'待排产','pending':'待排产','confirmed':'已排产','in_production':'生产中','report_complete':'报工完成','warehousing':'成品入库','shipped':'已发货','order_complete':'订单完成','completed':'已完成'};
    var html = '<table style="width:100%;border-collapse:collapse;font-size:13px;">';
    html += '<thead><tr style="background:#f8f9fa;"><th style="padding:10px;text-align:left;">订单号</th><th style="padding:10px;text-align:left;">客户</th><th style="padding:10px;text-align:left;">产品</th><th style="padding:10px;text-align:right;">数量</th><th style="padding:10px;text-align:center;">状态</th><th style="padding:10px;text-align:left;">排产时间</th></tr></thead><tbody>';
    list.forEach(function(o){
      var orderNo = o.workOrderNo||o.order_no||'';
      var customer = o.customerGroup||o.customer_group_name||o.customerName||'';
      var product = o.productType||o.product_type||o.productName||'';
      var qty = o.quantity||o.orderQty||0;
      var status = o.status||'pending';
      var statusText = statusMap[status]||status;
      var color = (status==='completed'||status==='shipped')?'#27ae60':(status==='in_production'||status==='report_complete')?'#3498db':'#f39c12';
      var ts = (o.createTime||o.created_at||'').toString().substring(0,19);
      html += '<tr style="border-bottom:1px solid #f0f0f0;">';
      html += '<td style="padding:10px;">'+orderNo+'</td><td style="padding:10px;">'+customer+'</td><td style="padding:10px;">'+product+'</td>';
      html += '<td style="padding:10px;text-align:right;">'+parseFloat(qty).toFixed(0)+'</td>';
      html += '<td style="padding:10px;text-align:center;"><span style="padding:2px 10px;border-radius:10px;font-size:11px;background:'+color+'22;color:'+color+';">'+statusText+'</span></td>';
      html += '<td style="padding:10px;font-size:12px;color:#888;">'+ts+'</td></tr>';
    });
    html += '</tbody></table>';
    container.innerHTML = html;
  }).catch(function(e){container.innerHTML='<div style="padding:30px;text-align:center;color:#e74c3c;">加载失败</div>';});
}

// ============= 物料任务 =============
function loadMaterialDc(){
  var container = document.getElementById('mat-dc-list');
  container.innerHTML = '<div style="padding:30px;text-align:center;color:#999;">加载中...</div>';
  fetch('/api/tasks?page_route=material').then(function(r){return r.json();}).then(function(ret){
    var tasks = ret.data?ret.data.tasks:ret.tasks||[];
    var filter = (document.getElementById('mat-dc-filter')||{}).value||'';
    if(filter){tasks = tasks.filter(function(t){return (t.related_order||'').indexOf(filter)>=0;});}
    if(!tasks.length){container.innerHTML='<div style="padding:30px;text-align:center;color:#999;">暂无数据</div>';return;}
    var orders = {};
    tasks.forEach(function(t){var oid=t.related_order||'未知'; if(!orders[oid]) orders[oid]=[]; orders[oid].push(t);});
    var stMap={'material_requested':'待确认','material_confirmed':'已确认','material_arrived':'已到货','material_delivered':'已出库'};
    var html = '';
    Object.keys(orders).sort().forEach(function(oid){
      html += '<div style="margin-bottom:10px;background:#f8f9fa;border-left:4px solid #f39c12;border-radius:6px;padding:10px 12px;">';
      html += '<div style="font-weight:bold;color:#2c3e50;margin-bottom:8px;">📋 '+oid+' ('+orders[oid].length+'项)</div>';
      orders[oid].forEach(function(t){
        var ct = t.content||{}; if(typeof ct==='string'){try{ct=JSON.parse(ct);}catch(e){ct={};}}
        var stText = stMap[t.status]||t.status||'';
        var pname = (t.related_process||ct.material_name||'物料').replace(/^备料-/,'');
        var spec = ct.spec?' | '+ct.spec:'';
        html += '<div style="background:#fff;border-radius:6px;padding:8px 12px;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center;">';
        html += '<div><span>📦 '+pname+spec+'</span></div>';
        html += '<div style="display:flex;gap:10px;align-items:center;">';
        html += '<span style="font-size:13px;">数量: '+(ct.quantity||'?')+' '+(ct.unit||'')+'</span>';
        html += '<span style="padding:1px 8px;border-radius:8px;font-size:11px;background:#f39c12;color:#fff;">'+stText+'</span>';
        html += '</div></div>';
      });
      html += '</div>';
    });
    container.innerHTML = html;
  }).catch(function(e){container.innerHTML='<div style="padding:30px;text-align:center;color:#e74c3c;">加载失败</div>';});
}

// ============= 报工记录管理 JS =============
var RR_API = '/api/report_record';
var rrCurrentPage = 1;
var rrEditingId = null;
var rrWithdrawingId = null;

function loadReportRecords(page){
  if(page) rrCurrentPage = page;
  var params = [];
  var orderEl = document.getElementById('rr-filter-order');
  var stepEl = document.getElementById('rr-filter-step');
  var opEl = document.getElementById('rr-filter-operator');
  var startEl = document.getElementById('rr-filter-start');
  var endEl = document.getElementById('rr-filter-end');
  var order = orderEl ? orderEl.value : '';
  var step = stepEl ? stepEl.value : '';
  var op = opEl ? opEl.value : '';
  var start = startEl ? startEl.value : '';
  var end = endEl ? endEl.value : '';
  if(order) params.push('order_no='+encodeURIComponent(order));
  if(step) params.push('step_name='+encodeURIComponent(step));
  if(op) params.push('operator='+encodeURIComponent(op));
  if(start) params.push('start_date='+encodeURIComponent(start+' 00:00:00'));
  if(end) params.push('end_date='+encodeURIComponent(end+' 23:59:59'));
  params.push('page='+rrCurrentPage);
  params.push('page_size=20');
  var url = RR_API + '/list?' + params.join('&');
  var listBox = document.getElementById('rr-list');
  listBox.innerHTML = '<div style="padding:30px;text-align:center;color:#999;">加载中...</div>';
  fetch(url).then(function(r){return r.json();}).then(function(ret){
    if(ret.code !== 0){listBox.innerHTML = '<div style="padding:30px;text-align:center;color:#e74c3c;">'+(ret.message||'')+'</div>';return;}
    var data = ret.data || {};
    var rows = data.list || [];
    document.getElementById('rr-total').innerText = data.total || 0;
    if(!rows.length){
      listBox.innerHTML = '<div style="padding:30px;text-align:center;color:#999;">暂无数据</div>';
      document.getElementById('rr-pagination').innerHTML = '';
      return;
    }
    var html = '<table style="width:100%;border-collapse:collapse;font-size:13px;">';
    html += '<thead><tr style="background:#f8f9fa;">';
    html += '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">订单号</th>';
    html += '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">工序</th>';
    html += '<th style="padding:10px;text-align:right;border-bottom:1px solid #eee;">数量</th>';
    html += '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">操作员</th>';
    html += '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">批次</th>';
    html += '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">时间</th>';
    html += '<th style="padding:10px;text-align:center;border-bottom:1px solid #eee;">操作</th>';
    html += '</tr></thead><tbody>';
    rows.forEach(function(r){
      var id = r.id;
      var orderNo = r.order_no || '';
      var stepN = r.step_name || '';
      var qty = r.quantity || 0;
      var operatorN = r.operator || '';
      var bn = r.batch_no || '-';
      var d = new Date(r.created_at);
      var ts = d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')+' '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')+':'+String(d.getSeconds()).padStart(2,'0');
      html += '<tr style="border-bottom:1px solid #f0f0f0;">';
      html += '<td style="padding:10px;">'+orderNo+'</td>';
      html += '<td style="padding:10px;">'+stepN+'</td>';
      html += '<td style="padding:10px;text-align:right;font-weight:bold;">'+parseFloat(qty).toFixed(2)+'</td>';
      html += '<td style="padding:10px;">'+operatorN+'</td>';
      html += '<td style="padding:10px;font-size:12px;color:#888;">'+bn+'</td>';
      html += '<td style="padding:10px;font-size:12px;color:#888;">'+ts+'</td>';
      html += '<td style="padding:10px;text-align:center;">';
      html += '<button class="rr-btn-edit" data-id="'+id+'" data-order="'+orderNo+'" data-step="'+stepN+'" data-op="'+operatorN+'" data-bn="'+bn+'" data-qty="'+qty+'" style="padding:3px 10px;background:#3498db;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-right:4px;font-size:12px;">修改</button>';
      html += '<button class="rr-btn-wd" data-id="'+id+'" data-order="'+orderNo+'" data-step="'+stepN+'" data-op="'+operatorN+'" data-qty="'+qty+'" style="padding:3px 10px;background:#e74c3c;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-right:4px;font-size:12px;">撤回</button>';
      html += '<button class="rr-btn-hist" data-id="'+id+'" style="padding:3px 10px;background:#95a5a6;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">历史</button>';
      html += '</td></tr>';
    });
    html += '</tbody></table>';
    listBox.innerHTML = html;
    // 绑定事件
    listBox.querySelectorAll('.rr-btn-edit').forEach(function(b){
      b.onclick = function(){
        var d = b.dataset;
        openRrEditModal(d.id, d.order, d.step, d.op, d.bn, parseFloat(d.qty));
      };
    });
    listBox.querySelectorAll('.rr-btn-wd').forEach(function(b){
      b.onclick = function(){
        var d = b.dataset;
        openRrWithdrawModal(d.id, d.order, d.step, d.op, parseFloat(d.qty));
      };
    });
    listBox.querySelectorAll('.rr-btn-hist').forEach(function(b){
      b.onclick = function(){ openRrHistoryModal(b.dataset.id); };
    });
    // 分页
    var total = data.total || 0;
    var ps = data.page_size || 20;
    var totalPages = Math.ceil(total / ps);
    var pagHtml = '';
    if(totalPages > 1){
      for(var i=1;i<=totalPages;i++){
        var active = (i===rrCurrentPage) ? 'background:#3498db;color:#fff;' : 'background:#fff;color:#333;';
        pagHtml += '<button onclick="loadReportRecords('+i+')" style="padding:5px 10px;border:1px solid #ddd;border-radius:4px;cursor:pointer;'+active+'">'+i+'</button>';
      }
    }
    document.getElementById('rr-pagination').innerHTML = pagHtml;
  }).catch(function(e){
    listBox.innerHTML = '<div style="padding:30px;text-align:center;color:#e74c3c;">加载失败: '+e.message+'</div>';
  });
}

function resetReportRecordFilter(){
  ['rr-filter-order','rr-filter-step','rr-filter-operator','rr-filter-start','rr-filter-end'].forEach(function(id){
    var el = document.getElementById(id); if(el) el.value = '';
  });
  loadReportRecords(1);
}

function openRrEditModal(id, orderNo, stepName, operator, batchNo, oldQty){
  rrEditingId = id;
  document.getElementById('rre-order').innerText = orderNo;
  document.getElementById('rre-step').innerText = stepName;
  document.getElementById('rre-operator').innerText = operator;
  document.getElementById('rre-batch').innerText = batchNo || '-';
  document.getElementById('rre-old-qty').innerText = parseFloat(oldQty).toFixed(2);
  document.getElementById('rre-new-qty').value = oldQty;
  document.getElementById('rre-reason').value = 'admin_force';
  document.getElementById('rre-remark').value = '';
  document.getElementById('rr-edit-modal').style.display = 'flex';
}

function closeRrEditModal(){
  document.getElementById('rr-edit-modal').style.display = 'none';
  rrEditingId = null;
}

function submitRrUpdate(){
  if(!rrEditingId){alert('记录ID缺失');return;}
  var newQty = document.getElementById('rre-new-qty').value;
  var reason = document.getElementById('rre-reason').value;
  var remark = document.getElementById('rre-remark').value;
  if(!newQty || isNaN(parseFloat(newQty))){alert('请输入有效数量');return;}
  var body = {
    sub_step_id: rrEditingId,
    new_quantity: parseFloat(newQty),
    admin_user: window.currentUser || '调度员',
    reason: reason,
    remark: remark,
    confirm: 0
  };
  fetch(RR_API + '/update', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  }).then(function(r){return r.json();}).then(function(ret){
    if(ret.code === 300 && ret.action === 'prompt'){
      if(confirm('⚠️ '+ret.message+'\n\n是否确认强制修改？')){
        body.confirm = 1;
        fetch(RR_API + '/update', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
          .then(function(r){return r.json();}).then(function(ret2){
            if(ret2.code === 0){alert('✅ '+ret2.message);closeRrEditModal();loadReportRecords();}
            else{alert('❌ '+ret2.message);}
          });
      }
      return;
    }
    if(ret.code === 0){alert('✅ '+ret.message);closeRrEditModal();loadReportRecords();}
    else{alert('❌ '+ret.message);}
  }).catch(function(e){alert('❌ 请求失败: '+e.message);});
}

function openRrWithdrawModal(id, orderNo, stepName, operator, qty){
  rrWithdrawingId = id;
  document.getElementById('rrw-order').innerText = orderNo;
  document.getElementById('rrw-step').innerText = stepName;
  document.getElementById('rrw-operator').innerText = operator;
  document.getElementById('rrw-qty').innerText = parseFloat(qty).toFixed(2);
  document.getElementById('rrw-reason').value = '';
  document.getElementById('rr-withdraw-modal').style.display = 'flex';
}

function closeRrWithdrawModal(){
  document.getElementById('rr-withdraw-modal').style.display = 'none';
  rrWithdrawingId = null;
}

function submitRrWithdraw(){
  if(!rrWithdrawingId){alert('记录ID缺失');return;}
  var reason = document.getElementById('rrw-reason').value.trim();
  if(!reason){alert('请填写撤回原因');return;}
  fetch(RR_API + '/withdraw', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      sub_step_id: rrWithdrawingId,
      admin_user: window.currentUser || '调度员',
      reason: 'admin_withdraw:' + reason
    })
  }).then(function(r){return r.json();}).then(function(ret){
    if(ret.code === 0){alert('✅ '+ret.message);closeRrWithdrawModal();loadReportRecords();}
    else{alert('❌ '+ret.message);}
  }).catch(function(e){alert('❌ 请求失败: '+e.message);});
}

function openRrHistoryModal(id){
  document.getElementById('rr-history-modal').style.display = 'flex';
  var body = document.getElementById('rrh-body');
  body.innerHTML = '<div style="text-align:center;color:#999;padding:30px;">加载中...</div>';
  fetch(RR_API + '/history_full?sub_step_id='+encodeURIComponent(id))
    .then(function(r){return r.json();}).then(function(ret){
      if(ret.code !== 0){body.innerHTML = '<div style="color:#e74c3c;">'+ret.message+'</div>';return;}
      var data = ret.data || {};
      var rec = data.record || {};
      var h = data.history || [];
      var html = '<div style="margin-bottom:15px;padding:12px;background:#f8f9fa;border-radius:6px;font-size:13px;">';
      html += '<div>订单: <strong>'+rec.order_no+'</strong> / 工序: <strong>'+rec.step_name+'</strong></div>';
      html += '<div>操作员: '+rec.operator+' | 当前数量: <strong>'+parseFloat(rec.quantity).toFixed(2)+'</strong></div>';
      var recD = new Date(rec.created_at);
      var recTs = recD.getFullYear()+'-'+String(recD.getMonth()+1).padStart(2,'0')+'-'+String(recD.getDate()).padStart(2,'0')+' '+String(recD.getHours()).padStart(2,'0')+':'+String(recD.getMinutes()).padStart(2,'0');
      html += '<div style="font-size:12px;color:#888;margin-top:5px;">报工时间: '+recTs+'</div>';
      html += '</div>';
      if(!h.length){
        html += '<div style="text-align:center;color:#999;padding:20px;">暂无修改记录</div>';
      } else {
        h.forEach(function(item){
          var reasonMap = {
            'self_withdraw': '🔴 操作员撤回',
            'admin_withdraw': '🟠 调度员撤回',
            'other_override': '🟡 异人覆盖',
            'self_correct': '🟢 操作员自改',
            'admin_force': '🔵 调度员修正',
            'desktop_sync': '⚪ 桌面端同步'
          };
          var reason = reasonMap[item.revert_reason] || item.revert_reason;
          html += '<div style="padding:12px;background:#fff;border-left:3px solid #3498db;margin-bottom:8px;border-radius:4px;">';
          var histD = new Date(item.reverted_at);
          var histTs = histD.getFullYear()+'-'+String(histD.getMonth()+1).padStart(2,'0')+'-'+String(histD.getDate()).padStart(2,'0')+' '+String(histD.getHours()).padStart(2,'0')+':'+String(histD.getMinutes()).padStart(2,'0');
          html += '<div style="font-size:12px;color:#888;">'+histTs+'</div>';
          html += '<div style="margin-top:5px;"><strong>'+reason+'</strong> '+parseFloat(item.old_quantity).toFixed(2)+' → '+parseFloat(item.new_quantity).toFixed(2)+'</div>';
          html += '<div style="font-size:12px;color:#666;margin-top:3px;">操作人: '+item.reverted_by+' | 原操作员: '+item.operator_before+'</div>';
          html += '</div>';
        });
      }
      body.innerHTML = html;
    });
}

function closeRrHistoryModal(){
  document.getElementById('rr-history-modal').style.display = 'none';
}

// ============= 质检回归审计 JS =============
var QR_API = '/api/quality_record';
var qrCurrentPage = 1;
var qrEditingId = null;
var qrWithdrawingId = null;

function loadQualityRegression(page){
  if(page) qrCurrentPage = page;
  var params = [];
  ['qr-filter-order','qr-filter-type','qr-filter-operator','qr-filter-start','qr-filter-end'].forEach(function(id){
    var el = document.getElementById(id);
    if(el && el.value){
      var k = id.replace('qr-filter-','');
      var v = el.value;
      if(k==='start'){params.push('start_date='+encodeURIComponent(v+' 00:00:00'));}
      else if(k==='end'){params.push('end_date='+encodeURIComponent(v+' 23:59:59'));}
      else if(k==='order'){params.push('order_no='+encodeURIComponent(v));}
      else if(k==='type'){params.push('inspection_type='+encodeURIComponent(v));}
      else if(k==='operator'){params.push('operator='+encodeURIComponent(v));}
    }
  });
  params.push('page='+qrCurrentPage,'page_size=20');
  var listBox = document.getElementById('qr-list');
  listBox.innerHTML = '<div style="padding:30px;text-align:center;color:#999;">加载中...</div>';
  fetch(QR_API+'/list?'+params.join('&')).then(function(r){return r.json();}).then(function(ret){
    if(ret.code!==0){listBox.innerHTML='<div style="padding:30px;text-align:center;color:#e74c3c;">'+(ret.message||'')+'</div>';return;}
    var data=ret.data||{}, rows=data.list||[];
    document.getElementById('qr-total').innerText=data.total||0;
    if(!rows.length){listBox.innerHTML='<div style="padding:30px;text-align:center;color:#999;">暂无数据</div>';document.getElementById('qr-pagination').innerHTML='';return;}
    var html='<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f8f9fa;">'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">订单号</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">类型</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">工序</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">质检员</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">结果</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">状态</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">时间</th>'+
      '<th style="padding:10px;text-align:center;border-bottom:1px solid #eee;">审计</th>'+
      '<th style="padding:10px;text-align:center;border-bottom:1px solid #eee;">操作</th></tr></thead><tbody>';
    rows.forEach(function(r){
      var clr=(r.result==='合格'||r.result==='pass')?'#27ae60':(r.result==='不合格'||r.result==='fail')?'#e74c3c':'#f39c12';
      var d=new Date(r.record_date), ts=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')+' '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
      html+='<tr style="border-bottom:1px solid #f0f0f0;">'+
        '<td style="padding:10px;">'+(r.order_no||'')+'</td>'+
        '<td style="padding:10px;font-size:12px;">'+(r.inspection_type||'')+'</td>'+
        '<td style="padding:10px;">'+(r.process_name||'')+'</td>'+
        '<td style="padding:10px;">'+(r.inspector||'')+'</td>'+
        '<td style="padding:10px;font-weight:bold;color:'+clr+';">'+(r.result||'')+'</td>'+
        '<td style="padding:10px;font-size:12px;">'+(r.status==='withdrawn'?'<span style="color:#e74c3c;">已撤回</span>':'<span style="color:#27ae60;">正常</span>')+'</td>'+
        '<td style="padding:10px;font-size:12px;color:#888;">'+ts+'</td>'+
        '<td style="padding:10px;text-align:center;font-size:11px;">'+(r.history_count?'<span style="color:#3498db;">'+r.history_count+'次</span>':'-')+'</td>'+
        '<td style="padding:10px;text-align:center;">'+
        '<button class="qr-btn-edit" data-id="'+r.id+'" data-order="'+(r.order_no||'')+'" data-step="'+(r.process_name||'')+'" data-op="'+(r.inspector||'')+'" data-result="'+(r.result||'')+'" style="padding:3px 8px;background:#9b59b6;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-right:4px;font-size:12px;">修改</button>'+
        '<button class="qr-btn-wd" data-id="'+r.id+'" data-order="'+(r.order_no||'')+'" data-step="'+(r.process_name||'')+'" data-op="'+(r.inspector||'')+'" style="padding:3px 8px;background:#e74c3c;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-right:4px;font-size:12px;">撤回</button>'+
        '<button class="qr-btn-hist" data-id="'+r.id+'" style="padding:3px 8px;background:#95a5a6;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">历史</button></td></tr>';
    });
    html+='</tbody></table>';
    listBox.innerHTML=html;
    listBox.querySelectorAll('.qr-btn-edit').forEach(function(b){b.onclick=function(){var d=b.dataset;openQrEditModal(d.id,d.order,d.step,d.op,d.result);};});
    listBox.querySelectorAll('.qr-btn-wd').forEach(function(b){b.onclick=function(){var d=b.dataset;openQrWithdrawModal(d.id,d.order,d.step,d.op);};});
    listBox.querySelectorAll('.qr-btn-hist').forEach(function(b){b.onclick=function(){openQrHistoryModal(b.dataset.id);};});
    var tp=Math.ceil((data.total||0)/(data.page_size||20)), pg='';
    if(tp>1) for(var i=1;i<=tp;i++){var a=(i===qrCurrentPage)?'background:#9b59b6;color:#fff;':'background:#fff;color:#333;';pg+='<button onclick="loadQualityRegression('+i+')" style="padding:5px 10px;border:1px solid #ddd;border-radius:4px;cursor:pointer;'+a+'">'+i+'</button>';}
    document.getElementById('qr-pagination').innerHTML=pg;
  }).catch(function(e){listBox.innerHTML='<div style="padding:30px;text-align:center;color:#e74c3c;">加载失败: '+e.message+'</div>';});
}
function resetQualityRegressionFilter(){['qr-filter-order','qr-filter-type','qr-filter-operator','qr-filter-start','qr-filter-end'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='';});loadQualityRegression(1);}
function openQrEditModal(id,order,step,op,result){
  qrEditingId=id;
  document.getElementById('qre-order').innerText=order;document.getElementById('qre-step').innerText=step;
  document.getElementById('qre-operator').innerText=op;document.getElementById('qre-old-result').innerText=result;
  document.getElementById('qre-new-result').value=result;document.getElementById('qre-reason').value='admin_force';
  document.getElementById('qre-remark').value='';document.getElementById('qr-edit-modal').style.display='flex';
}
function closeQrEditModal(){document.getElementById('qr-edit-modal').style.display='none';qrEditingId=null;}
function submitQrUpdate(){
  if(!qrEditingId){alert('记录ID缺失');return;}
  var nr=document.getElementById('qre-new-result').value;
  if(!nr){alert('请选择质检结果');return;}
  fetch(QR_API+'/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record_id:qrEditingId,new_result:nr,admin_user:window.currentUser||'调度员',reason:document.getElementById('qre-reason').value,remark:document.getElementById('qre-remark').value})})
  .then(function(r){return r.json();}).then(function(ret){if(ret.code===0){alert('✅ '+ret.message);closeQrEditModal();loadQualityRegression();}else{alert('❌ '+ret.message);}})
  .catch(function(e){alert('❌ 请求失败: '+e.message);});
}
function openQrWithdrawModal(id,order,step,op){
  qrWithdrawingId=id;document.getElementById('qrw-order').innerText=order;document.getElementById('qrw-step').innerText=step;
  document.getElementById('qrw-operator').innerText=op;document.getElementById('qrw-reason').value='';document.getElementById('qr-withdraw-modal').style.display='flex';
}
function closeQrWithdrawModal(){document.getElementById('qr-withdraw-modal').style.display='none';qrWithdrawingId=null;}
function submitQrWithdraw(){
  if(!qrWithdrawingId){alert('记录ID缺失');return;}
  var r=document.getElementById('qrw-reason').value.trim();if(!r){alert('请填写撤回原因');return;}
  fetch(QR_API+'/withdraw',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record_id:qrWithdrawingId,admin_user:window.currentUser||'调度员',reason:'admin_withdraw:'+r})})
  .then(function(r){return r.json();}).then(function(ret){if(ret.code===0){alert('✅ '+ret.message);closeQrWithdrawModal();loadQualityRegression();}else{alert('❌ '+ret.message);}})
  .catch(function(e){alert('❌ 请求失败: '+e.message);});
}
function openQrHistoryModal(id){
  document.getElementById('qr-history-modal').style.display='flex';
  var bd=document.getElementById('qrh-body');bd.innerHTML='<div style="text-align:center;color:#999;padding:30px;">加载中...</div>';
  fetch(QR_API+'/history_full?record_id='+encodeURIComponent(id)).then(function(r){return r.json();}).then(function(ret){
    if(ret.code!==0){bd.innerHTML='<div style="color:#e74c3c;">'+ret.message+'</div>';return;}
    var rec=(ret.data||{}).record||{},h=(ret.data||{}).history||[];
    var html='<div style="margin-bottom:15px;padding:12px;background:#f8f9fa;border-radius:6px;font-size:13px;">'+
      '<div>订单: <strong>'+(rec.order_no||'')+'</strong> / 工序: <strong>'+(rec.process_name||'')+'</strong></div>'+
      '<div>质检员: '+(rec.inspector||'')+' | 当前结果: <strong style="color:'+((rec.result==='合格')?'#27ae60':'#e74c3c')+';">'+(rec.result||'')+'</strong></div></div>';
    if(!h.length){html+='<div style="text-align:center;color:#999;padding:20px;">暂无修改记录</div>';}
    else{h.forEach(function(item){
      var fb=item.field_before?JSON.parse(item.field_before):{},fa=item.field_after?JSON.parse(item.field_after):{};
      html+='<div style="padding:12px;background:#fff;border-left:3px solid #9b59b6;margin-bottom:8px;border-radius:4px;">'+
        '<div style="font-size:12px;color:#888;">'+item.reverted_at+'</div>'+
        '<div style="margin-top:5px;"><strong>'+(item.revert_reason||'')+'</strong> '+(fb.result||'')+'→'+(fa.result||'')+'</div>'+
        '<div style="font-size:12px;color:#666;margin-top:3px;">操作人: '+item.reverted_by+'</div></div>';
    });}
    bd.innerHTML=html;
  });
}
function closeQrHistoryModal(){document.getElementById('qr-history-modal').style.display='none';}

// ============= 物料回归审计 JS =============
var MR_API = '/api/material_record';
var mrCurrentPage = 1;
var mrEditingId = null;
var mrWithdrawingId = null;

function loadMaterialRegression(page){
  if(page) mrCurrentPage = page;
  var params = [];
  ['mr-filter-order','mr-filter-operator','mr-filter-start','mr-filter-end'].forEach(function(id){
    var el=document.getElementById(id);if(!el||!el.value) return;
    var k=id.replace('mr-filter-','');
    if(k==='order') params.push('order_no='+encodeURIComponent(el.value));
    else if(k==='operator') params.push('operator='+encodeURIComponent(el.value));
    else if(k==='start') params.push('start_date='+encodeURIComponent(el.value+' 00:00:00'));
    else if(k==='end') params.push('end_date='+encodeURIComponent(el.value+' 23:59:59'));
  });
  params.push('page='+mrCurrentPage,'page_size=20');
  var listBox=document.getElementById('mr-list');
  listBox.innerHTML='<div style="padding:30px;text-align:center;color:#999;">加载中...</div>';
  fetch(MR_API+'/list?'+params.join('&')).then(function(r){return r.json();}).then(function(ret){
    if(ret.code!==0){listBox.innerHTML='<div style="padding:30px;text-align:center;color:#e74c3c;">'+(ret.message||'')+'</div>';return;}
    var data=ret.data||{},rows=data.list||[];
    document.getElementById('mr-total').innerText=data.total||0;
    if(!rows.length){listBox.innerHTML='<div style="padding:30px;text-align:center;color:#999;">暂无数据</div>';document.getElementById('mr-pagination').innerHTML='';return;}
    var html='<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f8f9fa;">'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">订单号</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">标题</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">操作员</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">优先级</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">状态</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">时间</th>'+
      '<th style="padding:10px;text-align:center;border-bottom:1px solid #eee;">审计</th>'+
      '<th style="padding:10px;text-align:center;border-bottom:1px solid #eee;">操作</th></tr></thead><tbody>';
    rows.forEach(function(r){
      var pc=r.priority==='urgent'?'#e74c3c':r.priority==='high'?'#e67e22':'#95a5a6';
      var d=new Date(r.created_at),ts=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')+' '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
      html+='<tr style="border-bottom:1px solid #f0f0f0;">'+
        '<td style="padding:10px;">'+(r.related_order||'')+'</td>'+
        '<td style="padding:10px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+(r.title||'')+'</td>'+
        '<td style="padding:10px;">'+(r.target_operator||'')+'</td>'+
        '<td style="padding:10px;font-size:12px;color:'+pc+';">'+(r.priority||'')+'</td>'+
        '<td style="padding:10px;font-size:12px;">'+(r.status||'')+'</td>'+
        '<td style="padding:10px;font-size:12px;color:#888;">'+ts+'</td>'+
        '<td style="padding:10px;text-align:center;font-size:11px;">'+(r.history_count?'<span style="color:#3498db;">'+r.history_count+'次</span>':'-')+'</td>'+
        '<td style="padding:10px;text-align:center;">'+
        '<button class="mr-btn-edit" data-id="'+r.id+'" data-order="'+(r.related_order||'')+'" data-step="'+(r.related_process||'')+'" data-op="'+(r.target_operator||'')+'" data-title="'+escapeHtml(r.title||'')+'" data-pri="'+(r.priority||'')+'" style="padding:3px 8px;background:#e67e22;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-right:4px;font-size:12px;">修改</button>'+
        '<button class="mr-btn-wd" data-id="'+r.id+'" data-order="'+(r.related_order||'')+'" data-step="'+(r.related_process||'')+'" data-op="'+(r.target_operator||'')+'" style="padding:3px 8px;background:#e74c3c;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-right:4px;font-size:12px;">撤回</button>'+
        '<button class="mr-btn-hist" data-id="'+r.id+'" style="padding:3px 8px;background:#95a5a6;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">历史</button></td></tr>';
    });
    html+='</tbody></table>';
    listBox.innerHTML=html;
    listBox.querySelectorAll('.mr-btn-edit').forEach(function(b){b.onclick=function(){var d=b.dataset;openMrEditModal(d.id,d.order,d.step,d.op,d.title,d.pri);};});
    listBox.querySelectorAll('.mr-btn-wd').forEach(function(b){b.onclick=function(){var d=b.dataset;openMrWithdrawModal(d.id,d.order,d.step,d.op);};});
    listBox.querySelectorAll('.mr-btn-hist').forEach(function(b){b.onclick=function(){openMrHistoryModal(b.dataset.id);};});
    var tp=Math.ceil((data.total||0)/(data.page_size||20)),pg='';
    if(tp>1) for(var i=1;i<=tp;i++){var a=(i===mrCurrentPage)?'background:#e67e22;color:#fff;':'background:#fff;color:#333;';pg+='<button onclick="loadMaterialRegression('+i+')" style="padding:5px 10px;border:1px solid #ddd;border-radius:4px;cursor:pointer;'+a+'">'+i+'</button>';}
    document.getElementById('mr-pagination').innerHTML=pg;
  }).catch(function(e){listBox.innerHTML='<div style="padding:30px;text-align:center;color:#e74c3c;">加载失败: '+e.message+'</div>';});
}
function resetMaterialRegressionFilter(){['mr-filter-order','mr-filter-operator','mr-filter-start','mr-filter-end'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='';});loadMaterialRegression(1);}
function openMrEditModal(id,order,step,op,title,pri){
  mrEditingId=id;document.getElementById('mre-order').innerText=order;document.getElementById('mre-step').innerText=step;
  document.getElementById('mre-operator').innerText=op;document.getElementById('mre-title').value=title||'';
  document.getElementById('mre-priority').value=pri||'normal';document.getElementById('mre-target-op').value=op||'';
  document.getElementById('mre-reason').value='admin_force';document.getElementById('mr-edit-modal').style.display='flex';
}
function closeMrEditModal(){document.getElementById('mr-edit-modal').style.display='none';mrEditingId=null;}
function submitMrUpdate(){
  if(!mrEditingId){alert('记录ID缺失');return;}
  fetch(MR_API+'/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record_id:mrEditingId,admin_user:window.currentUser||'调度员',reason:document.getElementById('mre-reason').value,title:document.getElementById('mre-title').value,priority:document.getElementById('mre-priority').value,target_operator:document.getElementById('mre-target-op').value})})
  .then(function(r){return r.json();}).then(function(ret){if(ret.code===0){alert('✅ '+ret.message);closeMrEditModal();loadMaterialRegression();}else{alert('❌ '+ret.message);}})
  .catch(function(e){alert('❌ 请求失败: '+e.message);});
}
function openMrWithdrawModal(id,order,step,op){mrWithdrawingId=id;document.getElementById('mrw-order').innerText=order;document.getElementById('mrw-step').innerText=step;document.getElementById('mrw-operator').innerText=op;document.getElementById('mrw-reason').value='';document.getElementById('mr-withdraw-modal').style.display='flex';}
function closeMrWithdrawModal(){document.getElementById('mr-withdraw-modal').style.display='none';mrWithdrawingId=null;}
function submitMrWithdraw(){if(!mrWithdrawingId){alert('记录ID缺失');return;}var r=document.getElementById('mrw-reason').value.trim();if(!r){alert('请填写撤回原因');return;}fetch(MR_API+'/withdraw',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record_id:mrWithdrawingId,admin_user:window.currentUser||'调度员',reason:'admin_withdraw:'+r})}).then(function(r){return r.json();}).then(function(ret){if(ret.code===0){alert('✅ '+ret.message);closeMrWithdrawModal();loadMaterialRegression();}else{alert('❌ '+ret.message);}}).catch(function(e){alert('❌ 请求失败: '+e.message);});}
function openMrHistoryModal(id){document.getElementById('mr-history-modal').style.display='flex';var bd=document.getElementById('mrh-body');bd.innerHTML='<div style="text-align:center;color:#999;padding:30px;">加载中...</div>';fetch(MR_API+'/history_full?record_id='+encodeURIComponent(id)).then(function(r){return r.json();}).then(function(ret){if(ret.code!==0){bd.innerHTML='<div style="color:#e74c3c;">'+ret.message+'</div>';return;}var rec=(ret.data||{}).record||{},h=(ret.data||{}).history||[];var html='<div style="margin-bottom:15px;padding:12px;background:#f8f9fa;border-radius:6px;font-size:13px;"><div>订单: <strong>'+(rec.related_order||'')+'</strong></div></div>';if(!h.length){html+='<div style="text-align:center;color:#999;padding:20px;">暂无修改记录</div>';}else{h.forEach(function(item){html+='<div style="padding:12px;background:#fff;border-left:3px solid #e67e22;margin-bottom:8px;border-radius:4px;"><div style="font-size:12px;color:#888;">'+item.reverted_at+'</div><div style="margin-top:5px;"><strong>'+(item.revert_reason||'')+'</strong></div><div style="font-size:12px;color:#666;margin-top:3px;">操作人: '+item.reverted_by+'</div></div>';});}bd.innerHTML=html;});}
function closeMrHistoryModal(){document.getElementById('mr-history-modal').style.display='none';}

// ============= 外协回归审计 JS =============
var OR_API = '/api/outsource_record';
var orCurrentPage = 1;
var orEditingId = null;
var orWithdrawingId = null;

function loadOutsourceRegression(page){
  if(page) orCurrentPage = page;
  var params = [];
  ['or-filter-order','or-filter-operator','or-filter-start','or-filter-end'].forEach(function(id){
    var el=document.getElementById(id);if(!el||!el.value) return;
    var k=id.replace('or-filter-','');
    if(k==='order') params.push('order_no='+encodeURIComponent(el.value));
    else if(k==='operator') params.push('operator='+encodeURIComponent(el.value));
    else if(k==='start') params.push('start_date='+encodeURIComponent(el.value+' 00:00:00'));
    else if(k==='end') params.push('end_date='+encodeURIComponent(el.value+' 23:59:59'));
  });
  params.push('page='+orCurrentPage,'page_size=20');
  var listBox=document.getElementById('or-list');
  listBox.innerHTML='<div style="padding:30px;text-align:center;color:#999;">加载中...</div>';
  fetch(OR_API+'/list?'+params.join('&')).then(function(r){return r.json();}).then(function(ret){
    if(ret.code!==0){listBox.innerHTML='<div style="padding:30px;text-align:center;color:#e74c3c;">'+(ret.message||'')+'</div>';return;}
    var data=ret.data||{},rows=data.list||[];
    document.getElementById('or-total').innerText=data.total||0;
    if(!rows.length){listBox.innerHTML='<div style="padding:30px;text-align:center;color:#999;">暂无数据</div>';document.getElementById('or-pagination').innerHTML='';return;}
    var html='<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f8f9fa;">'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">订单号</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">标题</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">操作员</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">优先级</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">状态</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">时间</th>'+
      '<th style="padding:10px;text-align:center;border-bottom:1px solid #eee;">审计</th>'+
      '<th style="padding:10px;text-align:center;border-bottom:1px solid #eee;">操作</th></tr></thead><tbody>';
    rows.forEach(function(r){
      var d=new Date(r.created_at),ts=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')+' '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
      var pc=r.priority==='urgent'?'#e74c3c':r.priority==='high'?'#e67e22':'#95a5a6';
      html+='<tr style="border-bottom:1px solid #f0f0f0;">'+
        '<td style="padding:10px;">'+(r.related_order||'')+'</td>'+
        '<td style="padding:10px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+(r.title||'')+'</td>'+
        '<td style="padding:10px;">'+(r.target_operator||'')+'</td>'+
        '<td style="padding:10px;font-size:12px;color:'+pc+';">'+(r.priority||'')+'</td>'+
        '<td style="padding:10px;font-size:12px;">'+(r.status||'')+'</td>'+
        '<td style="padding:10px;font-size:12px;color:#888;">'+ts+'</td>'+
        '<td style="padding:10px;text-align:center;font-size:11px;">'+(r.history_count?'<span style="color:#3498db;">'+r.history_count+'次</span>':'-')+'</td>'+
        '<td style="padding:10px;text-align:center;">'+
        '<button class="or-btn-edit" data-id="'+r.id+'" data-order="'+(r.related_order||'')+'" data-step="'+(r.related_process||'')+'" data-op="'+(r.target_operator||'')+'" data-title="'+escapeHtml(r.title||'')+'" data-pri="'+(r.priority||'')+'" style="padding:3px 8px;background:#1abc9c;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-right:4px;font-size:12px;">修改</button>'+
        '<button class="or-btn-wd" data-id="'+r.id+'" data-order="'+(r.related_order||'')+'" data-step="'+(r.related_process||'')+'" data-op="'+(r.target_operator||'')+'" style="padding:3px 8px;background:#e74c3c;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-right:4px;font-size:12px;">撤回</button>'+
        '<button class="or-btn-hist" data-id="'+r.id+'" style="padding:3px 8px;background:#95a5a6;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">历史</button></td></tr>';
    });
    html+='</tbody></table>';
    listBox.innerHTML=html;
    listBox.querySelectorAll('.or-btn-edit').forEach(function(b){b.onclick=function(){var d=b.dataset;openOrEditModal(d.id,d.order,d.step,d.op,d.title,d.pri);};});
    listBox.querySelectorAll('.or-btn-wd').forEach(function(b){b.onclick=function(){var d=b.dataset;openOrWithdrawModal(d.id,d.order,d.step,d.op);};});
    listBox.querySelectorAll('.or-btn-hist').forEach(function(b){b.onclick=function(){openOrHistoryModal(b.dataset.id);};});
    var tp=Math.ceil((data.total||0)/(data.page_size||20)),pg='';
    if(tp>1) for(var i=1;i<=tp;i++){var a=(i===orCurrentPage)?'background:#1abc9c;color:#fff;':'background:#fff;color:#333;';pg+='<button onclick="loadOutsourceRegression('+i+')" style="padding:5px 10px;border:1px solid #ddd;border-radius:4px;cursor:pointer;'+a+'">'+i+'</button>';}
    document.getElementById('or-pagination').innerHTML=pg;
  }).catch(function(e){listBox.innerHTML='<div style="padding:30px;text-align:center;color:#e74c3c;">加载失败: '+e.message+'</div>';});
}
function resetOutsourceRegressionFilter(){['or-filter-order','or-filter-operator','or-filter-start','or-filter-end'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='';});loadOutsourceRegression(1);}
function openOrEditModal(id,order,step,op,title,pri){orEditingId=id;document.getElementById('ore-order').innerText=order;document.getElementById('ore-step').innerText=step;document.getElementById('ore-operator').innerText=op;document.getElementById('ore-title').value=title||'';document.getElementById('ore-priority').value=pri||'normal';document.getElementById('ore-target-op').value=op||'';document.getElementById('ore-reason').value='admin_force';document.getElementById('or-edit-modal').style.display='flex';}
function closeOrEditModal(){document.getElementById('or-edit-modal').style.display='none';orEditingId=null;}

function submitOrUpdate(){if(!orEditingId){alert('记录ID缺失');return;}fetch(OR_API+'/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record_id:orEditingId,admin_user:window.currentUser||'调度员',reason:document.getElementById('ore-reason').value,title:document.getElementById('ore-title').value,priority:document.getElementById('ore-priority').value,target_operator:document.getElementById('ore-target-op').value})}).then(function(r){return r.json();}).then(function(ret){if(ret.code===0){alert('✅ '+ret.message);closeOrEditModal();loadOutsourceRegression();}else{alert('❌ '+ret.message);}}).catch(function(e){alert('❌ 请求失败: '+e.message);});}
function openOrWithdrawModal(id,order,step,op){orWithdrawingId=id;document.getElementById('orw-order').innerText=order;document.getElementById('orw-step').innerText=step;document.getElementById('orw-operator').innerText=op;document.getElementById('orw-reason').value='';document.getElementById('or-withdraw-modal').style.display='flex';}
function closeOrWithdrawModal(){document.getElementById('or-withdraw-modal').style.display='none';orWithdrawingId=null;}
function submitOrWithdraw(){if(!orWithdrawingId){alert('记录ID缺失');return;}var r=document.getElementById('orw-reason').value.trim();if(!r){alert('请填写撤回原因');return;}fetch(OR_API+'/withdraw',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record_id:orWithdrawingId,admin_user:window.currentUser||'调度员',reason:'admin_withdraw:'+r})}).then(function(r){return r.json();}).then(function(ret){if(ret.code===0){alert('✅ '+ret.message);closeOrWithdrawModal();loadOutsourceRegression();}else{alert('❌ '+ret.message);}}).catch(function(e){alert('❌ 请求失败: '+e.message);});}
function openOrHistoryModal(id){document.getElementById('or-history-modal').style.display='flex';var bd=document.getElementById('orh-body');bd.innerHTML='<div style="text-align:center;color:#999;padding:30px;">加载中...</div>';fetch(OR_API+'/history_full?record_id='+encodeURIComponent(id)).then(function(r){return r.json();}).then(function(ret){if(ret.code!==0){bd.innerHTML='<div style="color:#e74c3c;">'+ret.message+'</div>';return;}var rec=(ret.data||{}).record||{},h=(ret.data||{}).history||[];var html='<div style="margin-bottom:15px;padding:12px;background:#f8f9fa;border-radius:6px;font-size:13px;"><div>订单: <strong>'+(rec.related_order||'')+'</strong></div></div>';if(!h.length){html+='<div style="text-align:center;color:#999;padding:20px;">暂无修改记录</div>';}else{h.forEach(function(item){html+='<div style="padding:12px;background:#fff;border-left:3px solid #1abc9c;margin-bottom:8px;border-radius:4px;"><div style="font-size:12px;color:#888;">'+item.reverted_at+'</div><div style="margin-top:5px;"><strong>'+(item.revert_reason||'')+'</strong></div><div style="font-size:12px;color:#666;margin-top:3px;">操作人: '+item.reverted_by+'</div></div>';});}bd.innerHTML=html;});}
function closeOrHistoryModal(){document.getElementById('or-history-modal').style.display='none';}

// ============= 排产回归审计 JS =============
var SR_API = '/api/schedule_record';
var srCurrentPage = 1; var srEditingId = null; var srWithdrawingId = null;

function loadScheduleRegression(page){
  if(page) srCurrentPage = page; var params = [];
  ['sr-filter-order','sr-filter-operator','sr-filter-start','sr-filter-end'].forEach(function(id){
    var el=document.getElementById(id);if(!el||!el.value) return; var k=id.replace('sr-filter-','');
    if(k==='order') params.push('order_no='+encodeURIComponent(el.value));
    else if(k==='operator') params.push('operator='+encodeURIComponent(el.value));
    else if(k==='start') params.push('start_date='+encodeURIComponent(el.value+' 00:00:00'));
    else if(k==='end') params.push('end_date='+encodeURIComponent(el.value+' 23:59:59'));
  });
  params.push('page='+srCurrentPage,'page_size=20');
  var listBox=document.getElementById('sr-list');
  listBox.innerHTML='<div style="padding:30px;text-align:center;color:#999;">加载中...</div>';
  fetch(SR_API+'/list?'+params.join('&')).then(function(r){return r.json();}).then(function(ret){
    if(ret.code!==0){listBox.innerHTML='<div style="padding:30px;text-align:center;color:#e74c3c;">'+(ret.message||'')+'</div>';return;}
    var data=ret.data||{},rows=data.list||[];
    document.getElementById('sr-total').innerText=data.total||0;
    if(!rows.length){listBox.innerHTML='<div style="padding:30px;text-align:center;color:#999;">暂无数据</div>';document.getElementById('sr-pagination').innerHTML='';return;}
    var html='<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f8f9fa;">'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">订单号</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">标题</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">操作员</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">优先级</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">状态</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">时间</th>'+
      '<th style="padding:10px;text-align:center;border-bottom:1px solid #eee;">审计</th>'+
      '<th style="padding:10px;text-align:center;border-bottom:1px solid #eee;">操作</th></tr></thead><tbody>';
    rows.forEach(function(r){
      var d=new Date(r.created_at),ts=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')+' '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
      var pc=r.priority==='urgent'?'#e74c3c':r.priority==='high'?'#e67e22':'#95a5a6';
      html+='<tr style="border-bottom:1px solid #f0f0f0;">'+
        '<td style="padding:10px;">'+(r.related_order||'')+'</td>'+
        '<td style="padding:10px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+(r.title||'')+'</td>'+
        '<td style="padding:10px;">'+(r.target_operator||'')+'</td>'+
        '<td style="padding:10px;font-size:12px;color:'+pc+';">'+(r.priority||'')+'</td>'+
        '<td style="padding:10px;font-size:12px;">'+(r.status||'')+'</td>'+
        '<td style="padding:10px;font-size:12px;color:#888;">'+ts+'</td>'+
        '<td style="padding:10px;text-align:center;font-size:11px;">'+(r.history_count?'<span style="color:#3498db;">'+r.history_count+'次</span>':'-')+'</td>'+
        '<td style="padding:10px;text-align:center;">'+
        '<button class="sr-btn-edit" data-id="'+r.id+'" data-order="'+(r.related_order||'')+'" data-step="'+(r.related_process||'')+'" data-op="'+(r.target_operator||'')+'" data-title="'+escapeHtml(r.title||'')+'" data-pri="'+(r.priority||'')+'" style="padding:3px 8px;background:#3498db;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-right:4px;font-size:12px;">修改</button>'+
        '<button class="sr-btn-wd" data-id="'+r.id+'" data-order="'+(r.related_order||'')+'" data-step="'+(r.related_process||'')+'" data-op="'+(r.target_operator||'')+'" style="padding:3px 8px;background:#e74c3c;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-right:4px;font-size:12px;">撤回</button>'+
        '<button class="sr-btn-hist" data-id="'+r.id+'" style="padding:3px 8px;background:#95a5a6;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">历史</button></td></tr>';
    });
    html+='</tbody></table>';
    listBox.innerHTML=html;
    listBox.querySelectorAll('.sr-btn-edit').forEach(function(b){b.onclick=function(){var d=b.dataset;openSrEditModal(d.id,d.order,d.step,d.op,d.title,d.pri);};});
    listBox.querySelectorAll('.sr-btn-wd').forEach(function(b){b.onclick=function(){var d=b.dataset;openSrWithdrawModal(d.id,d.order,d.step,d.op);};});
    listBox.querySelectorAll('.sr-btn-hist').forEach(function(b){b.onclick=function(){openSrHistoryModal(b.dataset.id);};});
    var tp=Math.ceil((data.total||0)/(data.page_size||20)),pg='';
    if(tp>1) for(var i=1;i<=tp;i++){var a=(i===srCurrentPage)?'background:#3498db;color:#fff;':'background:#fff;color:#333;';pg+='<button onclick="loadScheduleRegression('+i+')" style="padding:5px 10px;border:1px solid #ddd;border-radius:4px;cursor:pointer;'+a+'">'+i+'</button>';}
    document.getElementById('sr-pagination').innerHTML=pg;
  }).catch(function(e){listBox.innerHTML='<div style="padding:30px;text-align:center;color:#e74c3c;">加载失败: '+e.message+'</div>';});
}
function resetScheduleRegressionFilter(){['sr-filter-order','sr-filter-operator','sr-filter-start','sr-filter-end'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='';});loadScheduleRegression(1);}
function openSrEditModal(id,order,step,op,title,pri){srEditingId=id;document.getElementById('sre-order').innerText=order;document.getElementById('sre-step').innerText=step;document.getElementById('sre-operator').innerText=op;document.getElementById('sre-title').value=title||'';document.getElementById('sre-priority').value=pri||'normal';document.getElementById('sre-target-op').value=op||'';document.getElementById('sre-reason').value='admin_force';document.getElementById('sr-edit-modal').style.display='flex';}
function closeSrEditModal(){document.getElementById('sr-edit-modal').style.display='none';srEditingId=null;}
function submitSrUpdate(){if(!srEditingId){alert('记录ID缺失');return;}fetch(SR_API+'/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record_id:srEditingId,admin_user:window.currentUser||'调度员',reason:document.getElementById('sre-reason').value,title:document.getElementById('sre-title').value,priority:document.getElementById('sre-priority').value,target_operator:document.getElementById('sre-target-op').value})}).then(function(r){return r.json();}).then(function(ret){if(ret.code===0){alert('✅ '+ret.message);closeSrEditModal();loadScheduleRegression();}else{alert('❌ '+ret.message);}}).catch(function(e){alert('❌ 请求失败: '+e.message);});}
function openSrWithdrawModal(id,order,step,op){srWithdrawingId=id;document.getElementById('srw-order').innerText=order;document.getElementById('srw-step').innerText=step;document.getElementById('srw-operator').innerText=op;document.getElementById('srw-reason').value='';document.getElementById('sr-withdraw-modal').style.display='flex';}
function closeSrWithdrawModal(){document.getElementById('sr-withdraw-modal').style.display='none';srWithdrawingId=null;}
function submitSrWithdraw(){if(!srWithdrawingId){alert('记录ID缺失');return;}var r=document.getElementById('srw-reason').value.trim();if(!r){alert('请填写撤回原因');return;}fetch(SR_API+'/withdraw',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record_id:srWithdrawingId,admin_user:window.currentUser||'调度员',reason:'admin_withdraw:'+r})}).then(function(r){return r.json();}).then(function(ret){if(ret.code===0){alert('✅ '+ret.message);closeSrWithdrawModal();loadScheduleRegression();}else{alert('❌ '+ret.message);}}).catch(function(e){alert('❌ 请求失败: '+e.message);});}
function openSrHistoryModal(id){document.getElementById('sr-history-modal').style.display='flex';var bd=document.getElementById('srh-body');bd.innerHTML='<div style="text-align:center;color:#999;padding:30px;">加载中...</div>';fetch(SR_API+'/history_full?record_id='+encodeURIComponent(id)).then(function(r){return r.json();}).then(function(ret){if(ret.code!==0){bd.innerHTML='<div style="color:#e74c3c;">'+ret.message+'</div>';return;}var rec=(ret.data||{}).record||{},h=(ret.data||{}).history||[];var html='<div style="margin-bottom:15px;padding:12px;background:#f8f9fa;border-radius:6px;font-size:13px;"><div>订单: <strong>'+(rec.related_order||'')+'</strong></div></div>';if(!h.length){html+='<div style="text-align:center;color:#999;padding:20px;">暂无修改记录</div>';}else{h.forEach(function(item){html+='<div style="padding:12px;background:#fff;border-left:3px solid #3498db;margin-bottom:8px;border-radius:4px;"><div style="font-size:12px;color:#888;">'+item.reverted_at+'</div><div style="margin-top:5px;"><strong>'+(item.revert_reason||'')+'</strong></div><div style="font-size:12px;color:#666;margin-top:3px;">操作人: '+item.reverted_by+'</div></div>';});}bd.innerHTML=html;});}
function closeSrHistoryModal(){document.getElementById('sr-history-modal').style.display='none';}


// === 初始化 ===
const savedTab = sessionStorage.getItem('dc_active_tab');
if (savedTab && TAB_LOAD_FUNCS[savedTab]) {
  switchTab(savedTab);
} else {
  switchTab('overview');
}
startAutoRefresh();

setTimeout(function() {
  const el = document.getElementById('process-search');
  if (el && el.value) el.value = '';
}, 200);
// Chrome顽固自动填充，多次清除兜底
[400, 600, 1000].forEach(function(delay) {
  setTimeout(function() {
    var el = document.getElementById('process-search');
    if (el && el.value) el.value = '';
  }, delay);
});

// ── 系统配置（动态渲染） ──────────────────────────
function renderConfigCenter() {
  const sidebarEl = document.getElementById('config-category-tabs');
  const contentEl = document.getElementById('config-category-content');
  if (!sidebarEl || !contentEl) return;

  let activeCategory = null;
  let schemaData = null;
  let valuesData = {};

  function renderCategoryTabs() {
    if (!schemaData) return;
    sidebarEl.innerHTML = Object.keys(schemaData).map(key => {
      const cat = schemaData[key];
      return `<div class="config-sidebar-item${activeCategory === key ? ' active' : ''}" data-cat="${key}">${cat.icon || '📋'} ${cat.label}</div>`;
    }).join('');
  }

  // 使用事件委派避免重复绑定
  sidebarEl.addEventListener('click', function(e) {
    const item = e.target.closest('.config-sidebar-item');
    if (item) {
      activeCategory = item.dataset.cat;
      renderCategoryTabs();
      renderCategoryContent();
    }
  });

  function renderCategoryContent() {
    if (!activeCategory || !schemaData) return;
    const cat = schemaData[activeCategory];
    const fields = cat.fields || [];
    const hasTest = cat.test && cat.test.action;

    contentEl.innerHTML = '<h3 style="margin:0 0 16px;">' + (cat.icon || '📋') + ' ' + cat.label + '</h3>' +
      (cat.test && cat.test.label ? '<p style="margin:0 0 16px;color:#888;font-size:13px;">' + escHtml(cat.test.label) + '</p>' : '') +
      '<div class="form-grid">' +
      fields.map(f => renderField(f, valuesData[f.key] || '')).join('') +
      '</div>' +
      '<div class="config-action-bar">' +
      '<button class="btn btn-primary" onclick="saveSystemConfig()">💾 保存配置</button>' +
      (hasTest ? '<button class="btn btn-secondary" onclick="testSystemConfig()">🔌 ' + escHtml(cat.test.label || '测试连接') + '</button>' : '') +
      '<span id="config-status" style="font-size:13px;line-height:34px;"></span>' +
      '</div>';

    // 注: activeCategory 已通过闭包可访问，无需额外挂载到 window
  }

  function renderField(field, value) {
    const key = field.key;
    const label = field.label;
    const ph = field.placeholder || '';
    if (field.type === 'password' || (field.sensitive && field.type === 'text')) {
      return '<div class="form-group"><label>' + escHtml(label) +
        (field.required !== false ? ' <span style="color:#ff4d4f;">*</span>' : '') +
        '</label><input id="cfg-' + key + '" type="password" class="form-input" value="' + escHtml(value || '') + '" placeholder="' + escHtml(ph) + '" style="width:100%;"></div>';
    }
    if (field.type === 'boolean' || field.type === 'switch') {
      const checked = value === true || value === 'true' || value === 1 || value === '1' ? ' checked' : '';
      return '<div class="form-group"><label>' + escHtml(label) + '</label><label class="switch" style="margin-left:8px;"><input id="cfg-' + key + '" type="checkbox"' + checked + '></label></div>';
    }
    if (field.type === 'number') {
      return '<div class="form-group"><label>' + escHtml(label) +
        (field.required !== false ? ' <span style="color:#ff4d4f;">*</span>' : '') +
        '</label><input id="cfg-' + key + '" type="number" class="form-input" value="' + escHtml(value != null ? String(value) : '') + '" placeholder="' + escHtml(ph) + '" style="width:100%;"></div>';
    }
    return '<div class="form-group"><label>' + escHtml(label) +
      (field.required !== false ? ' <span style="color:#ff4d4f;">*</span>' : '') +
      '</label><input id="cfg-' + key + '" type="text" class="form-input" value="' + escHtml(value || '') + '" placeholder="' + escHtml(ph) + '" style="width:100%;"></div>';
  }

  function collectFormValues() {
    if (!activeCategory || !schemaData) return {};
    const fields = schemaData[activeCategory].fields || [];
    const values = {};
    fields.forEach(f => {
      const el = document.getElementById('cfg-' + f.key);
      if (!el) return;
      if (f.type === 'boolean' || f.type === 'switch') {
        values[f.key] = el.checked ? 'true' : 'false';
      } else if (f.type === 'number') {
        values[f.key] = el.value ? Number(el.value) : '';
      } else {
        values[f.key] = el.value.trim();
      }
    });
    return values;
  }

  window.saveSystemConfig = function() {
    const statusEl = document.getElementById('config-status');
    if (!statusEl) return;
    const values = collectFormValues();
    if (Object.keys(values).length === 0) { statusEl.textContent = '⚠️ 没有可保存的字段'; return; }
    statusEl.textContent = '保存中...';
    fetch((CONN.activeBase || '') + '/api/config-center/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(values)
    }).then(r => r.json()).then(d => {
      if (d.code === 0) {
        statusEl.textContent = '✅ 保存成功';
        toast('配置已保存', 'success');
        valuesData = Object.assign(valuesData, values);
        loadCloudConfig();
      } else {
        statusEl.textContent = '❌ ' + (d.message || '保存失败');
      }
    }).catch(e => {
      statusEl.textContent = '❌ 请求失败: ' + e.message;
    });
  };

  window.testSystemConfig = function() {
    const statusEl = document.getElementById('config-status');
    if (!statusEl || !activeCategory || !schemaData) return;
    const cat = schemaData[activeCategory];
    if (!cat.test || !cat.test.action) { statusEl.textContent = '⚠️ 该分类不支持测试'; return; }
    const values = collectFormValues();
    statusEl.textContent = '测试中...';
    fetch((CONN.activeBase || '') + '/api/config-center/test/' + cat.test.action, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(values)
    }).then(r => r.json()).then(d => {
      if (d.code === 0) {
        statusEl.textContent = d.message || '✅ 测试通过';
        toast('测试通过', 'success');
      } else {
        statusEl.textContent = d.message || '❌ 测试失败';
      }
    }).catch(e => {
      statusEl.textContent = '❌ 请求失败: ' + e.message;
    });
  };

  contentEl.innerHTML = '<div class="loading">加载配置中...</div>';
  Promise.all([
    fetch((CONN.activeBase || '') + '/api/config-center/schema').then(r => r.json()),
    fetch((CONN.activeBase || '') + '/api/config-center/values').then(r => r.json())
  ]).then(([schemaResp, valuesResp]) => {
    if (schemaResp.code !== 0) { contentEl.innerHTML = '<div class="error">加载 schema 失败</div>'; return; }
    schemaData = schemaResp.data;
    if (valuesResp.code === 0) valuesData = valuesResp.data || {};
    const keys = Object.keys(schemaData);
    if (keys.length === 0) { contentEl.innerHTML = '<div class="empty-state">暂无配置</div>'; return; }
    activeCategory = keys[0];
    renderCategoryTabs();
    renderCategoryContent();
  }).catch(e => {
    contentEl.innerHTML = '<div class="error">请求失败: ' + escHtml(e.message) + '</div>';
  });
}

// === 工序配置页面 ===
async function loadProcessConfig() {
  console.debug('[DEBUG] loadProcessConfig 开始执行');
  try {
    const configRes = await api('/global-config');
    console.debug('[DEBUG] global-config 返回:', configRes);
    if (configRes?.code === 0) {
      const cfg = configRes.data;
      const autoSendEl = document.getElementById('cfg-auto-send');
      const defaultAllEl = document.getElementById('cfg-default-all');
      const templateEl = document.getElementById('cfg-template');
      if (autoSendEl) autoSendEl.checked = cfg.auto_send !== false;
      if (defaultAllEl) defaultAllEl.checked = cfg.default_to_all !== false;
      if (templateEl) templateEl.value = cfg.message_template || '';
    }
  } catch(e) { console.error('[DEBUG] global-config 错误:', e); }

  console.debug('[DEBUG] 加载工序部门列表...');
  loadProcessDeptList();

  console.debug('[DEBUG] 加载工序和部门选项...');
  loadProcessAndDeptOptions();

  console.debug('[DEBUG] 加载模板列表...');
  loadTemplateList();
  console.debug('[DEBUG] loadProcessConfig 完成');
}

function loadTemplateList() {
  const select = document.getElementById('template-name-select');

  api('/templates').then(ret => {
    const data = ret?.data || {};
    const templates = data.templates || [];
    const currentVal = select.value;
    if (templates.length === 0) {
      select.innerHTML = '<option value="">-- 暂无模板 --</option>';
      return;
    }
    select.innerHTML = '<option value="">-- 选择模板 --</option>'
      + templates.map(t => `<option value="${escHtml(t.name)}">${escHtml(t.name)}</option>`).join('');
    if (currentVal && templates.some(t => t.name === currentVal)) {
      select.value = currentVal;
    }
  }).catch(err => {
    console.error('加载模板列表失败:', err);
  });
}

async function saveTemplate() {
  try {
    const select = document.getElementById('template-name-select');
    const name = select.value?.trim();
    const content = document.getElementById('cfg-template').value;
    if (!name) { toast('请选择或输入模板名称', 'error'); return; }
    const res = await api('/templates', {
      method: 'POST',
      body: { name, content }
    });
    toast(res.message, res.code === 0 ? 'success' : 'error');
    if (res.code === 0) {
      loadTemplateList();
    }
  } catch(e) {
    toast('操作异常: ' + e.message, 'error');
  }
}

function selectTemplate(name) {
  console.debug('[DEBUG] selectTemplate called with:', name);
  api('/templates').then(ret => {
    console.debug('[DEBUG] selectTemplate templates API返回:', ret);
    if (ret.code !== 0) return;
    const templates = ret.data?.templates || [];
    const tpl = templates.find(t => t.name === name);
    if (tpl) {
      document.getElementById('cfg-template').value = tpl.content || '';
      const select = document.getElementById('template-name-select');
      if (select) select.value = tpl.name || '';
    }
  });
}

function onProcessTemplateSelect(name) {
  console.debug('[DEBUG] onProcessTemplateSelect called with:', name);
  if (!name) return;
  selectTemplate(name);
}

function loadTemplate() {
  const name = document.getElementById('template-name')?.value?.trim();
  if (!name) { toast('请选择模板', 'error'); return; }
  selectTemplate(name);
}

async function deleteTemplate(name) {
  try {
    if (!confirm(`确定删除模板"${name}"？`)) return;
    const res = await api(`/templates/${encodeURIComponent(name)}`, { method: 'DELETE' });
    toast(res.message, res.code === 0 ? 'success' : 'error');
    if (res.code === 0) loadTemplateList();
  } catch(e) {
    toast('操作异常: ' + e.message, 'error');
  }
}

function deleteSelectedTemplate() {
  const select = document.getElementById('template-name-select');
  const name = select.value?.trim();
  if (!name) { toast('请先选择一个模板', 'error'); return; }
  deleteTemplate(name);
}

async function loadProcessDeptList() {
  console.debug('[DEBUG] loadProcessDeptList called');
  const res = await api('/cc-api/process-departments');
  const list = document.getElementById('process-dept-list');
  console.debug('[DEBUG] process-departments API返回:', res);
  if (res.code !== 0) { list.innerHTML = '<div class="error">加载失败</div>'; return; }

  const mapping = res.data || {};
  const entries = Object.entries(mapping);
  console.debug('[DEBUG] 工序部门映射条目数:', entries.length);

  if (entries.length === 0) {
    list.innerHTML = '<div class="no-tasks">暂无工序部门绑定</div>';
    return;
  }

  // 加载工序名映射
  let nameMap = {};
  try {
    const pnRes = await api('/cc-api/process-names');
    if (pnRes.code === 0) { nameMap = pnRes.data || {}; }
  } catch(e) {}

  list.innerHTML = entries.map(([process, dept]) => `
    <div class="process-dept-item">
      <span class="process-name">${escHtml(nameMap[process] || process)}</span>
      <span class="arrow">→</span>
      <span class="dept-name">${escHtml(dept)}</span>
      <span class="delete-btn" onclick="removeProcessDept('${escHtml(process)}')" title="删除">×</span>
    </div>
  `).join('');
}

async function loadProcessAndDeptOptions() {
  try {
    const [pnRes, deptRes] = await Promise.all([
      api('/process-names'),
      api('/all-departments-flat')
    ]);
    if (pnRes.code === 0) {
      const processes = pnRes.data || [];
      const processSelect = document.getElementById('add-process-select');
      if (processSelect) {
        processSelect.innerHTML = '<option value="">请选择工序</option>' +
          processes.map(p => `<option value="${escHtml(p)}">${escHtml(p)}</option>`).join('');
      }
    }
    if (deptRes.code === 0) {
      const depts = deptRes.data || [];
      const deptSelect = document.getElementById('add-dept-select');
      if (deptSelect) {
        deptSelect.innerHTML = '<option value="">请选择部门</option>' +
          depts.map(d => `<option value="${escHtml(d.name)}">${escHtml(d.full_path)}</option>`).join('');
      }
    }
  } catch (e) {
    console.error('[loadProcessAndDeptOptions]', e);
  }
}

async function removeProcessDept(process) {
  if (!confirm(`确定删除工序"${process}"的部门绑定？`)) return;
  const res = await api(`/process-departments/${encodeURIComponent(process)}`, {
    method: 'DELETE'
  });
  toast(res.message, res.code === 0 ? 'success' : 'error');
  if (res.code === 0) loadProcessDeptList();
}

async function addProcessDept() {
  const processSelect = document.getElementById('add-process-select');
  const deptSelect = document.getElementById('add-dept-select');
  const process = processSelect?.value?.trim();
  const dept = deptSelect?.value?.trim();
  if (!process || !dept) { toast('请选择工序和部门', 'error'); return; }
  const res = await api(`/process-departments/${encodeURIComponent(process)}`, {
    method: 'POST',
    body: { department: dept }
  });
  toast(res.message, res.code === 0 ? 'success' : 'error');
  if (res.code === 0) {
    processSelect.value = '';
    deptSelect.value = '';
    loadProcessDeptList();
  }
}

async function saveGlobalConfig() {
  const auto_send = document.getElementById('cfg-auto-send').checked;
  const default_to_all = document.getElementById('cfg-default-all').checked;
  const message_template = document.getElementById('cfg-template').value;

  const res = await api('/global-config', {
    method: 'POST',
    body: { auto_send, default_to_all, message_template }
  });
  toast(res.message, res.code === 0 ? 'success' : 'error');
  if (res.code === 0) loadCloudConfig();
}

// ========== 服务管理 ==========
async function refreshServers() {
  const container = document.getElementById('server-cards');
  if (!container) return;
  container.innerHTML = '<div class="loading" style="text-align:center;padding:40px;">加载服务状态...</div>';

  const res = await api('/servers');
  if (res.code !== 0) {
    container.innerHTML = '<div style="color:#ff4d4f;text-align:center;padding:40px;">获取服务状态失败</div>';
    return;
  }

  const servers = res.data || [];
  let html = '';
  servers.forEach(s => {
    const isRunning = s.running;
    const statusColor = isRunning ? '#52c41a' : '#ff4d4f';
    const statusText = isRunning ? '🟢 运行中' : '🔴 已停止';
    const pidInfo = s.pid ? `PID: ${s.pid}` : '';
    const managedInfo = s.managed ? '(托管)' : '';

    html += '<div style="border:1px solid #e8e8e8;border-radius:8px;padding:20px;background:#fff;">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">';
    html += '<h3 style="margin:0;font-size:16px;">' + s.name + '</h3>';
    html += '<span style="font-size:14px;font-weight:600;color:' + statusColor + ';">' + statusText + '</span>';
    html += '</div>';
    html += '<div style="font-size:13px;color:#888;margin-bottom:16px;">';
    html += '端口: <code>' + s.port + '</code>';
    if (pidInfo) html += ' &nbsp;|&nbsp; ' + pidInfo;
    if (managedInfo) html += ' ' + managedInfo;
    html += '</div>';
    html += '<div style="display:flex;gap:8px;">';
    if (isRunning) {
      html += '<button class="btn btn-sm btn-outline" onclick="operateServer(\'' + s.key + '\',\'stop\')" style="color:#ff4d4f;border-color:#ff4d4f;">⏹ 停止</button>';
    } else {
      html += '<button class="btn btn-sm btn-primary" onclick="operateServer(\'' + s.key + '\',\'start\')">▶ 启动</button>';
    }
    html += '<button class="btn btn-sm btn-outline" onclick="openServerPage(' + s.port + ')">🌐 打开页面</button>';
    html += '</div></div>';
  });
  container.innerHTML = html;

  // 显示 python 配置
  const pyRes = await api('/servers/python-path');
  if (pyRes.code === 0 && pyRes.data) {
    document.getElementById('server-python-config').innerHTML =
      'Python: <code>' + escHtml(pyRes.data.python_path) + '</code><br>' +
      '项目根目录: <code>' + escHtml(pyRes.data.project_root) + '</code>';
  }
}

async function operateServer(key, action) {
  const actionText = action === 'start' ? '启动' : '停止';
  const res = await api('/servers/' + key + '/' + action, { method: 'POST' });
  toast(res.message, res.code === 0 ? 'success' : 'error');
  setTimeout(refreshServers, 1000);
}

function openServerPage(port) {
  window.open('http://localhost:' + port, '_blank');
}

async function loadServerLogs() {
  const res = await api('/servers/logs');
  const content = document.getElementById('server-log-content');
  if (res.code === 0 && res.data) {
    const lines = res.data.join('');
    content.textContent = lines || '(无日志)';
  } else {
    content.textContent = '(获取日志失败)';
  }
  openModal('server-log-modal');
}

// process tasks functions removed