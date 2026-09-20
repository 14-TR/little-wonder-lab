import { test, expect } from './fixtures.js';
import { readFileSync } from 'node:fs';

const lessons = JSON.parse(readFileSync(new URL('../../src/data/lessons.json', import.meta.url), 'utf8'));

test('Cell Atlas is an optional external companion, not a tracked lesson', async ({ page }, testInfo) => {
  const outsideRequests = [];
  page.on('request', request => {
    if (new URL(request.url()).origin !== 'http://127.0.0.1:4173') outsideRequests.push(request.url());
  });
  await page.goto('./#explore');
  const companion = page.getByRole('region', { name: 'Cell Atlas' });
  await expect(companion).toBeVisible();
  await expect(companion).toContainText('Optional companion exploration');
  await expect(companion).toContainText('Pick two parts. What shapes do you notice?');
  await expect(companion).toContainText('Point, talk, or draw');
  await expect(companion).toContainText('generalized mammalian cell');
  await expect(companion).toContainText('false colors');
  await expect(companion).toContainText('not a microscope image');
  await expect(companion).toContainText('not every cell looks like this');
  await expect(companion).toContainText('not a full lesson');
  await expect(companion).toContainText('not saved in your explored marks');
  await expect(companion).toContainText('external site');
  await expect(companion).toContainText('Google Fonts');
  const link = companion.getByRole('link', { name: /Open Cell Atlas/ });
  await expect(link).toHaveAttribute('href', 'https://14-tr.github.io/cell-atlas/');
  await expect(link).toHaveAttribute('target', '_blank');
  await expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  await expect(link).toContainText('new tab');
  await expect(companion.getByRole('link', { name: /Source on GitHub/ })).toHaveAttribute('href', 'https://github.com/14-TR/cell-atlas');
  await expect(page.locator('[data-lesson-link]')).toHaveCount(lessons.length);
  await expect(page.locator('#catalog-count')).toContainText(`${lessons.length} investigations`);
  await expect(page.locator('#lesson-catalog')).not.toContainText('Cell Atlas');
  await expect(companion.locator('button, input, textarea, iframe, canvas')).toHaveCount(0);
  await expect(page.locator('iframe')).toHaveCount(0);
  await link.focus();
  await expect(link).toBeFocused();
  expect(await link.evaluate(el => getComputedStyle(el).outlineStyle)).not.toBe('none');
  for (const target of await companion.getByRole('link').all()) {
    const box = await target.boundingBox();
    expect(box.width).toBeGreaterThanOrEqual(44);
    expect(box.height).toBeGreaterThanOrEqual(44);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([]);
  expect(outsideRequests).toEqual([]);
  await companion.screenshot({ path: testInfo.outputPath('cell-atlas-companion.png') });
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({ path: testInfo.outputPath('explore-full.png'), fullPage: true });

  // Lesson-only filters must not add companions to lesson results or counts.
  await page.getByLabel('Search lessons').fill('Cell Atlas');
  await expect(page.locator('[data-lesson-link]')).toHaveCount(0);
  await expect(page.locator('#catalog-count')).toContainText('0 investigations');
  await expect(companion).toBeVisible();
  await page.getByRole('button', { name: 'Show all wonders' }).click();
  await expect(page.locator('[data-lesson-link]')).toHaveCount(lessons.length);
  await page.locator('[data-lesson-link="shadow-detective"]').click();
  await expect(page.getByRole('region', { name: 'Cell Atlas' })).toHaveCount(0);
});
