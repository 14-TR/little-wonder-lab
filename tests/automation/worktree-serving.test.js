import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, realpath, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { createServer } from 'vite';

const project = fileURLToPath(new URL('../../', import.meta.url));

test('helper-created worktree serves HTML and transformed source with default Vite metadata denial', { timeout: 20000 }, async () => {
  const temporary = await realpath(await mkdtemp(path.join(tmpdir(), 'lwl-serving-')));
  const root = path.join(temporary, 'repo');
  const env = { ...process.env, GIT_CONFIG_GLOBAL: '/dev/null', GIT_CONFIG_NOSYSTEM: '1' };
  for (const key of Object.keys(env)) if (key.startsWith('GIT_') && !['GIT_CONFIG_GLOBAL', 'GIT_CONFIG_NOSYSTEM'].includes(key)) delete env[key];
  const git = (...args) => execFileSync('git', args, { cwd: root, env, encoding: 'utf8', timeout: 10000 });
  async function serve(worktree, expected) {
    const server = await createServer({ root: worktree, configFile: false, logLevel: 'silent',
      optimizeDeps: { noDiscovery: true }, server: { host: '127.0.0.1', port: 0 } });
    try {
      await server.listen();
      const address = `http://127.0.0.1:${server.httpServer.address().port}`;
      const get = (url) => fetch(address + url, { signal: AbortSignal.timeout(3000) });
      const html = await get('/');
      assert.equal(html.status, expected, `HTML serving from ${worktree}`);
      if (expected === 200) {
        assert.match(await html.text(), /worktree fixture/);
        const source = await get('/src/main.jsx');
        const transformed = await source.text();
        assert.equal(source.status, 200, transformed);
        assert.match(transformed, /createElement/);
      }
      const metadata = await get('/@fs' + path.join(root, '.git/config'));
      assert.equal(metadata.status, 403, 'operator Git metadata must remain denied');
      assert.doesNotMatch(await metadata.text(), /\[core\]/);
    } finally { await server.close(); }
  }
  try {
    await mkdir(path.join(root, 'src'), { recursive: true });
    await writeFile(path.join(root, '.gitignore'), await readFile(path.join(project, '.gitignore')));
    await writeFile(path.join(root, 'index.html'), '<h1>worktree fixture</h1><script type="module" src="/src/main.jsx"></script>');
    await writeFile(path.join(root, 'src/main.jsx'), '/** @jsxRuntime classic */\nexport const view = <h1>worktree fixture</h1>;');
    git('init', '-q', '-b', 'main');
    git('add', '.');
    git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture');
    git('remote', 'add', 'origin', root);
    const receipt = JSON.parse(execFileSync('python3', ['-c',
      'import json,sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from autonomy import prepare; print(json.dumps(prepare(Path(sys.argv[2]),"request-42")))',
      path.join(project, 'scripts'), root], { env, encoding: 'utf8', timeout: 10000 }));
    // Before the fix this is the real helper's .git ancestor failure (403, not 200).
    await serve(receipt.worktree, 200);
    assert.equal(receipt.worktree, path.join(root, '.autonomy-worktrees/request-42'));
    assert.equal(git('status', '--porcelain').trim(), '', 'owned worktrees must be ignored');
    const legacy = path.join(root, '.git/autonomy/worktrees/legacy');
    git('worktree', 'add', '-b', 'legacy', legacy);
    await serve(legacy, 403);
  } finally { await rm(temporary, { recursive: true, force: true }); }
});
