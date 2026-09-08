import { test, expect } from './fixtures.js';

test('Pattern Path completes both rules by keyboard with explicit advance and fresh restarts', async ({ page }) => {
  await page.addInitScript(() => {
    window.answerWrites = [];
    Storage.prototype.setItem = (...args) => { window.answerWrites.push(args); };
    Object.defineProperty(window, 'localStorage', { get() { throw new Error('Storage blocked'); } });
  });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('./#lesson/pattern-path');
  const next = page.getByRole('button', { name: 'Next space', exact: true });
  const restart = page.getByRole('button', { name: 'Restart path', exact: true });
  await expect(next).toBeVisible({ timeout: 1000 });
  const requests = [];
  page.on('request', request => requests.push(request.url()));
  const status = page.locator('#model-result');
  await expect(status).toHaveAttribute('aria-live', 'polite');
  for (const [mode, answers, ending] of [
    ['AB', ['Flower', 'Leaf', 'Flower'], 'leaf, flower | leaf, flower | leaf, flower | leaf, flower'],
    ['AAB', ['Flower', 'Leaf', 'Leaf'], 'leaf, leaf, flower | leaf, leaf, flower | leaf, leaf'],
  ]) {
    const modeButton = page.getByRole('button', { name: mode, exact: true });
    await modeButton.focus();
    await modeButton.press('Space');
    await expect(modeButton).toBeFocused();
    await expect(modeButton).toHaveAttribute('aria-pressed', 'true');
    await expect(status).toContainText('What comes next?');
    await next.focus();
    await next.press('Enter');
    await expect(page.locator('.pattern-tile')).toHaveCount(6);
    for (const [index, answer] of answers.entries()) {
      const choice = page.getByRole('button', { name: answer, exact: true });
      await choice.focus();
      await choice.press('Enter');
      await expect(choice).toBeFocused();
      await expect(status).toContainText('That fits the rule!');
      const explanation = await status.textContent();
      await choice.press('Space');
      expect(await status.textContent()).toBe(explanation);
      await expect(page.locator('.pattern-tile')).toHaveCount(6 + index);
      if (index < 2) {
        await next.focus();
        await next.press('Space');
        await expect(next).toBeFocused();
        await expect(page.locator('#pattern-sequence')).toContainText('blank');
      }
    }
    await expect(page.locator('#pattern-sequence')).toHaveText(ending);
    await expect(status).toContainText('Three drawings added');
    await next.focus();
    await next.press('Enter');
    await expect(page.locator('.pattern-tile')).toHaveCount(8);
    await restart.focus();
    await restart.press('Space');
    await expect(restart).toBeFocused();
    await expect(status).toContainText('What comes next?');
    await expect(page.locator('.pattern-tile')).toHaveCount(6);
    await page.getByRole('button', { name: 'Leaf', exact: true }).press('Enter');
    await expect(status).toContainText('Try looking');
  }
  await page.getByRole('button', { name: 'AB', exact: true }).press('Enter');
  await expect(status).not.toContainText('Try looking');
  await expect(page.locator('#pattern-sequence')).toHaveText('leaf, flower | leaf, flower | leaf, blank');
  expect(await page.evaluate(() => window.answerWrites)).toEqual([]);
  expect(requests).toEqual([]);
});

test('Pattern Path offers an explained first prediction with a standalone printable lesson', async ({ page }) => {
  await page.goto('./#explore');
  await expect(page.getByRole('button', { name: 'Math', exact: true })).toBeVisible({ timeout: 1000 });
  await page.getByRole('button', { name: 'Math', exact: true }).click();
  const card = page.locator('[data-lesson-link="pattern-path"]');
  await expect(card).toContainText('Find the little group. Follow its rule.');
  await card.click();
  await expect(page.getByRole('heading', { name: 'Pattern Path', exact: true })).toBeVisible();
  await expect(page.locator('.interactive')).toContainText('AN ARRANGED REPEATING RULE');
  await expect(page.locator('#pattern-sequence')).toHaveText('leaf, flower | leaf, flower | leaf, blank');
  await expect(page.locator('#pattern-repeat')).toContainText('leaf, flower');
  const leaf = page.getByRole('button', { name: 'Leaf', exact: true });
  const flower = page.getByRole('button', { name: 'Flower', exact: true });
  await leaf.focus();
  await leaf.press('Enter');
  await expect(leaf).toBeFocused();
  await expect(page.locator('#model-result')).toContainText('Try looking at the whole group');
  await expect(page.locator('#pattern-sequence')).toContainText('blank');
  await page.keyboard.press('Tab');
  await expect(flower).toBeFocused();
  await page.keyboard.press('Space');
  await expect(flower).toBeFocused();
  await expect(page.locator('#model-result')).toContainText('place 2');
  await expect(page.locator('#pattern-sequence')).toHaveText('leaf, flower | leaf, flower | leaf, flower');
  const explanation = await page.locator('#model-result').textContent();
  await flower.press('Enter');
  expect(await page.locator('#model-result').textContent()).toBe(explanation);
  expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
  await page.getByRole('button', { name: 'Next step' }).click();
  await page.emulateMedia({ media: 'print' });
  await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
  await expect(page.locator('.interactive')).toBeHidden();
  await expect(page.locator('.experiment-steps > li:visible')).toHaveCount(5);
  await expect(page.locator('.prediction')).toContainText('AB: leaf, flower | leaf, flower | leaf, ___');
  await expect(page.locator('.prediction')).toContainText('AAB: leaf, leaf, flower | leaf, leaf, ___');
  await expect(page.locator('.safety')).toContainText('large intact crayon');
  await expect(page.getByRole('heading', { name: 'Where the math comes from' })).toBeVisible();
  await expect(page.locator('.grown-up a[href^="https://nrich.maths.org/"]')).toHaveCount(2);
  await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
  await page.emulateMedia({ media: 'screen' });
  await expect(page.locator('#step-status')).toHaveText('Step 2 of 5');
  await expect(page.locator('.experiment-steps > li:visible')).toHaveCount(1);
  await expect(page.locator('.grown-up')).not.toHaveAttribute('open');
});

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
