import { test, expect } from './fixtures.js';

test('shadow size follows the hand position with a readable qualitative explanation', async ({ page }) => {
  await page.goto('./#lesson/shadow-detective');
  await expect(page.getByRole('heading', { name: 'Make a shadow grow' })).toBeVisible();
  const control = page.getByRole('slider', { name: 'Hand position' });
  await control.focus();
  await control.press('Home');
  await expect(page.locator('#model-result')).toContainText('bigger');
  const near = await page.locator('#cast-shadow').getAttribute('transform');
  await control.press('End');
  await expect(page.locator('#model-result')).toContainText('smaller');
  expect(await page.locator('#cast-shadow').getAttribute('transform')).not.toBe(near);
  await expect(page.getByText('A simple picture, not a measurement.', { exact: false })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('ramp keeps both stopping markers for a fair visual comparison', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('./#lesson/ramp-racers');
  await expect(page.getByRole('heading', { name: 'One car. Two little hills.' })).toBeVisible();
  await page.getByRole('button', { name: 'Let it roll' }).click();
  await expect(page.locator('#model-result')).toContainText('lower ramp');
  const low = await page.locator('[data-stop="low"]').getAttribute('transform');
  await page.getByRole('button', { name: 'Higher ramp', exact: true }).click();
  await page.getByRole('button', { name: 'Let it roll' }).click();
  await expect(page.locator('#model-result')).toContainText('farther');
  await expect(page.locator('[data-stop="low"]')).toBeVisible();
  await expect(page.locator('[data-stop="high"]')).toBeVisible();
  expect(await page.locator('[data-stop="high"]').getAttribute('transform')).not.toBe(low);
  await page.getByRole('button', { name: 'Clear the track' }).click();
  await expect(page.locator('[data-stop]')).toHaveCount(0);
});

test('paper bridge compares shapes while keeping the same load', async ({ page }) => {
  await page.goto('./#lesson/paper-bridge');
  await expect(page.getByRole('heading', { name: 'Give paper a new shape' })).toBeVisible();
  await page.getByRole('button', { name: 'Place the spoon' }).click();
  await expect(page.locator('#model-result')).toContainText('sags');
  const flat = await page.locator('#bridge-deck').getAttribute('d');
  await page.getByRole('button', { name: 'Folded sides', exact: true }).click();
  await expect(page.locator('#model-result')).toContainText('same spoon');
  expect(await page.locator('#bridge-deck').getAttribute('d')).not.toBe(flat);
  await expect(page.locator('#bridge-spoon')).toBeVisible();
  await page.getByRole('button', { name: 'Remove the spoon' }).click();
  await expect(page.locator('#bridge-spoon')).toBeHidden();
  await expect(page.locator('#model-result')).toContainText('Predict');
});
