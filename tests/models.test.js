import test from 'node:test';
import assert from 'node:assert/strict';
import * as models from '../src/models.js';

test('pattern rule generates a bounded path from whole immutable units', () => {
  assert.equal(typeof models.patternModel, 'function', 'pattern model must exist');
  for (const [mode, unit] of [['AB', ['leaf', 'flower']], ['AAB', ['leaf', 'leaf', 'flower']]]) {
    for (let length = 0; length <= 8; length += 1) {
      const model = models.patternModel(mode, length);
      assert.deepEqual(model.unit, unit);
      assert.deepEqual(model.sequence, Array.from({ length }, (_, i) => unit[i % unit.length]));
      assert.equal(model.expected, unit[length % unit.length]);
      assert.equal(model.position, length % unit.length + 1);
      assert.match(model.reason, new RegExp(`place ${model.position}`));
      assert.match(model.reason, new RegExp(model.expected));
      model.sequence.push('flower');
      assert.equal(models.patternModel(mode, length).sequence.length, length);
      assert.throws(() => model.unit.push('flower'), TypeError);
    }
  }
  for (const mode of ['ABC', '__proto__', '', null]) assert.throws(() => models.patternModel(mode, 5), TypeError);
  for (const length of [-1, 9, 1.5, NaN, Infinity, '5', null]) assert.throws(() => models.patternModel('AB', length), RangeError);
});

test('moving an unchanged hand toward a fixed light grows its shadow', () => {
  assert.equal(typeof models.shadowModel, 'function', 'shadow model must exist');
  const near = models.shadowModel(0);
  const far = models.shadowModel(100);
  assert.ok(near.scale > far.scale);
  assert.ok(near.handX < far.handX);
  assert.match(near.description, /bigger/i);
  assert.match(far.description, /smaller/i);
  assert.deepEqual(models.shadowModel(-20), near);
  assert.deepEqual(models.shadowModel(500), far);
  assert.ok(Number.isFinite(models.shadowModel(NaN).scale));
});

test('the qualitative ramp model keeps its baseline and increases runout with height', () => {
  assert.equal(typeof models.rampModel, 'function', 'ramp model must exist');
  const low = models.rampModel('low');
  const high = models.rampModel('high');
  assert.equal(low.rampBottomX, high.rampBottomX);
  for (const ramp of [low, high]) {
    const dx = ramp.rampBottomX - ramp.startX;
    const dy = ramp.rampBottomY - ramp.startY;
    const length = Math.hypot(dx, dy);
    assert.ok(Math.abs(length - 222) < 1e-9, 'the same board rotates without stretching');
    assert.ok(Math.abs(((ramp.carX - ramp.startX) * dx + (ramp.carY - ramp.startY) * dy) / length ** 2 - 0.14) < 1e-9, 'the car starts at the same fraction of the board');
    assert.equal(ramp.supportTop, ramp.startY + dy * (137 - ramp.startX) / dx + 7 * length / dx, 'the support touches the underside at its right edge');
  }
  assert.ok(high.stopX > low.stopX);
  assert.ok(high.startY < low.startY);
  assert.deepEqual(models.rampModel('not-a-height'), low);
});

test('folded sides reduce illustrated bending under the same spoon, not a capacity claim', () => {
  assert.equal(typeof models.bridgeModel, 'function', 'bridge model must exist');
  assert.equal(models.bridgeModel('flat', false).sag, 0);
  assert.ok(models.bridgeModel('flat', true).sag > models.bridgeModel('folded', true).sag);
  assert.match(models.bridgeModel('folded', true).description, /same spoon/);
  assert.deepEqual(models.bridgeModel('unknown', true), models.bridgeModel('flat', true));
});
