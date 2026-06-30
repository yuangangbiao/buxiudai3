// 物料详情 - 测试 4 种状态
const { chromium } = require('playwright');
const OUT = 'd:/yuan/不锈钢网带跟单3.0/.shots';
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

(async () => {
  const browser = await chromium.launch({ executablePath: EDGE, headless: true, args: ['--no-sandbox'] });
  const ctx = await browser.newContext({ viewport: { width: 480, height: 900 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();

  await page.goto('http://localhost:5008', { waitUntil: 'networkidle' });
  await page.fill('#username', '苑岗彪');
  await page.click('button:has-text("登")');
  await page.waitForTimeout(2000);

  // 取 4 个不同状态的物料 ID
  const apiResp = await page.evaluate(async () => {
    const r = await fetch('/api/tasks?page_route=material&page_size=20');
    const d = await r.json();
    return d.data.tasks.map(t => ({ id: t.id, status: t.status, data_type: t.data_type }));
  });
  console.log('物料任务列表:');
  for (const t of apiResp) console.log(`  ${t.id}  status=${t.status}  data_type=${t.data_type}`);

  // 直接调用 showMaterialDetail 弹窗
  const statesToTest = [...new Set(apiResp.map(t => t.status))];
  console.log('\n不同状态:', statesToTest);

  for (const status of statesToTest) {
    const task = apiResp.find(t => t.status === status);
    if (!task) continue;
    console.log(`\n=== 测状态 ${status} (id=${task.id}) ===`);
    await page.evaluate((id) => showMaterialDetail(id), task.id);
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${OUT}/06_物料详情_${status}.png` });
    console.log(`  截图: 06_物料详情_${status}.png`);
    // 关闭弹窗
    await page.evaluate(() => { try { closeMaterialDetail(); } catch(e){} });
    await page.waitForTimeout(500);
  }

  await browser.close();
})();
