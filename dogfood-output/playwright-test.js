const { chromium } = require('playwright');

const TEST_URLS = {
  desktop: 'http://localhost:5001',
  container: 'http://localhost:5002',
  dispatch: 'http://localhost:5003',
  workreport: 'http://localhost:5008'
};

async function runTests() {
  console.log('Starting Playwright UI Tests...');
  
  const browser = await chromium.launch({ headless: false });
  const results = { passed: 0, failed: 0, tests: [] };
  
  // Test 1: Desktop 5001
  console.log('\n=== Test 1: Desktop 5001 ===');
  try {
    const page = await browser.newPage();
    await page.goto(TEST_URLS.desktop, { timeout: 10000 });
    await page.waitForLoadState('networkidle');
    const title = await page.title();
    const status = await page.evaluate(() => document.readyState);
    results.passed++;
    results.tests.push({ name: 'Desktop 5001', status: 'PASS', details: `Title: ${title}, Ready: ${status}` });
    await page.screenshot({ path: 'd:\\yuan\\不锈钢网带跟单3.0\\dogfood-output\\test-5001-desktop.png', fullPage: true });
    console.log(`Desktop 5001: ${title}`);
    await page.close();
  } catch (e) {
    results.failed++;
    results.tests.push({ name: 'Desktop 5001', status: 'FAIL', details: e.message });
    console.log(`Desktop 5001: ${e.message}`);
  }
  
  // Test 2: Container 5002
  console.log('\n=== Test 2: Container 5002 ===');
  try {
    const page = await browser.newPage();
    await page.goto(TEST_URLS.container, { timeout: 10000 });
    await page.waitForLoadState('networkidle');
    const title = await page.title();
    results.passed++;
    results.tests.push({ name: 'Container 5002', status: 'PASS', details: `Title: ${title}` });
    await page.screenshot({ path: 'd:\\yuan\\不锈钢网带跟单3.0\\dogfood-output\\test-5002-container.png', fullPage: true });
    console.log(`Container 5002: ${title}`);
    await page.close();
  } catch (e) {
    results.failed++;
    results.tests.push({ name: 'Container 5002', status: 'FAIL', details: e.message });
    console.log(`Container 5002: ${e.message}`);
  }
  
  // Test 3: Dispatch 5003
  console.log('\n=== Test 3: Dispatch 5003 ===');
  try {
    const page = await browser.newPage();
    await page.goto(TEST_URLS.dispatch, { timeout: 10000 });
    await page.waitForLoadState('networkidle');
    const title = await page.title();
    results.passed++;
    results.tests.push({ name: 'Dispatch 5003', status: 'PASS', details: `Title: ${title}` });
    await page.screenshot({ path: 'd:\\yuan\\不锈钢网带跟单3.0\\dogfood-output\\test-5003-dispatch.png', fullPage: true });
    console.log(`Dispatch 5003: ${title}`);
    await page.close();
  } catch (e) {
    results.failed++;
    results.tests.push({ name: 'Dispatch 5003', status: 'FAIL', details: e.message });
    console.log(`Dispatch 5003: ${e.message}`);
  }
  
  // Test 4: WorkReport 5008
  console.log('\n=== Test 4: WorkReport 5008 ===');
  try {
    const page = await browser.newPage();
    await page.goto(TEST_URLS.workreport, { timeout: 10000 });
    await page.waitForLoadState('networkidle');
    const title = await page.title();
    results.passed++;
    results.tests.push({ name: 'WorkReport 5008', status: 'PASS', details: `Title: ${title}` });
    await page.screenshot({ path: 'd:\\yuan\\不锈钢网带跟单3.0\\dogfood-output\\test-5008-workreport.png', fullPage: true });
    console.log(`WorkReport 5008: ${title}`);
    await page.close();
  } catch (e) {
    results.failed++;
    results.tests.push({ name: 'WorkReport 5008', status: 'FAIL', details: e.message });
    console.log(`WorkReport 5008: ${e.message}`);
  }
  
  // Test 5: Login Flow Test
  console.log('\n=== Test 5: Login Flow 5008 ===');
  try {
    const page = await browser.newPage();
    await page.goto(TEST_URLS.workreport, { timeout: 10000 });
    await page.waitForLoadState('networkidle');
    
    // Try to find login form
    const hasLogin = await page.locator('input[name="name"], input[name="username"], input[type="text"]').count() > 0;
    if (hasLogin) {
      await page.fill('input[name="name"], input[name="username"], input[type="text"]', '微风细雨');
      const hasSubmit = await page.locator('button[type="submit"], button:has-text("登录")').count() > 0;
      if (hasSubmit) {
        await page.click('button[type="submit"], button:has-text("登录")');
        await page.waitForTimeout(2000);
      }
    }
    
    await page.waitForLoadState('networkidle');
    const title = await page.title();
    results.passed++;
    results.tests.push({ name: 'Login Flow 5008', status: 'PASS', details: `Title: ${title}` });
    await page.screenshot({ path: 'd:\\yuan\\不锈钢网带跟单3.0\\dogfood-output\\test-5008-login.png', fullPage: true });
    console.log(`Login Flow 5008: ${title}`);
    await page.close();
  } catch (e) {
    results.failed++;
    results.tests.push({ name: 'Login Flow 5008', status: 'FAIL', details: e.message });
    console.log(`Login Flow 5008: ${e.message}`);
  }
  
  await browser.close();
  
  // Print summary
  console.log('\n========================================');
  console.log('         TEST SUMMARY');
  console.log('========================================');
  console.log(`Total Tests: ${results.passed + results.failed}`);
  console.log(`Passed: ${results.passed}`);
  console.log(`Failed: ${results.failed}`);
  console.log('========================================');
  console.log('Screenshots saved to dogfood-output:');
  console.log('- test-5001-desktop.png');
  console.log('- test-5002-container.png');
  console.log('- test-5003-dispatch.png');
  console.log('- test-5008-workreport.png');
  console.log('- test-5008-login.png');
  console.log('========================================');
  
  return results;
}

runTests().catch(console.error);
