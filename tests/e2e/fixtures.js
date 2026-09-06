import { test as base, expect } from '@playwright/test';

export const test = base.extend({
  browserErrors: [async ({ page }, use) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    await use(errors);
    expect(errors, 'No runtime, SVG parsing, or browser console errors').toEqual([]);
  }, { auto: true }],
});
export { expect };
