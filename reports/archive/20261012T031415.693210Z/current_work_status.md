# RNA-StableAI current work status

Workspace: `/home/zyliu/Documents/rna-stable-ai`.
Canonical handoff: `RNA-StableAI_HANDOFF_2026-10-11_V4.md`.
Current step: 4 — independent biological validation.

User metadata acquisition succeeded: 705 seed entries, 704 screening candidates,
15 preselected sequences of 97–128 nt from three families. Model checkpoints and
selection/decoder settings remain frozen. No new predictions or scores exist.
Successful source summary: `/home/zyliu/Documents/rna-stable-ai/results/prospective_family_acquisition_runs/20261012T024003.811773Z/summary.json`.

Next evidence batch has ten requests: PDB mappings, exposed-family descriptions
and Stockholm alignments. Workspace DNS failures left seven requests failed and
three annotations unstarted. User should run `download_prospective_evidence.py`
from the normal terminal, then return the report for offline checks and binding.
Full suite: 516 passed in 216.49 seconds. Eight new focused tests passed.

PDB/clan provenance, annotation binding and final evaluation-plan freezing remain
required before inference. Changes remain local. Earlier status files are
preserved under `/home/zyliu/Documents/rna-stable-ai/reports/archive/20261012T025259.144841Z`.
