# Travel Itinerary Agent — How This Project Was Built

This document is a slash-command-by-slash-command guide to how this project was built
with OpenSpec's spec-driven workflow inside Claude Code. It is written from the
perspective of the person typing the commands, not from the perspective of the tooling
underneath them: OpenSpec's own CLI (`openspec status`, `openspec instructions`,
`openspec validate`, `openspec archive`, and so on) is never typed by a user. Each
`/opsx:*` slash command's definition, installed verbatim by `openspec init`, calls that
CLI internally to resolve templates, check dependencies, and track progress. None of
that internal orchestration appears below, because none of it is something a user does
by hand.

What does appear below, for every step: the exact command typed, what it produced —
grounded in this project's real, complete files, not a generic template — and what a
human has to open and edit afterward. Every artifact referenced here still exists in
this repository at the path given, so any claim below can be checked directly against
the file it describes.

## 1. One-Time Setup

Before any `/opsx:*` command exists to type, OpenSpec has to be installed into the
project once. This is the one step in the whole workflow that happens outside the
slash-command system, because the slash commands themselves don't exist until it runs.
Running `openspec init --tools claude` (either typed directly by the user in a
terminal, or asked of Claude Code as a plain request) against this project's root
directory created:

| Path | What it is |
|---|---|
| `.claude/commands/opsx/{explore,propose,apply,sync,archive}.md` | The five slash-command definitions. Typing `/opsx:propose` from this point on loads `propose.md` and follows it. |
| `.claude/skills/openspec-{explore,propose,apply-change,sync-specs,archive-change}/SKILL.md` | The matching Skill definitions Claude Code can also invoke directly by name. |
| `openspec/config.yaml` | Project-level configuration: which artifact schema to use, plus optional `context` and `rules` blocks. |

**What to edit before the first `/opsx:propose`**: `openspec/config.yaml`'s `context`
and `rules` blocks. This is optional but was done for this project, because every
artifact every `/opsx:*` command generates afterward includes this block automatically
— writing the tech stack and domain once here means it never has to be repeated in a
propose request. The real block used for this project:

```yaml
context: |
  Tech stack: Python 3.11+, stdlib argparse for the CLI, the `openai` Python package
  as the client, pointed at an OpenAI-compatible endpoint via a configurable base_url
  so any OpenAI-compatible provider works, not just OpenAI itself.
  Domain: a small, single-user command-line travel itinerary generator. Given a
  destination, trip length, and traveler preferences, it produces a structured
  day-by-day itinerary.
  No database, no web server, no auth — this is a local CLI tool, intentionally small.
  The API key is never hardcoded; it is read from an environment variable at runtime.

rules:
  tasks:
    - Break tasks into small, independently verifiable steps
    - The final tasks must include verification steps that do not require a live API key
```

See `openspec-guide/02-command-outputs-and-token-optimization.md` in this repository
for why this specific edit is worth making before the first propose, generally, not
just for this project.

## 2. `/opsx:explore` — Thinking Before Writing Anything

**What was typed**: `/opsx:explore`, scoped to one question — what should this tool's
core scope and architecture be, given that no API key is available yet.

**What it generates**: nothing, by design. Explore is a thinking mode: reading and
discussing are expected, writing files is not, unless a note is explicitly requested.
No file exists in this project that was produced by this step — the output is entirely
the reasoning that gets carried into the next command.

**What to review/edit**: there is nothing on disk to review. The thing that matters is
making sure the real decisions from this step are stated explicitly in the next
command's input, rather than assumed to be remembered. For this project, the decisions
that came out of this step and were carried forward into `/opsx:propose` were:

- **Core scope, kept deliberately narrow**: destination, trip length, and a short list
  of preferences (pace, interests, budget) in; a day-by-day itinerary out. No booking,
  no live availability, no maps integration.
- **"OpenAI-compatible" is a design constraint, not just a client library choice.**
  Both the API key and the base URL need to be configurable at runtime, or "compatible"
  silently narrows to "OpenAI only."
- **The no-key-yet constraint should drive the architecture.** If the one function that
  calls the model is isolated from argument parsing, prompt construction, and output
  formatting, everything except that one function can be verified today, with the live
  call deferred until a key exists.
- **Ask the model for structured JSON, not prose.** A JSON shape can be validated
  before being shown to the user; free text cannot.
- **Explicitly out of scope**: persistence, authentication, a web server, geocoding, or
  real-world venue validation. The model's suggestions are not checked against reality
  — a stated limitation, not a defect to fix later.

## 3. `/opsx:propose` — Generating the Planning Artifacts

**What was typed**: `/opsx:propose`, followed by a description of the change carrying
forward the explore-step decisions above — a CLI tool named `itinerary` that accepts a
destination, day count, and optional preferences, calls a configurable OpenAI-compatible
endpoint for a structured itinerary, validates the response shape, and renders it as
plain text.

**What it generates, in order** (each depends on the one before it being written):

### 3.1 `proposal.md`

Written to `openspec/changes/add-travel-itinerary-cli/proposal.md` (now preserved at
`openspec/changes/archive/2026-07-09-add-travel-itinerary-cli/proposal.md`). One new
capability was declared: `travel-itinerary`. The **Why** section states the actual
motivation — planning a multi-day trip by hand means manually researching activities
for every day; a small tool that returns a structured itinerary removes that step for a
simple, personal-use case.

**What to review here specifically**: the **Capabilities** section. It is the contract
between the proposal and the spec files that get created next — a wrong or missing
capability name here means the wrong spec file gets created or updated. For this
project it read simply: one new capability, `travel-itinerary`; no modified
capabilities, since this was a greenfield project with no existing specs.

### 3.2 `design.md` and `specs/travel-itinerary/spec.md`

Both unlock together once the proposal is written, and were generated together here.

`design.md` recorded the one decision everything else in this project follows from:
isolate the model call in a single function, `generate_itinerary(...)`, so everything
downstream and upstream of it is independently testable without a live key. It also
recorded the decision to read the API key, base URL, and model name from three separate
environment variables (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `ITINERARY_MODEL`) rather
than hardcoding any of them, and to fail fast with a named error if the key is missing,
before any network call is attempted.

`specs/travel-itinerary/spec.md` (the delta spec, later merged into the project's
durable spec by `/opsx:archive`) defined four requirements, each with two or three
scenarios:

| Requirement | Scenarios |
|---|---|
| Trip parameters via CLI arguments | valid input accepted; missing argument rejected; invalid day count rejected |
| Configuration read from environment variables | key present and used; key missing and named in the error; base URL falls back to default when unset |
| Structured itinerary generation | well-formed response accepted; malformed or short response rejected with a validation error |
| Readable terminal rendering | a validated itinerary prints in day order |

**What to review here specifically**: every scenario header uses exactly four `#`
characters (`#### Scenario: ...`). Three hashtags fails silently rather than raising an
error — this is the single most common formatting mistake in a hand-edited spec file,
and it is worth a specific pass over the generated file before moving on.

### 3.3 `tasks.md`

Unlocks once both `design.md` and `specs/` are written. Generated with seven task
groups (scaffold, CLI parsing, configuration, generation, rendering, wiring, and
verification), 17 checkboxes total, deliberately ending with a group named
"Verification without a live API key" whose last item required this build log to state
outright, at that point, that the live network call was unverified.

**What to review here specifically**: keep each checkbox's description on a single
line. A task that wraps onto a second line in the file is still tracked correctly by
`/opsx:apply`'s progress view, but only that first line is what gets displayed — for
example, one task in this project's real `tasks.md` reads in full as "Create the
package layout (`itinerary/` package plus `pyproject.toml` or a `requirements.txt`,
whichever is simpler for a single-package CLI tool)", and a progress summary shown
mid-apply displayed only "Create the package layout (`itinerary/` package plus
`pyproject.toml` or a" — the file itself is unaffected, only its live display is
truncated. Beyond the display issue, a task that's genuinely one line is usually also a
signal that the task is appropriately small.

**A quick formatting check worth running here**: after the spec file is written, a
fast, local formatting check (no model call involved) exists to catch the four-hashtag
mistake and confirm every requirement has at least one scenario, before moving on to
`/opsx:apply`. It is worth running immediately after `/opsx:propose` finishes, not
after `/opsx:apply` has already started building against a spec that turns out to be
malformed.

## 4. `/opsx:apply` — Building the Actual Project

**What was typed**: `/opsx:apply`.

**What it generates**: not a fixed set of OpenSpec files — this is the one command
whose output is the project's real source code. The only file inside `openspec/` this
command modifies is `tasks.md` itself, where each completed task's `- [ ]` becomes
`- [x]`.

For this project, the code produced maps directly onto the task groups from Section
3.3:

| File | Task group satisfied |
|---|---|
| `pyproject.toml` | 1. Project scaffold |
| `itinerary/__init__.py`, `itinerary/cli.py` | 2. CLI argument parsing, 6. Wiring and error handling |
| `itinerary/config.py` | 3. Configuration handling |
| `itinerary/generator.py` | 4. Itinerary generation |
| `itinerary/schema.py` | 4. Itinerary generation (the JSON shape and its validation) |
| `itinerary/renderer.py` | 5. Rendering |
| `tests/test_cli.py`, `tests/test_config.py`, `tests/test_schema.py`, `tests/test_renderer.py`, `tests/test_generator.py` | 7. Verification without a live API key |
| `README.md` | project usage documentation — standard project hygiene, not itself a numbered task |

The central `design.md` decision is directly visible in the code: `generate_itinerary`
in `itinerary/generator.py` accepts an optional `client` parameter, defaulting to a
real `openai.OpenAI` client, specifically so `tests/test_generator.py` can substitute a
stand-in object (`FakeClient`/`FakeChatCompletions`) instead of a live client. That
parameter is the concrete mechanism that makes "isolate the model call" an actually
testable claim rather than a stated intention.

**What to review/edit**:

- **The actual code, not just the checkbox.** A task marked `[x]` means the agent
  believes the task is done, not that it has been independently verified. Read the
  diff.
- **Run the real test suite.** For this project: `python -m unittest discover -s
  tests -v`. Every task in the final "Verification" group specifically defines what
  "done" means as passing tests, not just written code — confirm they actually ran and
  actually passed.
- **Watch for a blocked state.** If `/opsx:apply` reports an artifact it depends on
  isn't finished yet, the fix is to go back to `/opsx:propose` (or `/opsx:continue` in
  the expanded profile), not to force the apply step forward.
- **Exercise the CLI directly for anything that doesn't require the live network
  call**, the same way the "Verification without a live API key" task group specifies:
  a missing-argument usage error, a missing-`OPENAI_API_KEY` configuration error, an
  invalid day count, and `--help` output. All four behaved exactly as specified in
  `specs/travel-itinerary/spec.md` for this project.

## 5. `/opsx:archive` — Making the Spec Durable

**What was typed**: `/opsx:archive`, once all tasks were checked off.

**What it generates/modifies**:

- Merges the change's delta spec into `openspec/specs/travel-itinerary/spec.md` — the
  project's durable, permanent specification, independent of any one change.
- Moves the entire change directory to
  `openspec/changes/archive/YYYY-MM-DD-<name>/`, preserving `proposal.md`, `design.md`,
  the delta `specs/`, and the completed `tasks.md` exactly as they were.

For this project, archiving `add-travel-itinerary-cli` created
`openspec/specs/travel-itinerary/spec.md` for the first time, with all four requirements
from Section 3.2 merged in.

**What to review/edit — this one is concrete and was actually observed, not
hypothetical**: when `/opsx:archive` creates a brand-new capability's main spec file for
the first time, the `## Purpose` section is written as a placeholder — literally `TBD -
created by archiving change add-travel-itinerary-cli. Update Purpose after archive.` —
and nothing in the archive step itself replaces it with real content. This had to be
fixed by hand, once, after this archive ran, with the one-paragraph purpose statement
that is still in `openspec/specs/travel-itinerary/spec.md` today. This is the one edit
that reliably has to be made after archiving a change that introduces a capability for
the first time. It does not recur on later archives that only add to an existing
capability — see Section 8 below, where a second archive against this same capability
required no such fix.

This concluded the first full loop —
`/opsx:explore` → `/opsx:propose` → `/opsx:apply` → `/opsx:archive` — against a real
OpenSpec 1.5.0 installation, start to finish.

## 6. Using the Finished Tool

None of the commands in this section are OpenSpec commands — this is the product that
was built, used the way its own `README.md` documents. Set up once:

```
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Then, with `OPENAI_API_KEY` (and optionally `OPENAI_BASE_URL`, `ITINERARY_MODEL`) set
in the environment:

```
itinerary "Lisbon, Portugal" 3 --pace relaxed --interests "food,history" --budget moderate
```

This was run for real against a live OpenAI-compatible proxy and returned a
well-formed, three-day, day-ordered itinerary — confirming that a real provider's
response parses cleanly through `generate_itinerary` → `validate_itinerary` →
`render_itinerary` on the first try, with no code changes needed for the success path.

The same invocation was repeated with `ITINERARY_MODEL` set to a different model on the
same proxy, and produced an equally well-formed itinerary with zero code changes — the
concrete proof that "OpenAI-compatible" really was treated as a runtime configuration
choice in this project, not a client-library assumption baked into the code.

## 7. A Real Bug, Found by Actually Running the Tool

The same live call was also deliberately repeated with an invalid API key, to check the
failure path. This surfaced a real gap: the tool crashed with a full Python traceback
(an unhandled `openai.AuthenticationError`) instead of the clean, one-line error every
other failure mode in this tool already produced. Nothing in
`specs/travel-itinerary/spec.md` accounted for this case, because it was never
identified during the original `/opsx:explore` step — it only surfaced under an actual
network failure, which no stand-in test client can produce on its own.

This is exactly the situation the workflow is meant for: a real gap, found by
verification, fed back through the same loop rather than patched silently. What
follows is a second full pass through the same five commands, against the same
project.

## 8. A Second Loop: `/opsx:propose` → `/opsx:apply` → `/opsx:archive`, for a Bug Fix

**What was typed**: `/opsx:propose`, describing the gap found in Section 7 — API-level
failures during generation should exit cleanly instead of crashing.

**What it generated**:

- `proposal.md`: one modified capability, `travel-itinerary` — add a requirement that
  an API-level failure during generation produces a clean error and a non-zero exit,
  not a stack trace.
- `design.md`: recorded catching `openai.APIError` (the SDK's base class for
  authentication failures, rate limits, and connection failures alike) inside
  `generate_itinerary` and re-raising it as the existing `ItineraryValidationError`,
  reusing the exception type `cli.py` already handles cleanly rather than adding a
  second error type and a second handler for what is, from the CLI's perspective, the
  same category of failure — the tool could not produce an itinerary.

  **A nuance worth knowing here**: this artifact's own generation guidance says to
  create `design.md` only for changes that are cross-cutting, add a dependency, or
  carry real risk — by that standard alone, a change this small might not need one.
  But `tasks` depends on both `design` and `specs` being complete regardless of a
  change's size, so a design document — kept deliberately short — was written anyway.
  Small size is not, by itself, sufficient reason to expect this artifact can be
  skipped.
- `specs/travel-itinerary/spec.md` (a new delta, scoped to this change): one `## ADDED
  Requirements` block — "Graceful handling of API-level request failures" — with one
  scenario: when the model client raises an error, the system prints a description of
  the failure and exits without a traceback.
- `tasks.md`: two groups, five tasks — catch the error and re-raise it, confirm the CLI
  already handles the new error type, add a regression test using a real
  `openai.APIError` instance, run the full suite, and re-verify live with a
  deliberately invalid key.

**What was typed next**: `/opsx:apply`.

**What it generated**: a small, targeted change to `itinerary/generator.py` — the
`client.chat.completions.create(...)` call wrapped in a `try`/`except APIError`,
re-raising as `ItineraryValidationError` — and an extended
`tests/test_generator.py`, whose fake client can now optionally raise a supplied
exception instead of returning content, plus one new test constructing a real
`openai.APIError` to confirm the `except` clause matches the actual exception type, not
a same-named stand-in.

**What to review/edit**: exactly the same two things as Section 4 — read the diff
rather than trust the checkbox, and run the real suite. For this change:
`python -m unittest discover -s tests -v` reported all tests passing, 26 total (the 25
from the first loop plus the one new case). The live re-verification specified in the
last task was then run for real, with a deliberately invalid key: the traceback was
gone, replaced by a clean, single-line error in the same style as every other failure
mode in the tool.

**What was typed last**: `/opsx:archive`.

**What it generated/modified**: the new requirement merged directly into the existing
`openspec/specs/travel-itinerary/spec.md`, under the four already there, and the change
directory moved to `openspec/changes/archive/2026-07-09-fix-api-error-handling/`.
Unlike Section 5, this archive introduced **no** `## Purpose` placeholder to fix by
hand — that placeholder is only written the first time a capability's main spec file is
created, and `travel-itinerary` already existed from the first loop. No manual
correction was needed after this one.

## 9. Token Consumption: Structured SDD vs. a Single Unstructured Request

**Methodology, stated up front**: there is no tool available in this session that
reports the exact number of tokens actually billed for this conversation. Everything
below is an estimate derived from the real, measured size (in characters and lines) of
the artifacts this project actually contains, converted to an approximate token count
using the common ~4-characters-per-token heuristic for English text and source code.
Treat the figures as order-of-magnitude, not exact — the point is the comparison
between the two approaches, not a precise accounting of either one.

**What was actually measured**, across both loops:

| Category | Files | Lines | Characters | Approx. tokens (÷4) |
|---|---|---|---|---|
| OpenSpec planning artifacts — both changes' `proposal.md`, `design.md`, delta `specs/`, `tasks.md`, plus `config.yaml` and the final merged main spec | 10 | 423 | 21,394 | ~5,350 |
| This document (the process narration) | 1 | ~430 | ~21,500 | ~5,400 |
| Application code (`itinerary/`) | 6 | 269 | 8,653 | ~2,150 |
| Tests (`tests/`) | 6 | 268 | 10,169 | ~2,550 |
| `README.md` + `pyproject.toml` | 2 | 66 | 2,032 | ~500 |

**Process overhead not captured in any single file**: every `/opsx:*` command's
underlying template, project `context`, per-artifact `rules`, and dependency/progress
state is real text that becomes part of the conversation the moment the command runs —
it is simply not something the person typing the command has to read or produce by
hand, and it is not stored anywhere as its own file. Across both loops, the two
generation passes and the two apply passes each involved this kind of injected context
and returned progress state; based on the measured size of comparable content shown
inline above (the `context` block in Section 1, the requirement tables in Sections 3
and 8), that overhead is roughly another 3,500-4,500 tokens of real context consumption
that no single file's size reflects.

**Rough total for the structured SDD path on this project, both loops combined**: code
+ tests + README/config (~5,200 tokens — the actual deliverable) plus planning
artifacts, this document, and injected per-command context (~14,250-15,250 tokens of
process overhead) — on the order of **19,500-20,500 tokens** in total.

**Constructed comparison: the same project built as a single unstructured request**
("build me a travel itinerary CLI in Python using an OpenAI-compatible client, and
handle request failures cleanly," no proposal, no design doc, no spec, no task list, no
build log). This scenario was not actually run — it is estimated the same way, from
what that request would realistically have to produce:

- Comparable application code, plausibly with less of the isolation and edge-case test
  coverage this project has (the empty-activities, wrong-day-count, non-JSON-response,
  and API-error test cases exist here specifically because a spec file named them as
  required scenarios) — call it roughly 60-80% of the code+test volume measured above,
  so **~3,300-3,900 tokens**.
- A short explanation of what was built and fixed, in place of proposal/design
  documents — **~400-900 tokens**.
- No per-command injected-context cost, since there is no structured workflow to drive.
- A realistic possibility of one or more extra clarifying turns, and of the API-error
  gap being found later, by a user, rather than by deliberate verification during
  development — a cost the SDD path pays once, up front, by specifying and testing
  failure modes before they ship.

**Rough total for the unstructured path**: on the order of **3,700-4,800 tokens**.

**Net comparison**: on a project this small, the structured OpenSpec workflow used
roughly **4-5x the tokens** of an equivalent single-shot build. Nearly all of that
difference is planning artifacts, process documentation, and per-command injected
context — not the application code itself, which is comparable in size either way, and
arguably more correct in the SDD version, since its test cases trace to written-down
requirements rather than to whatever the author happened to think of at the time.

**The trade-off, stated plainly rather than resolved in either direction**: the extra
tokens bought a written proposal and design rationale that exist independently of any
one conversation, a spec that is now permanent project documentation, and tests that
verify — rather than merely assert — that stated decisions were actually followed. They
also bought something the unstructured estimate above explicitly could not have: a
mechanism (spec → apply → verify) that turned a bug found by live testing into a
second, equally structured change, at roughly a quarter of the first loop's cost,
instead of a silent, undocumented patch. An unstructured build is cheaper the first
time; if the same context has to be reconstructed later — a teammate asking why a
decision was made, or a bug needing to be traced back to what was actually specified —
the unstructured path pays that cost later instead of now. Whether that is worth it
depends on whether the project outlives one build; for anything meant to be maintained,
reviewed, or handed off, the up-front cost is what makes that later reconstruction
unnecessary.

## 10. Related Documentation

See `openspec-guide/Openspec-Documenetation.md` in this repository for the full
`/opsx` command reference and two additional sample-project walkthroughs, and
`openspec-guide/02-command-outputs-and-token-optimization.md` for the general,
project-independent version of the per-command "what it generates, what to edit"
reference this document applies to one real project.
