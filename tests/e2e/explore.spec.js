import { test, expect } from './fixtures.js';
import { readFileSync } from 'node:fs';

const lessons = JSON.parse(readFileSync(new URL('../../src/data/lessons.json', import.meta.url), 'utf8'));

test('Pattern Path catalog labels do not overlap the field-note folio', async ({ page }) => {
  for (const width of [1440, 1100, 390, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto('./#explore');
    const card = page.locator('[data-lesson-link="pattern-path"]');
    const folio = await card.locator('.folio').boundingBox();
    const label = await card.locator('svg text').first().boundingBox();
    expect(label.y, `AB label clears the folio at ${width}px`).toBeGreaterThanOrEqual(folio.y + folio.height + 4);
  }
});

test('Pattern Path stays readable from a narrow catalog to either repeat', async ({ page }) => {
  for (const width of [320, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('./#explore');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `catalog at ${width}`).toBe(true);
    await page.getByRole('button', { name: 'Math', exact: true }).click();
    const card = page.locator('[data-lesson-link="pattern-path"]');
    const art = await card.locator('svg').boundingBox();
    const wrap = await card.locator('.art-wrap').boundingBox();
    expect(art.x).toBeGreaterThanOrEqual(wrap.x);
    expect(art.x + art.width).toBeLessThanOrEqual(wrap.x + wrap.width);
    await card.click();
    for (const mode of ['AB', 'AAB']) {
      await page.getByRole('button', { name: mode, exact: true }).click();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${mode} at ${width}`).toBe(true);
      for (const button of await page.locator('.interactive button').all()) {
        const box = await button.boundingBox();
        expect(box.width).toBeGreaterThanOrEqual(44);
        expect(box.height).toBeGreaterThanOrEqual(44);
        expect(box.x).toBeGreaterThanOrEqual(0);
        expect(box.x + box.width).toBeLessThanOrEqual(width);
      }
      const tiles = await page.locator('.pattern-tile').evaluateAll(elements => elements.map(element => ({ width: element.clientWidth, scroll: element.scrollWidth })));
      expect(tiles.every(tile => tile.width >= tile.scroll)).toBe(true);
    }
  }
});

test('explore is an illustrated catalog with usable lesson routes', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('./');
  await expect(page.getByRole('heading', { name: 'Follow your what if.' })).toBeVisible();
  await expect(page.locator('[data-lesson-link]')).toHaveCount(lessons.length);
  await expect(page.locator('[data-lesson-link] svg')).toHaveCount(lessons.length);
  await page.locator('[data-lesson-link="shadow-detective"]').click();
  await expect(page).toHaveURL(/#lesson\/shadow-detective$/);
  await expect(page.getByRole('heading', { name: lessons.find(l => l.id === 'shadow-detective').title, exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Gather your things' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Try it in your world' })).toBeVisible();
  await page.getByRole('link', { name: 'Back to explore' }).click();
  await expect(page.getByRole('heading', { name: 'Follow your what if.' })).toBeVisible();
  expect(errors).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('new notes, topic filters, search and reset remain usable as the catalog grows', async ({ page }) => {
  await page.goto('./#explore');
  const latest = [...lessons].sort((a, b) => b.published.localeCompare(a.published) || b.order - a.order)[0];
  await expect(page.locator('.latest-note time')).toHaveAttribute('datetime', latest.published);
  await expect(page.locator('.latest-note a')).toHaveAttribute('href', `#lesson/${latest.id}`);
  await page.getByLabel('Lesson order').selectOption('newest');
  await expect(page.locator('[data-lesson-link]').first()).toHaveAttribute('data-lesson-link', latest.id);
  await page.getByRole('button', { name: 'Engineering', exact: true }).click();
  await expect(page.locator('[data-lesson-link]')).toHaveCount(lessons.filter(l => l.topic === 'Engineering').length);
  await page.getByLabel('Search lessons').fill('no-such-wonder-xyz');
  await expect(page.getByRole('heading', { name: 'No wonders found. Yet.' })).toBeVisible();
  await page.getByRole('button', { name: 'Show all wonders' }).click();
  await expect(page.locator('[data-lesson-link]')).toHaveCount(lessons.length);
});
