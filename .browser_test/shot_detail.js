// 物料详情截图（重试）
const { chromium } = require('playwright');
const OUT = 'd:/yuan/不锈钢网带跟单3.0/.shots';
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

(async () => {
  const browser = await chromium.launch({
    executablePath: EDGE, headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const ctx = await browser.newContext({
    viewport: { width: 480, height: 900 }, deviceScaleFactor: 2
  });
  const page = await ctx.newPage();

  await page.goto('http://localhost:5008', { waitUntil: 'networkidle' });
  await page.fill('#username', '苑岗彪');
  await page.click('button:has-text("登")');
  await page.waitForTimeout(2000);

  // 进入物料页
  await page.evaluate(() => showMaterial());
  await page.waitForTimeout(2000);

  // 找 .item-list (订单组) 并点击展开
  const groupCount = await page.locator('#material-list .item-list').count();
  console.log('订单组数:', groupCount);
  if (groupCount > 0) {
    await page.locator('#material-list .item-list').first().click();
    await page.waitForTimeout(800);
  }
  // 再点开具体物料卡
  const cardCount = await page.locator('#material-list .item-card').count();
  console.log('物料卡数:', cardCount);
  if (cardCount > 0) {
    await page.locator('#material-list .item-card').first().click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${OUT}/06_物料详情.png` });
    console.log('  截图: 06_物料详情.png');
  } else {
    console.log('无物料卡，可能订单组内为空');
    // 先看页面状态
    await page.screenshot({ path: `${OUT}/06_物料展开后.png` });
  }

  // 关闭弹窗，质检页
  await page.evaluate(() => { try { closeMaterialDetail(); } catch(e){} });
  await page.waitForTimeout(500);
  await page.evaluate(() => showQuality());
  await page.waitForTimeout(2000);
  // 找质检任务卡 (qi-list 里) - 可能在 .item-card / .item-list
  const qiCards = await page.locator('#qi-list .item-card, #qi-list .item-list, #qi-list [onclick]').count();
  console.log('质检任务卡数:', qiCards);
  if (qiCards > 0) {
    await page.locator('#qi-list .item-card, #qi-list .item-list, #qi-list [onclick]').first().click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${OUT}/07_质检表单.png` });
    console.log('  截图: 07_质检表单.png');
  } else {
    await page.screenshot({ path: `${OUT}/07_质检列表空.png` });
    console.log('  截图: 07_质检列表空.png');
  }

  // 关闭弹窗，工序任务详情
  await page.evaluate(() => { try { closeQualityInspectionModal && closeQualityInspectionModal(); } catch(e){} });
  await page.waitForTimeout(500);
  await page.evaluate(() => showProcessTasks());
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/08_工序任务列表.png` });
  console.log('  截图: 08_工序任务列表.png (备份)');

  await browser.close();
})();
