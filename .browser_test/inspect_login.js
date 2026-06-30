// 登录后完整功能测试
const { chromium } = require('playwright');
const fs = require('fs');

const OUT = 'd:/yuan/不锈钢网带跟单3.0/dogfood-output';
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

(async () => {
  const browser = await chromium.launch({
    executablePath: EDGE,
    headless: false,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1920, height: 1080 });
  
  // 访问登录页
  await page.goto('http://localhost:5001/login', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(2000);
  
  // 获取页面HTML结构
  const html = await page.content();
  console.log('=== 登录页HTML结构（前2000字符）===');
  console.log(html.substring(0, 2000));
  
  // 查找所有input
  const inputs = await page.locator('input').all();
  console.log(`\n=== 找到 ${inputs.length} 个输入框 ===`);
  for (let i = 0; i < inputs.length; i++) {
    const name = await inputs[i].getAttribute('name');
    const type = await inputs[i].getAttribute('type');
    const id = await inputs[i].getAttribute('id');
    const placeholder = await inputs[i].getAttribute('placeholder');
    console.log(`  [${i}] name=${name}, type=${type}, id=${id}, placeholder=${placeholder}`);
  }
  
  // 查找所有按钮
  const buttons = await page.locator('button').all();
  console.log(`\n=== 找到 ${buttons.length} 个按钮 ===`);
  for (let i = 0; i < buttons.length; i++) {
    const text = await buttons[i].textContent();
    const type = await buttons[i].getAttribute('type');
    console.log(`  [${i}] text="${text}", type=${type}`);
  }
  
  // 查找表单
  const forms = await page.locator('form').all();
  console.log(`\n=== 找到 ${forms.length} 个表单 ===`);
  
  await page.screenshot({ path: `${OUT}/login_page_inspect.png`, fullPage: true });
  console.log('\n截图: login_page_inspect.png');
  
  await browser.close();
})().catch(e => {
  console.error('错误:', e.message);
  process.exit(1);
});
