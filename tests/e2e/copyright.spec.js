import { test, expect } from './fixtures.js';
import { readFileSync } from 'node:fs';

const lessons = JSON.parse(readFileSync(new URL('../../src/data/lessons.json', import.meta.url), 'utf8'));
const routes = ['./', './#explore', './#request', ...lessons.map(lesson => `./#lesson/${lesson.id}`), './#lesson/missing-wonder'];

test('every page retains the footer and displays the owner copyright notice', async ({ page }) => {
  for (const route of routes) {
    await page.goto(route);
    const footer = page.getByRole('contentinfo');
    await expect(footer.getByText('© 2026 TR Ingram', { exact: true })).toBeVisible();
    await expect(footer.getByText('Small experiments. Big possibilities.', { exact: true })).toBeVisible();
    await expect(footer.getByText('Made for curious kids & their grown-ups.', { exact: true })).toBeVisible();
    await expect(footer.getByText('No accounts. No tracking. Just wonder.', { exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
});
