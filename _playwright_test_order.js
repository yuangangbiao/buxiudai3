const { chromium } = require('playwright');

const TARGET_URL = 'http://localhost:5001';

(async () => {
  const browser = await chromium.launch({ headless: false, args: ['--no-sandbox'] });
  const context = await browser.newContext();
  const page = await context.newPage();

  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });

  console.log('=== 测试 /orders/new 页面 ===');
  await page.goto(`${TARGET_URL}/orders/new`);
  await page.waitForLoadState('networkidle');

  const title = await page.title();
  console.log('页面标题:', title);

  const navLinks = await page.locator('#appNav a').count();
  console.log('导航链接数:', navLinks);

  const productTypeSelect = await page.locator('#productType').count();
  console.log('产品类型选择器:', productTypeSelect ? '存在' : '不存在');

  const dimGrid = await page.locator('#dimGrid .param-item').count();
  console.log('尺寸参数字段数:', dimGrid);

  const matGrid = await page.locator('#matGrid .param-item').count();
  console.log('材质参数字段数:', matGrid);

  const sections = await page.locator('.section').count();
  console.log('折叠区块数:', sections);

  const bottomBar = await page.locator('.bottom-bar').count();
  console.log('底部操作栏:', bottomBar ? '存在' : '不存在');

  if (errors.length > 0) {
    console.log('\n控制台错误:');
    errors.forEach(e => console.log('  ERROR:', e));
  } else {
    console.log('\n无控制台错误');
  }

  console.log('\n=== 测试 /orders 页面（新建按钮）===');
  await page.goto(`${TARGET_URL}/orders`);
  await page.waitForLoadState('networkidle');
  const newBtn = await page.locator('button:has-text("新建订单")').count();
  console.log('新建订单按钮:', newBtn ? '存在' : '不存在');

  await page.screenshot({ path: 'D:/yuan/不锈钢网带跟单3.0/_order_new.png', fullPage: true });
  console.log('\n截图已保存到 _order_new.png');

  await browser.close();
  console.log('\n测试完成');
})().catch(e => { console.error('测试失败:', e); process.exit(1); });
