# gstack Project-Local Usage Notes

Date: 2026-05-28
Project: `/Users/tanglin/VibeCoding/VoiceAgents`

## Current Status

This project is now a git repository:

```bash
cd /Users/tanglin/VibeCoding/VoiceAgents
git rev-parse --show-toplevel
```

Expected output:

```text
/Users/tanglin/VibeCoding/VoiceAgents
```

This matters because the generated gstack Codex skills use `git rev-parse --show-toplevel` to locate the repo-local runtime at:

```text
.agents/skills/gstack
```

Before `git init`, skills such as `$gstack-office-hours` could not reliably find the project-local install and would fall back toward non-existent/global paths.

## What Was Verified

### 1. `$gstack-office-hours` exists

The repo-local Codex skill exists at:

```text
.agents/skills/gstack-office-hours/SKILL.md
```

It is a symlink into:

```text
.agents/skills/gstack/.agents/skills/gstack-office-hours/
```

The generated skill frontmatter name is:

```yaml
name: office-hours
```

### 2. `$gstack-office-hours` preamble runs with project-local environment

Run:

```bash
cd /Users/tanglin/VibeCoding/VoiceAgents

awk '/^```bash$/{flag=1;next} /^```$/{if(flag) exit} flag{print}' \
  .agents/skills/gstack-office-hours/SKILL.md \
| env \
  HOME=/Users/tanglin/VibeCoding/VoiceAgents/.gstack-home \
  GSTACK_HOME=/Users/tanglin/VibeCoding/VoiceAgents/.gstack \
  GSTACK_STATE_DIR=/Users/tanglin/VibeCoding/VoiceAgents/.gstack \
  PATH=/Users/tanglin/VibeCoding/VoiceAgents/.bun/bin:/Users/tanglin/.nvm/versions/node/v24.15.0/bin:/usr/local/bin:/usr/bin:/bin \
  zsh -s
```

Observed successful signals:

```text
BRANCH: main
PROACTIVE: true
TELEMETRY: off
LEARNINGS: 0
HAS_ROUTING: no
VENDORED_GSTACK: yes
CHECKPOINT_MODE: explicit
GSTACK_PLAN_MODE: inactive
```

`VENDORED_GSTACK: yes` is expected for this local-only installation shape: the gstack runtime is intentionally present inside `.agents/skills/gstack` for this working copy.

### 3. `$gstack-office-hours` Phase 1 commands run

Run:

```bash
cd /Users/tanglin/VibeCoding/VoiceAgents

env \
  HOME=/Users/tanglin/VibeCoding/VoiceAgents/.gstack-home \
  GSTACK_HOME=/Users/tanglin/VibeCoding/VoiceAgents/.gstack \
  GSTACK_STATE_DIR=/Users/tanglin/VibeCoding/VoiceAgents/.gstack \
  PATH=/Users/tanglin/VibeCoding/VoiceAgents/.bun/bin:/Users/tanglin/.nvm/versions/node/v24.15.0/bin:/usr/local/bin:/usr/bin:/bin \
  zsh -lc 'GSTACK_ROOT=$(git rev-parse --show-toplevel)/.agents/skills/gstack; GSTACK_BIN="$GSTACK_ROOT/bin"; eval "$($GSTACK_BIN/gstack-slug 2>/dev/null)"; echo "SLUG=$SLUG"; echo "DESIGN_DOCS:"; ls -t ~/.gstack/projects/$SLUG/*-design-*.md 2>/dev/null || echo "none"; echo "LEARNINGS:"; $GSTACK_BIN/gstack-learnings-search --limit 10 2>/dev/null || true'
```

Observed:

```text
SLUG=VoiceAgents
DESIGN_DOCS:
none
LEARNINGS:
```

This proves `$gstack-office-hours` can locate the project runtime and run its project-context discovery commands.

### 4. gstack browser runtime also works

Run:

```bash
cd /Users/tanglin/VibeCoding/VoiceAgents

env \
  HOME=/Users/tanglin/VibeCoding/VoiceAgents/.gstack-home \
  GSTACK_HOME=/Users/tanglin/VibeCoding/VoiceAgents/.gstack \
  PATH=/Users/tanglin/VibeCoding/VoiceAgents/.bun/bin:/Users/tanglin/.nvm/versions/node/v24.15.0/bin:/usr/local/bin:/usr/bin:/bin \
  /Users/tanglin/VibeCoding/VoiceAgents/.agents/skills/gstack/browse/dist/browse status
```

Observed:

```text
Status: healthy
Mode: launched
URL: about:blank
Tabs: 1
```

The browser verification page used for interaction testing is:

```text
problems/gstack-verification-page.html
```

The screenshot evidence is:

```text
problems/gstack-verification-screenshot.png
```

## How To Use gstack In This Project

Prefer generated gstack skills, not the root `$gstack` skill.

Use:

```text
$gstack-office-hours
$gstack-browse
$gstack-qa
$gstack-review
$gstack-autoplan
```

Avoid:

```text
$gstack
```

Reason: `.agents/skills/gstack` is both the runtime root and a source checkout. Its root `SKILL.md` contains Claude-oriented paths. The generated `gstack-*` skills are the Codex-compatible entry points.

## Required Environment For Manual Commands

When running gstack commands manually, use project-local env vars:

```bash
cd /Users/tanglin/VibeCoding/VoiceAgents

env \
  HOME="$PWD/.gstack-home" \
  GSTACK_HOME="$PWD/.gstack" \
  GSTACK_STATE_DIR="$PWD/.gstack" \
  PATH="$PWD/.bun/bin:/Users/tanglin/.nvm/versions/node/v24.15.0/bin:/usr/local/bin:/usr/bin:/bin" \
  <gstack-command>
```

Examples:

```bash
env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" \
  "$PWD/.agents/skills/gstack/browse/dist/browse" status
```

```bash
env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" \
  "$PWD/.agents/skills/gstack/bin/gstack-config" get telemetry
```

## If The Project Is Not A Git Repo

Initialize it before using repo-local gstack:

```bash
cd /Users/tanglin/VibeCoding/VoiceAgents
git init
```

Then verify:

```bash
git rev-parse --show-toplevel
```

Expected:

```text
/Users/tanglin/VibeCoding/VoiceAgents
```

Without a git repo, generated skills may not find `.agents/skills/gstack` and may incorrectly fall back to global paths.

## Git Ignore Policy

This repo now has `.gitignore` entries for local tooling and runtime state:

```text
.bun/
.gstack/
.gstack-home/
.agents/skills/gstack/
.agents/skills/gstack-*
```

This keeps the project-local gstack install usable in this working copy without accidentally committing Bun, Playwright caches, gstack runtime files, or generated skill symlinks.

## Current Limitation

`$gstack-office-hours` is an interactive skill. Its full workflow eventually requires `AskUserQuestion`. In this Codex tool environment, no callable AskUserQuestion variant is available in the tool list, so the complete guided office-hours conversation cannot be fully executed by shell commands alone.

What is verified:

- The skill is discoverable on disk.
- Its generated Codex entrypoint exists.
- Its preamble runs.
- It resolves `GSTACK_ROOT` to the project-local install after `git init`.
- Its Phase 1 context commands run.

What still depends on the host UI:

- Completing the interactive office-hours question flow.
- Writing the final design doc after user choices.
