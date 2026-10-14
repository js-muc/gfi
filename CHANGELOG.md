# Changelog

All notable changes to this project will be documented in this file.

## [0.1.1] - 2026-10-11

24 commits of hardening since 0.1.0. No new commands; the focus was making the
existing surface safe for scripted use and honest about its own failures.

### Added

- `ROADMAP.md` — consolidated view of proposed vs. completed work.
- A warning on stderr when `--limit` exceeds the 1000-result ceiling the GitHub
  search API imposes, instead of silently returning fewer results (#100).

### Changed

- `gfi feed` now marks issues as seen in `--json-output` and `--csv` mode, not
  just the human-readable table. Those two branches returned before the marking
  loop ran, so scripted callers received their payload but the seen cache never
  grew and every run handed back the same issues — the queue never drained.
  The payload is written before marking, so an issue is only consumed once it
  has actually been delivered (#72).
- `--json-output` and `--csv` no longer write the progress spinner or status
  prose to stdout. Machine-readable output now goes to stdout and human-facing
  messages to stderr, so the documented `gfi search --json-output | jq ...`
  pipeline works unfiltered.
- An empty result set is now valid in machine formats: `--json-output` prints
  `[]` and `--csv` prints just the header row, instead of a sentence that broke
  the consumer's parser.
- `trending` preserves per-topic results instead of truncating them against a
  global limit (#77, #102).
- The `--language` filter is case-insensitive (#87).
- `--limit` is capped at 1000 up front rather than letting `gh` reject the call
  (#93).
- `gfi open` reports a failure when the browser opener is missing or exits
  non-zero, instead of exiting 0 over a page that never opened (#101).
- A missing `gh` binary produces a clear message rather than a traceback (#95).
- `gh gfi --version` prints the version instead of falling through to help text
  (#98).

### Fixed

- **CSV formula injection (CWE-1236).** Issue titles beginning with `=`, `+`, `-`
  or `@` are neutralised in `--csv` output so a spreadsheet cannot be induced to
  execute them (#96).
- Every CSV field is quoted, so an embedded CR can no longer split one row into
  two.
- Search qualifier values are no longer double-escaped, which had been sending a
  literal backslash to the API (#82).
- User-supplied search terms are quoted so GitHub treats them as data rather than
  as query syntax (#73).
- The `/` separator is preserved when building repository API endpoints, so
  `owner/name` queries no longer 404 (#81).
- `gh gfi` is installable as a GitHub CLI extension, and the PATH-dependent test
  that hid this now fails for the right reason (#78).
- Issue titles and repository names are rendered as literal text, so a title
  containing Rich markup syntax is no longer swallowed by the renderer (#86).

### CI

- The lint gate runs a real `ruff check` against a pinned version and rule set,
  replacing a step that could not fail (#74, #79).
- Coverage is enforced in pytest config: `fail_under=60`, raised to 78 (#70,
  #74).
- Generated `egg-info` metadata is no longer tracked.

## [0.1.0] - 2026-10-01

- Initial release.
