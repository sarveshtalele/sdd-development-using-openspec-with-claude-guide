# Agent Skills

*How the Agent Skills architecture works underneath a `SKILL.md` file, and why that
architecture is built the way it is. This document covers the same underlying model
Anthropic calls "Agent Skills" across its products, focused entirely on the filesystem
approach available in Claude Code: scripts and `SKILL.md` files, with no API account,
upload step, or key required.*

## 1. Purpose of This Document

[Creating a SKILL.md File in Claude Code](01-creating-a-skill.md) explains how to
author a Skill. This document explains the architecture underneath that authoring
guide — why Skills are structured as directories rather than prompts, how Claude
decides what to load and when, and what that means for how you should design a Skill's
files and scripts. Read the two together: this document for the model, the other for
the step-by-step mechanics.

## 2. What Agent Skills Are

Agent Skills are modular capabilities that extend what Claude can do. Each Skill
packages instructions, metadata, and optional resources — scripts, templates,
reference material — that Claude uses automatically when relevant to the task at hand.

Skills are reusable, filesystem-based resources that give Claude domain-specific
expertise: workflows, context, and best practices that turn a general-purpose agent
into a specialist for a particular kind of task. This is different from a prompt, which
is a conversation-level instruction good for one conversation only. A Skill is written
once, saved to disk, and is then available automatically in every relevant
conversation going forward.

## 3. Why Agent Skills Exist

- **Specialize Claude.** Tailor its behavior for domain-specific tasks — a particular
  document format, a particular internal workflow, a particular set of conventions.
- **Reduce repetition.** Write the guidance once; Claude applies it automatically
  whenever it's relevant, instead of it being re-typed into chat each time.
- **Compose capabilities.** Multiple Skills can combine within a single task, each
  contributing the part of the workflow it specializes in.

## 4. The Progressive Disclosure Architecture

Claude operates inside a virtual machine with filesystem access. This is what makes a
Skill possible in the first place: a Skill is not a block of text stuffed into a
prompt, it is a directory on disk, containing instructions, executable code, and
reference material, organized the way you might organize an onboarding guide for a new
team member.

This filesystem-based design enables **progressive disclosure** — Claude loads
information in stages, only as needed, instead of consuming context upfront. A Skill's
content falls into three levels, each loaded at a different point:

| Level | Content | When it loads | Token cost |
|---|---|---|---|
| 1. Metadata | The `name` and `description` fields from the Skill's YAML frontmatter | Always, at session startup | Roughly 100 tokens per Skill |
| 2. Instructions | The body of `SKILL.md` — workflows, best practices, procedural guidance | Only when the Skill is triggered by a matching request | Typically under 5,000 tokens |
| 3. Resources and code | Bundled markdown references, executable scripts, templates, schemas | Only when a specific file is read or a specific script is run | Effectively unlimited — files not accessed cost nothing |

Because Level 1 is so lightweight, a project can install many Skills with no
meaningful context penalty — Claude simply knows each one exists and roughly what it's
for, until one is actually needed.

## 5. How Claude Accesses Skill Content

Claude interacts with a Skill directory the same way you would interact with files on
your own computer: by running bash commands.

- When a Skill is triggered, Claude reads `SKILL.md` from the filesystem via bash. That
  brings the instructions into the context window for the first time.
- If those instructions reference another file — a form-filling guide, a database
  schema, an API reference — Claude reads that specific file via an additional bash
  command, only if the current task actually needs it.
- If the instructions mention an executable script, Claude runs it via bash. The
  script's source code never enters the context window — only its output does (for
  example, "Validation passed" or a specific error message).

This is what makes progressive disclosure work in practice, and it produces three
concrete effects worth designing around:

- **On-demand file access.** A Skill can bundle dozens of reference files; if a task
  only needs one of them, only that one is read. The rest sit on disk consuming zero
  tokens.
- **Efficient script execution.** Running a script that validates a form costs only the
  tokens in its output — not the tokens of the script itself. This is substantially
  cheaper than having Claude write equivalent logic from scratch inside the
  conversation, and more reliable, since the same script runs the same way every time.
- **No practical ceiling on bundled content.** Because unopened files cost nothing, a
  Skill can include comprehensive reference documentation, large examples, or extensive
  datasets without a context penalty for the parts that go unused on any given task.

## 6. Walkthrough: Loading a Skill

A concrete sequence, for a Skill named `pdf-processing`:

1. **Startup.** The system prompt already includes the Skill's Level 1 metadata: *PDF
   Processing — Extract text and tables from PDF files, fill forms, merge documents.*
2. **User request.** "Extract the text from this PDF and summarize it."
3. **Claude reads `SKILL.md`.** `bash: read pdf-skill/SKILL.md` brings the Level 2
   instructions into context.
4. **Claude decides what else it needs.** The task doesn't involve filling out a form,
   so a bundled `FORMS.md` file is never read — it stays on disk, costing nothing.
5. **Claude completes the task**, following the instructions now loaded in context.

At every step, only what the specific request actually required entered the context
window.

## 7. Skill Structure Requirements

A Skill is a folder. `SKILL.md` is the only file it must contain; everything else is
optional and exists only to be referenced from `SKILL.md`'s instructions:

```
my-skill/
├── SKILL.md      # Required: YAML frontmatter + instructions
├── scripts/      # Optional: executable code
├── references/   # Optional: documentation Claude reads on demand
├── assets/       # Optional: templates and other resources
└── ...           # Any additional files or directories
```

| Path | Purpose | Loads when... |
|---|---|---|
| `SKILL.md` | Required. YAML frontmatter (`name`, `description`) plus the instructions themselves. | Frontmatter always, at startup; the instruction body only once the Skill triggers (Section 4) |
| `scripts/` | Executable code — Python, shell, or anything else the runtime can execute. Claude runs these via bash instead of rewriting equivalent logic inline. | Only when `SKILL.md` instructs Claude to run a specific script (Section 5) |
| `references/` | Documentation too detailed to keep in `SKILL.md` itself — API references, schemas, style guides. | Only when the current task actually needs that specific file (Section 4) |
| `assets/` | Non-code resources a Skill produces or consumes — templates, boilerplate, sample data. | Only when the instructions point to a specific asset |

`scripts/`, `references/`, and `assets/` are a naming convention, not a requirement of
the format — a Skill can organize its supporting files however it wants, or have none
at all. `SKILL.md` is the one file every Skill must have, and the only one Claude reads
unconditionally once the Skill is triggered.

Every Skill requires a `SKILL.md` file with YAML frontmatter naming it and describing
it:

```yaml
---
name: your-skill-name
description: Brief description of what this Skill does and when to use it
---

# Your Skill Name

## Instructions

Clear, step-by-step guidance for Claude to follow.

## Examples

Concrete examples of using this Skill.
```

`name` and `description` are the only required fields, and both have exact
constraints:

| Field | Constraint |
|---|---|
| `name` | Maximum 64 characters. Only lowercase letters, numbers, and hyphens. No XML tags. Cannot use the reserved words "anthropic" or "claude". |
| `description` | Must be non-empty. Maximum 1,024 characters. No XML tags. |

The `description` should state both what the Skill does and when Claude should use it
— this is the field Claude compares against a request to decide whether to trigger the
Skill. See [Creating a SKILL.md File in Claude Code](01-creating-a-skill.md) for the
complete frontmatter reference, including the Claude Code–specific fields beyond these
two required ones, and for guidance on writing an effective `description`.

## 8. The Runtime Environment in Claude Code

The exact runtime a Skill's scripts execute in depends on where the Skill runs. In
Claude Code specifically:

- **Full network access.** A script has the same network access as any other program
  running on your machine — there is no sandboxing beyond what your own system
  provides.
- **Global package installation is discouraged.** Install any dependency a script needs
  locally, scoped to the project, rather than globally — a Skill should not alter the
  broader state of the machine it runs on.

Plan a Skill's scripts to work within these constraints, and treat network calls made
by a script with the same scrutiny you would apply to any other code running with your
own machine's permissions.

## 9. Security Considerations

Use Skills only from trusted sources — ones you wrote yourself, or ones you have
personally audited. A Skill gives Claude new capabilities through instructions and
code; that same mechanism means a malicious Skill can direct Claude to invoke tools or
run code in ways that don't match what the Skill claims to do.

If you must use a Skill from an untrusted or unknown source, audit it thoroughly before
running it at all:

- **Audit every bundled file.** Read `SKILL.md`, every script, and every other bundled
  resource. Look for anything that doesn't match the Skill's stated purpose — an
  unexpected network call, an unusual file access pattern, an operation with no
  apparent connection to what the Skill claims to do.
- **Treat external data sources as risky.** A Skill that fetches content from an
  external URL is exposed to whatever that URL returns — including content designed to
  look like an instruction. Even a Skill that was trustworthy when written can become
  risky later if an external dependency it relies on changes.
- **Tool misuse is the core risk.** A malicious Skill's danger comes from directing
  Claude to use its own available tools — file operations, bash, code execution — in a
  harmful way, not from some separate exploit mechanism.
- **Data exposure is a real consequence.** A Skill with access to sensitive data could,
  deliberately or through a compromised dependency, leak that data to an external
  system.

Treat installing a Skill the way you would treat installing any other piece of
software on your machine: only from a source you trust, and with extra caution before
giving one access to sensitive data or production systems.

## 10. Sharing Scope in Claude Code

A Skill's location determines who else can use it:

| Location | Scope |
|---|---|
| `~/.claude/skills/` | Personal — available to you, across every project you work in |
| `.claude/skills/` (project root) | Project — shared with anyone who clones the repository, via version control |
| Bundled inside a Claude Code Plugin | Distributed to anyone who installs the plugin |

See Section 5 of [Creating a SKILL.md File in Claude Code](01-creating-a-skill.md) for
the full discovery rules, including nested directories and precedence.

## 11. Relationship to Other Surfaces

Agent Skills, as an architecture, is not unique to Claude Code — the same `SKILL.md`
format and progressive-disclosure model is also used by the Claude API and by
claude.ai, each with its own upload mechanism for getting a Skill onto that surface.
This document deliberately covers only the Claude Code path: a Skill placed directly on
your filesystem, discovered automatically, with no account upload or API key required.
A Skill written this way is not automatically available on those other surfaces, and a
Skill uploaded to one of those other surfaces is not automatically available in Claude
Code — each is a separate deployment of the same underlying idea.

The format itself is an open standard, originally developed by Anthropic and since
adopted by a growing number of agent products beyond Claude — a Skill written to the
specification is not inherently tied to any one vendor. See Section 14 for the formal
specification.

## 12. Best Practices

- Keep `SKILL.md` itself focused on procedure; move detailed reference material into
  separate bundled files so it only loads when actually needed (Section 4).
- Prefer a script over inline instructions for any step that is deterministic — a
  script's output costs far fewer tokens than the equivalent reasoning written out in
  the conversation, and its behavior doesn't vary between runs.
- Install script dependencies locally to the project, never globally, so a Skill never
  alters the state of the machine it runs on.
- Audit a Skill's full contents — not just `SKILL.md` — before using one you didn't
  write yourself.

## 13. Common Pitfalls

| Symptom | Likely cause | Fix |
|---|---|---|
| Context fills up even though a Skill isn't being used | Instructions or reference material were written directly into a heavily loaded file instead of a separate bundled file | Split rarely needed material into its own file, referenced only when relevant (Section 4) |
| A script's logic seems to silently vanish from context | This is expected — script source code is never loaded, only its output | Rely on the script's printed output for verification, not on Claude "seeing" the code |
| A Skill behaves unpredictably or performs an unexpected action | The Skill (or one of its bundled scripts) came from an unaudited source | Remove it, and only reinstall after a full read-through of every bundled file (Section 9) |

## 14. Related Documentation

See [Creating a SKILL.md File in Claude Code](01-creating-a-skill.md) for the complete
authoring guide, and
[agentskills.io/specification](https://agentskills.io/specification) for the formal,
vendor-independent Agent Skills format specification referenced throughout this
document.
