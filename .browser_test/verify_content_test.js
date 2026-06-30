// 深度UI功能测试 - 验证页面内容和功能
const { chromium } = require('playwright');
const fs = require('fs');

const OUT = 'd:/yuan/不锈钢网带跟单3.0/dogfood-output';
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });

const results = [];

async function verifyPage(name, url, checks) {
  const browser = await chromium.launch({
    executablePath: EDGE,
    headless: false,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1920, height: 1080 });
  
  const result = { name, url, checks: [], passed: 0, failed: 0 };
  
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    // 获取页面标题
    const title = await page.title();
    console.log(`\n[${name}]`);
    console.log(`  标题: ${title}`);
    result.title = title;
    
    // 执行检查
    for (const check of checks) {
      try {
        if (check.type === 'selector') {
          const element = await page.locator(check.selector).first();
          const exists = await element.count() > 0;
          if (exists && check.attribute) {
            const value = await element.getAttribute(check.attribute);
            const pass = check.expected ? value === check.expected : !!value;
            console.log(`  ${pass ? '✅' : '❌'} ${check.desc}: ${value || '(存在)'}`);
            result.checks.push({ desc: check.desc, pass });
            pass ? result.passed++ : result.failed++;
          } else if (exists) {
            console.log(`  ✅ ${check.desc} (元素存在)`);
            result.checks.push({ desc: check.desc, pass: true });
            result.passed++;
          } else {
            console.log(`  ❌ ${check.desc} (元素不存在)`);
            result.checks.push({ desc: check.desc, pass: false });
            result.failed++;
          }
        } else if (check.type === 'text') {
          const content = await page.content();
          const found = content.includes(check.text);
          console.log(`  ${found ? '✅' : '❌'} ${check.desc}`);
          result.checks.push({ desc: check.desc, pass: found });
          found ? result.passed++ : result.failed++;
        } else if (check.type === 'url') {
          const currentUrl = page.url();
          const match = currentUrl.includes(check.text);
          console.log(`  ${match ? '✅' : '❌'} ${check.desc}: ${currentUrl}`);
          result.checks.push({ desc: check.desc, pass: match });
          match ? result.passed++ : result.failed++;
        }
      } catch (e) {
        console.log(`  ❌ ${check.desc}: ${e.message}`);
        result.checks.push({ desc: check.desc, pass: false, error: e.message });
        result.failed++;
      }
    }
    
    // 截图
    const filename = `verify_${name.replace(/[^a-z0-9]/gi, '_')}_${Date.now()}.png`;
    await page.screenshot({ path: `${OUT}/${filename}`, fullPage: true });
    result.screenshot = filename;
    
  } catch (e) {
    console.log(`\n[${name}] ❌ 加载失败: ${e.message}`);
    result.error = e.message;
    result.failed++;
  }
  
  await browser.close();
  results.push(result);
  return result;
}

async function runTests() {
  console.log('========================================');
  console.log('  深度UI功能测试 - 验证页面内容');
  console.log('========================================\n');
  
  // ========== 桌面端5001测试 ==========
  console.log('\n【一、桌面端5001深度验证】');
  
  await verifyPage('5001_首页', 'http://localhost:5001', [
    { type: 'text', text: '订单', desc: '包含"订单"文字' },
    { type: 'text', text: '生产', desc: '包含"生产"文字' },
    { type: 'selector', selector: 'button, a, input', desc: '存在交互元素' }
  ]);
  
  await verifyPage('5001_订单', 'http://localhost:5001/orders', [
    { type: 'text', text: '订单', desc: '包含"订单"文字' },
    { type: 'text', text: '客户', desc: '包含"客户"文字' },
    { type: 'selector', selector: 'table, .table, [class*="table"]', desc: '存在表格' }
  ]);
  
  // ========== 容器中心5002测试 ==========
  console.log('\n【二、容器中心5002深度验证】');
  
  await verifyPage('5002_容器', 'http://localhost:5002/container', [
    { type: 'text', text: '容器', desc: '包含"容器"文字' },
    { type: 'text', text: 'container', desc: '包含"container"文字' },
    { type: 'selector', selector: 'button, a, .btn', desc: '存在按钮' }
  ]);
  
  await verifyPage('5002_库存', 'http://localhost:5002/inventory/dashboard', [
    { type: 'text', text: '库存', desc: '包含"库存"文字' },
    { type: 'text', text: 'inventory', desc: '包含"inventory"文字' },
    { type: 'selector', selector: 'table, .card, .dashboard', desc: '存在数据展示' }
  ]);
  
  await verifyPage('5002_质检', 'http://localhost:5002/quality', [
    { type: 'text', text: '质量', desc: '包含"质量"文字' },
    { type: 'text', text: '质检', desc: '包含"质检"文字' }
  ]);
  
  // ========== 调度中心5003测试 ==========
  console.log('\n【三、调度中心5003深度验证】');
  
  await verifyPage('5003_首页', 'http://localhost:5003', [
    { type: 'text', text: '调度', desc: '包含"调度"文字' },
    { type: 'text', text: 'dispatch', desc: '包含"dispatch"文字' },
    { type: 'selector', selector: 'nav, .sidebar, menu', desc: '存在导航' }
  ]);
  
  await verifyPage('5003_工序', 'http://localhost:5003/process', [
    { type: 'text', text: '工序', desc: '包含"工序"文字' },
    { type: 'text', text: 'process', desc: '包含"process"文字' }
  ]);
  
  // ========== 报工系统5008测试 ==========
  console.log('\n【四、报工系统5008深度验证】');
  
  await verifyPage('5008_登录', 'http://localhost:5008', [
    { type: 'text', text: '登录', desc: '包含"登录"文字' },
    { type: 'text', text: 'login', desc: '包含"login"文字' },
    { type: 'selector', selector: 'input', desc: '存在输入框' },
    { type: 'selector', selector: 'button', desc: '存在按钮' }
  ]);
  
  await verifyPage('5008_任务', 'http://localhost:5008/#/tasks', [
    { type: 'text', text: '任务', desc: '包含"任务"文字' },
    { type: 'text', text: 'task', desc: '包含"task"文字' }
  ]);
  
  // ========== 结果汇总 ==========
  console.log('\n========================================');
  console.log('         深度测试结果汇总');
  console.log('========================================\n');
  
  let totalPassed = 0, totalFailed = 0;
  
  for (const r of results) {
    console.log(`[${r.name}] ${r.title || '(无标题)'}`);
    if (r.error) {
      console.log(`  ❌ 加载失败: ${r.error}`);
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
  
  // 保存报告
  fs.writeFileSync(`${OUT}/deep_test_report.json`, JSON.stringify(results, null, 2));
  console.log(`\n详细报告: ${OUT}/deep_test_report.json`);
  
  return results;
}

runTests().catch(e => {
  console.error('测试失败:', e);
  process.exit(1);
});
