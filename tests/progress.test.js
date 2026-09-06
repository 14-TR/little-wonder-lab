import test from 'node:test';
import assert from 'node:assert/strict';
import * as progress from '../src/progress.js';

test('progress writes only after opt-in and forget clears only its own key', () => {
  assert.equal(typeof progress.createProgress, 'function', 'progress store must exist');
  const data = new Map([['other-site-key', 'keep me']]);
  const storage = { getItem: key => data.get(key) ?? null, setItem: (key, value) => data.set(key, value), removeItem: key => data.delete(key) };
  const store = progress.createProgress(() => storage, ['shadow', 'ramp']);
  assert.deepEqual(store.read(), { enabled: false, completed: [] });
  assert.equal(data.size, 1);
  assert.equal(store.save({ enabled: true, completed: ['shadow', 'shadow', 'unknown'] }), true);
  assert.deepEqual(store.read(), { enabled: true, completed: ['shadow'] });
  assert.equal(store.clear(), true);
  assert.deepEqual(store.read(), { enabled: false, completed: [] });
  assert.equal(data.get('other-site-key'), 'keep me');
});

test('blocked or malformed local storage cannot break a lesson', () => {
  assert.equal(typeof progress.createProgress, 'function', 'progress store must exist');
  const blocked = progress.createProgress(() => { throw new Error('Blocked'); }, ['shadow']);
  assert.deepEqual(blocked.read(), { enabled: false, completed: [] });
  assert.equal(blocked.save({ enabled: true, completed: ['shadow'] }), false);
  assert.equal(blocked.clear(), false);
  const corrupt = progress.createProgress(() => ({ getItem: () => '{broken' }), ['shadow']);
  assert.deepEqual(corrupt.read(), { enabled: false, completed: [] });
});
