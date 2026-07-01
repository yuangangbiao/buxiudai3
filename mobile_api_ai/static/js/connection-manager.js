var _cfg = window.__CONN_CONFIG__ || {};
var CONN = window.CONN = {
    localHost: _cfg.localHost || '',
    localPort: _cfg.localPort || 0,
    cloudHost: _cfg.cloudHost || '',
    cloudPort: _cfg.cloudPort || 0,
    detectTimeout: _cfg.detectTimeout || 3000,
    mode: '',
    activeBase: ''
};

function apiUrl(path) {
    return (CONN.activeBase || '') + path;
}

function _isPrivateHost(host) {
    return /^(localhost|127\.|192\.168\.|10\.|172\.(1[6-9]|2\d|3[01])\.)/.test(host);
}

async function detectMode() {
    // 直接用当前页面地址作为 API 基础路径，不猜测 IP
    CONN.activeBase = window.location.origin;
    CONN.mode = _isPrivateHost(window.location.hostname) ? 'local' : 'cloud';
}

function switchMode(mode) {
    // 已废弃：用当前页面地址即可，无需手动切换
    CONN.mode = mode || CONN.mode;
    updateModeIndicator();
}

function updateModeIndicator() {
    const el = document.getElementById('mode-indicator');
    if (!el) return;
    el.style.display = 'block';
    if (CONN.mode === 'local') {
        el.innerHTML = '🟢 本地';
        el.className = 'mode-local';
        el.style.background = '#e8f5e9';
        el.style.color = '#2e7d32';
        el.style.borderColor = '#a5d6a7';
    } else {
        el.innerHTML = '☁️ 远程';
        el.className = 'mode-cloud';
        el.style.background = '#fff3e0';
        el.style.color = '#e65100';
        el.style.borderColor = '#ffcc80';
    }
}

const MODE_HTML = `
<div id="mode-indicator" class="mode-local" onclick="switchMode(CONN.mode==='local'?'cloud':'local')"
     title="点击切换模式" style="
        position:fixed; top:12px; right:12px; z-index:99999;
        padding:4px 14px; border-radius:12px; font-size:13px;
        cursor:pointer; user-select:none; font-weight:600;
        background:#e8f5e9; color:#2e7d32; border:1px solid #a5d6a7;
        box-shadow:0 1px 4px rgba(0,0,0,0.15);">
    ⏳ 检测中...
</div>`;

document.addEventListener('DOMContentLoaded', function() {
    const existing = document.getElementById('mode-indicator');
    if (!existing) {
        document.body.insertAdjacentHTML('beforeend', MODE_HTML);
    }
    detectMode().then(updateModeIndicator);
});
