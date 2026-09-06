import { test, expect } from './fixtures.js';

test('remembering discoveries is opt-in, device local, reversible, and survives reload', async ({ page }) => {
  await page.goto('./#lesson/shadow-detective');
  expect(await page.evaluate(() => localStorage.length)).toBe(0);
  const remember = page.getByLabel('Remember our discoveries on this device');
  await expect(remember).not.toBeChecked();
  await remember.check();
  await page.getByRole('button', { name: 'We explored this!' }).click();
  await expect(page.locator('#progress-status')).toContainText('Saved on this device');
  await page.reload();
  await expect(remember).toBeChecked();
  await expect(page.getByRole('button', { name: 'We explored this!' })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('link', { name: 'Back to explore' }).click();
  await expect(page.locator('[data-lesson-link="shadow-detective"]')).toContainText('Explored');
  await page.locator('[data-lesson-link="shadow-detective"]').click();
  await page.getByRole('button', { name: 'Forget saved wonders' }).click();
  await expect(remember).not.toBeChecked();
  expect(await page.evaluate(() => localStorage.getItem('little-wonder-lab:progress:v1'))).toBeNull();
});

test('blocked storage leaves the lesson and experiment usable with an honest status', async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(window, 'localStorage', { get() { throw new Error('Storage blocked'); } }));
  await page.goto('./#lesson/shadow-detective');
  await page.getByLabel('Remember our discoveries on this device').check();
  await expect(page.locator('#progress-status')).toContainText('cannot save');
  await page.getByRole('slider', { name: 'Hand position' }).focus();
  await page.getByRole('slider', { name: 'Hand position' }).press('Home');
  await expect(page.locator('#model-result')).toContainText('bigger');
});

test('hands-on directions are one step at a time and every step is printable', async ({ page }) => {
  await page.goto('./#lesson/paper-bridge');
  const steps = page.locator('.experiment-steps > li');
  const count = await steps.count();
  await expect(steps.filter({ visible: true })).toHaveCount(1);
  await expect(page.getByRole('button', { name: 'Previous step' })).toBeDisabled();
  await page.getByRole('button', { name: 'Next step' }).click();
  await expect(page.locator('#step-status')).toHaveText(`Step 2 of ${count}`);
  await expect(steps.nth(1)).toBeVisible();
  await page.getByRole('button', { name: 'Previous step' }).click();
  await expect(steps.first()).toBeVisible();
  await page.evaluate(() => { window.printCalls = 0; window.print = () => { window.printCalls += 1; }; });
  await page.getByRole('button', { name: 'Print this field note' }).click();
  expect(await page.evaluate(() => window.printCalls)).toBe(1);
  await page.emulateMedia({ media: 'print' });
  await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
  await expect(steps.filter({ visible: true })).toHaveCount(count);
  await expect(page.locator('.grown-up > div')).toBeVisible();
  await expect(page.locator('.interactive')).toBeHidden();
  await expect(page.getByText('Our field notes', { exact: true })).toBeVisible();
  await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
  await page.emulateMedia({ media: 'screen' });
  await expect(steps.filter({ visible: true })).toHaveCount(1);
});
