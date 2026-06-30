// 4个服务器页面截图测试
const { chromium } = require('playwright');
const fs = require('fs');

const OUT = 'd:/yuan/不锈钢网带跟单3.0/dogfood-output';
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });

(async () => {
  console.log('启动 Edge...');
  const browser = await chromium.launch({
    executablePath: EDGE,
    headless: false,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const servers = [
    { name: '5001_desktop', url: 'http://localhost:5001' },
    { name: '5002_container', url: 'http://localhost:5002' },
    { name: '5003_dispatch', url: 'http://localhost:5003' },
    { name: '5008_workreport', url: 'http://localhost:5008' }
  ];
  
  const results = { passed: 0, failed: 0, tests: [] };
  
  for (const s of servers) {
    console.log(`\n[测试] ${s.name} - ${s.url}`);
    try {
      const page = await browser.newPage();
      await page.goto(s.url, { waitUntil: 'networkidle', timeout: 15000 });
      await page.waitForTimeout(1000);
      const filename = `${s.name}_${Date.now()}.png`;
      await page.screenshot({ path: `${OUT}/${s.name}.png`, fullPage: true });
      console.log(`  截图: ${s.name}.png`);
      results.passed++;
      results.tests.push({ name: s.name, status: 'PASS', screenshot: `${s.name}.png` });
      await page.close();
    } catch (e) {
      console.log(`  失败: ${e.message}`);
      results.failed++;
      results.tests.push({ name: s.name, status: 'FAIL', error: e.message });
    }
  }
  
  await browser.close();
  
  console.log('\n========================================');
  console.log('         测试结果');
  console.log('========================================');
  console.log(`通过: ${results.passed}`);
  console.log(`失败: ${results.failed}`);
  console.log('截图保存: dogfood-output/');
  console.log('========================================');
  
  return results;
})().catch(e => {
  console.error('测试失败:', e);
  process.exit(1);
});
