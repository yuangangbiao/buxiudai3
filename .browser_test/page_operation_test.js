// 真实页面操作测试 - 点击、输入、提交
const { chromium } = require('playwright');
const fs = require('fs');

const OUT = 'd:/yuan/不锈钢网带跟单3.0/dogfood-output';
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

const results = [];

async function doLogin(page, baseUrl, username) {
  console.log(`  [登录] 访问 ${baseUrl}/login`);
  await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(2000);
  
  // 截图登录页
  await page.screenshot({ path: `${OUT}/op_login_page_${Date.now()}.png`, fullPage: true });
  
  // 5001桌面端登录
  if (baseUrl.includes('5001')) {
    console.log(`  [登录] 输入用户名: ${username}`);
    await page.fill('#u', username);
    await page.waitForTimeout(500);
    await page.click('#b');
  }
  // 5003调度中心登录
  else if (baseUrl.includes('5003')) {
    console.log(`  [登录] 输入用户名: ${username}`);
    await page.fill('#username', username);
    await page.waitForTimeout(500);
    await page.click('#loginBtn');
  }
  // 5008报工系统登录
  else if (baseUrl.includes('5008')) {
    console.log(`  [登录] 输入用户名: ${username}`);
    // 5008的登录可能用不同选择器
    const inputs = await page.locator('input[type="text"], input[name="name"], input[name="username"]').all();
    if (inputs.length > 0) {
      await inputs[0].fill(username);
      await page.waitForTimeout(500);
      const submitBtn = await page.locator('button[type="submit"], button:has-text("登录"), button:has-text("确定")').first();
      await submitBtn.click();
    }
  }
  
  await page.waitForTimeout(3000);
  await page.waitForLoadState('networkidle');
  
  const finalUrl = page.url();
  const finalTitle = await page.title();
  
  console.log(`  [登录] 完成后URL: ${finalUrl}`);
  console.log(`  [登录] 完成后标题: ${finalTitle}`);
  
  // 截图登录后状态
  await page.screenshot({ path: `${OUT}/op_after_login_${Date.now()}.png`, fullPage: true });
  
  return { url: finalUrl, title: finalTitle };
}

async function testClick(page, name, url, description) {
  console.log(`\n[${name}] ${description}`);
  console.log(`  URL: ${url}`);
  
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    const title = await page.title();
    const finalUrl = page.url();
    const content = await page.content();
    
    // 检查是否在登录页
    const isLoginPage = content.includes('请输入员工姓名') || content.includes('请输入您的真实姓名');
    
    if (isLoginPage) {
      console.log(`  ❌ 仍在登录页`);
      return { name, status: '未登录', url: finalUrl, title };
    }
    
    // 截图
    const filename = `op_${name.replace(/[^a-z0-9]/gi, '_')}_${Date.now()}.png`;
    await page.screenshot({ path: `${OUT}/${filename}`, fullPage: true });
    
    // 检查页面元素
    const buttons = await page.locator('button').count();
    const inputs = await page.locator('input').count();
    const links = await page.locator('a').count();
    
    console.log(`  ✅ 页面加载成功: ${title}`);
    console.log(`  📊 元素统计: ${buttons}个按钮, ${inputs}个输入框, ${links}个链接`);
    
    return { name, status: '通过', url: finalUrl, title, screenshot: filename, buttons, inputs, links };
  } catch (e) {
    console.log(`  ❌ 错误: ${e.message}`);
    return { name, status: '失败', error: e.message };
  }
}

async function testFormSubmit(page, name, url, formData) {
  console.log(`\n[${name}] 表单操作测试`);
  
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    // 查找表单
    const forms = await page.locator('form').count();
    console.log(`  找到表单: ${forms}`);
    
    if (forms === 0) {
      return { name, status: '无表单' };
    }
    
    // 截图前
    const filename1 = `op_form_before_${Date.now()}.png`;
    await page.screenshot({ path: `${OUT}/${filename1}`, fullPage: true });
    
    return { name, status: '有表单', forms };
  } catch (e) {
    return { name, status: '失败', error: e.message };
  }
}

async function runTests() {
  console.log('========================================');
  console.log('  真实页面操作测试');
  console.log('  测试账号: 苑岗彪');
  console.log('========================================\n');
  
  const browser = await chromium.launch({
    executablePath: EDGE,
    headless: false,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1920, height: 1080 });
  
  // 监听请求
  page.on('response', response => {
    if (response.url().includes('api/login') || response.url().includes('dispatch-center/login')) {
      console.log(`  [网络] ${response.status()} ${response.url()}`);
    }
  });
  
  // ========== 5001 桌面端测试 ==========
  console.log('\n【一、桌面端5001页面操作】');
  await doLogin(page, 'http://localhost:5001', '苑岗彪');
  
  // 业务页面测试
  const pages5001 = [
    { name: '5001_首页', url: 'http://localhost:5001/' },
    { name: '5001_订单', url: 'http://localhost:5001/orders' },
    { name: '5001_看板', url: 'http://localhost:5001/kanban' },
    { name: '5001_生产', url: 'http://localhost:5001/production' },
    { name: '5001_物料', url: 'http://localhost:5001/material' },
    { name: '5001_质检', url: 'http://localhost:5001/quality' },
    { name: '5001_仪表盘', url: 'http://localhost:5001/dashboard' },
  ];
  
  for (const p of pages5001) {
    const r = await testClick(page, p.name, p.url, '业务页面');
    results.push(r);
  }
  
  // ========== 5003 调度中心测试 ==========
  console.log('\n\n【二、调度中心5003页面操作】');
  await doLogin(page, 'http://localhost:5003/api/dispatch-center', '苑岗彪');
  
  const pages5003 = [
    { name: '5003_首页', url: 'http://localhost:5003/api/dispatch-center/' },
    { name: '5003_工单', url: 'http://localhost:5003/workorder' },
    { name: '5003_生产订单', url: 'http://localhost:5003/production-orders' },
  ];
  
  for (const p of pages5003) {
    const r = await testClick(page, p.name, p.url, '调度页面');
    results.push(r);
  }
  
  // ========== 5008 报工系统测试 ==========
  console.log('\n\n【三、报工系统5008页面操作】');
  
  const pages5008 = [
    { name: '5008_登录', url: 'http://localhost:5008/' },
    { name: '5008_首页', url: 'http://localhost:5008/#/home' },
    { name: '5008_任务', url: 'http://localhost:5008/#/tasks' },
  ];
  
  for (const p of pages5008) {
    const r = await testClick(page, p.name, p.url, '报工页面');
    results.push(r);
  }
  
  // ========== 5002 容器中心测试 ==========
  console.log('\n\n【四、容器中心5002页面操作】');
  
  const pages5002 = [
    { name: '5002_容器中心', url: 'http://localhost:5002/container/' },
    { name: '5002_库存仪表盘', url: 'http://localhost:5002/inventory/dashboard' },
  ];
  
  for (const p of pages5002) {
    const r = await testClick(page, p.name, p.url, '容器中心页面');
    results.push(r);
  }
  
  await browser.close();
  
  // 汇总
  console.log('\n\n========================================');
  console.log('         页面操作测试结果汇总');
  console.log('========================================');
  
  const passed = results.filter(r => r.status === '通过').length;
  const notLogged = results.filter(r => r.status === '未登录').length;
  const failed = results.filter(r => r.status === '失败').length;
  
  console.log(`总测试数: ${results.length}`);
  console.log(`通过: ${passed} ✅`);
  console.log(`未登录: ${notLogged} ⚠️`);
  console.log(`失败: ${failed} ❌`);
  console.log(`通过率: ${((passed / results.length) * 100).toFixed(1)}%`);
  console.log('========================================');
  
  // 保存报告
  fs.writeFileSync(`${OUT}/page_operation_test_report.json`, JSON.stringify({
    timestamp: new Date().toISOString(),
    summary: { total: results.length, passed, notLogged, failed },
    results
  }, null, 2));
  
  console.log(`\n报告: ${OUT}/page_operation_test_report.json`);
  console.log(`截图: ${OUT}/op_*.png`);
}

runTests().catch(e => {
  console.error('测试失败:', e);
  process.exit(1);
});
