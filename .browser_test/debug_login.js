// 调试登录流程
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
  
  // 监听所有网络请求
  page.on('request', request => {
    if (request.url().includes('5001') || request.url().includes('5003')) {
      console.log(`[请求] ${request.method()} ${request.url()}`);
    }
  });
  
  page.on('response', response => {
    if (response.url().includes('5001') || response.url().includes('5003')) {
      console.log(`[响应] ${response.status()} ${response.url()}`);
    }
  });
  
  page.on('console', msg => {
    console.log(`[浏览器] ${msg.type()}: ${msg.text()}`);
  });
  
  // 访问登录页
  console.log('=== 访问登录页 ===');
  await page.goto('http://localhost:5001/login', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(2000);
  
  // 填写用户名
  console.log('\n=== 输入账号 ===');
  await page.fill('#u', '苑岗彪');
  await page.waitForTimeout(500);
  
  // 点击登录
  console.log('\n=== 点击登录 ===');
  await page.click('#b');
  await page.waitForTimeout(5000);
  
  const finalUrl = page.url();
  const finalTitle = await page.title();
  const errorMsg = await page.locator('#e').textContent().catch(() => '');
  
  console.log('\n=== 登录结果 ===');
  console.log(`URL: ${finalUrl}`);
  console.log(`标题: ${finalTitle}`);
  console.log(`错误信息: ${errorMsg || '(无)'}`);
  
  await page.screenshot({ path: `${OUT}/debug_login_${Date.now()}.png`, fullPage: true });
  
  await browser.close();
})().catch(e => {
  console.error('错误:', e.message);
  process.exit(1);
});
