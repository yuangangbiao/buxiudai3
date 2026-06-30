// 手机报工页面 Playwright 测试脚本
const { chromium } = require('playwright');

const TARGET_URL = 'http://localhost:5008';

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

        // 测试 2: 检查页面元素
        console.log('\n[测试 2] 检查页面元素...');
        const elements = {
            '报工按钮': await page.locator('text=报工').count(),
            '考勤按钮': await page.locator('text=考勤').count(),
            '工单按钮': await page.locator('text=工单').count(),
            '签到按钮': await page.locator('text=签到').count()
        };

        for (const [name, count] of Object.entries(elements)) {
            const status = count > 0 ? '✅' : '❌';
            console.log(`  ${status} ${name}: ${count} 个`);
            results.tests.push({ name, count, status: count > 0 ? 'PASS' : 'FAIL' });
        }

        // 测试 3: 点击报工按钮
        console.log('\n[测试 3] 测试报工功能...');
        try {
            const reportButton = page.locator('text=报工').first();
            if (await reportButton.isVisible()) {
                await reportButton.click();
                await page.waitForTimeout(2000);
                const url = page.url();
                console.log(`  ✅ 点击后 URL: ${url}`);
                results.tests.push({ name: '报工按钮点击', status: 'PASS', url });
            } else {
                console.log('  ❌ 报工按钮不可见');
                results.tests.push({ name: '报工按钮点击', status: 'FAIL', reason: '按钮不可见' });
            }
        } catch (e) {
            console.log(`  ❌ 报工按钮点击失败: ${e.message}`);
            results.errors.push({ test: '报工按钮点击', error: e.message });
        }

        // 测试 4: 返回首页并测试考勤
        console.log('\n[测试 4] 测试考勤功能...');
        try {
            await page.goto(TARGET_URL, { timeout: 10000 });
            await page.waitForLoadState('networkidle');

            const attendanceButton = page.locator('text=考勤').first();
            if (await attendanceButton.isVisible()) {
                await attendanceButton.click();
                await page.waitForTimeout(2000);
                const url = page.url();
                console.log(`  ✅ 点击后 URL: ${url}`);
                results.tests.push({ name: '考勤按钮点击', status: 'PASS', url });
            } else {
                console.log('  ❌ 考勤按钮不可见');
                results.tests.push({ name: '考勤按钮点击', status: 'FAIL', reason: '按钮不可见' });
            }
        } catch (e) {
            console.log(`  ❌ 考勤按钮点击失败: ${e.message}`);
            results.errors.push({ test: '考勤按钮点击', error: e.message });
        }

        // 测试 5: 检查控制台错误
        console.log('\n[测试 5] 检查控制台错误...');
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
            consoleErrors.forEach(e => console.log(`    - ${e}`));
            results.errors.push(...consoleErrors.map(e => ({ type: 'console', error: e })));
        } else {
            console.log('  ✅ 无控制台错误');
        }
        results.tests.push({ name: '控制台错误检查', errors: consoleErrors.length });

        // 截图保存
        console.log('\n[截图] 保存页面截图...');
        await page.screenshot({ path: 'd:/yuan/不锈钢网带跟单3.0/logs/playwright_test.png', fullPage: true });
        console.log('  ✅ 截图已保存到 logs/playwright_test.png');

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

    return results;
}

// 执行测试
testMobileAPI()
    .then(results => {
        console.log('\n测试完成!');
        process.exit(results.errors.length > 0 ? 1 : 0);
    })
    .catch(e => {
        console.error('测试失败:', e);
        process.exit(1);
    });
