# Little Wonder Lab — visual and interaction design

## Surface

**Explore** is the primary surface: a warm illustrated field notebook. A large first investigation sits beside a smaller shelf of discoveries. Mobile becomes a single, ordered illustrated column. Preserve this asymmetry; do not replace it with a dashboard or equal-weight feature tiles.

The child-facing path is: choose a wonder → play with one qualitative idea → predict → gather materials with a grown-up → follow one hands-on step at a time → notice → ask another question. Expandable adult guidance holds context and sources. Nothing is locked behind completion.

## Visual vocabulary

| Token | Value | Use |
|---|---|---|
| Paper | `#f7f3e8` | Warm page; faint dot texture |
| Ink | `#293f32` | Botanical text, actions, outlines |
| Muted | `#586353` | Secondary adult-facing notes |
| Vermilion | `#b64025` | Questions, active state, annotations |
| Rule | `#c9cdbb` | Fine notebook dividers |
| Soft paper | `#ececdd` | Quiet secondary surfaces |
| Display | Georgia / Times New Roman | Editorial headings and handwritten-style italics |
| Body | Trebuchet MS / Verdana | Deliberately warm, readable system type |

There are no CDN fonts, stock photographs, external illustration requests, analytics, or runtime dependencies. All drawings in `src/illustrations.js` are original SVGs. The flower wordmark, lamp and waving hand, two-book car ramp, and spoon on a folded-side paper bridge share botanical ink and restrained pigment fills. The art must match the materials and safe activity, not suggest alternative small loads.

## Responsive and accessible behavior

- Semantic navigation, one page heading, main landmark, working keyboard skip link, visible focus ring.
- Native buttons, labelled range input, selected-state buttons, labelled form fields and errors, polite model/progress announcements.
- Navigation, controls and parent prerequisite links have at least 44px interaction targets. Checkbox labels provide the larger target.
- Layout audited at 1440px, 390px and 320px. SVG annotations must not be cropped by their illustration frames.
- Reduced motion removes transitions and the optional car animation. Motion never carries the only explanation.
- Hands-on steps are progressively revealed. Print reveals every step, safety instructions, vocabulary and adult guidance, plus blank prediction/observation lines. Print copy is at least 12pt.

## Product behavior

- Routes: `#explore`, `#lesson/<exact-id>`, `#request`. Unknown lesson IDs have a friendly recovery page.
- Catalog counts, topics and latest publication are derived from `src/data/lessons.json`. The latest note links directly to the lesson and displays its real publication date. `Newest first` supports a growing catalog without a fixed-size assumption.
- Search matches every entered word against child-facing lesson metadata; topic filters combine with it. Empty results offer a reset.
- Each science kind owns a bespoke interactive renderer. Models are qualitative, not real measurements or universal physical predictions. Same-object/fair-test invariants must remain true in the drawing as controls change.
- Requests first prepare a URL-encoded draft to the fixed repository issue composer. A second, explicit link opens GitHub. The grown-up must sign in, review, and choose **Submit new issue** there. Preparing the URL is not submission. Inputs are not saved by this site.
- Progress has a separate, unchecked opt-in. Only allowed lesson IDs and the opt-in flag are stored under `little-wonder-lab:progress:v1`; no names, answers, dates, accounts or analytics. Storage denial/corruption does not break lessons. Forget removes only that key.

## Module map

- `src/main.js`: page shell, routes, catalog and lesson composition.
- `src/catalog.js`: search/filter/order/latest helpers.
- `src/illustrations.js`: original catalog and lesson artwork.
- `src/interactions.js`, `src/models.js`: per-kind experiments and pure qualitative models.
- `src/notebook.js`: step navigation and print lifecycle.
- `src/request.js`: validation, fixed GitHub draft URL and parent form.
- `src/progress.js`: storage-safe optional completion.
- `src/schema.js`: content contract and dependency-graph test gate.
- `src/styles.css`: layered base, components, breakpoints, print and reduced motion.

## Adding a lesson

Content authors own the JSON. Do not duplicate lesson copy in UI source. Existing kinds require matching science and art; new kinds need an intentional renderer, illustration, `SUPPORTED_KINDS` entry and corresponding model/browser tests. Validation checks complete fields, literal slugs, unique IDs/orders, dates, valid prerequisites, acyclic dependency graph, supported kinds and safe source URLs. Tests derive catalog sizes from JSON rather than expecting exactly three lessons.

## Verification commands

```sh
npm ci
npx playwright install chromium
npm test
npm run test:e2e
npm run build
npm run preview -- --host 127.0.0.1 --port 4174
# In another terminal, against the built production artifact:
node tests/visual-audit.mjs
```

`npm test` includes frontend node:test files and the automation specialist's JavaScript tests. Python automation tests are separate. `test:e2e` uses one Playwright worker for desktop and mobile Chromium projects, the same `/little-wonder-lab/` base as production, and automatic console/page-error checks. The visual audit visits every JSON lesson plus Explore, requests and a missing route at three widths; it verifies no third-party requests, no overflow, uncropped SVG annotations, 44px targets including expanded adult guidance, and keyboard skip navigation.

## Design self-audit

Slop diagnostic: **0/10** after visual inspection. The composition is an Explore catalog with a clear first investigation, not a marketing center-stack or a feature-tile dashboard. No tech gradients, generic violet, glass, accent rails, monument statistics, icon toppers or default software typography. See `tests/QA.md` for the separate functional/review status; visual approval does not imply scientific correctness.
