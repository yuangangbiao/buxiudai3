// 不锈钢网带跟单系统3.0 - 完整UI功能测试 v2
// 使用正确的路由配置
const { chromium } = require('playwright');
const fs = require('fs');

const OUT = 'd:/yuan/不锈钢网带跟单3.0/dogfood-output';
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });

const results = [];

// 正确的路由配置
const ROUTES = {
  // 5001 桌面端
  5001: [
    { name: '5001_首页', url: 'http://localhost:5001/' },
    { name: '5001_登录', url: 'http://localhost:5001/login' },
    { name: '5001_订单', url: 'http://localhost:5001/orders' },
    { name: '5001_新建订单', url: 'http://localhost:5001/orders/new' },
    { name: '5001_订单查询', url: 'http://localhost:5001/order-query' },
    { name: '5001_看板', url: 'http://localhost:5001/kanban' },
    { name: '5001_生产', url: 'http://localhost:5001/production' },
    { name: '5001_物料', url: 'http://localhost:5001/material' },
    { name: '5001_质检', url: 'http://localhost:5001/quality' },
    { name: '5001_仪表盘', url: 'http://localhost:5001/dashboard' },
    { name: '5001_报工', url: 'http://localhost:5001/work-reports' },
    { name: '5001_发货', url: 'http://localhost:5001/shipment' },
    { name: '5001_工序跟踪', url: 'http://localhost:5001/process-track' },
    { name: '5001_工序管理', url: 'http://localhost:5001/process-admin' },
    { name: '5001_操作员', url: 'http://localhost:5001/operators' },
    { name: '5001_健康检查', url: 'http://localhost:5001/health' },
  ],
  // 5002 容器中心
  5002: [
    { name: '5002_容器中心', url: 'http://localhost:5002/container/' },
    { name: '5002_健康检查', url: 'http://localhost:5002/api/health' },
  ],
  // 5003 调度中心
  5003: [
    { name: '5003_调度中心', url: 'http://localhost:5003/api/dispatch-center/' },
    { name: '5003_工单', url: 'http://localhost:5003/workorder' },
    { name: '5003_生产订单', url: 'http://localhost:5003/production-orders' },
    { name: '5003_外协记录', url: 'http://localhost:5003/outsource-records' },
    { name: '5003_健康检查', url: 'http://localhost:5003/health' },
  ],
  // 5008 报工系统
  5008: [
    { name: '5008_登录', url: 'http://localhost:5008/' },
    { name: '5008_首页', url: 'http://localhost:5008/#/home' },
    { name: '5008_工序任务', url: 'http://localhost:5008/#/tasks' },
    { name: '5008_扫码报工', url: 'http://localhost:5008/#/scan' },
    { name: '5008_考勤', url: 'http://localhost:5008/#/attendance' },
    { name: '5008_健康检查', url: 'http://localhost:5008/api/health' },
  ],
};

async function testPage(name, url) {
  const browser = await chromium.launch({
    executablePath: EDGE,
    headless: false,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1920, height: 1080 });
  
  const result = { name, url, status: 'pending', title: '', checks: [] };
  
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 20000 });
    await page.waitForTimeout(2000);
    
    result.title = await page.title();
    result.status = 'PASS';
    result.checks.push({ desc: '页面加载成功', pass: true });
    
    // 截图
    const filename = `v2_${name.replace(/[^a-z0-9]/gi, '_')}_${Date.now()}.png`;
    await page.screenshot({ path: `${OUT}/${filename}`, fullPage: true });
    result.screenshot = filename;
    result.checks.push({ desc: '截图成功', pass: true });
    
  } catch (e) {
    result.status = 'FAIL';
    result.error = e.message;
    result.checks.push({ desc: '页面加载失败', pass: false, error: e.message });
  }
  
  await browser.close();
  return result;
}

async function runTests() {
  console.log('========================================');
  console.log('  不锈钢网带跟单系统3.0 UI测试 v2');
  console.log('  使用正确路由配置');
  console.log('========================================\n');
  
  let totalPassed = 0;
  let totalFailed = 0;
  
  // 测试5001桌面端
  console.log('\n【一、桌面端5001】');
  for (const route of ROUTES[5001]) {
    const result = await testPage(route.name, route.url);
    results.push(result);
    const icon = result.status === 'PASS' ? '✅' : '❌';
    console.log(`  ${icon} ${route.name}: ${result.title || result.error}`);
    if (result.status === 'PASS') totalPassed++;
    else totalFailed++;
  }
  
  // 测试5002容器中心
  console.log('\n【二、容器中心5002】');
  for (const route of ROUTES[5002]) {
    const result = await testPage(route.name, route.url);
    results.push(result);
    const icon = result.status === 'PASS' ? '✅' : '❌';
    console.log(`  ${icon} ${route.name}: ${result.title || result.error}`);
    if (result.status === 'PASS') totalPassed++;
    else totalFailed++;
  }
  
  // 测试5003调度中心
  console.log('\n【三、调度中心5003】');
  for (const route of ROUTES[5003]) {
    const result = await testPage(route.name, route.url);
    results.push(result);
    const icon = result.status === 'PASS' ? '✅' : '❌';
    console.log(`  ${icon} ${route.name}: ${result.title || result.error}`);
    if (result.status === 'PASS') totalPassed++;
    else totalFailed++;
  }
  
  // 测试5008报工系统
  console.log('\n【四、报工系统5008】');
  for (const route of ROUTES[5008]) {
    const result = await testPage(route.name, route.url);
    results.push(result);
    const icon = result.status === 'PASS' ? '✅' : '❌';
    console.log(`  ${icon} ${route.name}: ${result.title || result.error}`);
    if (result.status === 'PASS') totalPassed++;
    else totalFailed++;
  }
  
  // 汇总
  console.log('\n========================================');
  console.log('         测试结果汇总');
  console.log('========================================');
  console.log(`总测试数: ${totalPassed + totalFailed}`);
  console.log(`通过: ${totalPassed} ✅`);
  console.log(`失败: ${totalFailed} ❌`);
  console.log(`通过率: ${((totalPassed / (totalPassed + totalFailed)) * 100).toFixed(1)}%`);
  console.log('========================================');
  
  // 保存报告
  fs.writeFileSync(`${OUT}/ui_test_v2_report.json`, JSON.stringify({
    timestamp: new Date().toISOString(),
    summary: { total: totalPassed + totalFailed, passed: totalPassed, failed: totalFailed },
    results
  }, null, 2));
  
  console.log(`\n报告已保存: ${OUT}/ui_test_v2_report.json`);
  console.log(`截图已保存: ${OUT}/v2_*.png`);
  
  return { totalPassed, totalFailed, results };
}

runTests().catch(e => {
  console.error('测试失败:', e);
  process.exit(1);
});
