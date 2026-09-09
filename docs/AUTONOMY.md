# Bounded autonomy runbook

## What runs

Two Hermes cron **script-only** ticks share one small POSIX supervisor, not a bespoke agent framework. The supervisor reserves an attempt in SQLite, holds a kernel `flock`, and launches a real fresh default-profile Hermes lead. The lead uses fresh CLI role sessions through supervised `scripts/run_role.py`, with separate planner, engineer, code/accessibility reviewer and curriculum/safety reviewer contexts. It is not one model role-playing a team.

The target is **one substantive, safe educational update per America/Denver day**. Quality wins over the target. A failed/blocked day stays visibly failed; no timestamp-only commits and no backlog of forced catch-up releases.

| Bound | Policy |
|---|---|
| Attempts | At most 2 per local day, persisted across restarts; a verified success closes that day |
| Overlap | One OS lock plus persistent unresolved-process quarantine for both jobs and manual runs; no expiry or stale-lock deletion |
| Lead | `--run-budget 2100 --max-turns 90`; outer process-group bound 2400 seconds |
| Team | 4 fresh children normally, at most 7 including one targeted repair and two replacement reviewers |
| Change | At most 25 files / 1500 changed lines; substantive lesson data OR a product interaction/accessibility repair with regression tests |
| Network | GitHub calls 30 seconds; Git commands 60 seconds; pagination at most 20 × 100 rows per collection, then fail closed |
| Polling | CI at most 8 × 15 seconds; deployment at most 8 × 20 seconds, within total run budget |
| Trust | Same repository `auto/<item>` branches only; no fork checkout, issue-supplied execution or attachments |

A real interaction/accessibility repair can leave correct prose unchanged: the deterministic guard admits product-source plus regression-test changes, while BOTH independent reviewers must still explicitly confirm substantive learning benefit. Metadata-only, docs-only and test-only changes fail. Engineer/code-reviewer toolsets include vision; both must render desktop/mobile with installed Playwright Chromium and actually inspect screenshot images via vision_analyze. No Chrome browser-helper dependency.

The lead/child time and turn allocations inside the prompt are operating limits; the CLI wall budget, supervisor timer, lock and daily attempt ledger are deterministic. Foreground tools must also have finite timeouts. No detached/background work is allowed. **The outer timer bounds the lead's original process group, not every tool.** Ordinary Hermes local foreground terminal commands already start separate sessions and do not inherit the lock descriptor; they can survive a lead timeout/crash without deliberately detaching. Group termination therefore cannot prove that editing, building or publishing has stopped. A durable marker written before lead launch blocks every later run, even on a new day, after any abnormal or unverified shutdown. This is fail-closed quarantine, not automatic orphan cleanup or an OS sandbox. Existing Hermes approvals, repository protection and operator reconciliation remain boundaries; do not use this as a hostile-code runner.

## Planner timing and bounded handoffs

The lead's sequential allocation is selection 120 seconds, planner 360, engineering plus lead gates 720 (540 engineer / 180 lead), independent reviews 360, release 420 and stop buffer 120: 2100 seconds total. The extra 60 selection seconds come only from the engineer's implementation allowance, not mandatory gates, reviews, release or stop reserves. The 2400-second outer limit is not extra working time. Check elapsed time at dispatch and irreversible boundaries; require 1620 seconds remaining before engineering, 900 before review and 540 before release. A 65-second selection plus the full 360-second planner leaves 55 seconds for report validation/preparation/dispatch before the 1620-second downstream reservation; recheck at dispatch and stop if that full reservation no longer fits. This is budget arithmetic, not observed execution. Baseline work may overlap planning, never replace post-change gates. The optional repair and two new reviews require real remaining slack, not a larger total budget.

The planner gets an absolute dispatch deadline and a self-contained JSON handoff limit of 1200 words and 12000 UTF-8 bytes. It should batch mandatory document reads, inspect only relevant code seams, reuse source-body receipts honestly, and target discovery within 90 seconds before saving a compact decision. A resumed item needs a current-base delta assessment, not another full implementation essay. The complete schema lives in automation/roles/planner.md; the lead parses and checks the file, exact identity/base, completion/status and limits before engineering. Missing or invalid evidence fails closed. Read-only scope, source-body verification, independent reviews and release gates are unchanged.

Observed interrupted planner traces completed their reads/tools, then spent approximately three minutes waiting for a model response with no report saved. A fixed three-minute planning instruction therefore cut off the handoff, not a failing baseline test. A six-minute window plus smaller output is a bounded mitigation, not proof of provider latency or daily delivery. Timing/contract regression tests validate the instructions only; an owner-authorized supervised retry must still verify the real planner, lesson, independent reviews and live release. Never change model/profile/approval settings or reset attempts to make this trial pass. A timed-out child remains subject to the same unresolved-process quarantine and positive operator reconciliation.

## Why script-only cron

The current [cron docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron) and installed runtime support a final stdout line `{"wakeAgent": false}`: an ordinary pre-run script skips the LLM, and a script-only job is silent. `python3 scripts/autonomy.py gate` implements that format; malformed state/network exceptions exit nonzero rather than silently approving work.

Native cron's pre-run script timeout is currently 3600 seconds; the LLM uses a separate inactivity budget. Native `cron create` has no per-job CLI run-budget flag. Therefore the installed script is the whole cron job and launches the bounded lead using supported [`hermes chat` flags](https://hermes-agent.nousresearch.com/docs/reference/cli-commands). No global timeout/config changes are needed. The outer script normally ends within 2400 seconds. Both normal and recovery ticks use the same entrypoint and ledger. Do not use monitor-script hash suppression: a quiet request queue must still permit a meaningful roadmap update.

One-shot CLI leads do not consume asynchronous `delegate_task` callbacks. Use only the canonical `python3 /Users/tr/little-wonder-lab/scripts/run_role.py --file /absolute/spec.json` in finite FOREGROUND terminal calls. Separate reviewer calls can run in parallel; no detached shell jobs or polling for callbacks. Each spec directly under LWL_STATE supplies `role`, `item`, `base`, `worktree`, absolute epoch `deadline`, and trusted `context`; non-planners also supply checkpoint `lesson_id`, and reviewers supply exact `sha`. The active supervised attempt is required; this is not a quota-bypass command. Planner uses operator main; later roles use the exact checkpoint worktree/item/base.

The helper injects REPORT_PATH and requires a compact JSON artifact (1200 words / 12000 UTF-8 bytes), followed by ONLY LWL_ROLE_COMPLETE. It waits for CLI exit zero and verifies the exact observed session ID, normal closed-session export, paired tool calls/results, marker, identity and role schema before recording completed.json. It does not normalize identifiers, accept dispatch handles as completion, or infer a passing review. Save started/process/exit/log/export/report receipts, including failures. A completed transport may contain an honest blocked report or failed review; the lead must still inspect ready/pass, full design/test/visual/source evidence and exact SHA/base. The lead attaches the observed CLI session ID unchanged as agent_id and its own actual session ID as lead_agent_id. Distinct IDs are consistency evidence, not cryptographic proof of independence. Missing/abnormal completion blocks the attempt and retains the existing supervisor quarantine; process-group cleanup cannot prove separate terminal descendants ended.

All phase bounds include startup, final response and export. Engineer freezes implementation by 360 seconds, saves a complete report by 450, returns by 480, within the SAME 540-second allocation. Planner and reviewers save by 270 and return by 300 within 360 seconds. The final 60 seconds reserve transport, not extra implementation. Shorter absolute deadlines shorten work, never downstream gates or safe-stop reserves. These are transport and instruction contracts, not evidence that a real autonomous release succeeded.

## Operator installation — default profile only

Do this **after** the initial reviewed launch PR is merged, CI and Pages pass, and the operator checkout is a clean `main`. These commands are instructions for the operator; repository setup does not install jobs, change profiles, or write remote settings.

1. Confirm the existing gateway/cron ticker, model authentication and timezone without changing global configuration:

   ```sh
   hermes --profile default gateway status
   hermes --profile default cron status
   hermes --profile default cron list
   hermes --profile default config get timezone
   date
   gh auth status
   ```

   Cron expressions use the gateway's effective timezone (`HERMES_TIMEZONE`, configured timezone, otherwise host-local); the ledger explicitly uses America/Denver. Confirm the gateway is using America/Denver before using the times below. Do not alter unrelated jobs or global timezone to fit this project. The Mac must remain awake, logged in, online and able to refresh the existing openai-codex authentication. A saved job alone is not proof of a running ticker. Sleep can miss a daily window; recovery is not an unlimited catch-up queue.

2. In `/Users/tr/little-wonder-lab`, inspect clean status, then update clean main with `git fetch origin main` and `git merge --ff-only origin/main`. Never reset/stash user work. Install dependencies and browser, then run real gates:

   ```sh
   npm ci
   npx playwright install chromium
   npm test
   node --test tests/automation/*.test.js
   python3 -m unittest discover -s tests/automation -v
   npm run build
   npm run test:e2e
   python3 scripts/autonomy.py gate
   python3 scripts/autonomy.py scan
   ```

   Scan is read-only on GitHub and writes local untrusted DATA to `.git/autonomy/requests.json`. It scans paginated issues, all paginated comments for candidates, and all paginated PRs. Similar titles are advisory duplicate candidates only; distinct issue numbers remain available. A pagination cap or malformed page blocks rather than claiming completeness.

3. Install a **copy**, not a symlink escaping the profile's script directory:

   ```sh
   install -d -m 700 /Users/tr/.hermes/scripts
   install -m 600 automation/cron-entry.py /Users/tr/.hermes/scripts/little-wonder-lab.py
   hermes --profile default cron create '0 8 * * *' \
     --name 'Little Wonder Lab — daily' --no-agent \
     --script little-wonder-lab.py --workdir /Users/tr/little-wonder-lab --deliver local
   hermes --profile default cron create '0 16 * * *' \
     --name 'Little Wonder Lab — recovery' --no-agent \
     --script little-wonder-lab.py --workdir /Users/tr/little-wonder-lab --deliver local
   ```

   Record the TWO returned job IDs, read them back with `cron list`, inspect `cron status`, then trigger only the daily ID with `hermes --profile default cron run DAILY_ID`. Read `cron runs DAILY_ID` and `.git/autonomy/attempt-N.log`. The wrapper explicitly pins `gpt-6-astra` / `openai-codex` on each fresh CLI invocation; no fallback/approval/profile configuration is changed. Script-only cron model flags would be irrelevant.

4. Verify the first real end-to-end result: actual request, distinct child handles, RED/GREEN tests, successful required checks, squash merge read-back, matching deployment SHA and live browser receipt. Installation is **not verified** until that completes. Do not bypass a blocked approval to make the unattended demo pass. The owner-created starter request is #2, Pattern Path; it is not a family's submission.

At each real run, clean operator main is fetched and fast-forwarded with `git merge --ff-only origin/main` before launching the lead. Dirty or diverged user work is never reset or stashed.

Manual invocation is `python3 /Users/tr/little-wonder-lab/scripts/autonomy.py run` with terminal workdir `/Users/tr/little-wonder-lab`. It uses the SAME lock/attempt limit as cron. There is no bypass/reset-attempt flag. Do not run the lead prompt directly outside the supervisor for releases.

## Protected repository settings

Operator-owned settings, never changed by the cron team:
- `main`: PR required, strict/up-to-date required checks named exactly **quality** and **independent-review**; enforce administrators, resolve conversations, dismiss stale reviews, linear history; deny force pushes/deletion and bypass.
- Single GitHub account means zero required GitHub approving reviews (it cannot approve its own PR). Independent Hermes evidence drives the separate exact-SHA commit status; this is not a fabricated GitHub approval.
- Squash-only merges, Actions default token read-only, Actions may not approve pull requests. Pages source GitHub Actions; `github-pages` environment restricted to main.
- Quality workflow runs on PRs and main with read-only contents permission, no secrets, no `pull_request_target`. Deploy is a separate workflow triggered only by a successful Quality **push to same-repo main**, checking out its exact SHA. Official Pages actions, SHA-pinned actions, narrow deploy-only `pages:write`/`id-token:write`; no PR artifacts are reused for privileged deployment.

All autonomous paths outside the allowlist in AGENTS.md are protected, including `scripts/`, `automation/`, `.github/`, `tests/automation/`, this document, AGENTS/CONTRACT/SECURITY/LICENSE and package/configuration files. Nested hidden/instruction files, symlinks, submodules, binary changes and file/lesson deletions are not autonomous work. A user may separately authorize protected-path changes in an interactive reviewed PR; the ordinary autonomous merge helper deliberately will not release that PR.

## State contract and commands

Canonical state is `git rev-parse --git-common-dir` + `/autonomy/` in the operator checkout, normally `/Users/tr/little-wonder-lab/.git/autonomy/`. Nothing here is committed. SQLite WAL transactions persist attempt counts and the single active-item checkpoint. A live CLI inherits the lock descriptor, but ordinary terminal tools do not. After the supervisor and lead die the kernel lock can release while tools remain alive. Never unlink the lock. `unresolved-process.json` is created exclusively and fsynced before lead launch (including its parent directory); its presence blocks supervisor/gate/status independently of the date, ledger, PID liveness, or lock availability. Empty, malformed and dangling-symlink markers also block. There is no expiry or automatic stale-PID cleanup. Logs/receipts/worktrees are retained; the operator can archive old data while both jobs are paused. Do not erase the ledger to retry.

The same supervisor clears its own attempt's marker only after observing CLI exit **0** and that attempt's verified-live-success ledger entry, while still holding the lock and before successful-worktree cleanup. This is the normal non-adversarial CLI completion contract, **not** a supported process-ownership receipt proving every descendant is gone. A zero exit without verified live success, nonzero exit (even with a live receipt), timeout, interruption, failed launch, or supervisor death leaves quarantine. If a normally successful CLI is known to leave tools behind, pause scheduling and reconcile those too; do not rely on the success exception as containment.

- `gate`: cheap JSON wake/skip result; lock/content corruption and unresolved-process quarantine fail closed.
- `status`: daily gate (including quarantine reason/path), attempt count, pending checkpoint; an informational snapshot, not a lock acquisition.
- `scan`: complete bounded GitHub snapshot, summary and DATA-file path.
- `prepare --item request-N` (or `roadmap-slug`): requires active supervised attempt; creates/reuses dedicated `auto/ITEM` worktree; read back its path/base.
- `checkpoint --file /absolute/checkpoint.json`: supervised only; same item; stages planned, engineered, reviewed only. Include `item`, `branch`, `worktree`, `base`, `lesson_id`; add `sha`, `pr`, `evidence_file` as known. Retain prior fields when advancing. Save before push/PR and before merge; checkpoint cannot forge merged/live stages.
- `check-local --item ITEM --base SHA`: after staging explicit new allowed files, before commit/push. Reads the worktree and checks scope, deletions, mode, size and substantive lesson changes. Tests should not leave untracked artifacts outside ignored paths.
- `merge --pr N --file /absolute/evidence.json`: requires checkpointed same PR. Reads quality workflow/job evidence; fetches only trusted branch; checks complete PR file list, modes/content/review. Posts and reads `independent-review`, rechecks exact head/base/CI, sends `{sha: HEAD, merge_method: squash}`, and reads the merged PR. No administrator bypass or auto-merge.
- `recover-merged --pr N`: read-back-only on GitHub; recovers a same-item merged PR only with canonical local autonomous merge evidence. Use after an interrupted merge or a crash between live-checkpoint and final receipt where that proof exists; otherwise stop for owner-only reconciliation.
- `verify-live --lesson ID`: verifies same merged PR, successful matching Deploy Pages run, public `release.json` exact merge SHA, and a real Chromium mobile lesson heading, keyboard focus, no horizontal overflow or JavaScript/HTTP errors. Only then writes daily success. It does not submit an issue or grant a review.
- `stamp --sha SHA`: CI-only build helper writes `dist/release.json` with actual built lesson IDs/titles and exact SHA.

Evidence JSON (placeholders must be replaced with real observed values):

```json
{
  "sha": "40 lowercase hex characters from git rev-parse HEAD",
  "base": "40 lowercase hex characters for current main",
  "lead_agent_id": "actual lead session ID",
  "engineer_agent_id": "actual observed engineer CLI session ID",
  "reviews": [
    {"role":"code","agent_id":"actual observed code-review CLI session ID","sha":"same exact head SHA","base":"same exact base SHA","passed":true,"security_concerns":[],"logic_errors":[],"curriculum_concerns":[],"substantive":true,"tests":["actual command and result"],"summary":"verdict"},
    {"role":"curriculum","agent_id":"different observed curriculum-review CLI session ID","sha":"same exact head SHA","base":"same exact base SHA","passed":true,"security_concerns":[],"logic_errors":[],"curriculum_concerns":[],"substantive":true,"tests":["actual sources/lesson checks and outcomes"],"summary":"verdict"}
  ]
}
```

The parser rejects malformed SHA values rather than normalizing them. Every reviewer must pass explicitly with empty findings. Stale head/base invalidates both reviews. Persist full role completion receipts and closed-session exports beside evidence; the public PR needs a concise non-sensitive summary, not raw issue text or private logs.

## Recovery / stop rules

**Abnormal-run operator exception:** unattended recovery stops at quarantine, even when the next daily/recovery tick has budget. Pause BOTH project cron jobs and read back their paused state. Inspect the recorded attempt/log/checkpoint and positively reconcile all work/processes belonging to that run; the marker's supervisor PID is diagnostic only, not a safe kill target or a complete child list. Use project-owned process identities and runtime evidence, not command-name guessing, broad process kills, elapsed time, or a free lock. Resolve any possibly completed remote publishing before retrying. If ownership or termination remains uncertain, leave the marker and scheduling paused.

Only after establishing that the prior run's tools have ended, archive `unresolved-process.json` under an operator-chosen unique receipt name **while holding the existing `run.lock` with `autonomy_runtime.run_lock`**; record the reconciliation evidence alongside it. Do not just delete a marker to retry, do not call `clear_after_success` for an abnormal run, and do not remove/recreate the lock or reset SQLite attempts/releases/checkpoints. Then read `gate` and `status` back before resuming either job. This is an explicit human maintenance operation, not an autonomous reset command; the same daily attempt cap and pending-item recovery requirements still apply.

- **Open PR / dirty owned worktree:** inspect and resume the same item. Never create a replacement merely because a process restarted. Fetch current main; if branch is stale merge main normally, rerun all tests and new independent review. No force push.
- **Closed-unmerged PR:** surface the PR and original request as a human blocker. Do not reopen/overwrite a rejection. Requests in this state remain represented in scan `existing_prs`; they are not completed or silently dropped.
- **Merged but no live receipt:** only recover that merge/deployment with trustworthy local autonomous release provenance. If checkpoint stage is live after a crash, `recover-merged` then rerun `verify-live` under the same provenance gate. Historical owner publication or absent/ambiguous proof => STOP for owner-only reconciliation, not today's contribution. Deployment delay, stale cache, missing manifest, failed browser or newer unexpected deployment => keep pending and report, no second lesson and no fake success.
- **No local ledger / ambiguous remote history:** do not infer today's completion from an old merged marker. Ask operator to reconcile. Back up SQLite using its backup API, not a partial WAL file copy.
- **Timeout, two failures, changed protected paths, denied approvals, missing CLI/auth, unavailable sources, unsafe request or incomplete scan:** stop and preserve evidence. Never weaken rules to meet the daily target.
- **Stop scheduling:** `hermes --profile default cron pause DAILY_ID` and separately `... pause RECOVERY_ID`, then read back `cron list`. To stop an active run, interrupt its supervisor; inspect for surviving project-owned tools before resuming. Do not kill unrelated processes, alter unrelated jobs, or remove a live lock file.

## Reconciling an owner-published pending item

An interactive owner publication can finish outside the daily supervisor while intentionally preserving its failed attempt ledger. That must not leave an already-published item perpetually pending or turn it into a new day's contribution. Before routine binding/recovery, establish trustworthy local autonomous release provenance, not just an exact remote PR, item marker, candidate/base/merge SHAs and checkpoint. Do not infer origin from public text or dates. An already-completed owner publication or missing/ambiguous proof means STOP for owner-only reconciliation before binding or recording daily success.

Both `recover-merged` and direct `verify-live` require the canonical private `evidence-<sha>.json` saved by the normal supervised merge helper. They validate its exact head/base and full independent-review schema against the trusted merged PR and checkpoint; a caller's `evidence_file` path, symlink or fabricated merged stage is not proof. This relies on the trusted operator state directory, not cryptographic attestation against arbitrary local writers. Never manufacture/copy canonical evidence to satisfy the gate. The existing persistence order is protected merge and remote read-back, then canonical evidence write, then merged checkpoint. A crash after evidence persistence or between live checkpoint and final receipt remains recoverable. A crash before proof is saved, partial/malformed proof, or lost state requires operator reconciliation even if GitHub merged successfully; do not move the evidence write before protected release validation to make recovery pass.

Only after that provenance prerequisite may an ordinary active lead use `checkpoint` to bind a missing observed matching PR before `recover-merged`, retaining the complete prior checkpoint, permitted stage and exact head/base. A missing marker requires separately authorized operator correction after identity/review verification; the routine lead must not add one retrospectively.

For a fully reviewed, already merged **and currently live** owner-directed publication, the owner may explicitly authorize `scripts/reconcile_completed.py`. This is **not a cron command, a new supervised attempt or a way to meet today's target**. First follow the abnormal-process reconciliation procedure above; it refuses any unresolved marker, held lock, running attempt or supervised `LWL_ATTEMPT` environment. Preserve the existing pending worktree. Do not invoke it merely because an attempt limit was reached.

Create a private trusted intent JSON with exact `item`, integer `pr`, `lesson_id`, lowercase 40-character `sha`, `base`, `merge_sha`, and a nonempty `authorization` describing the explicit owner request. Do not source authorization from public issue/PR text. Run from the canonical operator checkout:

```sh
python3 scripts/reconcile_completed.py --authorize-existing-publication --file /absolute/private/owner-intent.json
```

Under the same kernel lock it requires a matching pending item/lesson, a clean unchanged same-repository owned worktree, exact trusted merged PR, original successful Quality workflow/job and latest exact-SHA independent-review status, matching successful Pages deployment and fresh real live-browser verification. It makes no GitHub writes, launches no model, skips no approval or CI gate, and does not change source/worktrees. It saves a SQLite backup (including WAL) and full historical checkpoint/live receipt privately before clearing only that completed checkpoint. All attempt and daily release rows remain unchanged. It does **not** mark the old failed engineer complete, claim a new contribution, restore quota, remove quarantine or clean worktrees. Partial/existing archive artifacts, new dirty work, stale deployment or verification failure stop for inspection, not an automatic retry. Read `status` afterward: today's exhausted attempt count must remain exhausted; future work is no longer stuck on the completed item.

The owner helper revalidates exact PR, mutable Quality/latest independent-review/deployment evidence after the browser and again after archival at the clearing boundary. It rechecks owned worktree identity, exact HEAD and dirty state after archives, immediately before clearing. A mismatch retains the checkpoint and any archives for inspection. These sequential observations are not atomic against GitHub changes or arbitrary external worktree writers; archive gate fields describe observations, not a successful clearing receipt.

This path repairs bookkeeping after an owner publication, not planner/engineer latency. A successful historical reconciliation is not proof of a fresh request-to-lesson autonomous cycle; that still requires a separate bounded run and all independent release gates.

## Operator retention maintenance

Implementation worktrees live under the ignored `/Users/tr/little-wonder-lab/.autonomy-worktrees/ITEM`, **not** inside Git metadata. The canonical `.git/autonomy/` location is only for private state/evidence. Vite's default `**/.git/**` protection correctly refuses serving the legacy `.git/autonomy/worktrees/ITEM` layout; leave Vite's deny list intact. Existing legacy paths/receipts are not auto-migrated or deleted: pause both jobs, reconcile processes, hold the run lock, back up the checkpoint, and use `git worktree move` plus an exact checkpoint-path update as reviewed operator maintenance before resuming. Preserve attempt counts and failure history.

After verified live success, while still holding the supervisor lock, the runner removes only exact registered, clean agent-owned worktrees whose branch, HEAD and successful live receipt match. Normal `git worktree remove` also removes ignored dependencies; `--force` is never used. Dirty, failed, pending, locked, changed or ambiguous worktrees are retained and reported, not recursively deleted. Receipts, logs, ledger and branches remain available. Optional long-term log archiving requires pausing BOTH project jobs and using the SQLite backup API; never delete ledger rows to regain attempts or touch unrelated repositories/profiles.

## Verification commands

```sh
python3 -m unittest discover -s tests/automation -v
node --test tests/automation/*.test.js
npm test
npm run build
npm run test:e2e
```

Python tests exercise real temporary SQLite, OS locks/child timeouts, temporary Git repositories/worktrees, policy decisions and offline GitHub-boundary fixtures. Portable runtime regressions launch real separate-session subprocesses with closed inherited descriptors, prove tools survive timeout or abrupt supervisor death, reacquire the lock, and verify future-date quarantine. CLI tests verify supervisor/gate/status refuse quarantine before reserving another attempt and successful clearing precedes worktree cleanup. Node automation tests launch real Chromium against a local HTTP fixture and reject stale manifests/browser errors. Fixture API responses are tests, never claimed as live GitHub results. Remote publishing/scheduling verification belongs to the operator's first real run.

Optional installed-backend regressions run the actual `LocalEnvironment._run_bash` launch site, offline with a temporary Hermes home and a minimal shell environment. Set `LWL_HERMES_SOURCE` to an installed source checkout and run `python -m unittest discover -s tests/automation -p test_runtime.py -v` using that installation's Python environment. Without explicit opt-in these tests skip; the portable equivalents always run. Each regression kills only its own recorded test process groups afterward. Neither test launches a model conversation or proves the full CLI graceful-shutdown path.
