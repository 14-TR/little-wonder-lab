import test from 'node:test';
import assert from 'node:assert/strict';
import * as requests from '../src/request.js';

test('request validation requires a useful question and public sharing consent', () => {
  assert.equal(typeof requests.validateRequest, 'function', 'request validation must exist');
  assert.ok(requests.validateRequest({ question: '  ', details: '', consent: false }).question);
  assert.ok(requests.validateRequest({ question: 'Why do leaves change?', details: '', consent: false }).consent);
  assert.deepEqual(requests.validateRequest({ question: 'Why do leaves change?', details: '', consent: true }), {});
  assert.ok(requests.validateRequest({ question: 'x'.repeat(101), details: '', consent: true }).question);
  assert.ok(requests.validateRequest({ question: 'A useful question', details: 'x'.repeat(601), consent: true }).details);
});

test('a draft URL encodes untrusted text into a fixed repository issue composer', () => {
  assert.equal(typeof requests.buildRequestUrl, 'function', 'draft URL builder must exist');
  const input = { question: 'Why do rainbows bend? & ☀', details: '<script>alert("hi")</script>\nA & B # C', consent: true };
  const url = new URL(requests.buildRequestUrl(input));
  assert.equal(url.origin, 'https://github.com');
  assert.equal(url.pathname, '/14-TR/little-wonder-lab/issues/new');
  assert.equal(url.searchParams.get('labels'), 'lesson-request');
  assert.equal(url.searchParams.get('title'), 'Lesson request: Why do rainbows bend? & ☀');
  assert.ok(url.searchParams.get('body').includes(input.details));
  assert.equal(url.hash, '');
  assert.throws(() => requests.buildRequestUrl({ question: '', consent: true }));
});
