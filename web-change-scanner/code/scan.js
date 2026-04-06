import { logger, endThis } from './sammaParser.js';
import * as storage from './storage.js';
import * as extractor from './extractor.js';
import * as differ from './differ.js';
import { chromium } from 'playwright';

async function main() {
  const target = process.env.TARGET;
  if (!target) {
    console.error('TARGET env var is required');
    process.exit(1);
  }

  const playwrightTimeout = parseInt(process.env.PLAYWRIGHT_TIMEOUT ?? '30000', 10);
  const playwrightWait = process.env.PLAYWRIGHT_WAIT ?? 'networkidle';

  const domain = new URL(target).hostname;

  const baseline = await storage.load(domain);

  const browser = await chromium.launch({ headless: true });
  let snapshot;
  try {
    const context = await browser.newContext();
    const page = await context.newPage();

    let response;
    try {
      response = await page.goto(target, {
        timeout: playwrightTimeout,
        waitUntil: playwrightWait,
      });
    } catch (err) {
      await logger({
        url: target,
        domain,
        category: 'error',
        change_type: 'scan_failed',
        old_value: null,
        new_value: err.message,
        type: 'WebChange',
      });
      await endThis();
      return;
    }

    snapshot = await extractor.extract(page, response);
  } finally {
    await browser.close();
  }

  if (!baseline) {
    try {
      await storage.save(domain, snapshot);
    } catch (err) {
      await logger({
        url: target,
        domain,
        category: 'error',
        change_type: 'baseline_save_failed',
        old_value: null,
        new_value: err.message,
        type: 'WebChange',
      });
    }

    await logger({
      url: target,
      domain,
      type: 'WebChangeBaseline',
      categories_captured: Object.keys(snapshot),
    });

    await endThis();
    return;
  }

  const findings = differ.compare(baseline, snapshot);
  for (const finding of findings) {
    await logger({ url: target, domain, type: 'WebChange', ...finding });
  }

  try {
    await storage.save(domain, snapshot);
  } catch (err) {
    await logger({
      url: target,
      domain,
      category: 'error',
      change_type: 'baseline_save_failed',
      old_value: null,
      new_value: err.message,
      type: 'WebChange',
    });
  }

  await endThis();
}

main().catch((err) => {
  console.error('Fatal:', err);
  process.exit(1);
});
