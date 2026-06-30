/**
 * 最终验证: 14 张幻灯片结构 + :has() 修复 + active 类 + 4 大功能关键词
 */
const fs = require('fs');
const path = require('path');

const HTML_PATH = 'd:\\yuan\\不锈钢网带跟单3.0\\docs\\演示视频_不锈钢3.0_客户演示.html';
const html = fs.readFileSync(HTML_PATH, 'utf-8');

const results = [];

// 1. 14 张幻灯片都在
const slideMatches = [...html.matchAll(/data-slide="(\d+)"/g)];
const slideNums = slideMatches.map(m => parseInt(m[1])).sort((a, b) => a - b);
const expected = Array.from({length: 14}, (_, i) => i + 1);
const slidesOk = JSON.stringify(slideNums) === JSON.stringify(expected);
results.push(['14 张幻灯片', slidesOk, slideNums.join(',')]);

// 2. 第一张是 active
const activeMatch = html.match(/<div class="slide slide-cover active" data-slide="1">/);
results.push(['默认 active slide=1', activeMatch !== null, '']);

// 3. :has() 修复保留
const hasFix = html.includes('.stage:has(> .slide.active)');
results.push(['.stage:has() 修复', hasFix, '']);

// 4. .stage 默认 display: none
const stageDefaultNone = /\.stage\s*\{[^}]*display:\s*none/.test(html);
results.push(['.stage 默认 display:none', stageDefaultNone, '']);

// 5. 4 大功能关键词都存在
const keywords = [
  ['企业微信智能通知', '主推 ①'],
  ['客户企微生态绑定', '主推 ②'],
  ['企业微信智能表格', '主推 ③'],
  ['车间生产大屏', '主推 ④'],
];
keywords.forEach(([kw, mark]) => {
  results.push([`${mark}: ${kw}`, html.includes(kw), '']);
});

// 6. 9 大通知模板
const templateCount = (html.match(/tmpl_/g) || []).length;
results.push(['9 大通知模板 (tmpl_*)', templateCount >= 9, `共 ${templateCount} 处`]);

// 7. 流程触点标签
const flowTags = ['🔔 企微通知', '🤝 客户绑定', '📊 智能表格', '📺 车间大屏'];
const tagCount = flowTags.filter(t => html.includes(t)).length;
results.push(['4 大功能触点标签', tagCount === 4, `${tagCount}/4`]);

// 8. script + html close
const hasScript = html.includes('<script>') && html.includes('</script>');
const hasBodyClose = html.includes('</body>');
const hasHtmlClose = html.includes('</html>');
results.push(['<script> + </script>', hasScript, '']);
results.push(['</body>', hasBodyClose, '']);
results.push(['</html>', hasHtmlClose, '']);

// 9. 文件大小
const sizeKB = (html.length / 1024).toFixed(1);
results.push(['文件大小 (KB)', true, sizeKB]);

// 输出
console.log('| 检查项 | 状态 | 详情 |');
console.log('|---|---|---|');
let pass = 0, fail = 0;
results.forEach(([item, ok, detail]) => {
  const icon = ok ? '✅' : '❌';
  console.log(`| ${icon} ${item} | ${ok ? 'PASS' : 'FAIL'} | ${detail} |`);
  if (ok) pass++; else fail++;
});
console.log('');
console.log(`总计: ${pass} PASS / ${fail} FAIL`);

process.exit(fail > 0 ? 1 : 0);
