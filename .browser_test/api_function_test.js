// API级别功能测试 - 绕过登录
const { chromium } = require('playwright');
const fs = require('fs');

const OUT = 'd:/yuan/不锈钢网带跟单3.0/dogfood-output';
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

const results = [];

async function testAPI(name, method, url, body = null, headers = {}) {
  const startTime = Date.now();
  try {
    const options = {
      method,
      headers: { 'Content-Type': 'application/json', ...headers },
      timeout: 10000
    };
    if (body) options.body = JSON.stringify(body);
    
    const response = await fetch(url, options);
    const duration = Date.now() - startTime;
    const text = await response.text();
    
    let data = null;
    try {
      data = JSON.parse(text);
    } catch (e) {
      data = { raw: text.substring(0, 200) };
    }
    
    return {
      name, method, url,
      status: response.status,
      duration,
      success: response.status >= 200 && response.status < 400,
      data
    };
  } catch (e) {
    return {
      name, method, url,
      status: 0,
      duration: Date.now() - startTime,
      success: false,
      error: e.message
    };
  }
}

async function runTests() {
  console.log('========================================');
  console.log('  API级别功能测试');
  console.log('========================================\n');
  
  // ========== 5001 桌面端 API测试 ==========
  console.log('【一、桌面端5001 API】\n');
  
  // 健康检查
  let r = await testAPI('5001健康检查', 'GET', 'http://localhost:5001/health');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5001登录', 'POST', 'http://localhost:5001/api/login', { name: '苑岗彪' });
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} - ${r.data?.message || r.error || 'OK'}`);
  results.push(r);
  
  // 订单相关
  r = await testAPI('5001订单列表', 'GET', 'http://localhost:5001/api/orders/list');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5001未排产订单', 'GET', 'http://localhost:5001/api/orders/unscheduled');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5001产品类型', 'GET', 'http://localhost:5001/api/orders/product-types');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5001订单查询', 'GET', 'http://localhost:5001/api/orders/query');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5001总览', 'GET', 'http://localhost:5001/api/overview');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5001操作员', 'GET', 'http://localhost:5001/api/operators');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5001企业结构', 'GET', 'http://localhost:5001/api/enterprise/structure');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5001看板', 'GET', 'http://localhost:5001/api/kanban/list');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5001生产列表', 'GET', 'http://localhost:5001/api/production/list');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5001物料列表', 'GET', 'http://localhost:5001/api/material/list');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5001质检列表', 'GET', 'http://localhost:5001/api/quality/list');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5001仪表盘', 'GET', 'http://localhost:5001/api/dashboard/summary');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5001报工列表', 'GET', 'http://localhost:5001/api/work-reports/list');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5001发货列表', 'GET', 'http://localhost:5001/api/shipment/list');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5001工序列表', 'GET', 'http://localhost:5001/api/process/list');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5001操作员列表', 'GET', 'http://localhost:5001/api/operators/list');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  // ========== 5002 容器中心 API测试 ==========
  console.log('\n【二、容器中心5002 API】\n');
  
  r = await testAPI('5002健康检查', 'GET', 'http://localhost:5002/api/health');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5002仪表盘', 'GET', 'http://localhost:5002/api/dashboard');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5002操作员', 'GET', 'http://localhost:5002/api/operators');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5002工序名称', 'GET', 'http://localhost:5002/api/process_names');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5002部门', 'GET', 'http://localhost:5002/api/process_departments');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5002状态', 'GET', 'http://localhost:5002/api/status');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5002企业结构', 'GET', 'http://localhost:5002/api/enterprise/structure');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  // ========== 5003 调度中心 API测试 ==========
  console.log('\n【三、调度中心5003 API】\n');
  
  r = await testAPI('5003健康检查', 'GET', 'http://localhost:5003/health');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5003工单', 'GET', 'http://localhost:5003/workorder');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5003生产订单', 'GET', 'http://localhost:5003/production-orders');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5003外协', 'GET', 'http://localhost:5003/outsource-records');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5003报工记录', 'GET', 'http://localhost:5003/api/report_record/list');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5003质检记录', 'GET', 'http://localhost:5003/api/quality_record/list');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5003物料记录', 'GET', 'http://localhost:5003/api/material_record/list');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5003外协记录', 'GET', 'http://localhost:5003/api/outsource_record/list');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5003企业结构', 'GET', 'http://localhost:5003/api/enterprise/structure');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5003企业操作员', 'GET', 'http://localhost:5003/api/enterprise/operators');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  // ========== 5008 报工系统 API测试 ==========
  console.log('\n【四、报工系统5008 API】\n');
  
  r = await testAPI('5008健康检查', 'GET', 'http://localhost:5008/api/health');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5008首页', 'GET', 'http://localhost:5008/');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  r = await testAPI('5008登录页面', 'GET', 'http://localhost:5008/');
  console.log(`  ${r.success ? '✅' : '❌'} ${r.name}: ${r.status} (${r.duration}ms)`);
  results.push(r);
  
  // ========== 汇总 ==========
  console.log('\n========================================');
  console.log('         API测试结果汇总');
  console.log('========================================');
  
  const passed = results.filter(r => r.success).length;
  const failed = results.length - passed;
  
  console.log(`总测试数: ${results.length}`);
  console.log(`通过: ${passed} ✅`);
  console.log(`失败: ${failed} ❌`);
  console.log(`通过率: ${((passed / results.length) * 100).toFixed(1)}%`);
  console.log('========================================');
  
  // 按服务统计
  console.log('\n各服务通过率:');
  const services = {
    '5001': results.filter(r => r.name.startsWith('5001')),
    '5002': results.filter(r => r.name.startsWith('5002')),
    '5003': results.filter(r => r.name.startsWith('5003')),
    '5008': results.filter(r => r.name.startsWith('5008')),
  };
  
  for (const [svc, items] of Object.entries(services)) {
    if (items.length > 0) {
      const p = items.filter(r => r.success).length;
      console.log(`  ${svc}: ${p}/${items.length} (${((p / items.length) * 100).toFixed(1)}%)`);
    }
  }
  
  // 保存报告
  fs.writeFileSync(`${OUT}/api_function_test_report.json`, JSON.stringify({
    timestamp: new Date().toISOString(),
    summary: { total: results.length, passed, failed },
    services,
    results
  }, null, 2));
  
  console.log(`\n报告: ${OUT}/api_function_test_report.json`);
}

runTests().catch(e => {
  console.error('测试失败:', e);
  process.exit(1);
});
