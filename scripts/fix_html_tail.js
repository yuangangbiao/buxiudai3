/**
 * 一次性处理 HTML 文件:
 * 1. 删除文件末尾的错位 Slide 9 内容
 * 2. 在末尾追加 Slide 12, 13, 14 + script + html close
 */
const fs = require('fs');
const path = require('path');

const HTML_PATH = 'd:\\yuan\\不锈钢网带跟单3.0\\docs\\演示视频_不锈钢3.0_客户演示.html';

let html = fs.readFileSync(HTML_PATH, 'utf-8');

const SLIDE_12 = `

<!-- Slide 12: 阶段 8-9 详解 (入库 → 发货) -->
<div class="stage">
  <div class="slide" data-slide="12">
    <div class="header">
      <div class="logo"><div class="logo-icon">📦</div><div class="logo-text">不锈钢 3.0 · 阶段 8-9 详解</div></div>
      <div class="slide-counter">12 / 14</div>
    </div>
    <div class="stage-content">
      <div class="stage-info">
        <div class="stage-badge">阶段 8-9 · 交付期</div>
        <div class="stage-title">成品入库 → 订单发货</div>
        <div class="stage-value">
          累计报工达标后系统自动判定入库,支持自动/手动两种方式。
          发货时<span style="color: var(--wechat); font-weight: 600;">客户企微自动收到发货通知</span>,
          <span style="color: var(--primary); font-weight: 600;">智能表格</span> 同步更新发货记录。
        </div>
        <div class="stage-features">
          <div class="stage-feature">自动入库判定</div>
          <div class="stage-feature">客户企微通知</div>
          <div class="stage-feature">智能表格更新</div>
          <div class="stage-feature">物流单号同步</div>
        </div>
      </div>
      <div class="stage-visual">
        <div class="flow-diagram">
          <div class="flow-node">
            <div class="flow-icon flow-icon-blue">📊</div>
            <div class="flow-text">
              <div class="flow-title">自动完成判定</div>
              <div class="flow-desc">completed_qty ≥ order_qty</div>
            </div>
          </div>
          <div class="flow-node">
            <div class="flow-icon flow-icon-green">✅</div>
            <div class="flow-text">
              <div class="flow-title">入库完成</div>
              <div class="flow-desc">📱 tmpl_warehousing</div>
            </div>
          </div>
          <div class="flow-node">
            <div class="flow-icon flow-icon-orange">🚚</div>
            <div class="flow-text">
              <div class="flow-title">仓库发货</div>
              <div class="flow-desc">订单状态 → 已发货</div>
            </div>
          </div>
          <div class="flow-node">
            <div class="flow-icon flow-icon-wechat">📱</div>
            <div class="flow-text">
              <div class="flow-title">客户企微通知</div>
              <div class="flow-desc">🤝 客户绑定收到发货</div>
            </div>
          </div>
          <div class="flow-node">
            <div class="flow-icon flow-icon-purple">📊</div>
            <div class="flow-text">
              <div class="flow-title">智能表格同步</div>
              <div class="flow-desc">📱 tmpl_shipment</div>
            </div>
          </div>
        </div>
        <div class="wechat-banner">
          <span class="hl">客户企微通知:</span>"🚚 您的订单 WG-2024-0815 已发货 / 顺丰单号:SF1234567890"
        </div>
      </div>
    </div>
  </div>
</div>
`;

const SLIDE_13 = `

<!-- Slide 13: 核心价值对比 -->
<div class="stage">
  <div class="slide" data-slide="13">
    <div class="header">
      <div class="logo"><div class="logo-icon">📈</div><div class="logo-text">不锈钢 3.0 · 核心价值</div></div>
      <div class="slide-counter">13 / 14</div>
    </div>
    <h2>用不锈钢 3.0 · 业务价值<span class="gradient-text">看得见</span></h2>
    <p class="subtitle">围绕「企业微信」生态,4 大核心解决方案带来的真实改变</p>
    <div class="value-grid">
      <div class="value-card">
        <div class="value-num">9</div>
        <div class="value-label">企微通知模板</div>
        <div class="value-desc">覆盖全流程 9 大业务节点</div>
      </div>
      <div class="value-card">
        <div class="value-num">4</div>
        <div class="value-label">端协同</div>
        <div class="value-desc">桌面/小程序/调度/企微</div>
      </div>
      <div class="value-card">
        <div class="value-num">80<span class="value-unit">%↓</span></div>
        <div class="value-label">客户咨询量</div>
        <div class="value-desc">企微绑定后客户不再问</div>
      </div>
      <div class="value-card">
        <div class="value-num">10<span class="value-unit">x</span></div>
        <div class="value-label">数据查询效率</div>
        <div class="value-desc">智能表格实时可视化</div>
      </div>
      <div class="value-card">
        <div class="value-num">4<span class="value-unit">h</span></div>
        <div class="value-label">异常发现提前</div>
        <div class="value-desc">车间大屏实时报警</div>
      </div>
    </div>
    <div class="value-section-title">📊 4 大功能效果对比</div>
    <div class="value-comparison">
      <div class="value-col old">
        <div class="value-col-head">❌ 传统模式</div>
        <div class="value-row"><span class="v1">客户咨询</span><span class="v2">销售反复答</span></div>
        <div class="value-row"><span class="v1">工序通知</span><span class="v2">5-8 通电话</span></div>
        <div class="value-row"><span class="v1">数据查询</span><span class="v2">翻 Excel</span></div>
        <div class="value-row"><span class="v1">异常发现</span><span class="v2">发货前</span></div>
      </div>
      <div class="value-arrow">→</div>
      <div class="value-col new">
        <div class="value-col-head">✅ 不锈钢 3.0</div>
        <div class="value-row"><span class="v1">客户咨询</span><span class="v2">企微自助</span></div>
        <div class="value-row"><span class="v1">工序通知</span><span class="v2">企微自动</span></div>
        <div class="value-row"><span class="v1">数据查询</span><span class="v2">智能表格</span></div>
        <div class="value-row"><span class="v1">异常发现</span><span class="v2">大屏实时</span></div>
      </div>
    </div>
  </div>
</div>
`;

const SLIDE_14 = `

<!-- Slide 14: CTA -->
<div class="stage">
  <div class="slide" data-slide="14">
    <div class="floating-orb orb-1" style="opacity: 0.3;"></div>
    <div class="floating-orb orb-2" style="opacity: 0.3;"></div>
    <div class="floating-orb orb-3" style="opacity: 0.2;"></div>
    <div class="cta-content">
      <div class="cta-title"><span class="wechat-text">企业微信全流程协同</span><br>让生产跟单更简单</div>
      <div class="cta-tagline">不锈钢网带跟单系统 v3.0 · 4 大核心解决方案 · 您的生产数字化伙伴</div>
      <div class="cta-points">
        <div class="cta-point">
          <div class="cta-point-icon">🔔</div>
          <div class="cta-point-title">企微智能通知</div>
          <div class="cta-point-desc">9 大模板 / 全流程自动触达</div>
        </div>
        <div class="cta-point">
          <div class="cta-point-icon">🤝</div>
          <div class="cta-point-title">客户生态绑定</div>
          <div class="cta-point-desc">客户扫码自助 / 订单透明</div>
        </div>
        <div class="cta-point">
          <div class="cta-point-icon">📊</div>
          <div class="cta-point-title">智能表格</div>
          <div class="cta-point-desc">数据实时可视化 / 多维分析</div>
        </div>
        <div class="cta-point">
          <div class="cta-point-icon">📺</div>
          <div class="cta-point-title">车间大屏</div>
          <div class="cta-point-desc">4K 大屏 / 实时数据 / 异常报警</div>
        </div>
      </div>
      <div class="cta-contact">
        <div class="cta-contact-title">📞 联系我们,预约现场演示</div>
        <div class="cta-contact-info">企业微信: <span class="hl">不锈钢网带跟单 3.0</span> · 演示预约通道已开启</div>
      </div>
    </div>
  </div>
</div>
`;

const SCRIPT_AND_CLOSE = `

<!-- 控制脚本 -->
<script>
  const slides = document.querySelectorAll('.slide');
  const progressBar = document.getElementById('progressBar');
  const urlParams = new URLSearchParams(window.location.search);
  const startParam = parseInt(urlParams.get('start') || '1', 10);
  let current = Math.max(0, Math.min(startParam - 1, slides.length - 1));

  function show(n) {
    slides.forEach((s, i) => s.classList.toggle('active', i === n));
    if (progressBar) progressBar.style.width = ((n + 1) / slides.length * 100) + '%';
  }
  function next() { current = (current + 1) % slides.length; show(current); }
  function prev() { current = (current - 1 + slides.length) % slides.length; show(current); }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') { e.preventDefault(); next(); }
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { e.preventDefault(); prev(); }
    else if (e.key === 'Home') { current = 0; show(current); }
    else if (e.key === 'End') { current = slides.length - 1; show(current); }
  });

  let autoTimer = null;
  document.addEventListener('dblclick', () => {
    if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
    else { autoTimer = setInterval(next, 12000); }
  });

  show(0);
</script>

</body>
</html>
`;

const DUPLICATE_HEADER = '    <div class="header">\n      <div class="logo"><div class="logo-icon">📋</div><div class="logo-text">不锈钢 3.0 · 阶段 1-3 详解</div></div>\n      <div class="slide-counter">09 / 14</div>\n    </div>';

// 找到第二个 DUPLICATE_HEADER 出现的位置(即错位 Slide 9 内容)
// 由于 Slide 9 真实 + 错位内容完全一样,删第一个会删错。
// 用更安全的方式:找 file 中第二次出现 DUPLICATE_HEADER 后,删到文件末尾。
let pos = 0;
let firstIdx = html.indexOf(DUPLICATE_HEADER, pos);
if (firstIdx === -1) { console.error('未找到 Slide 9 header'); process.exit(1); }
let secondIdx = html.indexOf(DUPLICATE_HEADER, firstIdx + DUPLICATE_HEADER.length);
if (secondIdx === -1) { console.error('未找到第二个 Slide 9 header (错位)'); process.exit(1); }

// 从 secondIdx 开始,删除到 file 末尾,替换为 Slide 12-14 + script + close
// 但要保留前面的 Slide 11 闭合标签
// 找到 secondIdx 之前最近的 </div> 闭合标签
let before = html.substring(0, secondIdx);
// 确保 before 末尾以 </div> 结尾(Slide 11 stage 闭合)
const trimmed = before.replace(/[\s\n]*$/, '');
const after = SLIDE_12 + SLIDE_13 + SLIDE_14 + SCRIPT_AND_CLOSE;

const newHtml = trimmed + '\n' + after;

fs.writeFileSync(HTML_PATH, newHtml, 'utf-8');
console.log('已删除错位 Slide 9 内容,追加 Slide 12-14 + script + close');
console.log('原文件大小:', html.length, '字符');
console.log('新文件大小:', newHtml.length, '字符');
