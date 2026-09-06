"""SHA-pinned release boundary. API callable enables offline behavioral tests."""
import json
import subprocess
from autonomy_policy import REPO, Blocked, item_id, pages, sha40, validate_changes, validate_release


def command(argv, cwd, timeout=60):
    return subprocess.run(argv, cwd=cwd, check=True, capture_output=True, text=True, timeout=timeout).stdout.rstrip('\n')


class Git:
    def __init__(self, root):
        self.root = root

    def inspect(self, pr, files):
        branch = 'auto/' + item_id(pr['head']['ref'].removeprefix('auto/'))
        sha, base = sha40(pr['head']['sha']), sha40(pr['base']['sha'])
        command(['git', 'fetch', 'origin', 'main', branch], self.root)
        # Require the reviewed branch to include current main; do not fix it by force-push.
        command(['git', 'merge-base', '--is-ancestor', base, sha], self.root)
        exact = []
        for entry in command(['git', 'diff', '--numstat', '-z', '--no-renames', '--no-ext-diff',
                              '--no-textconv', base, sha, '--'], self.root).split('\0'):
            if not entry:
                continue
            added, removed, path = entry.split('\t', 2)
            if not added.isdecimal() or not removed.isdecimal():
                raise Blocked('binary change requires human review')
            exact.append({'filename': path, 'changes': int(added) + int(removed)})
        raw = command(['git', 'diff', '--raw', '-z', '--no-renames', '--no-ext-diff',
                       '--no-textconv', base, sha, '--'], self.root).split('\0')
        metadata = {raw[i + 1]: raw[i].split() for i in range(0, len(raw) - 1, 2)}
        for f in exact:
            fields = metadata[f['filename']]
            f['mode'] = fields[1]
            f['status'] = {'A': 'added', 'M': 'modified', 'D': 'removed'}.get(fields[4], 'unsupported')
        files[:] = exact
        def lessons(ref):
            return json.loads(command(['git', 'show', ref + ':src/data/lessons.json'], self.root))
        return lessons(base), lessons(sha)


class GitHub:
    def __init__(self, root):
        self.root = root

    def __call__(self, endpoint, method='GET', data=None):
        if not endpoint.startswith(f'repos/{REPO}/'):
            raise Blocked('GitHub request outside the authorized repository')
        args = ['gh', 'api', '--method', method, endpoint]
        if data is not None:
            args += ['--input', '-']
        result = subprocess.run(args, input=json.dumps(data) if data is not None else None,
                                cwd=self.root, text=True, capture_output=True, timeout=30, check=True)
        return json.loads(result.stdout)


def quality_green(api, sha, branch):
    def runs(url):
        return api(url)['workflow_runs']
    runs_found = pages(runs, f'repos/{REPO}/actions/workflows/quality.yml/runs?head_sha={sha}&event=pull_request')
    candidates = [r for r in runs_found if r.get('head_sha') == sha and r.get('head_branch') == branch
                  and r.get('event') == 'pull_request' and r.get('path') == '.github/workflows/quality.yml']
    if not candidates:
        return False
    latest = max(candidates, key=lambda r: r['id'])
    if latest['status'] != 'completed' or latest['conclusion'] != 'success':
        return False
    jobs = pages(lambda u: api(u)['jobs'], f"repos/{REPO}/actions/runs/{latest['id']}/jobs?filter=latest")
    quality = [j for j in jobs if j['name'] == 'quality']
    return len(quality) == 1 and quality[0]['status'] == 'completed' and quality[0]['conclusion'] == 'success' and quality[0]['head_sha'] == sha


def release(api, git, number, evidence, expected_item):
    expected_item = item_id(expected_item)
    if type(number) is not int or number < 1:
        raise Blocked('invalid PR number')
    endpoint = f'repos/{REPO}/pulls/{number}'
    pr = api(endpoint)
    sha = sha40(evidence['sha'])
    main = api(f'repos/{REPO}/git/ref/heads/main')['object']['sha']
    # Validate trust and review evidence BEFORE fetching any branch or running its code.
    validate_release(pr, evidence, main, quality=True)
    if (pr['head']['ref'] != 'auto/' + expected_item or
            f'<!-- lwl:item:{expected_item} -->' not in (pr.get('body') or '')):
        raise Blocked('PR does not match the active checkpoint item')
    if not quality_green(api, sha, pr['head']['ref']):
        raise Blocked('quality workflow/job not successful at reviewed SHA')
    files = pages(api, endpoint + '/files')
    if len(files) != pr['changed_files']:
        raise Blocked('incomplete PR file list')
    before, after = git.inspect(pr, files)
    validate_changes(files, before, after)
    # Every status is tied to the exact reviewed SHA. This is NOT a GitHub approving review.
    api(f'repos/{REPO}/statuses/{sha}', 'POST', {
        'state': 'success', 'context': 'independent-review',
        'description': 'Fresh code + curriculum review passed for this exact SHA',
        'target_url': f'https://github.com/{REPO}/pull/{number}'})
    statuses = api(f'repos/{REPO}/commits/{sha}/status')['statuses']
    if not any(s['context'] == 'independent-review' and s['state'] == 'success' for s in statuses):
        raise Blocked('review status was not read back')
    # Re-read immediately before the merge. Strict branch protection closes the base race.
    current = api(endpoint)
    main = api(f'repos/{REPO}/git/ref/heads/main')['object']['sha']
    validate_release(current, evidence, main, quality=quality_green(api, sha, pr['head']['ref']))
    if (current['head']['ref'] != 'auto/' + expected_item or
            f'<!-- lwl:item:{expected_item} -->' not in (current.get('body') or '')):
        raise Blocked('PR does not match the active checkpoint item')
    merged = api(endpoint + '/merge', 'PUT', {'sha': sha, 'merge_method': 'squash'})
    if merged.get('merged') is not True:
        raise Blocked('GitHub refused the merge')
    final = api(endpoint)
    if final.get('merged') is not True or final.get('state') != 'closed' or final.get('merge_commit_sha') != merged['sha']:
        raise Blocked('merge read-back failed; recover by reading PR, never create a duplicate')
    return {'pr': number, 'reviewed_sha': sha, 'merge_sha': sha40(merged['sha']), 'stage': 'merged'}
