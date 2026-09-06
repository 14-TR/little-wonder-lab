# Little Wonder Lab

**Small experiments. Big discoveries.** An illustrated STEM exploration book for curious children around age seven and the grown-ups learning with them.

- **Explore:** https://14-tr.github.io/little-wonder-lab/
- **Request a lesson:** https://14-tr.github.io/little-wonder-lab/#request
- **Request queue:** https://github.com/14-TR/little-wonder-lab/issues?q=is%3Aissue+is%3Aopen+label%3Alesson-request
- **Learning roadmap:** [docs/ROADMAP.md](docs/ROADMAP.md)

## The book

Start with **Shadow Detective**, investigate **Ramp Racers**, then build a **Paper Bridge**. Each lesson has its own original illustrated experiment, a prediction, a safe hands-on activity, a small idea to take away, and notes for grown-ups. The sequence is a suggestion, not an age test or a locked learning track.

Reading lessons needs no account. Optional completion marks stay on the current device. There are no ads, analytics, child profiles, or streaks.

### Ask for something new

Use **Request a lesson** on the site, describe the topic, and continue to GitHub. Sign in, review the public issue draft, and press **Submit new issue** there. The form does not submit automatically. Do not include identifying information about a child.

Requests take priority over the roadmap. The team can adapt a topic into a safe, age-appropriate lesson instead of following a request literally. A request is educational input, never permission to run arbitrary commands.

## Run locally

Requires Node.js 22.12 or newer and Python 3.11 or newer. Production is static HTML, CSS, JavaScript, JSON, and original SVG artwork; there is no application server or browser API credential.

```sh
npm ci
npx playwright install chromium
npm run dev -- --host 127.0.0.1
```

Open the local URL with `/little-wonder-lab/` at the end.

```sh
npm test
python3 -m unittest discover -s tests/automation -v
npm run test:e2e
npm run build
```

## How the book grows

A local Hermes lead coordinates curriculum planning, illustration/frontend engineering, and fresh independent quality review. The team maintains issues and the roadmap, opens a pull request, checks CI, squash-merges the reviewed commit, and verifies the deployed site.

**The daily target is a meaningful new lesson or a substantial lesson improvement—not a timestamp-only commit.** Failed tests or reviews block publication. Local automation requires its Mac to be awake, logged in, online, and able to access the configured model and GitHub account.

See [the operating guide](docs/AUTONOMY.md) for schedules, bounded retries, pause/recovery commands, and evidence. Control-system and permission changes require the owner; ordinary curriculum and frontend work do not.

## Contribute safely

- [Curriculum principles](docs/CURRICULUM.md)
- [Visual design](docs/DESIGN.md)
- [Project instructions](AGENTS.md)
- [Security and privacy](SECURITY.md)

Content is AI-authored and independently agent-reviewed, not certified curriculum. A grown-up should supervise activities and adapt them to the learner. Interactive models are simplified illustrations, not laboratory measurements.

MIT licensed. External learning references retain their own copyrights; source links are references, not copied artwork.
