# Spec-Driven Development with OpenSpec and Claude Code

[![View Website](https://img.shields.io/badge/View%20Website-2f8fe0?style=for-the-badge)](https://sarveshtalele.github.io/sdd-development-using-openspec-with-claude-guide/)

Every document in this repository is also published as a styled, browsable website —
[**view it here**](https://sarveshtalele.github.io/sdd-development-using-openspec-with-claude-guide/)
— rebuilt automatically on every push by
[.github/workflows/deploy-docs.yml](.github/workflows/deploy-docs.yml).

This repository is a single reference point for two related things: how to practice
**Spec-Driven Development (SDD)** using OpenSpec, and how to configure and extend
**Claude Code** — the environment OpenSpec runs inside — with Skills, Subagents, Hooks,
Plugins, and MCP servers. It assumes no prior setup and no dependency on any specific
project.

## 1. What Is Spec-Driven Development

Spec-Driven Development is a way of working where the specification of a change is
written, reviewed, and agreed upon **before** any code is written, rather than being
reconstructed from the code (or skipped entirely) after the fact. The specification is
not a one-time planning document that goes stale — it is a durable artifact that is kept
in sync with the codebase as the codebase evolves.

In practice, using OpenSpec, this means every non-trivial change moves through four
reviewable artifacts before implementation begins: `proposal.md` (why does this change
need to happen, and what is explicitly out of scope), `design.md` (the technical
approach and key decisions), `specs/<capability>/spec.md` (the exact required behavior,
expressed as testable scenarios), and `tasks.md` (the ordered, checkable implementation
steps).

Once every task in a change is implemented and genuinely verified — not just marked
done — the change is **archived**: its specs are folded into `openspec/specs/`
permanently, becoming the project's living, durable documentation. The next change
starts from that updated baseline, so specs never drift far from what the code actually
does.

This differs from writing code first and documenting afterward in one important way:
review happens while a change is still cheap to alter — at the proposal and design
stage — instead of after implementation, when revising course is expensive.

The full command-by-command workflow, including two complete start-to-finish sample
projects, is documented in
[openspec-guide/Openspec-Documenetation.md](openspec-guide/Openspec-Documenetation.md).

## 2. Repository Contents

| Path | Description |
|---|---|
| [README.md](README.md) | This file — overview of SDD and an index of everything else in this repository. |
| [openspec-guide/](openspec-guide/) | Everything needed to practice Spec-Driven Development with OpenSpec inside Claude Code. |
| [openspec-guide/Openspec-Documenetation.md](openspec-guide/Openspec-Documenetation.md) | OpenSpec reference: setup, the full `/opsx` command set (core and expanded profiles), the typical day-to-day loop, guidance for legacy/existing codebases, and two complete sample projects executed start to finish — one using the core profile, one using the expanded profile. |
| [openspec-guide/02-command-outputs-and-token-optimization.md](openspec-guide/02-command-outputs-and-token-optimization.md) | Per-command reference: exactly what each `/opsx:*` command generates on disk, what a human has to review or edit by hand afterward, and concrete practices for keeping token consumption down. |
| [travel-itinerary-agent/](travel-itinerary-agent/) | A real, complete example project — a small Python CLI travel itinerary generator — built end to end with the OpenSpec workflow described above, then verified live against a real OpenAI-compatible endpoint and taken through a second propose-to-archive loop to fix a bug the live run surfaced. `BUILD-LOG.md` inside it documents every `/opsx:*` command typed, every file generated, what had to be edited by hand, and a token-consumption comparison against an unstructured build. |
| [claude-guide/](claude-guide/) | Everything needed to configure and extend Claude Code itself, independent of OpenSpec. |
| [claude-guide/01-creating-a-skill.md](claude-guide/01-creating-a-skill.md) | What a Skill is, why the feature exists, how it works, and how to author a `SKILL.md` file in Claude Code. |
| [claude-guide/02-creating-agent-skills.md](claude-guide/02-creating-agent-skills.md) | The Agent Skills architecture underneath `SKILL.md`: progressive disclosure, how Claude loads and executes Skill content via scripts and bash, and security considerations. |
| [claude-guide/03-adding-mcp-servers.md](claude-guide/03-adding-mcp-servers.md) | How to add, scope, authenticate, and manage MCP servers in Claude Code, individually and for a team. |
| [claude-guide/04-general-guide.md](claude-guide/04-general-guide.md) | An orientation guide to Claude Code's four extensibility mechanisms — Skills, Subagents, Hooks, and Plugins — how each works, and how to choose between them. |
| [claude-guide/05-creating-claude-md.md](claude-guide/05-creating-claude-md.md) | What `CLAUDE.md` is, why it exists, how it loads and how it differs from Skills, and how to create and maintain one. |

## 3. Learning Materials

External resources this repository's documentation was cross-checked against, for
readers who want the primary sources or a video walkthrough alongside the written
guides above.

| Topic | Resource | Format |
|---|---|---|
| Agent Skills open standard | [Agent Skills Overview](https://agentskills.io/home) | Website |
| Agent Skills open standard | [What AI Agent Skills Are and How They Work](https://youtu.be/Lg-meK5IU8Q) | Video |
| Claude Code Skills | [What are skills?](https://www.youtube.com/watch?v=bjdBVZa66oU) | Video |
| Claude Code Skills | [Skills in Claude Code — official docs](https://code.claude.com/docs/en/skills) | Documentation |
| OpenSpec with Claude Code | [OpenSpec & Spec-Driven Development with Claude Code](https://www.youtube.com/watch?v=FpBYgYyU-SE&t=775s) | Video |
