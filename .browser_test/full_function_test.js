// 不锈钢网带跟单系统3.0 完整UI功能测试
const { chromium } = require('playwright');
const fs = require('fs');

const OUT = 'd:/yuan/不锈钢网带跟单3.0/dogfood-output';
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });

const results = {
  total: 0,
  passed: 0,
  failed: 0,
  tests: []
};

async function testPage(name, url, options = {}) {
  const browser = await chromium.launch({
    executablePath: EDGE,
    headless: false,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  if (options.viewport) {
    await page.setViewportSize(options.viewport);
  }
  
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(1000);
    const filename = `${name.replace(/[^a-z0-9]/gi, '_')}_${Date.now()}.png`;
    await page.screenshot({ path: `${OUT}/${filename}`, fullPage: true });
    console.log(`  ✅ ${name}`);
    results.passed++;
    results.tests.push({ name, status: 'PASS', screenshot: filename });
  } catch (e) {
    console.log(`  ❌ ${name}: ${e.message}`);
    results.failed++;
    results.tests.push({ name, status: 'FAIL', error: e.message });
  }
  
  await browser.close();
  return results;
}

async function runTests() {
  console.log('========================================');
  console.log('  不锈钢网带跟单系统3.0 UI功能测试');
  console.log('========================================\n');
  
  const baseUrl = 'http://localhost:';
  
  // ========== 一、桌面端5001测试 ==========
  console.log('\n【一、桌面端5001】');
  
  console.log('\n1.1 登录测试');
  await testPage('5001_登录页', `${baseUrl}5001`, { viewport: { width: 1920, height: 1080 } });
  
  console.log('\n1.2 订单管理');
  await testPage('5001_订单列表', `${baseUrl}5001/orders`, { viewport: { width: 1920, height: 1080 } });
  
  console.log('\n1.3 订单排产');
  await testPage('5001_订单排产', `${baseUrl}5001/scheduling`, { viewport: { width: 1920, height: 1080 } });
  
  console.log('\n1.4 生产看板');
  await testPage('5001_生产看板', `${baseUrl}5001/dashboard`, { viewport: { width: 1920, height: 1080 } });
  
  // ========== 二、容器中心5002测试 ==========
  console.log('\n【二、容器中心5002】');
  
  console.log('\n2.1 容器中心首页');
  await testPage('5002_容器中心', `${baseUrl}5002/container`, { viewport: { width: 1920, height: 1080 } });
  
  console.log('\n2.2 库存管理');
  await testPage('5002_库存仪表盘', `${baseUrl}5002/inventory/dashboard`, { viewport: { width: 1920, height: 1080 } });
  await testPage('5002_入库管理', `${baseUrl}5002/inbound`, { viewport: { width: 1920, height: 1080 } });
  await testPage('5002_出库管理', `${baseUrl}5002/outbound`, { viewport: { width: 1920, height: 1080 } });
  
  console.log('\n2.3 质量管理');
  await testPage('5002_质检列表', `${baseUrl}5002/quality`, { viewport: { width: 1920, height: 1080 } });
  
  console.log('\n2.4 外协管理');
  await testPage('5002_外协列表', `${baseUrl}5002/outsource`, { viewport: { width: 1920, height: 1080 } });
  
  console.log('\n2.5 物料管理');
  await testPage('5002_物料列表', `${baseUrl}5002/material`, { viewport: { width: 1920, height: 1080 } });
  
  // ========== 三、调度中心5003测试 ==========
  console.log('\n【三、调度中心5003】');
  
  console.log('\n3.1 调度中心首页');
  await testPage('5003_调度中心', `${baseUrl}5003`, { viewport: { width: 1920, height: 1080 } });
  
  console.log('\n3.2 调度管理');
  await testPage('5003_调度管理', `${baseUrl}5003/dispatch`, { viewport: { width: 1920, height: 1080 } });
  
  console.log('\n3.3 工序管理');
  await testPage('5003_工序管理', `${baseUrl}5003/process`, { viewport: { width: 1920, height: 1080 } });
  
  console.log('\n3.4 任务管理');
  await testPage('5003_任务管理', `${baseUrl}5003/tasks`, { viewport: { width: 1920, height: 1080 } });
  
  console.log('\n3.5 流程管理');
  await testPage('5003_流程管理', `${baseUrl}5003/flow`, { viewport: { width: 1920, height: 1080 } });
  
  console.log('\n3.6 报表统计');
  await testPage('5003_报表统计', `${baseUrl}5003/reports`, { viewport: { width: 1920, height: 1080 } });
  
  console.log('\n3.7 企业架构');
  await testPage('5003_企业架构', `${baseUrl}5003/enterprise`, { viewport: { width: 1920, height: 1080 } });
  
  console.log('\n3.8 系统监控');
  await testPage('5003_系统监控', `${baseUrl}5003/monitor`, { viewport: { width: 1920, height: 1080 } });
  
  // ========== 四、报工系统5008测试 ==========
  console.log('\n【四、报工系统5008】');
  
  console.log('\n4.1 登录测试');
  await testPage('5008_登录页', `${baseUrl}5008`, { viewport: { width: 480, height: 900 } });
  
  console.log('\n4.2 移动端首页');
  await testPage('5008_首页', `${baseUrl}5008/#/home`, { viewport: { width: 480, height: 900 } });
  
  console.log('\n4.3 工序任务');
  await testPage('5008_工序任务', `${baseUrl}5008/#/tasks`, { viewport: { width: 480, height: 900 } });
  
  console.log('\n4.4 扫码报工');
  await testPage('5008_扫码报工', `${baseUrl}5008/#/scan`, { viewport: { width: 480, height: 900 } });
  
  console.log('\n4.5 考勤');
  await testPage('5008_考勤', `${baseUrl}5008/#/attendance`, { viewport: { width: 480, height: 900 } });
  
  console.log('\n4.6 质检');
  await testPage('5008_质检', `${baseUrl}5008/#/quality`, { viewport: { width: 480, height: 900 } });
  
  console.log('\n4.7 物料');
  await testPage('5008_物料', `${baseUrl}5008/#/material`, { viewport: { width: 480, height: 900 } });
  
  console.log('\n4.8 外协');
  await testPage('5008_外协', `${baseUrl}5008/#/outsource`, { viewport: { width: 480, height: 900 } });
  
  // ========== 五、API端点测试 ==========
  console.log('\n【五、API健康检查】');
  
  const apiEndpoints = [
    { name: '5001_健康检查', url: `${baseUrl}5001/health` },
    { name: '5002_健康检查', url: `${baseUrl}5002/api/health` },
    { name: '5003_健康检查', url: `${baseUrl}5003/health` },
    { name: '5008_健康检查', url: `${baseUrl}5008/api/health` }
  ];
  
  for (const api of apiEndpoints) {
    await testPage(api.name, api.url);
  }
  
  // ========== 结果汇总 ==========
  console.log('\n========================================');
  console.log('         测试结果汇总');
  console.log('========================================');
  console.log(`总测试数: ${results.passed + results.failed}`);
  console.log(`通过: ${results.passed} ✅`);
  console.log(`失败: ${results.failed} ❌`);
  console.log(`通过率: ${((results.passed / (results.passed + results.failed)) * 100).toFixed(1)}%`);
  console.log('========================================\n');
  
  // 保存详细报告
  const report = {
    timestamp: new Date().toISOString(),
    summary: {
      total: results.passed + results.failed,
      passed: results.passed,
      failed: results.failed,
      passRate: `${((results.passed / (results.passed + results.failed)) * 100).toFixed(1)}%`
    },
    tests: results.tests
  };
  
  fs.writeFileSync(`${OUT}/ui_test_report.json`, JSON.stringify(report, null, 2));
  console.log(`详细报告已保存: ${OUT}/ui_test_report.json`);
  
  return report;
}

runTests().catch(e => {
  console.error('测试失败:', e);
  process.exit(1);
});
