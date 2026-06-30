// 手机报工页面独立 Playwright 测试
const { chromium } = require('playwright');

const TARGET_URL = 'http://localhost:5008';
const SCREENSHOT_DIR = 'd:/yuan/不锈钢网带跟单3.0/logs';

async function testMobileAPI() {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.new_page();
    const results = {
        timestamp: new Date().toISOString(),
        tests: [],
        errors: []
    };

    try {
        console.log('='*60);
        console.log('手机报工页面 Playwright 测试');
        console.log('='*60);

        // 测试 1: 访问首页
        console.log('\n[测试 1] 访问首页...');
        await page.goto(TARGET_URL, { timeout: 10000 });
        await page.waitForLoadState('networkidle');
        const title = await page.title();
        console.log(`  页面标题: ${title}`);
        results.tests.push({ name: '首页访问', status: 'PASS', title });

        // 截图
        await page.screenshot({ path: `${SCREENSHOT_DIR}/01_home.png`, fullPage: true });
        console.log('  ✅ 首页截图已保存');

        // 测试 2: 检查页面元素
        console.log('\n[测试 2] 检查页面元素...');
        const elements = {
            '报工': await page.locator('text=报工').count(),
            '考勤': await page.locator('text=考勤').count(),
            '工单': await page.locator('text=工单').count(),
            '签到': await page.locator('text=签到').count()
        };

        for (const [name, count] of Object.entries(elements)) {
            const status = count > 0 ? '✅' : '❌';
            console.log(`  ${status} ${name}: ${count} 个`);
            results.tests.push({ name, count, status: count > 0 ? 'PASS' : 'FAIL' });
        }

        // 测试 3: 点击报工功能
        console.log('\n[测试 3] 测试报工功能...');
        try {
            const reportButtons = await page.locator('text=报工').all();
            if (reportButtons.length > 0) {
                await reportButtons[0].click();
                await page.waitForTimeout(2000);
                const url = page.url();
                console.log(`  ✅ 点击后 URL: ${url}`);
                await page.screenshot({ path: `${SCREENSHOT_DIR}/02_report.png`, fullPage: true });
                console.log('  ✅ 报工截图已保存');
                results.tests.push({ name: '报工功能', status: 'PASS', url });
            } else {
                console.log('  ❌ 未找到报工按钮');
                results.tests.push({ name: '报工功能', status: 'FAIL', reason: '按钮不可见' });
            }
        } catch (e) {
            console.log(`  ❌ 报工功能失败: ${e.message}`);
            results.errors.push({ test: '报工功能', error: e.message });
        }

        // 测试 4: 返回并测试考勤
        console.log('\n[测试 4] 测试考勤功能...');
        try {
            await page.goto(TARGET_URL, { timeout: 10000 });
            await page.waitForLoadState('networkidle');

            const attendanceButtons = await page.locator('text=考勤').all();
            if (attendanceButtons.length > 0) {
                await attendanceButtons[0].click();
                await page.waitForTimeout(2000);
                const url = page.url();
                console.log(`  ✅ 点击后 URL: ${url}`);
                await page.screenshot({ path: `${SCREENSHOT_DIR}/03_attendance.png`, fullPage: true });
                console.log('  ✅ 考勤截图已保存');
                results.tests.push({ name: '考勤功能', status: 'PASS', url });
            } else {
                console.log('  ❌ 未找到考勤按钮');
                results.tests.push({ name: '考勤功能', status: 'FAIL', reason: '按钮不可见' });
            }
        } catch (e) {
            console.log(`  ❌ 考勤功能失败: ${e.message}`);
            results.errors.push({ test: '考勤功能', error: e.message });
        }

        // 测试 5: 控制台错误检查
        console.log('\n[测试 5] 控制台错误检查...');
        const consoleErrors = [];
        page.on('console', msg => {
            if (msg.type() === 'error') {
                consoleErrors.push(msg.text());
            }
        });

        await page.goto(TARGET_URL, { timeout: 10000 });
        await page.waitForTimeout(3000);

        if (consoleErrors.length > 0) {
            console.log(`  ⚠️ 发现 ${consoleErrors.length} 个控制台错误:`);
            consoleErrors.slice(0, 5).forEach(e => console.log(`    - ${e}`));
            results.errors.push(...consoleErrors.slice(0, 5).map(e => ({ type: 'console', error: e })));
        } else {
            console.log('  ✅ 无控制台错误');
        }
        results.tests.push({ name: '控制台错误', errorCount: consoleErrors.length });

    } catch (e) {
        console.log(`\n❌ 测试异常: ${e.message}`);
        results.errors.push({ type: 'exception', error: e.message });
    } finally {
        await browser.close();
    }

    // 输出结果汇总
    console.log('\n' + '='*60);
    console.log('测试结果汇总');
    console.log('='*60);
    console.log(`测试时间: ${results.timestamp}`);
    console.log(`测试数量: ${results.tests.length}`);
    console.log(`错误数量: ${results.errors.length}`);

    const passed = results.tests.filter(t => t.status === 'PASS').length;
    const failed = results.tests.filter(t => t.status === 'FAIL').length;
    console.log(`通过: ${passed}, 失败: ${failed}`);

    if (results.errors.length > 0) {
        console.log('\n错误详情:');
        results.errors.forEach(e => console.log(`  - ${e.test || e.type}: ${e.error}`));
    }

    return results;
}

// 执行测试
testMobileAPI()
    .then(results => {
        console.log('\n✅ Playwright 测试完成!');
        process.exit(results.errors.length > 0 ? 1 : 0);
    })
    .catch(e => {
        console.error('❌ 测试失败:', e);
        process.exit(1);
    });
