# RNA-StableAI handoff — 2026-10-14 V3

Project: RNA-StableAI. Date: 2026-10-14 (America/Los_Angeles). Version: V3.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.

## Completed work

Read the live GitHub README and found the user's picture directly below the
`# RNA-StableAI` title. It is the diagram titled **RNA Secondary Structure
Prediction**, showing physics-based folding and learned pair scoring.

Exact markup to preserve:

```html
<img width="1774" height="887" alt="image" src="https://github.com/user-attachments/assets/4da2605a-3a6d-4130-9014-950dc75bd34d" />
```

The image is a GitHub user attachment, rather than a relative repository asset.
No GitHub files, local README, or published snapshots were changed by this check.
The preservation instruction remains recorded in `AGENTS.md` and V2.

## Verification

Retrieved the README through the GitHub API. Retrieved the referenced picture:
HTTP 200, `image/png`, 1,891,839 bytes. Visually inspected the downloaded image at
`/tmp/rna-stable-ai-readme-picture-4da2605a.png` (temporary diagnostic copy).

## Pending work

For the next authorized publication, merge the latest upstream README into the
local/publication copy and retain this exact image reference and placement.
The current local README and existing publication snapshots predate the picture.
Scientific development status remains as described in V1 and the current roadmap.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-14_V3.md
gh api repos/zyliu-OU/rna-stable-ai/readme --jq .content | base64 --decode
```

Inspect the current upstream version before editing or exporting. Preserve the
picture unless the user explicitly asks for its removal or replacement.
