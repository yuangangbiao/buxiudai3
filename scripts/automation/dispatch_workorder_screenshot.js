const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const TARGET_URL = process.env.DISPATCH_URL || 'http://localhost:5008/api/dispatch-center';
const OUTPUT_BASE = process.env.OUTPUT_DIR || 'd:/yuan/不锈钢网带跟单3.0/exports/workorder_screenshots';
const TIMESTAMP = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
const OUTPUT_DIR = path.join(OUTPUT_BASE, `session_${TIMESTAMP}`);

function ensureDir(dir) {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
}

function log(message, type = 'info') {
    const prefix = {
        'info': '📋',
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'progress': '🔄'
    }[type] || '📋';
    console.log(`${prefix} ${message}`);
}

async function waitForSelectorWithTimeout(page, selector, options = {}) {
    const { timeout = 10000, state = 'visible' } = options;
    try {
        await page.waitForSelector(selector, { state, timeout });
        return true;
    } catch (e) {
        log(`Selector not found: ${selector}`, 'warning');
        return false;
    }
}

async function scrollAndCaptureItems(page, containerSelector, itemSelector, outputSubDir, baseName, options = {}) {
    const { scrollDelay = 800, maxItems = 100, scrollAmount = 300 } = options;
    ensureDir(outputSubDir);
    const screenshots = [];

    try {
        const container = await page.$(containerSelector);
        if (!container) {
            log(`Container not found: ${containerSelector}`, 'warning');
            return screenshots;
        }

        const containerBox = await container.boundingBox();
        if (!containerBox) {
            log('Cannot get container bounding box', 'warning');
            return screenshots;
        }

        let lastHeight = 0;
        let currentHeight = 0;
        let scrollIteration = 0;
        const maxScrollIterations = 200;

        log(`Starting scroll capture in ${containerSelector}...`, 'progress');

        while (scrollIteration < maxScrollIterations) {
            const itemsInView = await page.evaluate((sel) => {
                const container = document.querySelector(sel);
                if (!container) return { items: [], scrollTop: 0, scrollHeight: 0 };

                const items = Array.from(container.querySelectorAll('[class*="task"], [class*="process"], [class*="step"], [class*="item"]'));
                const visibleItems = items.filter(item => {
                    const rect = item.getBoundingClientRect();
                    const containerRect = container.getBoundingClientRect();
                    return rect.top >= containerRect.top &&
                           rect.bottom <= containerRect.bottom &&
                           rect.height > 0;
                });

                return {
                    items: visibleItems.slice(0, 10).map(item => ({
                        className: item.className,
                        text: item.innerText?.substring(0, 100) || '',
                        rect: item.getBoundingClientRect()
                    })),
                    scrollTop: container.scrollTop,
                    scrollHeight: container.scrollHeight
                };
            }, containerSelector);

            if (itemsInView.items.length > 0) {
                const scrollTop = itemsInView.scrollTop;

                const filename = path.join(outputSubDir, `${baseName}_scroll_${String(scrollIteration).padStart(4, '0')}.png`);
                await page.screenshot({
                    path: filename,
                    type: 'png'
                });

                screenshots.push({
                    path: filename,
                    scrollPosition: scrollTop,
                    itemsCount: itemsInView.items.length,
                    iteration: scrollIteration
                });

                log(`Screenshot ${scrollingIteration + 1}: ${path.basename(filename)} (${itemsInView.items.length} items visible)`, 'info');
            }

            lastHeight = currentHeight;
            currentHeight = itemsInView.scrollHeight;

            const atBottom = itemsInView.scrollTop + containerBox.height >= itemsInView.scrollHeight - 50;

            if (atBottom && scrollIteration > 0) {
                log('Reached bottom of container', 'info');
                break;
            }

            await page.evaluate((sel, amount) => {
                const container = document.querySelector(sel);
                if (container) {
                    container.scrollBy(0, amount);
                }
            }, containerSelector, scrollAmount);

            await page.waitForTimeout(scrollDelay);
            scrollIteration++;
        }

        log(`Scroll capture complete: ${screenshots.length} screenshots`, 'success');

    } catch (e) {
        log(`Scroll capture error: ${e.message}`, 'error');
    }

    return screenshots;
}

async function clickAndScreenshotWorkorderDetail(page, workorderElement, outputDir, index) {
    const detailDir = path.join(outputDir, `workorder_${String(index).padStart(3, '0')}`);
    ensureDir(detailDir);

    try {
        await workorderElement.scrollIntoViewIfNeeded();
        await page.waitForTimeout(500);

        const overviewPath = path.join(detailDir, '00_overview.png');
        await workorderElement.screenshot({ path: overviewPath });
        log(`Workorder ${index} overview: ${path.basename(overviewPath)}`, 'info');

        const orderNo = await page.evaluate(el => {
            const text = el.innerText || '';
            const match = text.match(/WO[-\d]+|ORD[-\d]+|工单[：:]\s*([A-Z0-9-]+)/i);
            return match ? match[1] || match[0] : `order_${index}`;
        }, workorderElement);

        log(`Clicking workorder: ${orderNo}`, 'progress');

        await workorderElement.click();
        await page.waitForTimeout(2000);

        const modalSelectors = [
            '#schedule-detail-modal',
            '#workorder-detail-modal',
            '.modal.active',
            '[class*="detail-modal"]',
            '[class*="modal"]'
        ];

        let modalFound = false;
        for (const selector of modalSelectors) {
            if (await page.isVisible(selector)) {
                log(`Modal found: ${selector}`, 'success');
                modalFound = true;

                await page.waitForTimeout(1000);

                const modalFullPath = path.join(detailDir, '01_modal_full.png');
                await page.screenshot({ path: modalFullPath, fullPage: false });
                log(`Modal full screenshot: ${path.basename(modalFullPath)}`, 'success');

                const modalContentPath = path.join(detailDir, '02_modal_content.png');
                await page.screenshot({ path: modalContentPath, selector: selector });
                log(`Modal content screenshot: ${path.basename(modalContentPath)}`, 'success');

                const processSectionSelectors = [
                    '#process-list',
                    '#task-list',
                    '#process-tasks',
                    '[class*="process-list"]',
                    '[class*="task-list"]',
                    '[class*="step-list"]',
                    '#tab-processes',
                    '#tab-tasks'
                ];

                for (const sectionSelector of processSectionSelectors) {
                    const section = await page.$(sectionSelector);
                    if (section) {
                        log(`Scrolling process section: ${sectionSelector}`, 'progress');

                        const processDir = path.join(detailDir, 'processes');
                        await scrollAndCaptureItems(
                            page,
                            sectionSelector,
                            '[class*="task"], [class*="process"], [class*="step"], [class*="item"]',
                            processDir,
                            'process',
                            { scrollDelay: 600, maxItems: 100 }
                        );
                        break;
                    }
                }

                break;
            }
        }

        if (!modalFound) {
            log('No modal appeared, capturing current state', 'warning');
            const noModalPath = path.join(detailDir, 'no_modal_state.png');
            await page.screenshot({ path: noModalPath, fullPage: true });
        }

        await page.keyboard.press('Escape');
        await page.waitForTimeout(500);

        const closeButtons = await page.$$('button[class*="close"], [class*="close-btn"], [aria-label="close"]');
        for (const btn of closeButtons) {
            try {
                await btn.click();
                await page.waitForTimeout(300);
            } catch (e) {
            }
        }

        return {
            orderNo,
            detailDir,
            success: true
        };

    } catch (e) {
        log(`Error processing workorder ${index}: ${e.message}`, 'error');
        return {
            index,
            detailDir,
            success: false,
            error: e.message
        };
    }
}

async function main() {
    console.log('\n' + '='.repeat(70));
    console.log('🚀 调度中心工单详情截图自动化');
    console.log('='.repeat(70));
    console.log(`📍 目标URL: ${TARGET_URL}`);
    console.log(`📁 输出目录: ${OUTPUT_DIR}`);
    console.log('='.repeat(70) + '\n');

    ensureDir(OUTPUT_DIR);

    const browser = await chromium.launch({
        headless: false,
        args: [
            '--start-maximized',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox'
        ]
    });

    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 },
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    });

    const page = await context.newPage();

    const errors = [];
    page.on('console', msg => {
        if (msg.type() === 'error') {
            const text = msg.text();
            if (!text.includes('favicon')) {
                errors.push(`[Browser Error]: ${text}`);
            }
        }
    });

    page.on('pageerror', error => {
        errors.push(`[Page Error]: ${error.message}`);
    });

    try {
        log('Loading dispatch center page...', 'progress');
        await page.goto(TARGET_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);

        const title = await page.title();
        log(`Page loaded: ${title}`, 'success');

        const overviewPath = path.join(OUTPUT_DIR, '00_dispatch_center_overview.png');
        await page.screenshot({ path: overviewPath, fullPage: true });
        log(`Overview screenshot: ${overviewPath}`, 'success');

        log('Looking for Processes tab (流程编排)...', 'progress');
        const tabSelectors = [
            '[onclick*="switchTab(\'processes\')"]',
            '[onclick*="processes"]',
            '.sidebar-item:nth-child(5)',
            '.sidebar-item:has-text("流程")'
        ];

        let tabClicked = false;
        for (const selector of tabSelectors) {
            const tab = await page.$(selector);
            if (tab) {
                await tab.click();
                tabClicked = true;
                log(`Clicked tab using selector: ${selector}`, 'success');
                break;
            }
        }

        if (!tabClicked) {
            await page.evaluate(() => {
                const items = document.querySelectorAll('.sidebar-item');
                for (const item of items) {
                    if (item.innerText && item.innerText.includes('流程')) {
                        item.click();
                        return true;
                    }
                }
                return false;
            });
            log('Clicked tab using JavaScript evaluation', 'success');
        }

        await page.waitForTimeout(3000);

        const processesTabPath = path.join(OUTPUT_DIR, '01_processes_tab.png');
        await page.screenshot({ path: processesTabPath, fullPage: true });
        log(`Processes tab screenshot: ${processesTabPath}`, 'success');

        log('Waiting for process list to load...', 'progress');
        await page.waitForTimeout(2000);

        const listSelectors = [
            '#process-list',
            '#workorder-list',
            '#task-list',
            '[class*="process-list"]',
            '[class*="workorder"]',
            'table'
        ];

        let listContainer = null;
        for (const selector of listSelectors) {
            const el = await page.$(selector);
            if (el) {
                listContainer = el;
                log(`Found list container: ${selector}`, 'success');
                break;
            }
        }

        if (!listContainer) {
            log('No specific list container found, using page body', 'warning');
        }

        log('Extracting workorder items...', 'progress');
        const workorderItems = await page.evaluate(() => {
            const items = [];
            const selectors = [
                'tr[class*="workorder"]',
                'tr[class*="process"]',
                'tr[class*="task"]',
                '[class*="workorder-item"]',
                '[class*="process-item"]',
                '[class*="task-item"]',
                'tr[class*=""]',
                'table tbody tr',
                '.item',
                '.card'
            ];

            for (const sel of selectors) {
                const elements = document.querySelectorAll(sel);
                if (elements.length > 0) {
                    elements.forEach(el => {
                        if (el.innerText && el.innerText.length > 20) {
                            items.push({
                                tagName: el.tagName,
                                className: el.className,
                                textPreview: el.innerText.substring(0, 100)
                            });
                        }
                    });
                }
            }

            return {
                count: items.length,
                items: items.slice(0, 20)
            };
        });

        log(`Found ${workorderItems.count} potential workorder items`, 'info');

        const allItems = await page.$$('tr, .item, .card, [class*="item"]');
        log(`Found ${allItems.length} clickable elements in total`, 'info');

        log('\nStarting individual workorder detail screenshots...\n', 'progress');

        const maxWorkorders = Math.min(allItems.length, 50);
        const results = [];

        for (let i = 0; i < maxWorkorders; i++) {
            console.log(`\n${'─'.repeat(60)}`);
            log(`Processing item ${i + 1}/${maxWorkorders}`, 'progress');

            try {
                const item = allItems[i];
                if (!item) continue;

                const isVisible = await item.isVisible();
                if (!isVisible) {
                    log(`Item ${i + 1} not visible, skipping`, 'warning');
                    continue;
                }

                const result = await clickAndScreenshotWorkorderDetail(page, item, OUTPUT_DIR, i + 1);
                results.push(result);

                if (result.success) {
                    log(`Workorder ${i + 1} (${result.orderNo}) processed successfully`, 'success');
                } else {
                    log(`Workorder ${i + 1} processing failed: ${result.error}`, 'error');
                }

            } catch (e) {
                log(`Error on item ${i + 1}: ${e.message}`, 'error');
                results.push({
                    index: i + 1,
                    success: false,
                    error: e.message
                });
            }

            await page.waitForTimeout(500);
        }

        console.log(`\n${'='.repeat(70)}`);
        log('Generating summary report...', 'progress');

        const report = {
            timestamp: new Date().toISOString(),
            url: TARGET_URL,
            totalItemsFound: allItems.length,
            itemsProcessed: results.filter(r => r.success).length,
            itemsFailed: results.filter(r => !r.success).length,
            outputDirectory: OUTPUT_DIR,
            workorders: results,
            errors: errors
        };

        const reportPath = path.join(OUTPUT_DIR, 'report.json');
        fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
        log(`Report saved: ${reportPath}`, 'success');

        console.log('\n' + '='.repeat(70));
        log('Automation completed!', 'success');
        console.log('='.repeat(70));
        log(`Total items found: ${allItems.length}`, 'info');
        log(`Items processed: ${report.itemsProcessed}`, 'info');
        log(`Items failed: ${report.itemsFailed}`, 'info');
        log(`Total screenshots: ${report.itemsProcessed * 5 + 3} (approx)`, 'info');
        log(`Output directory: ${OUTPUT_DIR}`, 'info');
        console.log('='.repeat(70) + '\n');

        if (errors.length > 0) {
            log(`Browser/Page errors encountered: ${errors.length}`, 'warning');
            errors.slice(0, 5).forEach(err => console.log(`  - ${err}`));
        }

    } catch (e) {
        log(`Fatal error: ${e.message}`, 'error');
        const errorPath = path.join(OUTPUT_DIR, 'error_state.png');
        try {
            await page.screenshot({ path: errorPath, fullPage: true });
            log(`Error state screenshot: ${errorPath}`, 'info');
        } catch (screenshotError) {
            log(`Failed to capture error screenshot: ${screenshotError.message}`, 'error');
        }
    } finally {
        await browser.close();
        log('Browser closed.', 'info');
    }
}

main().catch(console.error);

process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});
