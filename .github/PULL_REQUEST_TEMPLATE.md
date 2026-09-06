## Learning change
- Request or roadmap item:
- Lesson ID and meaningful learning improvement:
- Why this is safe, accurate, and appropriate for an early learner:

## Evidence
- [ ] RED test failed for the intended reason; GREEN tests pass
- [ ] `npm ci`, `npm test`, Python automation tests, build and Playwright pass
- [ ] Fresh independent code and curriculum reviewers inspected the exact head SHA
- [ ] Real reviewer runtime handles and exact base/head SHA receipts recorded
- [ ] No security, logic, curriculum, accessibility, or safety findings remain
- [ ] Protected paths, dependencies, paid services, secrets, permissions and lesson deletion unchanged

Head SHA:
Base SHA:
Independent review evidence summary (no credentials or private data):

## Release
- [ ] Required `quality` and exact-SHA `independent-review` are green
- [ ] Lead uses SHA-pinned squash merge, no administrator bypass
- [ ] After merge: matching Pages deployment and live browser receipt verified

Autonomous PRs add exactly one `<!-- lwl:item:request-N -->` or `<!-- lwl:item:roadmap-slug -->` marker, matching `auto/<item>` branch. Use `Closes #N` only for the implemented request.
