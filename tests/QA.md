# Frontend QA handoff

**Target:** built production artifact at `http://127.0.0.1:4174/little-wonder-lab/`
**Scope:** Explore, every current JSON lesson, lesson models, adult request form, optional progress, print styles, keyboard and responsive layout.
**Tester:** frontend specialist, automated Chromium plus screenshot inspection.

## Current integration status

The fresh geometry repair is now applied. Parent reran `npm test` (**17 passed**) and `npm run test:e2e` (**22 passed**, desktop/mobile Chromium), plus a successful production build. The bridge deck/walls have nonzero parsed geometry; the ramp keeps its board length, floor pivot, release fraction and support contact at both heights. Final independent publication review and remote deployment verification are tracked separately; local green tests are not evidence of live publication.

The pre-fix handoff below is retained as historical evidence, not current test status.

## Historical frontend handoff

**Publication remains blocked by the independent curriculum review.** The parent reassigned `src/interactions.js`, `src/models.js` and related interaction tests to a fresh fix context. They are frozen by this specialist.

The last complete pre-freeze green suite had 17 node tests and 18 Playwright tests passing. Immediately before the freeze, a new ramp-support assertion was added to `tests/models.test.js`; it is RED because `supportTop` does not exist. The most recent `npm test` has **16 passed, 1 failed**. During the final E2E run, the fresh fix context added `tests/e2e/geometry.spec.js`: the resulting suite has **20 passed, 2 failed**, both failures proving the ramp-length invariant is broken at desktop and mobile widths. The new bridge geometry tests pass. This is not a releasable green state.

## Open findings / fresh fix ownership

| Finding | Severity | Category | Evidence / next owner |
|---|---|---|---|
| Raising the ramp changes its drawn board length instead of keeping the same ramp | High | Science / model | Parent's independent curriculum review; fresh interaction fix context |
| Ramp board visually floats above the book support | Medium | Visual / teaching | `ramp-racers-desktop.png`; pending `tests/models.test.js:24` assertion; fresh interaction fix context |

The pending support test assumes the old fixed horizontal geometry. The fresh fix context should replace it with the correct constant-length and support-contact invariants rather than preserve the incorrect geometry merely to satisfy this assertion.

## Findings corrected before handoff

1. **Bridge SVG parser errors — high / functional.** Reproduce by opening `#lesson/paper-bridge`, placing the spoon, then choosing folded sides. Missing separators produced paths such as `Q310 209478 157`; text feedback changed but paths did not render correctly. Spaces were added between coordinates **before the freeze**. A real Playwright console regression failed first, then passed. Every E2E flow now fails on both `pageerror` and console `error`, including SVG parser errors. The fresh review should independently confirm the correction.
2. **Illustration/activity mismatch — medium / content.** All catalog and lesson art now shows an open hand and desk lamp, a two-book ramp, and a two-fold U-channel bridge with a full-size spoon. Coins and accordion folds were removed from bridge art. Semantic illustration tests failed before this correction and now pass.
3. **Undersized mobile navigation and adult prerequisite links — medium / accessibility.** The production audit measured the wordmark at 36px tall, Explore at 38px wide, and expanded prerequisite links at 17px tall. Minimum target dimensions were corrected. Final audit includes expanded adult guidance and passes at all three widths.
4. **Cropped bridge annotation — low / visual.** The narrow desktop illustration frame clipped the annotation. The annotation was shortened, and the production audit now checks SVG text bounds against illustration frames.

## RED → GREEN evidence

Tool runs observed each missing vertical behavior before implementation:

- Catalog selection helper missing, and Explore heading absent → helper and desktop/mobile catalog-to-lesson flow passed.
- Shadow model/slider absent → keyboard Home/End changed visible shadow and qualitative text.
- Ramp model/controls absent → both stopping markers retained and clear action passed.
- Bridge model/controls absent → same spoon with two paper shapes and removal passed.
- Request validation/URL helper absent and parent page heading absent → validation, explicit public consent, URL encoding, no-send state, stale-draft clearing and reload privacy passed.
- Optional progress store/control absent → opt-in, reload persistence, forget, and blocked-storage flows passed.
- All hands-on directions initially visible (6 instead of 1) → step navigation and all-step print visibility passed.
- Latest publication helper/control absent → real publication date, newest ordering, filters and empty-state reset passed.
- Curriculum validator missing → complete contract, graph cycle, identifier, source protocol and supported-kind tests passed.
- Malformed SVG console errors reproduced by the added automatic browser fixture → corrected drawing passed.

## Final visual audit

`npm run build` passes. `node tests/visual-audit.mjs` passes against the production bundle after the non-overlapping CSS fixes. It visited all lessons, Explore, request and not-found routes at **1440, 390 and 320px** using one browser. No horizontal overflow, cropped illustration text, undersized enabled targets, console errors or third-party requests were detected by that audit. It does not prove the ramp's science invariant, which remains open above.

Screenshots inspected directly:

- `/Users/tr/.hermes/cache/lwl-final/explore-desktop.png`
- `/Users/tr/.hermes/cache/lwl-final/explore-mobile.png`
- `/Users/tr/.hermes/cache/lwl-final/paper-bridge-desktop.png`
- `/Users/tr/.hermes/cache/lwl-final/ramp-racers-desktop.png`
- `/Users/tr/.hermes/cache/lwl-final/request-mobile.png`

All ten desktop/mobile page captures and `audit.json` are in that cache directory. The final default Explore screenshots are unobscured; earlier full-page captures taken after exercising the skip link had a capture-only fixed-position artifact, avoided by capturing the default page before keyboard testing.

## Limits

- Chromium desktop and mobile emulation were exercised; physical Safari/iOS, Firefox, assistive-technology sessions and physical printing were not tested.
- Print CSS, print invocation, all-step visibility and expanded adult guidance were tested in Chromium; no physical printer was used.
- No GitHub issue was submitted and no remote repository writes or commits were made. The request flow's fixed composer URL, public warnings and explicit final GitHub step were verified locally.
- `npm audit` returned zero vulnerabilities. Runtime has no third-party dependencies; Vite and Playwright are development-only.
- Parent owns automation/Python test results and final independent review/deployment.
