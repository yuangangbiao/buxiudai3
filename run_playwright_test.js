// 运行 Playwright 测试
const { spawn } = require('child_process');
const path = require('path');

const testScript = path.join(__dirname, 'logs', 'playwright_mobile_test.js');
const skillDir = 'C:/Users/lenovo/.trae-cn/skills/playwright-skill';

const proc = spawn('node', [testScript], {
    cwd: skillDir,
    stdio: 'inherit'
});

proc.on('exit', code => {
    console.log(`\n测试进程退出，代码: ${code}`);
    process.exit(code);
});
