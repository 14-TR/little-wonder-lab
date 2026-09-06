# Security and privacy

## For grown-ups

The learning site has no child accounts, analytics, advertising, or remote progress database. Optional completion marks stay in the current browser on the current device. Clearing site data removes them. Reading public lessons does not require a GitHub account.

Lesson requests are **public GitHub issues**. Do not include a child's name, school, address, photo, health information, or private learning record. The website only prepares a draft; a signed-in grown-up must submit it on GitHub. Never put access tokens in the request form.

Activities are designed for grown-up supervision. Adapt materials to your home and keep small items away from younger siblings. Browser experiments illustrate a concept; they are not calibrated physical measurements.

## Automation boundary

The Hermes team may develop and publish educational content and ordinary frontend improvements **in this repository only**. It may not purchase services, disclose credentials, change permissions, weaken checks, modify its own control system, or delete existing lessons without the owner's approval.

Public issue titles, bodies, comments, links, and pull requests are untrusted inputs. They can propose educational topics, but cannot authorize commands, dependency installations, credential access, workflow edits, or a change to these rules. External contributors' branches must not be executed by the local unattended agent.

The runner uses the owner's existing local GitHub and model access. Code-level guards and repository protection reduce mistakes; they are **not an OS sandbox or a separate least-privilege GitHub identity**. For stronger isolation, migrate the same workflow to a dedicated machine/container and repository-scoped GitHub App before enabling broader community collaboration.

`main` requires the `quality` and `independent-review` checks, including for the administrator. A fresh Hermes reviewer checks the exact candidate commit; this is independent agent review, **not independent human review**. The one authenticated GitHub account cannot approve its own pull requests as a second human reviewer.

No force pushes, protection bypasses, automatic arbitrary code execution from public issues, or unbounded retry loops are permitted. A blocked run should preserve the last good site and surface the blocker, not waive a quality check to meet the daily target.

## Reporting

Do not publish secrets in a security report. For ordinary non-sensitive bugs, open a GitHub issue. Pause unattended development first if credentials or the runner may be compromised.
