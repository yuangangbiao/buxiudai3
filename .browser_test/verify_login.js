// 验证5001登录修复
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
  
  // 监听网络
  page.on('response', response => {
    if (response.url().includes('api/login') || response.url().includes('api/auth')) {
      console.log(`[网络] ${response.status()} ${response.url()}`);
    }
  });
  
  console.log('=== 访问5001登录页 ===');
  await page.goto('http://localhost:5001/login', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(2000);
  
  // 输入账号
  console.log('=== 输入账号: 苑岗彪 ===');
  await page.fill('#u', '苑岗彪');
  await page.waitForTimeout(500);
  
  // 点击登录
  console.log('=== 点击登录 ===');
  await page.click('#b');
  await page.waitForTimeout(3000);
  await page.waitForLoadState('networkidle');
  
  const finalUrl = page.url();
  const finalTitle = await page.title();
  const errMsg = await page.locator('#e').textContent().catch(() => '');
  
  console.log('\n=== 登录结果 ===');
  console.log(`URL: ${finalUrl}`);
  console.log(`标题: ${finalTitle}`);
  console.log(`错误信息: ${errMsg || '(无)'}`);
  
  await page.screenshot({ path: `${OUT}/fix_verify_login_${Date.now()}.png`, fullPage: true });
  console.log(`截图已保存: fix_verify_login_*.png`);
  
  await browser.close();
})().catch(e => {
  console.error('错误:', e.message);
  process.exit(1);
});
