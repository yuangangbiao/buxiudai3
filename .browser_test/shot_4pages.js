// 5008 4 个任务页截图
const { chromium } = require('playwright');
const fs = require('fs');

const TARGET = 'http://localhost:5008';
const OUT = 'd:/yuan/不锈钢网带跟单3.0/.shots';
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });

(async () => {
  console.log('启动 Edge...');
  const browser = await chromium.launch({
    executablePath: EDGE,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const ctx = await browser.newContext({
    viewport: { width: 480, height: 900 },
    deviceScaleFactor: 2,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
  });
  const page = await ctx.newPage();

  console.log('[1] 打开登录页');
  await page.goto(TARGET, { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${OUT}/00_login.png`, fullPage: false });
  console.log('  截图: 00_login.png');

  console.log('[2] 登录 苑岗彪');
  await page.fill('#username', '苑岗彪');
  await page.click('button:has-text("登")');
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${OUT}/01_dashboard.png`, fullPage: false });
  console.log('  截图: 01_dashboard.png');

  // 4 个任务页
  const pages = [
    { name: '02_工序任务', func: 'showProcessTasks' },
    { name: '03_质检',     func: 'showQuality' },
    { name: '04_物料',     func: 'showMaterial' },
    { name: '05_外协',     func: 'showOutsource' },
  ];

  for (const p of pages) {
    console.log(`[3] ${p.name}`);
    try {
      await page.evaluate((fn) => {
        if (typeof window[fn] === 'function') window[fn]();
      }, p.func);
    } catch (e) {
      console.log(`  调用 ${p.func} 失败: ${e.message.slice(0,100)}`);
    }
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUT}/${p.name}.png`, fullPage: false });
    console.log(`  截图: ${p.name}.png`);
  }

  // 物料详情弹窗 (展示 4 步操作按钮)
  console.log('[4] 物料详情弹窗');
  try {
    await page.evaluate(() => showMaterial());
    await page.waitForTimeout(1000);
    // 找第一张卡
    const firstCard = await page.locator('#material-list .item-card').first();
    if (await firstCard.count() > 0) {
      await firstCard.click();
      await page.waitForTimeout(1500);
      await page.screenshot({ path: `${OUT}/06_物料详情.png`, fullPage: false });
      console.log('  截图: 06_物料详情.png');
    }
  } catch (e) {
    console.log('  物料详情: ' + e.message.slice(0, 100));
  }

  // 关闭弹窗 + 质检页
  console.log('[5] 质检页表单');
  try {
    await page.evaluate(() => { closeMaterialDetail && closeMaterialDetail(); });
    await page.waitForTimeout(500);
    // 从质检任务列表点开一个
    await page.evaluate(() => showQuality());
    await page.waitForTimeout(1500);
    const qiCard = await page.locator('#qi-list .item-card, #qi-list .item-list').first();
    if (await qiCard.count() > 0) {
      await qiCard.click();
      await page.waitForTimeout(1500);
      await page.screenshot({ path: `${OUT}/07_质检表单.png`, fullPage: false });
      console.log('  截图: 07_质检表单.png');
    } else {
      await page.screenshot({ path: `${OUT}/07_质检列表.png`, fullPage: false });
      console.log('  截图: 07_质检列表.png (无任务卡)');
    }
  } catch (e) {
    console.log('  质检: ' + e.message.slice(0, 100));
  }

  await browser.close();
  console.log('\n所有截图保存在: ' + OUT);
  console.log('文件列表:');
  fs.readdirSync(OUT).sort().forEach(f => {
    const stat = fs.statSync(`${OUT}/${f}`);
    console.log(`  ${f}  (${(stat.size/1024).toFixed(1)} KB)`);
  });
})();
