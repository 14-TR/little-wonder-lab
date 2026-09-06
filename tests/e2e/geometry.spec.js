import { test, expect } from './fixtures.js';

// Inspect Chromium's parsed geometry, not just changes to SVG source strings.
test('bridge deck and folded walls have real geometry in every load state', async ({ page }) => {
  await page.goto('./#lesson/paper-bridge');
  for (const shape of ['flat', 'folded']) {
    await page.locator(`[data-shape="${shape}"]`).click();
    for (const loaded of [false, true]) {
      if (loaded) await page.locator('#spoon-toggle').click();
      const paths = page.locator('#bridge-deck, #bridge-rear-wall path, #bridge-front-wall path');
      await expect(paths).toHaveCount(shape === 'folded' ? 3 : 1);
      const geometry = await paths.evaluateAll(elements => elements.map(path => {
        const box = path.getBBox();
        return { length: path.getTotalLength(), width: box.width, height: box.height };
      }));
      for (const path of geometry) {
        expect(path.length).toBeGreaterThan(600);
        expect(path.width).toBeCloseTo(336, 5);
        expect(path.height).toBeGreaterThan(0);
      }
    }
    await page.locator('#spoon-toggle').click();
  }
});

async function rampGeometry(page) {
  return page.locator('#ramp-board').evaluate(board => {
    const [ax, ay, bx, by] = board.getAttribute('d').match(/-?\d+(?:\.\d+)?/g).map(Number);
    const dx = bx - ax, dy = by - ay;
    const length = Math.hypot(dx, dy);
    const car = document.querySelector('#rolling-car').transform.baseVal.consolidate().matrix;
    const releaseFraction = ((car.e - ax) * dx + (car.f - ay) * dy) / length ** 2;
    const wheelClearances = [-20, 19].map(x => {
      const contact = new DOMPoint(x, 12).matrixTransform(car);
      return ((contact.x - ax) * dy - (contact.y - ay) * dx) / length;
    });
    return { length, perimeter: board.getTotalLength(), bottom: [bx, by], releaseFraction, wheelClearances, angle: Math.atan2(car.b, car.a) };
  });
}

test('ramp rotates the same board around a fixed floor origin with the same release position', async ({ page }) => {
  await page.goto('./#lesson/ramp-racers');
  const low = await rampGeometry(page);
  await page.locator('[data-height="high"]').click();
  const high = await rampGeometry(page);
  expect(high.length, JSON.stringify({ low, high })).toBeCloseTo(low.length, 6);
  expect(high.perimeter).toBeCloseTo(low.perimeter, 3);
  expect(low.bottom).toEqual([280, 217]);
  expect(high.bottom).toEqual(low.bottom);
  expect(high.releaseFraction).toBeCloseTo(low.releaseFraction, 6);
  expect(low.releaseFraction).toBeGreaterThan(0);
  expect(low.releaseFraction).toBeLessThan(1);
  expect(high.angle).toBeGreaterThan(low.angle);
  for (const geometry of [low, high]) {
    for (const clearance of geometry.wheelClearances) expect(clearance).toBeCloseTo(0, 4);
  }
  await page.locator('#roll-car').click();
  await page.locator('#reset-ramp').click();
  expect(await rampGeometry(page)).toEqual(high);
  await page.locator('[data-height="low"]').click();
  expect(await rampGeometry(page)).toEqual(low);
});
