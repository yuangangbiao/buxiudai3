// 物料详情 - 强制窄视口
const { chromium } = require('playwright');
const OUT = 'd:/yuan/不锈钢网带跟单3.0/.shots';
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

(async () => {
  const browser = await chromium.launch({ executablePath: EDGE, headless: true, args: ['--no-sandbox'] });
  const ctx = await browser.newContext({
    viewport: { width: 380, height: 800 },
    deviceScaleFactor: 1,
    isMobile: true,
    hasTouch: true,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
  });
  const page = await ctx.newPage();

  await page.goto('http://localhost:5008', { waitUntil: 'networkidle' });
  await page.fill('#username', '苑岗彪');
  await page.click('button:has-text("登")');
  await page.waitForTimeout(2000);

  const apiResp = await page.evaluate(async () => {
    const r = await fetch('/api/tasks?page_route=material&page_size=20');
    const d = await r.json();
    return d.data.tasks.map(t => ({ id: t.id, status: t.status }));
  });

  for (const status of [...new Set(apiResp.map(t => t.status))]) {
    const task = apiResp.find(t => t.status === status);
    console.log(`测 ${status} (id=${task.id})`);
    await page.evaluate((id) => showMaterialDetail(id), task.id);
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${OUT}/06b_物料详情_${status}.png` });
    await page.evaluate(() => { try { closeMaterialDetail(); } catch(e){} });
    await page.waitForTimeout(500);
  }

  await browser.close();
  console.log('完成');
})();
