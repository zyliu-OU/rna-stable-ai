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

## Preserve the README picture

The user added a picture directly to the GitHub README. Keep that picture in all
future updates unless the user explicitly requests its removal or replacement.
Before publishing, inspect the latest GitHub README and its image references,
merge the user's upstream edits into the publication snapshot, and preserve both
the picture's Markdown/HTML and any repository image assets it uses. Do not
overwrite the live README with an older local/exported copy that omits the picture.
