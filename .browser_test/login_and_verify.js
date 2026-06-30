// 登录后深度UI功能测试
const { chromium } = require('playwright');
const fs = require('fs');

const OUT = 'd:/yuan/不锈钢网带跟单3.0/dogfood-output';
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });

const results = [];

async function testWithLogin(name, url, loginInfo, checks) {
  const browser = await chromium.launch({
    executablePath: EDGE,
    headless: false,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1920, height: 1080 });
  
  const result = { name, url, checks: [], passed: 0, failed: 0 };
  
  try {
    // 1. 访问登录页
    console.log(`\n[${name}] 访问页面...`);
    await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(1000);
    
    // 2. 检查是否需要登录
    const needLogin = await page.locator('input[type="text"], input[name="username"], input[name="name"]').count() > 0;
    
    if (needLogin && loginInfo) {
      console.log(`[${name}] 需要登录，输入账号...`);
      
      // 填写登录信息
      await page.fill('input[type="text"], input[name="username"], input[name="name"]', loginInfo.username);
      await page.waitForTimeout(500);
      
      // 点击登录按钮
      await page.click('button[type="submit"], button:has-text("登录"), button:has-text("确定")');
      await page.waitForTimeout(2000);
      await page.waitForLoadState('networkidle');
    }
    
    // 3. 获取页面信息
    const title = await page.title();
    const pageContent = await page.content();
    const currentUrl = page.url();
    
    console.log(`[${name}]`);
    console.log(`  标题: ${title}`);
    console.log(`  URL: ${currentUrl}`);
    result.title = title;
    result.url = currentUrl;
    
    // 4. 执行检查
    for (const check of checks) {
      try {
        let pass = false;
        let value = '';
        
        if (check.type === 'text') {
          pass = pageContent.includes(check.text);
          value = check.text;
        } else if (check.type === 'selector') {
          const count = await page.locator(check.selector).count();
          pass = count > 0;
          value = `元素数量: ${count}`;
        } else if (check.type === 'url') {
          pass = currentUrl.includes(check.text);
          value = currentUrl;
        }
        
        console.log(`  ${pass ? '✅' : '❌'} ${check.desc}: ${value}`);
        result.checks.push({ desc: check.desc, pass, value });
        pass ? result.passed++ : result.failed++;
      } catch (e) {
        console.log(`  ❌ ${check.desc}: ${e.message}`);
        result.checks.push({ desc: check.desc, pass: false, error: e.message });
        result.failed++;
      }
    }
    
    // 5. 截图
    const filename = `login_verify_${name.replace(/[^a-z0-9]/gi, '_')}_${Date.now()}.png`;
    await page.screenshot({ path: `${OUT}/${filename}`, fullPage: false });
    console.log(`  📸 截图: ${filename}`);
    result.screenshot = filename;
    
  } catch (e) {
    console.log(`[${name}] ❌ 错误: ${e.message}`);
    result.error = e.message;
    result.failed++;
  }
  
  await browser.close();
  results.push(result);
  return result;
}

async function runTests() {
  console.log('========================================');
  console.log('  登录后深度UI功能测试');
  console.log('  测试账号: 苑岗彪');
  console.log('========================================\n');
  
  const loginInfo = { username: '苑岗彪' };
  
  // ========== 桌面端5001测试 ==========
  console.log('\n【一、桌面端5001】');
  
  await testWithLogin('5001_首页', 'http://localhost:5001', loginInfo, [
    { type: 'text', text: '订单', desc: '包含"订单"' },
    { type: 'text', text: '生产', desc: '包含"生产"' },
    { type: 'selector', selector: 'nav, .sidebar, menu', desc: '存在导航菜单' },
    { type: 'selector', selector: 'button, a', desc: '存在按钮/链接' }
  ]);
  
  await testWithLogin('5001_订单列表', 'http://localhost:5001/orders', loginInfo, [
    { type: 'text', text: '订单', desc: '包含"订单"' },
    { type: 'selector', selector: 'table, [class*="table"]', desc: '存在数据表格' },
    { type: 'selector', selector: 'tbody, tr', desc: '存在数据行' }
  ]);
  
  await testWithLogin('5001_订单排产', 'http://localhost:5001/scheduling', loginInfo, [
    { type: 'text', text: '排产', desc: '包含"排产"' },
    { type: 'text', text: '工序', desc: '包含"工序"' }
  ]);
  
  // ========== 容器中心5002测试 ==========
  console.log('\n【二、容器中心5002】');
  
  await testWithLogin('5002_容器中心', 'http://localhost:5002/container', null, [
    { type: 'text', text: '容器', desc: '包含"容器"' },
    { type: 'selector', selector: 'nav, .menu, .sidebar', desc: '存在菜单' }
  ]);
  
  await testWithLogin('5002_库存仪表盘', 'http://localhost:5002/inventory/dashboard', null, [
    { type: 'text', text: '库存', desc: '包含"库存"' },
    { type: 'text', text: '仪表盘', desc: '包含"仪表盘"' }
  ]);
  
  await testWithLogin('5002_质检', 'http://localhost:5002/quality', null, [
    { type: 'text', text: '质量', desc: '包含"质量"' },
    { type: 'text', text: '质检', desc: '包含"质检"' }
  ]);
  
  // ========== 调度中心5003测试 ==========
  console.log('\n【三、调度中心5003】');
  
  await testWithLogin('5003_调度', 'http://localhost:5003/dispatch', null, [
    { type: 'text', text: '调度', desc: '包含"调度"' },
    { type: 'text', text: 'dispatch', desc: '包含"dispatch"' }
  ]);
  
  await testWithLogin('5003_工序', 'http://localhost:5003/process', null, [
    { type: 'text', text: '工序', desc: '包含"工序"' },
    { type: 'text', text: 'process', desc: '包含"process"' }
  ]);
  
  // ========== 报工系统5008测试 ==========
  console.log('\n【四、报工系统5008】');
  
  await testWithLogin('5008_首页', 'http://localhost:5008', loginInfo, [
    { type: 'text', text: '登录', desc: '包含"登录"' },
    { type: 'text', text: '报工', desc: '包含"报工"' },
    { type: 'selector', selector: 'input', desc: '存在输入框' }
  ]);
  
  await testWithLogin('5008_任务', 'http://localhost:5008/#/tasks', loginInfo, [
    { type: 'text', text: '任务', desc: '包含"任务"' },
    { type: 'text', text: 'task', desc: '包含"task"' }
  ]);
  
  // ========== 结果汇总 ==========
  console.log('\n========================================');
  console.log('         测试结果汇总');
  console.log('========================================\n');
  
  let totalPassed = 0, totalFailed = 0;
  
  for (const r of results) {
    console.log(`[${r.name}] ${r.title || '(无标题)'}`);
    if (r.error) {
      console.log(`  ❌ 错误: ${r.error}`);
    } else {
      for (const c of r.checks) {
        console.log(`  ${c.pass ? '✅' : '❌'} ${c.desc}`);
      }
      console.log(`  小计: ${r.passed}✅ ${r.failed}❌`);
    }
    totalPassed += r.passed;
    totalFailed += r.failed;
    console.log('');
  }
  
  console.log('========================================');
  console.log(`总检查项: ${totalPassed + totalFailed}`);
  console.log(`通过: ${totalPassed} ✅`);
  console.log(`失败: ${totalFailed} ❌`);
  console.log(`通过率: ${((totalPassed / (totalPassed + totalFailed)) * 100).toFixed(1)}%`);
  console.log('========================================');
  
  fs.writeFileSync(`${OUT}/login_verify_report.json`, JSON.stringify(results, null, 2));
  console.log(`\n详细报告: ${OUT}/login_verify_report.json`);
}

runTests().catch(e => {
  console.error('测试失败:', e);
  process.exit(1);
});
