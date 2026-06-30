// 登录后完整功能测试
const { chromium } = require('playwright');
const fs = require('fs');

const OUT = 'd:/yuan/不锈钢网带跟单3.0/dogfood-output';
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

const results = [];

// 正确的路由配置
const ROUTES = {
  5001: [
    { name: '5001_首页', url: 'http://localhost:5001/', expectText: '钢带跟单' },
    { name: '5001_订单', url: 'http://localhost:5001/orders', expectText: '订单' },
    { name: '5001_订单查询', url: 'http://localhost:5001/order-query', expectText: '订单' },
    { name: '5001_看板', url: 'http://localhost:5001/kanban', expectText: '看板' },
    { name: '5001_生产', url: 'http://localhost:5001/production', expectText: '生产' },
    { name: '5001_物料', url: 'http://localhost:5001/material', expectText: '物料' },
    { name: '5001_质检', url: 'http://localhost:5001/quality', expectText: '质量' },
    { name: '5001_仪表盘', url: 'http://localhost:5001/dashboard', expectText: '概览' },
    { name: '5001_报工', url: 'http://localhost:5001/work-reports', expectText: '报工' },
    { name: '5001_发货', url: 'http://localhost:5001/shipment', expectText: '发货' },
    { name: '5001_工序跟踪', url: 'http://localhost:5001/process-track', expectText: '工序' },
    { name: '5001_工序管理', url: 'http://localhost:5001/process-admin', expectText: '工序' },
    { name: '5001_操作员', url: 'http://localhost:5001/operators', expectText: '操作员' },
  ],
};

async function login(page, username) {
  await page.goto('http://localhost:5001/login', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(1000);
  
  // 填写用户名
  await page.fill('#u', username);
  await page.waitForTimeout(500);
  
  // 点击登录
  await page.click('#b');
  await page.waitForTimeout(3000);
  await page.waitForLoadState('networkidle');
}

async function testPage(page, name, url, expectText) {
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    const title = await page.title();
    const content = await page.content();
    const hasText = content.includes(expectText);
    const hasLogin = content.includes('请输入员工姓名');
    const isLoginPage = hasLogin && title.includes('登录');
    
    const filename = `logged_${name.replace(/[^a-z0-9]/gi, '_')}_${Date.now()}.png`;
    await page.screenshot({ path: `${OUT}/${filename}`, fullPage: true });
    
    if (isLoginPage) {
      return { name, status: '未登录', title, error: '页面跳转到登录页' };
    }
    
    if (hasText) {
      return { name, status: '通过', title, screenshot: filename };
    } else {
      return { name, status: '内容异常', title, error: `未找到关键字"${expectText}"`, screenshot: filename };
    }
  } catch (e) {
    return { name, status: '失败', error: e.message };
  }
}

async function runTests() {
  console.log('========================================');
  console.log('  登录后完整功能测试');
  console.log('  测试账号: 苑岗彪');
  console.log('========================================\n');
  
  const browser = await chromium.launch({
    executablePath: EDGE,
    headless: false,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1920, height: 1080 });
  
  // 登录
  console.log('【1. 登录】');
  await login(page, '苑岗彪');
  
  const currentUrl = page.url();
  const currentTitle = await page.title();
  console.log(`  登录后URL: ${currentUrl}`);
  console.log(`  登录后标题: ${currentTitle}`);
  
  // 截图登录后状态
  await page.screenshot({ path: `${OUT}/logged_main_${Date.now()}.png`, fullPage: true });
  console.log(`  截图: logged_main_*.png\n`);
  
  // 测试各页面
  let passed = 0, failed = 0, total = 0;
  
  console.log('【2. 业务页面测试】\n');
  
  for (const route of ROUTES[5001]) {
    total++;
    const result = await testPage(page, route.name, route.url, route.expectText);
    
    if (result.status === '通过') {
      passed++;
      console.log(`  ✅ ${route.name}: ${result.title}`);
    } else {
      failed++;
      console.log(`  ❌ ${route.name}: ${result.status} - ${result.error || result.title}`);
    }
    
    results.push(result);
  }
  
  await browser.close();
  
  // 汇总
  console.log('\n========================================');
  console.log('         测试结果汇总');
  console.log('========================================');
  console.log(`总测试数: ${total}`);
  console.log(`通过: ${passed} ✅`);
  console.log(`失败: ${failed} ❌`);
  console.log(`通过率: ${((passed / total) * 100).toFixed(1)}%`);
  console.log('========================================');
  
  // 保存报告
  fs.writeFileSync(`${OUT}/logged_test_report.json`, JSON.stringify({
    timestamp: new Date().toISOString(),
    loginUrl: currentUrl,
    loginTitle: currentTitle,
    summary: { total, passed, failed },
    results
  }, null, 2));
  
  console.log(`\n报告: ${OUT}/logged_test_report.json`);
  console.log(`截图: ${OUT}/logged_*.png`);
  
  return { total, passed, failed, results };
}

runTests().catch(e => {
  console.error('测试失败:', e);
  process.exit(1);
});
