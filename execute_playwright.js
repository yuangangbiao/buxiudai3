// Playwright 测试执行器
const { spawn } = require('child_process');
const path = require('path');

const skillDir = 'C:/Users/lenovo/.trae-cn/skills/playwright-skill';
const testScript = path.join(process.cwd(), 'logs', 'playwright_mobile_test.js');

console.log('开始执行 Playwright 测试...');
console.log('测试脚本:', testScript);
console.log('Skill 目录:', skillDir);

const proc = spawn('node', ['run.js', testScript], {
    cwd: skillDir,
    stdio: ['inherit', 'inherit', 'pipe']
});

let stderr = '';
proc.stderr.on('data', data => {
    stderr += data.toString();
});

proc.on('close', code => {
    if (stderr) {
        console.error('stderr:', stderr);
    }
    console.log(`\n退出代码: ${code}`);
    process.exit(code);
});

proc.on('error', err => {
    console.error('启动失败:', err);
    process.exit(1);
});
