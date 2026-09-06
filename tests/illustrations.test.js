import test from 'node:test';
import assert from 'node:assert/strict';
import { illustration } from '../src/illustrations.js';

test('lesson artwork agrees with the hand and safe spoon folded-side activities', () => {
  assert.match(illustration('shadows'), /aria-label="[^"]*hand/i);
  assert.match(illustration('bridges'), /aria-label="[^"]*spoon/i);
  assert.match(illustration('bridges'), /data-paper-shape="u-channel"/);
  assert.match(illustration('bridges'), /data-load="spoon"/);
  assert.doesNotMatch(illustration('bridges'), /coins/i);
});

test('unknown illustration kinds cannot silently show a different science activity', () => {
  assert.throws(() => illustration('unknown-kind'), /Unsupported/);
});
