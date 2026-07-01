var BASE = window.location.origin
var browserPath = ''
var _browserTarget = 'storagePath'

function getToken() { return sessionStorage.getItem('admin_token') }
function setToken(t) { sessionStorage.setItem('admin_token', t) }
function clearToken() { sessionStorage.removeItem('admin_token') }

function api(url, options) {
  options = options || {}
  options.headers = options.headers || {}
  options.headers['X-Admin-Token'] = getToken() || ''
  if (!options.headers['Content-Type'] && options.body) {
    options.headers['Content-Type'] = 'application/json'
  }
  return fetch(url, options)
}

function fmtTime(ts) {
  var d = new Date(ts * 1000)
  var pad = function(n) { return String(n).padStart(2, '0') }
  return d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate()) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds())
}

function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')
}

function handleUnauthorized(resp) {
  if (resp.status === 401) {
    clearToken()
    showLogin()
    return true
  }
  return false
}

function showLogin() {
  document.getElementById('loginOverlay').style.display = 'flex'
  document.getElementById('mainContent').style.display = 'none'
  document.getElementById('loginPassword').value = ''
  document.getElementById('loginPassword').focus()
}

document.addEventListener('DOMContentLoaded', function() {
  document.getElementById('loginBtn').addEventListener('click', doLogin)
  document.getElementById('loginPassword').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') doLogin()
  })
})

function showMain() {
  document.getElementById('loginOverlay').style.display = 'none'
  document.getElementById('mainContent').style.display = 'block'
}

async function doLogin() {
  var username = document.getElementById('loginUsername').value.trim()
  var pwd = document.getElementById('loginPassword').value.trim()
  var btn = document.getElementById('loginBtn')
  var errEl = document.getElementById('loginError')
  if (!username) { errEl.textContent = '请输入用户名'; return }
  if (!pwd) { errEl.textContent = '请输入密码'; return }
  btn.disabled = true; btn.textContent = '验证中...'; errEl.textContent = ''
  try {
    var r = await fetch(BASE + '/face/api/admin/login', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({username: username, password: pwd})
    })
    var ret = await r.json()
    if (r.status === 200 && ret.success) {
      setToken(ret.token)
      errEl.textContent = ''
      showMain()
      loadConfig()
      loadServerRecords()
      refreshSchedulerStatus()
      loadEnrollments()
      loadAdminUsers()
    } else {
      errEl.textContent = ret.message || '登录失败'
    }
  } catch(e) {
    errEl.textContent = '网络错误: ' + e.message
  }
  btn.disabled = false; btn.textContent = '登录'
}

function doLogout() {
  clearToken()
  showLogin()
}

async function checkLogin() {
  var setupHint = document.getElementById('setupHint')
  var loginBtn = document.getElementById('loginBtn')
  try {
    var r = await fetch(BASE + '/face/api/admin/check')
    var ret = await r.json()
    if (ret.valid) {
      showMain()
      loadConfig()
      loadServerRecords()
      refreshSchedulerStatus()
      loadEnrollments()
      loadAdminUsers()
    } else if (ret.hasAdmin) {
      setupHint.style.display = 'none'
      loginBtn.textContent = '登录'
      showLogin()
    } else {
      setupHint.style.display = 'block'
      loginBtn.textContent = '登录'
      showLogin()
    }
  } catch(e) {
    showLogin()
    document.getElementById('loginError').textContent = '无法连接服务器: ' + e.message
  }
}

async function changePassword() {
  var oldPwd = document.getElementById('oldAdminPwd').value.trim()
  var newPwd = document.getElementById('newAdminPwd').value.trim()
  var confirmPwd = document.getElementById('confirmAdminPwd').value.trim()
  var statusEl = document.getElementById('pwdStatus')
  if (!newPwd || !confirmPwd) { statusEl.textContent = '请填写新密码和确认密码'; return }
  if (newPwd.length < 4) { statusEl.textContent = '密码长度至少4位'; return }
  if (newPwd !== confirmPwd) { statusEl.textContent = '两次密码输入不一致'; return }
  statusEl.textContent = '修改中...'
  try {
    var r = await api(BASE + '/face/api/admin/password', {
      method: 'PUT',
      body: JSON.stringify({oldPassword: oldPwd, newPassword: newPwd})
    })
    var ret = await r.json()
    if (handleUnauthorized(r)) return
    if (ret.success) {
      statusEl.textContent = '密码已更新'
      document.getElementById('oldAdminPwd').value = ''
      document.getElementById('newAdminPwd').value = ''
      document.getElementById('confirmAdminPwd').value = ''
    } else {
      statusEl.textContent = ret.message || '修改失败'
    }
  } catch(e) {
    statusEl.textContent = '网络错误: ' + e.message
  }
}

async function loadEnrollments() {
  var el = document.getElementById('enrollList')
  el.innerHTML = '<div class="record-empty">加载中...</div>'
  try {
    var r = await api(BASE + '/face/api/enrollments')
    if (handleUnauthorized(r)) return
    var list = await r.json()
    document.getElementById('enrollCount').textContent = list.length
    if (!list || list.length === 0) {
      el.innerHTML = '<div class="record-empty">暂无注册人员</div>'
      return
    }
    var html = ''
    for (var i = 0; i < list.length; i++) {
      var p = list[i]
      var dateStr = p.createdAt ? fmtTime(p.createdAt) : '--'
      html += '<div class="record-item">'
        + '<div class="record-no-photo" style="width:48px;height:48px;border-radius:6px;background:#0f172a;border:1px solid #334155;display:flex;align-items:center;justify-content:center;color:#475569;font-size:18px;flex-shrink:0">&#x1F464;</div>'
        + '<div class="record-info">'
        + '<div class="record-name">' + escapeHtml(p.name) + '</div>'
        + '<div class="record-meta"><span>注册时间: ' + dateStr + '</span></div>'
        + '</div>'
        + '<button class="btn-danger" onclick="deleteEnrollment(\'' + p.name.replace(/'/g,"\\'") + '\')" style="padding:6px 12px;border:none;border-radius:4px;cursor:pointer;font-size:12px;font-family:inherit">删除</button>'
        + '</div>'
    }
    el.innerHTML = html
  } catch(e) {
    el.innerHTML = '<div class="record-empty">加载失败: ' + escapeHtml(e.message) + '</div>'
  }
}

async function deleteEnrollment(name) {
  if (!confirm('确定要删除人员 "' + name + '" 吗？')) return
  try {
    var r = await api(BASE + '/face/api/enrollments?name=' + encodeURIComponent(name), {method: 'DELETE'})
    if (handleUnauthorized(r)) return
    var ret = await r.json()
    if (ret.success) {
      loadEnrollments()
    } else {
      alert(ret.message || '删除失败')
    }
  } catch(e) {
    alert('删除失败: ' + e.message)
  }
}

async function loadAdminUsers() {
  var el = document.getElementById('adminUserList')
  var countEl = document.getElementById('adminCount')
  var curEl = document.getElementById('currentAdmin')
  try {
    var r = await api(BASE + '/face/api/admin/users')
    if (handleUnauthorized(r)) return
    var ret = await r.json()
    var users = ret.users || []
    var current = ret.current || 'admin'
    countEl.textContent = users.length
    curEl.textContent = current
    if (users.length === 0) {
      el.innerHTML = '<div class="record-empty">暂无管理员</div>'
      return
    }
    var html = ''
    for (var i = 0; i < users.length; i++) {
      var u = users[i]
      var isSelf = u.username === current
      html += '<div class="record-item">'
        + '<div class="record-info">'
        + '<div class="record-name">' + escapeHtml(u.username) + (isSelf ? ' <span style="color:#60a5fa;font-size:11px">(当前)</span>' : '') + '</div>'
        + '</div>'
        + (isSelf ? ''
          : '<button class="btn-danger" onclick="deleteAdminUser(\'' + u.username.replace(/'/g,"\\'") + '\')" style="padding:6px 12px;border:none;border-radius:4px;cursor:pointer;font-size:12px;font-family:inherit">删除</button>')
        + '</div>'
    }
    el.innerHTML = html
  } catch(e) {
    el.innerHTML = '<div class="record-empty">加载失败</div>'
  }
}

async function createAdminUser() {
  var username = document.getElementById('newAdminUser').value.trim()
  var password = document.getElementById('newAdminPwd2').value.trim()
  var statusEl = document.getElementById('adminStatus')
  if (!username) { statusEl.textContent = '请输入用户名'; return }
  if (!password) { statusEl.textContent = '请输入密码'; return }
  if (password.length < 4) { statusEl.textContent = '密码至少4位'; return }
  statusEl.textContent = '创建中...'
  try {
    var r = await api(BASE + '/face/api/admin/users', {
      method: 'POST',
      body: JSON.stringify({username: username, password: password})
    })
    if (handleUnauthorized(r)) return
    var ret = await r.json()
    if (ret.success) {
      statusEl.textContent = '管理员已创建'
      document.getElementById('newAdminUser').value = ''
      document.getElementById('newAdminPwd2').value = ''
      loadAdminUsers()
    } else {
      statusEl.textContent = ret.message || '创建失败'
    }
  } catch(e) {
    statusEl.textContent = '创建失败: ' + e.message
  }
}

async function deleteAdminUser(username) {
  if (!confirm('确定要删除管理员 "' + username + '" 吗？')) return
  try {
    var r = await api(BASE + '/face/api/admin/users', {
      method: 'DELETE',
      body: JSON.stringify({username: username})
    })
    if (handleUnauthorized(r)) return
    var ret = await r.json()
    if (ret.success) {
      loadAdminUsers()
    } else {
      alert(ret.message || '删除失败')
    }
  } catch(e) {
    alert('删除失败: ' + e.message)
  }
}

async function loadConfig() {
  try {
    var r = await api(BASE + '/face/api/config')
    if (handleUnauthorized(r)) return
    var cfg = await r.json()
    document.getElementById('storagePath').value = cfg.storage_path || 'attendance'
    document.getElementById('exportPath').value = cfg.export_path || 'exports'
    document.getElementById('exportScheduleDay').value = cfg.export_schedule_day || 1
    document.getElementById('exportScheduleTime').value = cfg.export_schedule_time || '09:00'
    loadCloudConfig(cfg)
  } catch(e) {
    document.getElementById('configStatus').textContent = '加载配置失败'
  }
}

function loadCloudConfig(cfg) {
  var cloudUrl = document.getElementById('cloudUrl')
  var toggle = document.getElementById('cloudEnabledToggle')
  var label = document.getElementById('cloudEnabledLabel')
  cloudUrl.value = (cfg && cfg.cloud_url) || ''
  var enabled = cfg ? !!cfg.cloud_attendance_enabled : false
  toggle.checked = enabled
  label.textContent = enabled ? '开启' : '关闭'
}

async function saveCloudConfig() {
  var url = document.getElementById('cloudUrl').value.trim()
  var enabled = document.getElementById('cloudEnabledToggle').checked
  var statusEl = document.getElementById('cloudConfigStatus')
  statusEl.textContent = '保存中...'
  try {
    var r = await api(BASE + '/face/api/config', {
      method: 'PUT',
      body: JSON.stringify({cloud_url: url, cloud_attendance_enabled: enabled})
    })
    if (handleUnauthorized(r)) return
    var ret = await r.json()
    statusEl.textContent = ret.success ? '已保存' : '保存失败'
    if (ret.success) {
      document.getElementById('cloudEnabledLabel').textContent = enabled ? '开启' : '关闭'
    }
  } catch(e) {
    statusEl.textContent = '保存失败: ' + e.message
  }
}

async function sendAttendanceToCloud() {
  var btn = document.getElementById('sendToCloudBtn')
  btn.disabled = true
  btn.textContent = '发送中...'
  try {
    var r = await api(BASE + '/face/api/send-attendance-to-cloud', {
      method: 'POST',
      body: JSON.stringify({limit: 100})
    })
    if (handleUnauthorized(r)) return
    var ret = await r.json()
    if (ret.success) {
      btn.textContent = '发送完成'
      if (ret.count > 0) {
        alert('发送完成: ' + ret.message)
      } else {
        alert(ret.message || '无记录发送')
      }
    } else {
      btn.textContent = '发送失败'
      alert('发送失败: ' + (ret.message || '未知错误'))
    }
  } catch(e) {
    btn.textContent = '发送失败'
    alert('发送失败: ' + e.message)
  }
  setTimeout(function() {
    btn.disabled = false
    btn.textContent = '发送到云端'
  }, 3000)
}

async function saveConfig() {
  var path = document.getElementById('storagePath').value.trim()
  if (!path) { document.getElementById('configStatus').textContent = '路径不能为空'; return }
  try {
    var r = await api(BASE + '/face/api/config', {
      method: 'PUT',
      body: JSON.stringify({storage_path: path})
    })
    if (handleUnauthorized(r)) return
    var ret = await r.json()
    document.getElementById('configStatus').textContent = ret.success ? '已保存' : '保存失败'
  } catch(e) {
    document.getElementById('configStatus').textContent = '保存失败: ' + e.message
  }
}

function openBrowser(target) {
  document.getElementById('dirOverlay').classList.add('show')
  document.getElementById('newFolderName').value = ''
  browserPath = ''
  _browserTarget = target || 'storagePath'
  loadDrives()
}

function closeBrowser() {
  document.getElementById('dirOverlay').classList.remove('show')
  browserPath = ''
}

function loadDrives() {
  var el = document.getElementById('dirList')
  var bread = document.getElementById('dirBreadcrumb')
  bread.textContent = '选择磁盘...'
  el.innerHTML = '<div class="dir-empty">加载中...</div>'
  api(BASE + '/face/api/drives').then(function(r){if(handleUnauthorized(r))return Promise.reject('unauth');return r.json()}).then(function(drives) {
    if (!drives || !drives.length) {
      el.innerHTML = '<div class="dir-empty">未检测到磁盘</div>'
      return
    }
    var html = ''
    for (var i = 0; i < drives.length; i++) {
      html += '<div class="dir-item" data-path="' + drives[i].path.replace(/"/g,'&quot;') + '">'
        + '<span class="icon">&#x1F4BD;</span>'
        + '<span class="name">' + drives[i].name + ': (' + drives[i].path + ')</span>'
        + '</div>'
    }
    el.innerHTML = html
  }).catch(function(e) {
    if (e === 'unauth') return
    el.innerHTML = '<div class="dir-error">加载失败: ' + escapeHtml(e.message) + '</div>'
  })
}

function enterDir(path) {
  var el = document.getElementById('dirList')
  var bread = document.getElementById('dirBreadcrumb')
  browserPath = path
  var parts = path.replace(/\\\\/g,'/').split('/').filter(Boolean)
  var cum = ''
  var breadHtml = ''
  if (path.match(/^[A-Z]:/)) {
    breadHtml += '<span data-action="drives">磁盘</span>'
    cum = parts[0] + '/'
    breadHtml += ' / <span data-action="enter" data-path="' + cum.replace(/"/g,'&quot;') + '">' + parts[0] + '</span>'
    for (var i = 1; i < parts.length; i++) {
      cum += parts[i] + '/'
      breadHtml += ' / <span data-action="enter" data-path="' + cum.replace(/"/g,'&quot;') + '">' + parts[i] + '</span>'
    }
  } else {
    breadHtml = path
  }
  bread.innerHTML = breadHtml
  el.innerHTML = '<div class="dir-empty">加载中...</div>'
  api(BASE + '/face/api/list-dirs', {
    method: 'POST',
    body: JSON.stringify({path: path})
  }).then(function(r){if(handleUnauthorized(r))return Promise.reject('unauth');return r.json()}).then(function(data) {
    if (!data) return
    if (data.error) {
      el.innerHTML = '<div class="dir-error">' + escapeHtml(data.error) + '</div>'
      return
    }
    if (!data.dirs || data.dirs.length === 0) {
      el.innerHTML = '<div class="dir-empty">(空目录)</div>'
      return
    }
    var html = ''
    for (var i = 0; i < data.dirs.length; i++) {
      var d = data.dirs[i]
      var attrs = 'data-path="' + d.path.replace(/"/g,'&quot;') + '"'
      html += '<div class="dir-item" ' + attrs + '>'
        + '<span class="icon">&#x1F4C1;</span>'
        + '<span class="name">' + escapeHtml(d.name) + '</span>'
        + '<button class="select-btn" data-select>选择</button>'
        + '</div>'
    }
    el.innerHTML = html
  }).catch(function(e) {
    if (e === 'unauth') return
    el.innerHTML = '<div class="dir-error">加载失败: ' + escapeHtml(e.message) + '</div>'
  })
}

function selectDir(path) {
  document.getElementById(_browserTarget).value = path
  closeBrowser()
}

function pickCurrentDir() {
  if (!browserPath) return
  document.getElementById(_browserTarget).value = browserPath
  closeBrowser()
}

function createFolder() {
  var name = document.getElementById('newFolderName').value.trim()
  if (!name) return
  var btn = document.getElementById('createFolderBtn')
  btn.disabled = true; btn.textContent = '创建中...'
  api(BASE + '/face/api/create-dir', {
    method: 'POST',
    body: JSON.stringify({parent: browserPath, name: name})
  }).then(function(r){if(handleUnauthorized(r))return Promise.reject('unauth');return r.json().then(function(d){return {status:r.status,data:d}})}).then(function(res) {
    if (!res) return
    btn.disabled = false; btn.textContent = '新建'
    if (res.status === 200) {
      document.getElementById('newFolderName').value = ''
      enterDir(browserPath)
    } else {
      var msg = res.data.detail
      if (Array.isArray(msg)) msg = msg[0].msg
      alert(msg || '创建失败')
    }
  }).catch(function(e) {
    if (e === 'unauth') return
    btn.disabled = false; btn.textContent = '新建'
    alert('创建失败: ' + e.message)
  })
}

function saveExportConfig() {
  var path = document.getElementById('exportPath').value.trim()
  var day = parseInt(document.getElementById('exportScheduleDay').value) || 1
  var timeVal = document.getElementById('exportScheduleTime').value || '09:00'
  if (!path) { document.getElementById('exportConfigStatus').textContent = '路径不能为空'; return }
  api(BASE + '/face/api/config', {
    method: 'PUT',
    body: JSON.stringify({export_path: path, export_schedule_day: day, export_schedule_time: timeVal})
  }).then(function(r){if(handleUnauthorized(r))return;return r.json()}).then(function(ret) {
    if (!ret) return
    document.getElementById('exportConfigStatus').textContent = ret.success ? '已保存' : '保存失败'
  }).catch(function(e) {
    document.getElementById('exportConfigStatus').textContent = '保存失败: ' + e.message
  })
}

function toggleScheduler() {
  var btn = document.getElementById('schedToggleBtn')
  var statusEl = document.getElementById('schedActionStatus')
  var action = btn.textContent === '启动' ? 'start' : 'stop'
  statusEl.textContent = action === 'start' ? '启动中...' : '停止中...'
  api(BASE + '/face/api/scheduler', {
    method: 'POST',
    body: JSON.stringify({action: action})
  }).then(function(r){if(handleUnauthorized(r))return;return r.json()}).then(function(ret) {
    if (!ret) return
    if (ret.success) { refreshSchedulerStatus(); statusEl.textContent = '' }
    else { statusEl.textContent = ret.message || (action === 'start' ? '启动失败' : '停止失败') }
  }).catch(function(e) { statusEl.textContent = '请求失败: ' + e.message })
}

function manualExport() {
  var el = document.getElementById('schedActionStatus')
  el.textContent = '导出中...'
  api(BASE + '/face/api/export-checkins', {method:'POST'}).then(function(r){if(handleUnauthorized(r))return;return r.json()}).then(function(ret) {
    if (!ret) return
    if (ret.success) {
      el.textContent = '已导出 ' + ret.count + ' 条记录 -> ' + ret.file
      refreshSchedulerStatus()
    } else {
      el.textContent = ret.message || '导出失败'
    }
  }).catch(function(e) { el.textContent = '导出失败: ' + e.message })
}

function loadServerRecords() {
  var el = document.getElementById('serverRecordList')
  el.innerHTML = '<div class="record-empty">加载中...</div>'
  api(BASE + '/face/api/checkins?limit=500').then(function(r){if(handleUnauthorized(r))return Promise.reject('unauth');return r.json()}).then(function(list) {
    if (!list) return
    document.getElementById('serverCount').textContent = list.length
    if (list.length === 0) {
      el.innerHTML = '<div class="record-empty">暂无签到记录</div>'
      return
    }
    var html = ''
    for (var i = 0; i < list.length; i++) {
      var rec = list[i]
      var photoUrl = rec.photoPath ? BASE + '/face/api/photos/' + encodeURIComponent(rec.photoPath) : ''
      var photoHtml = photoUrl
        ? '<img src="' + photoUrl + '" alt="' + escapeHtml(rec.name) + '" />'
        : '<div class="record-no-photo">无</div>'
      html += '<div class="record-item">'
        + '<div class="record-photo">' + photoHtml + '</div>'
        + '<div class="record-info">'
        + '<div class="record-name">' + escapeHtml(rec.name) + '</div>'
        + '<div class="record-meta">'
        + '<span class="similarity">' + (rec.similarity ? (rec.similarity * 100).toFixed(1) + '%' : '--') + '</span>'
        + '<span>' + fmtTime(rec.time) + '</span>'
        + '</div></div></div>'
    }
    el.innerHTML = html
  }).catch(function(e) {
    if (e === 'unauth') return
    el.innerHTML = '<div class="record-empty">加载失败: ' + escapeHtml(e.message) + '</div>'
  })
}

function refreshSchedulerStatus() {
  api(BASE + '/face/api/scheduler').then(function(r){if(handleUnauthorized(r))return;return r.json()}).then(function(s) {
    if (!s) return
    var dot = document.getElementById('schedDot')
    var statusText = document.getElementById('schedStatusText')
    var badge = document.getElementById('schedulerBadge')
    var toggleBtn = document.getElementById('schedToggleBtn')
    if (s.running) {
      dot.className = 'stat-dot on'
      statusText.textContent = '运行中'
      badge.textContent = '运行中'
      toggleBtn.textContent = '停止'
      toggleBtn.className = 'btn-danger'
    } else {
      dot.className = 'stat-dot off'
      statusText.textContent = '已停止'
      badge.textContent = '已停止'
      toggleBtn.textContent = '启动'
      toggleBtn.className = 'btn-primary'
    }
    document.getElementById('schedLastExport').textContent = s.lastExport ? fmtTime(s.lastExport) : '--'
    document.getElementById('schedNextExport').textContent = s.nextExportDate || '--'
    document.getElementById('schedError').textContent = s.lastError || ''
  }).catch(function() {})
}

document.addEventListener('click', function(e) {
  var item = e.target.closest('.dir-item')
  if (item && document.getElementById('dirOverlay').classList.contains('show')) {
    var path = item.getAttribute('data-path')
    if (!path) return
    if (e.target.closest('[data-select]')) {
      selectDir(path)
    } else {
      enterDir(path)
    }
    return
  }
  var bc = e.target.closest('#dirBreadcrumb span')
  if (bc && document.getElementById('dirOverlay').classList.contains('show')) {
    var action = bc.getAttribute('data-action')
    if (action === 'drives') { loadDrives(); return }
    if (action === 'enter') {
      var p = bc.getAttribute('data-path')
      if (p) enterDir(p)
    }
  }
})

checkLogin()
