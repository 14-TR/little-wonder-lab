import { pathToFileURL } from 'node:url';

export async function verifyLive(base, sha, lessonId) {
  const { chromium } = await import('@playwright/test');
  const response = await fetch(new URL(`release.json?sha=${sha}`, base), { signal: AbortSignal.timeout(20000), redirect: 'error' });
  if (!response.ok) throw new Error(`Manifest HTTP ${response.status}`);
  const lesson = validateManifest(await response.json(), sha, lessonId);
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    const errors = [];
    page.on('pageerror', error => errors.push(String(error)));
    page.on('response', res => {
      if (res.status() >= 400 && new URL(res.url()).origin === new URL(base).origin) errors.push(`HTTP ${res.status()}: ${res.url()}`);
    });
    const result = await page.goto(new URL(`#lesson/${lessonId}`, base).href, { waitUntil: 'networkidle', timeout: 30000 });
    if (!result?.ok()) throw new Error('Live HTML failed');
    await page.getByRole('heading', { name: lesson.title, exact: true }).waitFor({ timeout: 15000 });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
    if (overflow || errors.length) throw new Error(`Live errors: ${errors.join('; ')}; overflow=${overflow}`);
    await page.keyboard.press('Tab');
    if (!(await page.evaluate(() => document.activeElement !== document.body))) throw new Error('No keyboard focus target');
    return { passed: true, sha, lesson_id: lessonId, url: base, checks: ['release SHA', 'lesson heading', 'no JS/HTTP errors', 'mobile overflow', 'keyboard focus'] };
  } finally { await browser.close(); }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [sha, lessonId] = process.argv.slice(2);
  // The command-line release surface never takes an issue-supplied URL.
  verifyLive('https://14-tr.github.io/little-wonder-lab/', sha, lessonId)
    .then(result => console.log(JSON.stringify(result)))
    .catch(error => { console.error(String(error)); process.exitCode = 1; });
}

export function validateManifest(data, sha, lessonId) {
  if (!/^[a-f0-9]{40}$/.test(sha) || data?.sha !== sha || !Array.isArray(data.lessons)) {
    throw new Error('Live release SHA is stale or malformed');
  }
  const lesson = data.lessons.find(x => x.id === lessonId);
  if (!lesson || typeof lesson.title !== 'string' || !lesson.title.trim()) throw new Error('Expected live lesson is absent');
  return lesson;
}
