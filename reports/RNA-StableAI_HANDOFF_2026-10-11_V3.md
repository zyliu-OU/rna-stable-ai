# RNA-StableAI handoff

- Project: RNA-StableAI
- Date: 2026-10-11 (America/Los_Angeles)
- Version: V3
- Workspace: `/home/zyliu/Documents/rna-stable-ai`
- Saved UTC: 2026-10-12T02:37:35.102545+00:00
- Current roadmap step: **4 — independent biological validation**.

## Completed work

Added a preliminary prospective source-screening protocol and bounded Rfam
acquisition workflow. Config: `configs/prospective_family_panel.json`.
Implementation: `src/rnastable/prospective_data.py` and
`scripts/prepare_prospective_family_panel.py`.

The protocol freezes all three baseline/stack/helix model-seed-20261006 source
summaries, configurations and checkpoint bytes before new source outcomes. Exact
sparse decoding, zero pair penalty, 20–512 nt screening, sorted sequence IDs and
a cap of five nonredundant entries per family are fixed. Proposed source families
are RF00059/RF00162/RF00167. They are not yet approved independent test families.
No new model selection, training, structure labels or test inference occurred.

Frozen protocol: `/home/zyliu/Documents/rna-stable-ai/results/prospective_family_protocol_runs/20261012T023120.466587Z/manifest.json`.
Retained acquisition ledger: `/home/zyliu/Documents/rna-stable-ai/results/prospective_family_acquisition_runs/20261012T023237.122453Z`.

Downloads use official HTTPS family descriptions and ungapped seed FASTA
endpoints documented at https://docs.rfam.org/en/latest/api.html. Accession
binding, response limits, byte hashes and explicit uppercase/T-to-U normalization
are validated. The current live exposure ledger is rechecked before acquisition.
Errors, unstarted dependencies, invalid/redundant sequences and cap exclusions
remain visible. Every invocation retains a new attempt directory. Offline replay
uses snapshots, with no network access or prediction.

The earlier exposure heuristic now skips comparisons whose mathematically exact
length-based upper bound is below0.8, preserving the symmetric SequenceMatcher
screening decisions. The earlier local readiness result still replays unchanged.

## Actual data acquisition state

All three family-description requests failed with workspace DNS resolution errors;
their three dependent sequence requests remain unstarted. No new source files
were downloaded. `sources_complete:false` distinguishes missing acquisition from
an empty screened biological cohort. `complete:true` means the attempt ledger
finished, not that retrieval or evaluation succeeded. Browser raw-alignment
retrieval also failed; no replacement sequences were fabricated.

Local metadata still contains474 entries in four exposed families and zero new
candidates. Exact matching against local Rfam metadata resolves none of the3104
exposures lacking family IDs. Sixty-nine unassigned exposure records carry PDB
accessions. Exposure counts include generated/inference and development records;
they are not counts of distinct biological training examples. Family/clan and
legacy folding-tool training provenance remain unresolved.

## Verification

- Full suite: **508 passed in216.24seconds**
  (`reports/prospective-family-full-suite-2026-10-11.log`).
- Focused source/readiness checks:20 passed.
- Eleven new tests cover source-accession binding, FASTA normalization, malformed
  and oversized responses, redirects, heuristic upper-bound equivalence, fixed
  panel denominators, DNS ledger replay, fixture success without inference
  authorization, checkpoint tampering and family exposure after protocol freeze.
- Retained acquisition ledger and previous readiness audit replay passed.
- Changed/new Python files pass Ruff with script-bootstrap E402 ignored,
  compileall and whitespace checks.

## Pending work

Restore source access and rerun acquisition against the frozen protocol. Resolve
family/clan relationships and training/development overlap, including PDB mappings.
Bind selected sequences to exact annotation sources before freezing a final
exposure-aware evaluation plan. This preliminary protocol never authorizes test
inference, even after metadata downloads succeed. No independent biological
accuracy or stability result has been produced.

Long biological annotations, experimental stability/function evidence and a
validated release remain pending. The existing frozen native studies remain
complete. Changes are local; no Git commit, push or publication-checkout update
occurred. The original staged Git index remains preserved.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/prepare_prospective_family_panel.py --verify
.venv/bin/python scripts/audit_family_readiness.py --verify
.venv/bin/python -m pytest -q tests/test_prospective_data.py tests/test_family_readiness.py
```

When network source access is available, reuse this frozen protocol:

```bash
.venv/bin/python scripts/prepare_prospective_family_panel.py --acquire --protocol /home/zyliu/Documents/rna-stable-ai/results/prospective_family_protocol_runs/20261012T023120.466587Z/manifest.json
.venv/bin/python scripts/prepare_prospective_family_panel.py --verify
.venv/bin/python -m pytest -q
```

Do not call the freeze command again merely to retry a failed download: retain
checkpoint/selection identity by supplying the protocol path above. A later new
family exposure rejects acquisition; it must not be bypassed by editing the
frozen ledger. No structure import or evaluation command is authorized by the
metadata-screening protocol.

## Evidence

- `reports/prospective_family_development_2026-10-11.md`
- `reports/prospective_family_acquisition_report.md`
- `reports/prospective-family-acquisition-2026-10-11.log`
- `reports/prospective-family-final-audit-2026-10-11.log`
- `reports/PROJECT_ROADMAP_2026-10-11.md`
