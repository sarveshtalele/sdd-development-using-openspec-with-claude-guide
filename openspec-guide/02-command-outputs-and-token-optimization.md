# OpenSpec Command Outputs and Token Optimization

*A companion reference to [Openspec-Documenetation.md](Openspec-Documenetation.md):
exactly what each `/opsx:*` command generates, what a human has to review or edit by
hand afterward, and how to keep token consumption down while running the workflow.
Every claim in this document was verified against a real `openspec init --tools claude`
run on OpenSpec v1.5.0 — see `travel-itinerary-agent/BUILD-LOG.md` in this repository
for the full, real, slash-command-by-slash-command build this document was drawn from.*

## 1. Purpose of This Document

The main OpenSpec documentation describes the workflow and the commands. This document
goes one level deeper, into what actually lands on disk after each command runs, which
parts of that output are safe to trust as-is, and which parts consistently need a human
pass before moving on. It closes with concrete practices for keeping token consumption
down while working this way.

## 2. What's Actually Underneath /opsx:propose, /opsx:apply, and /opsx:archive

Before the per-command breakdown, one structural fact worth knowing: the `/opsx:*`
slash commands are not themselves where the artifact templates or task-tracking logic
live. Each one wraps a small number of public `openspec` CLI subcommands, and those
subcommands are directly callable too:

| CLI command | What it returns |
|---|---|
| `openspec new change "<name>"` | Scaffolds a new change directory under `openspec/changes/<name>/`. |
| `openspec status --change "<name>" --json` | The artifact dependency graph, which artifacts are `ready`/`blocked`/`done`, and the resolved file paths for each. |
| `openspec instructions <artifact-id> --change "<name>" --json` | The exact template, any project `context` and `rules` from `openspec/config.yaml`, and the resolved output path for one specific artifact. |
| `openspec instructions apply --change "<name>" --json` | The task checklist parsed out of `tasks.md`, with progress counts. |
| `openspec validate "<name>"` | Checks spec formatting (for example, that scenarios use exactly four `#### ` hashtags) before anything downstream depends on it. |
| `openspec archive "<name>" --yes` | Merges delta specs into `openspec/specs/`, and moves the change directory into `openspec/changes/archive/YYYY-MM-DD-<name>/`. |

Knowing this matters for two practical reasons: these commands can be run directly from
a terminal to inspect state without spending a conversational turn asking Claude to
describe it, and `openspec instructions` is what actually injects your
`openspec/config.yaml` `context` and `rules` into every artifact — which is the basis
for the first token-optimization practice in Section 4.

## 3. Per-Command Reference

### 3.1 `/opsx:explore`

**Generates**: nothing, by design. This is a thinking mode — reading files and
discussing is expected, writing files is not, unless you explicitly ask for a note to
be captured somewhere.

**What to review/edit**: nothing is produced to review. The output that matters is
conversational — decisions and constraints that should be carried into the next
`/opsx:propose` call. If a real decision was made, it's worth stating it explicitly in
the next command's input rather than assuming it will be remembered turn-to-turn.

### 3.2 `/opsx:propose`

**Generates**, in this order (later ones depend on earlier ones being done first):
- `openspec/changes/<name>/proposal.md`
- `openspec/changes/<name>/design.md` and `openspec/changes/<name>/specs/<capability>/spec.md` (these two unlock together, both depending only on the proposal — not necessarily produced strictly one after the other)
- `openspec/changes/<name>/tasks.md` (depends on both design and specs)

**What to review/edit before moving on to `/opsx:apply`**:
- `proposal.md` — check the **Capabilities** section specifically. It is the contract
  between the proposal and the spec files; a wrong or missing capability name here
  means the wrong spec file gets created or updated.
- `specs/<capability>/spec.md` — check that every requirement has at least one scenario
  and that scenario headers use exactly four `#` characters (`#### Scenario: ...`).
  Three hashtags fails silently rather than raising an error — this is the single most
  common formatting mistake, and `openspec validate "<name>"` catches it for free
  before it costs a wasted `/opsx:apply` cycle.
- `tasks.md` — check that each task is genuinely small and independently verifiable,
  and keep each checkbox's description on a single line. The apply-progress view only
  displays a checkbox's first line; a task description that wraps onto a second line in
  the file will show truncated in `openspec instructions apply --json` output (and
  therefore in whatever progress summary gets shown to you), even though the file
  itself is unaffected.

### 3.3 `/opsx:apply`

**Generates**: whatever the tasks in `tasks.md` actually call for — this is the one
command whose output isn't a fixed set of OpenSpec artifact files, it's your project's
real source code. The one file inside `openspec/` it modifies is `tasks.md` itself,
where each completed task's `- [ ]` is flipped to `- [x]`.

**What to review/edit**:
- The actual code changes — read them, don't just trust the "task complete" checkbox.
  A checkbox being marked `[x]` means the agent believes the task is done, not that it
  has been independently verified.
- Run whatever tests exist. If a task's own definition of done included verification
  (as it should — see Section 4), confirm that verification actually ran and actually
  passed, rather than being described as having passed.
- Watch for a `state: "blocked"` result from `openspec instructions apply` — this means
  an artifact `/opsx:apply` depends on isn't finished yet, and the fix is to go back to
  `/opsx:propose` or `/opsx:continue` (expanded profile), not to force the apply step.

### 3.4 `/opsx:sync`

**Generates/modifies**: `openspec/specs/<capability>/spec.md` — the durable, main spec
tree — merged in from the change's delta spec, without moving or archiving anything.

**What to review/edit**: the merge is described as "intelligent" — it adds a scenario
without requiring the whole requirement to be copied, for instance — which means it is
also worth a specific read after running, since a merge that goes slightly wrong (a
scenario attached to the wrong requirement, for example) is easy to miss if you assume
the operation was purely mechanical.

### 3.5 `/opsx:archive`

**Generates/modifies**:
- Creates (or updates) `openspec/specs/<capability>/spec.md` — the same merge `/opsx:sync`
  performs, run automatically as part of archiving if you confirm it.
- Moves the entire change directory to `openspec/changes/archive/YYYY-MM-DD-<name>/`.

**What to review/edit — this one is concrete and observed, not hypothetical**: when
`/opsx:archive` creates a brand-new capability's main spec file for the first time (as
opposed to merging into one that already exists), the `## Purpose` section is written
as a placeholder — literally `TBD - created by archiving change <name>. Update Purpose
after archive.` — and nothing in the archive step itself replaces that placeholder with
real content. This is the one edit that reliably has to be made by hand after archiving
a change that introduces a new capability. See
`travel-itinerary-agent/openspec/specs/travel-itinerary/spec.md` in this repository for
exactly this, before and after the fix.

## 4. Best Practices for Optimizing Token Consumption

- **Fill in `openspec/config.yaml`'s `context` and `rules` block once, before the first
  `/opsx:propose`, instead of repeating project context in every conversation.** Every
  artifact's `openspec instructions` output includes this block automatically. Writing
  it once — tech stack, domain, and any per-artifact rules — means every subsequent
  proposal, design, spec, and task list is generated with the right context the first
  time, instead of being generated generically and then corrected by hand, which costs
  a full extra round trip per correction.
- **Run `openspec validate "<name>"` right after the spec file is written, before
  `/opsx:apply`.** It is a fast, local check with no model call involved, and it catches
  the exact formatting mistakes (wrong hashtag count, missing scenarios) that would
  otherwise surface much later — typically during `/opsx:apply` or `/opsx:archive` —
  where fixing them costs a full re-generation of downstream artifacts instead of one
  small correction.
- **Keep `proposal.md` and `design.md` as short as their own instructions ask for.**
  The `proposal` artifact's own generation instructions specify "1-2 pages," and
  `design.md` explicitly says to create it only when the change is genuinely
  cross-cutting, introduces a new dependency, or carries real risk — not for every
  change. A one-file, low-risk change does not need a design document at all; skipping
  it when it isn't warranted avoids paying to generate and then read a document with
  no real decisions in it.
- **Review all artifacts from `/opsx:propose` in one pass, rather than after each
  individual file.** The command already creates all of them in one guided pass; batching
  your review into a single round trip avoids re-establishing context on every turn.
- **Keep each task in `tasks.md` on a single line.** Beyond the display truncation
  noted in Section 3.2, a task description that's genuinely one line is also a signal
  that the task itself is appropriately small — the same discipline that makes tasks
  independently verifiable also keeps each `/opsx:apply` turn focused and short.
- **Prefer `/opsx:propose` over the expanded step-by-step
  `/opsx:new` → `/opsx:continue` → `/opsx:continue` → `/opsx:continue` sequence for
  ordinary changes.** Both produce the same four artifacts; the step-by-step path adds
  a confirmation round trip per artifact, which is only worth paying for when you
  specifically want to stop and redirect between artifacts.
- **Scope `/opsx:explore` to a specific question rather than an open-ended prompt.**
  Explore mode has no fixed template or required output, so its token cost tracks
  conversation length directly. A bounded question ("what should the CLI's argument
  list look like") converges faster than an unscoped one ("let's talk about this
  project").
- **Let the CLI's own `--json` output tell you what changed, rather than re-reading
  entire files to check.** `openspec status --change "<name>" --json` reports exactly
  which artifacts are `done` versus `ready` versus `blocked`, and
  `openspec instructions apply --change "<name>" --json` reports exact task-completion
  counts — both far cheaper to consume than re-reading full markdown files purely to
  determine current state.

## 5. Related Documentation

See [Openspec-Documenetation.md](Openspec-Documenetation.md) for the full command
reference and two complete sample-project walkthroughs, and
`travel-itinerary-agent/BUILD-LOG.md` in this repository for the real, unabridged
slash-command-by-slash-command build that every claim in this document was checked
against.
