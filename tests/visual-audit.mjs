import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { chromium } from '@playwright/test';

const url = process.env.AUDIT_URL || 'http://127.0.0.1:4174/little-wonder-lab/';
const output = path.resolve(process.env.AUDIT_DIR || 'test-results/visual');
await mkdir(output, { recursive: true });
const lessons = JSON.parse(await readFile(new URL('../src/data/lessons.json', import.meta.url), 'utf8'));
const browser = await chromium.launch({ headless: true });
const report = [];
try {
  for (const [name, width, height] of [['desktop', 1440, 1000], ['mobile', 390, 844], ['narrow', 320, 720]]) {
    const context = await browser.newContext({ viewport: { width, height }, reducedMotion: 'reduce', deviceScaleFactor: 1 });
    const page = await context.newPage();
    const errors = [];
    const outsideRequests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    page.on('request', request => { if (new URL(request.url()).origin !== new URL(url).origin) outsideRequests.push(request.url()); });
    for (const [route, label] of [['', 'explore'], ...lessons.map(lesson => [`#lesson/${lesson.id}`, lesson.id]), ['#request', 'request'], ['#lesson/does-not-exist', 'not-found']]) {
      const response = await page.goto(`${url}${route}`);
      if (response) assert.equal(response.status(), 200);
      await page.locator('h1').waitFor();
      assert.equal(await page.locator('h1').count(), 1);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${name}/${label}: horizontal overflow`);
      if (label === 'explore') {
        assert.equal(await page.locator('[data-lesson-link]').count(), lessons.length);
      }
      if (label === 'paper-bridge') {
        await page.getByRole('button', { name: 'Folded sides', exact: true }).click();
        await page.getByRole('button', { name: 'Place the spoon' }).click();
        await page.evaluate(() => scrollTo(0, 0));
      }
      const clippedIllustrationText = await page.locator('.art-wrap svg text').evaluateAll(elements => elements.filter(el => {
        const bounds = el.getBoundingClientRect();
        const frame = el.closest('.art-wrap').getBoundingClientRect();
        return bounds.left < frame.left || bounds.right > frame.right;
      }).map(el => el.textContent));
      if (clippedIllustrationText.length) report.push({ viewport: name, route, clippedIllustrationText });
      if (name !== 'narrow' && label !== 'not-found') {
        await page.evaluate(() => scrollTo(0, 0));
        const screenshot = path.join(output, `${label}-${name}.png`);
        await page.screenshot({ path: screenshot, fullPage: true });
        report.push({ viewport: name, route, screenshot });
      }
      await page.locator('.grown-up').evaluateAll(elements => elements.forEach(details => { details.open = true; }));
      const smallTargets = await page.locator('button:not(:disabled), a:not(.skip-link), input, select, summary').evaluateAll(elements => elements.filter(el => {
        const style = getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden' || !el.getClientRects().length) return false;
        if (el.closest('details:not([open])') && el.tagName !== 'SUMMARY') return false;
        const target = el.type === 'checkbox' ? el.closest('label') || el : el;
        const box = target.getBoundingClientRect();
        return box.width < 44 || box.height < 44;
      }).map(el => ({ text: (el.textContent || el.getAttribute('aria-label') || el.id).trim().slice(0, 60), tag: el.tagName, width: el.getBoundingClientRect().width, height: el.getBoundingClientRect().height })));
      if (smallTargets.length) report.push({ viewport: name, route, smallTargets });
      if (label === 'explore') {
        await page.keyboard.press('Tab');
        assert.equal(await page.evaluate(() => document.activeElement.textContent.trim()), 'Skip to content');
        await page.keyboard.press('Enter');
        assert.equal(await page.evaluate(() => document.activeElement.id), 'main');
      }
    }
    assert.deepEqual(errors, [], `${name}: console or runtime errors`);
    assert.deepEqual(outsideRequests, [], `${name}: unexpected third-party requests`);
    await context.close();
  }
} finally { await browser.close(); }
await writeFile(path.join(output, 'audit.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify({ lessonCount: lessons.length, viewportCount: 3, report }, null, 2));
assert.equal(report.filter(item => item.smallTargets).length, 0, 'Interactive controls must meet 44px target size');
assert.equal(report.filter(item => item.clippedIllustrationText).length, 0, 'Illustration annotations must not be cropped');
