# RNA-StableAI handoff — 2026-10-16 V2

Project: RNA-StableAI. Date: 2026-10-16 (America/Los_Angeles). Version: V2.
Workspace: `/home/zyliu/Documents/rna-stable-ai`.
State: development was stopped immediately at the user's request. Work is
partial and unverified; no new protocol was frozen, no source was acquired, no
model inference was run, and nothing from this development step was uploaded.

## Completed work

Reviewed the V1 handoff, current roadmap, fresh-structure readiness report,
reference-readiness policy, inventory code, panel-freeze code and relevant
tests. Recomputed the metadata-only inventory in memory after the first contact
panel became exposed. It reported 4,985 known exposed sequences, 54 known
exposed families, 165 known exposed PDB accessions, and 73 remaining
metadata-only candidate families. Twenty-one candidates retained at least four
unexposed PDB accessions.

Drafted, but did not validate, a second metadata-only panel design:

- `configs/fresh_structure_panel_2026-10-16.json`
- `scripts/plan_sequence_diverse_structure_panel.py`
- `tests/test_sequence_diverse_structure_panel.py`

The draft selects eight unexposed families with varied RNA roles and distinct
known clans where available, and proposes deterministic evenly spaced sampling
over sorted distinct PDB accessions. Its intent is to broaden provenance before
any sequence or contact label is read. The draft preserves the no-replacement,
no-inference and provenance-audit requirements.

## Verification

Only a read-only existence check was completed after the stop request: the
three draft files exist with 36, 206 and 75 lines respectively. Tests, Python
compilation, formatting checks, protocol replay and scientific review were not
run. The draft must not be treated as valid or frozen.

## Pending work

Development is paused at the user's request. If resumed, first review the three
draft files for correctness and scientific selection bias. Run focused tests
and compilation before freezing anything. If validation succeeds, freeze the
metadata-only protocol before acquiring candidate sequences or contact labels.
Do not run model inference until reference coverage, per-sequence annotation
lineage and tool-training provenance gates all pass.

The independent biological reference gate remains closed. Long biological RNA,
causal stability, mutation effects and retained function remain open. No
validated release exists.

## Exact continuation commands

```bash
cd /home/zyliu/Documents/rna-stable-ai
cat AGENTS.md
cat reports/RNA-StableAI_HANDOFF_2026-10-16_V2.md
sed -n '1,260p' scripts/plan_sequence_diverse_structure_panel.py
cat configs/fresh_structure_panel_2026-10-16.json
.venv/bin/python -m pytest -q tests/test_sequence_diverse_structure_panel.py
.venv/bin/python -m py_compile scripts/plan_sequence_diverse_structure_panel.py
git diff --check -- configs/fresh_structure_panel_2026-10-16.json scripts/plan_sequence_diverse_structure_panel.py tests/test_sequence_diverse_structure_panel.py reports/RNA-StableAI_HANDOFF_2026-10-16_V2.md
```

Only after review and successful validation, freeze with:

```bash
.venv/bin/python scripts/plan_sequence_diverse_structure_panel.py
.venv/bin/python scripts/plan_sequence_diverse_structure_panel.py --verify results/sequence_diverse_structure_panel_protocol.json
```

Before any future GitHub publication, inspect the live README and preserve the
user's picture and any repository image assets.
