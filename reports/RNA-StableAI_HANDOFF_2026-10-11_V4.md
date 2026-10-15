# RNA-StableAI handoff

- Project: RNA-StableAI
- Date: 2026-10-11 (America/Los_Angeles)
- Version: V4
- Workspace: `/home/zyliu/Documents/rna-stable-ai`
- Saved UTC: 2026-10-12T02:52:59.144841+00:00
- Current roadmap step: **4 — independent biological validation**.

## Completed work

The user ran the frozen metadata acquisition in a terminal with network access.
All six family-description/seed-sequence requests succeeded. Saved bytes and
screening replay passed the acquisition audit. Successful acquisition:
`/home/zyliu/Documents/rna-stable-ai/results/prospective_family_acquisition_runs/20261012T024003.811773Z`.

Rfam release 15.1 provides 705 seed entries across RF00059 (115), RF00162 (457)
and RF00167 (133). Screening retains 704 candidates and one explicit ambiguous
sequence exclusion. The fixed protocol selects five entries per family: 15
sequences, lengths 97–128 nt. These are source metadata, not evaluated accuracy.
The three model checkpoints and selection/decoder configuration remain frozen.
No new training, predictions or test exposure events occurred.

Added `scripts/download_prospective_evidence.py` and eight regression tests.
The next fixed batch contains three family-to-PDB mapping files, four exposed
family descriptions for clan checks, and three Stockholm alignments. Bounded
HTTPS retrieval preserves raw bytes/hashes, failures and unstarted dependencies.
File-envelope validation checks descriptions' accession/release and complete
Stockholm headers/accessions. It does not parse reference pairs or certify
independence. Existing selected metadata records remain unchanged.

## Current evidence acquisition state

The workspace attempt `/home/zyliu/Documents/rna-stable-ai/results/prospective_evidence_runs/20261012T024646.468402Z`
contains seven DNS failures and three dependent Stockholm requests left
unstarted. Offline audit of that failure ledger passed. No provenance/annotation
files were downloaded by this attempt. The user must run the next batch from
the normal terminal that successfully fetched metadata.

Source descriptions report SAM clan CL00012, Purine clan CL00123, and null for
TPP. Descriptions of exposed RF00001/RF00008/RF00017/RF00169 are still required
for source-bound clan comparison. Family-to-PDB mappings remain pending; 69
previously exposed records carry PDB accessions without verified family IDs.
Unknown family/clan and legacy tool-training provenance still limit independence
claims, even where sequence screening passes.

## Verification

- Full suite: **516 passed in 216.49 seconds**
  (`reports/prospective-evidence-full-suite-2026-10-11.log`).
- Eight focused evidence tests passed.
- Successful user metadata acquisition and workspace evidence failure-ledger
  audits passed without network access or inference.
- New Python files pass Ruff with script-bootstrap E402 ignored, compileall and
  whitespace checks.

## Pending work

Acquire the ten evidence/annotation files. Inspect real mapping schemas, compare
PDB/clan provenance against exposures, and bind the 15 selected sequences exactly
to their Stockholm alignment members. Consensus-derived comparative annotation
must remain classified separately from direct experimental measurement.
Unsupported pseudoknots, missing paired columns and sequence mismatches must stay
explicit; do not silently drop annotated contacts or replace selected records.
Freeze the final evaluation plan before test inference.

Independent biological accuracy, long biological RNA validation and experimental
stability/function remain pending. No new test score or stability result is
claimed. Changes are local; no Git commit, push or publication-checkout update
was made. The pre-existing Git index was preserved.

## Exact continuation commands

Offline verification:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/download_prospective_evidence.py --verify
.venv/bin/python -m pytest -q tests/test_prospective_evidence.py
```

From a terminal with network access, fetch the next batch while preserving the
successful source selection:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/download_prospective_evidence.py --acquisition /home/zyliu/Documents/rna-stable-ai/results/prospective_family_acquisition_runs/20261012T024003.811773Z/summary.json
.venv/bin/python scripts/download_prospective_evidence.py --verify
cat reports/prospective_evidence_report.md
```

Check **Evidence acquisition complete: True** in that report. A successful
failure-ledger audit alone does not imply successful downloads. On user return,
inspect `results/prospective_evidence_summary.json` and its retained run files.
No need to reacquire metadata or refreeze the model protocol.

## Evidence

- `reports/prospective_evidence_development_2026-10-11.md`
- `reports/prospective_evidence_report.md`
- `reports/prospective-evidence-audit-2026-10-11.log`
- `reports/prospective_family_acquisition_report.md`
- `reports/PROJECT_ROADMAP_2026-10-11.md`
