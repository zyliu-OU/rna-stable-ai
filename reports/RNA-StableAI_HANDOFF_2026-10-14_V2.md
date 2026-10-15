# RNA-StableAI handoff — 2026-10-14 V2

Project: RNA-StableAI. Date: 2026-10-14 (America/Los_Angeles). Version: V2.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.

## Completed work

Recorded the user's instruction in `AGENTS.md`: preserve the picture they added
directly to the GitHub README in every future update. Before publication, inspect
the live README, merge upstream edits, and preserve its image markup and any
associated repository assets. An older local/exported README must not replace
the user's picture. Updated current-status pointers to this handoff.

No GitHub content was changed during this preference update. The completed
development publication and scientific status remain documented in
[V1](RNA-StableAI_HANDOFF_2026-10-14_V1.md).

## Verification

Read the current project instructions and existing handoff versions before
creating V2. Read back the saved preservation rule and handoff pointers. This
instruction/documentation change requires no experiment or test-suite rerun.

## Pending work

Before any future publication, retrieve the latest upstream README and preserve
the user's picture and other upstream edits. The picture has not been imported
into the local README during this turn; existing export copies predate it.
Scientific work remains at step 4, independent biological structure validation.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-14_V2.md
cat reports/PROJECT_ROADMAP_2026-10-14.md
gh api repos/zyliu-OU/rna-stable-ai/contents/README.md --jq .content | base64 --decode
```

Inspect the live picture reference and its asset before preparing the next
publication; merge it into both the local README and the new snapshot first.
