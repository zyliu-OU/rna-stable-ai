# Project collaboration preferences

For every handoff, save a Markdown file in reports/ named
RNA-StableAI_HANDOFF_YYYY-MM-DD_VN.md, using the local date in America/Los_Angeles.
Start with V1 each date, then use V2, V3, and so on for additional handoffs on that
same date. Determine the next version from existing files; never overwrite or
remove earlier handoffs. Avoid relying on "tomorrow" in the filename.

Include the project name (RNA-StableAI), date, version, and absolute workspace
path inside the handoff, plus completed work, verification, pending work and
exact continuation commands. Link the specific versioned handoff in the response.
For other projects, use their actual project name in the same naming pattern.
An undated convenience copy may also be kept, but the versioned file is the
canonical handoff to reference when resuming.

## Detailed handoffs

The user requests as much useful detail and information as possible in every
future handoff. Make the versioned Markdown file a self-contained resume record,
while keeping the chat response concise. Include:

- Current user priorities, scope boundaries, constraints, stage-transition gates,
  and decisions that supersede earlier handoffs.
- Completed work with exact code/config/report paths, the purpose of each change,
  preserved historical artifacts, and publication/workspace status.
- Experiment protocols, input inventories, cohorts and exposure/lineage limits,
  seeds, model/optimizer/loss/decoder settings, checkpoint selection rules,
  runtime versions and measured resources when available.
- Exact protocol/run/checkpoint/prediction paths, relevant hashes or manifests,
  per-seed and aggregate results, baseline comparisons, regressions and failures.
- Commands actually run and their outcomes, distinguishing unit tests, artifact
  checks, inference replay and deterministic retraining; state unverified items.
- Scientific interpretation, limitations, rejected approaches, why defaults or
  stage gates changed or stayed fixed, and what must not be claimed.
- Outstanding processes or partial runs with identifiers if any, unresolved
  issues, prioritized next steps, and exact safe continuation commands.

Do not invent missing measurements or claim checks that were not run. Preserve
earlier handoffs and frozen protocols; link concrete artifacts rather than
requiring a later reader to infer which version was used.

## Preserve the README picture

The user added a picture directly to the GitHub README. Keep that picture in all
future updates unless the user explicitly requests its removal or replacement.
Before publishing, inspect the latest GitHub README and its image references,
merge the user's upstream edits into the publication snapshot, and preserve both
the picture's Markdown/HTML and any repository image assets it uses. Do not
overwrite the live README with an older local/exported copy that omits the picture.
