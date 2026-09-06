import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as schema from '../src/schema.js';
import * as interactions from '../src/interactions.js';
import { illustrationKinds } from '../src/illustrations.js';

const lessons = JSON.parse(readFileSync(new URL('../src/data/lessons.json', import.meta.url), 'utf8'));
const clone = () => structuredClone(lessons);

test('every published lesson has the complete supported contract without capping the catalog size', () => {
  assert.equal(typeof schema.validateLessons, 'function', 'curriculum validation must exist');
  assert.ok(lessons.length >= 3);
  assert.deepEqual(schema.validateLessons(lessons), []);
  for (const id of ['shadow-detective', 'ramp-racers', 'paper-bridge']) assert.ok(lessons.some(l => l.id === id));
  assert.deepEqual([...interactions.interactiveKinds].sort(), [...illustrationKinds].sort());
  assert.deepEqual([...schema.SUPPORTED_KINDS].sort(), [...illustrationKinds].sort());
});

test('curriculum validation rejects duplicate or malformed identifiers and missing prerequisites', () => {
  assert.equal(typeof schema.validateLessons, 'function', 'curriculum validation must exist');
  const duplicate = clone(); duplicate[1].id = duplicate[0].id;
  assert.ok(schema.validateLessons(duplicate).some(error => /duplicate id/.test(error)));
  const malformed = clone(); malformed[0].id = 'Shadow_Detective';
  assert.ok(schema.validateLessons(malformed).some(error => /slug/.test(error)));
  const missing = clone(); missing[0].prerequisites = ['does-not-exist'];
  assert.ok(schema.validateLessons(missing).some(error => /unknown prerequisite/.test(error)));
});

test('curriculum validation rejects dependency cycles, unimplemented kinds and unsafe source protocols', () => {
  assert.equal(typeof schema.validateLessons, 'function', 'curriculum validation must exist');
  const cycle = clone(); cycle[0].prerequisites = [cycle[2].id];
  assert.ok(schema.validateLessons(cycle).some(error => /cycle/.test(error)));
  const kind = clone(); kind[0].kind = 'electricity';
  assert.ok(schema.validateLessons(kind).some(error => /unsupported kind/.test(error)));
  const source = clone(); source[0].sources[0].url = 'javascript:alert(1)';
  assert.ok(schema.validateLessons(source).some(error => /HTTPS/.test(error)));
  const invalidDate = clone(); invalidDate[0].published = '2026-02-31';
  assert.ok(schema.validateLessons(invalidDate).some(error => /published/.test(error)));
  const missingCopy = clone(); delete missingCopy[0].safety;
  assert.ok(schema.validateLessons(missingCopy).some(error => /safety/.test(error)));
  assert.ok(schema.validateLessons([]).length);
});

test('unsupported interactive kinds fail explicitly rather than leaving a blank experiment', () => {
  assert.throws(() => interactions.mountInteractive('unknown-kind', {}), /Unsupported/);
});
