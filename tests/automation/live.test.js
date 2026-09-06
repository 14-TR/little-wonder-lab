import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { createServer } from 'node:http';

test('real browser checks a served lesson and rejects page errors', async () => {
  const mod = await import('../../scripts/verify-live.mjs');
  assert.equal(typeof mod.verifyLive, 'function', 'browser verifier missing');
  const sha = 'a'.repeat(40);
  let broken = false;
  const server = createServer((req, res) => {
    if (req.url.startsWith('/release.json')) {
      res.setHeader('Content-Type', 'application/json');
      res.end(JSON.stringify({ sha, lessons: [{ id: 'test-lesson', title: 'Test Lesson' }] }));
    } else {
      res.setHeader('Content-Type', 'text/html');
      res.end(`<main><h1>Test Lesson</h1><button>Explore</button></main>${broken ? '<script>throw Error("bad")</script>' : ''}`);
    }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const url = `http://127.0.0.1:${server.address().port}/`;
    const result = await mod.verifyLive(url, sha, 'test-lesson');
    assert.equal(result.passed, true);
    broken = true;
    await assert.rejects(() => mod.verifyLive(url, sha, 'test-lesson'));
  } finally { await new Promise(resolve => server.close(resolve)); }
});

test('live manifest binds a release to exact SHA and expected lesson', async () => {
  assert.ok(existsSync(new URL('../../scripts/verify-live.mjs', import.meta.url)), 'live verifier missing');
  const { validateManifest } = await import('../../scripts/verify-live.mjs');
  const sha = 'a'.repeat(40);
  const data = { sha, lessons: [{ id: 'shadow-detective', title: 'Shadow Detective' }] };
  assert.equal(validateManifest(data, sha, 'shadow-detective').title, 'Shadow Detective');
  assert.throws(() => validateManifest(data, 'b'.repeat(40), 'shadow-detective'));
  assert.throws(() => validateManifest(data, sha, 'missing'));
  assert.throws(() => validateManifest(data, 'not-a-sha', 'shadow-detective'));
});
