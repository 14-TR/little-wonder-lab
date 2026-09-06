import test from 'node:test';
import assert from 'node:assert/strict';
import * as catalog from '../src/catalog.js';

test('catalog filters by topic and words without mutating lesson order', () => {
  assert.equal(typeof catalog.selectLessons, 'function', 'selectLessons must exist');
  const lessons = [
    { id: 'bridge', title: 'Paper Bridge', topic: 'Engineering', subtitle: 'Fold paper', order: 3 },
    { id: 'shadow', title: 'Shadow Detective', topic: 'Science', subtitle: 'Follow the light', order: 1 },
  ];
  assert.deepEqual(catalog.selectLessons(lessons, { query: '  LIGHT ', topic: 'All' }).map(x => x.id), ['shadow']);
  assert.deepEqual(catalog.selectLessons(lessons, { topic: 'Engineering' }).map(x => x.id), ['bridge']);
  assert.deepEqual(catalog.selectLessons(lessons).map(x => x.id), ['shadow', 'bridge']);
  assert.equal(lessons[0].id, 'bridge');
});

test('newest order and latest note derive from publication data as the catalog grows', () => {
  assert.equal(typeof catalog.latestLesson, 'function', 'latest publication helper must exist');
  const lessons = [
    { id: 'a', title: 'First', order: 1, published: '2026-09-01' },
    { id: 'b', title: 'Second', order: 2, published: '2026-09-02' },
    { id: 'c', title: 'Third', order: 3, published: '2026-09-02' },
    { id: 'd', title: 'Fourth', order: 4, published: '2026-09-07' },
  ];
  assert.deepEqual(catalog.selectLessons(lessons, { sort: 'newest' }).map(l => l.id), ['d', 'c', 'b', 'a']);
  assert.equal(catalog.latestLesson(lessons).id, 'd');
  assert.equal(catalog.latestLesson([]), null);
});
