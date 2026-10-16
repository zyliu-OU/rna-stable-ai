# RNA-StableAI coverage development dataset review — 2026-10-15

The original frozen sequence-first source run remains unchanged: 140 selected
records, 81 complete references and 59 unsupported references. RF00024 supplied
zero complete references. A first versioned extension selected RF00022 as the
next unused metadata-ranked training group before its source was read. That
sequence-first extension selected seven records, all unsupported because paired
consensus columns were absent. Its run and denominator remain retained.

The next protocol explicitly used that **development label feedback**. It
reused the hash-bound RF00022 source, screened every sequence against the frozen
prior exposure ledger and the 15 retained family selections, required complete
consensus paired-column coverage, then selected nonredundant candidates by
lexicographic ID up to the declared cap. Every candidate decision and missing
paired-column count is retained. The two selected RF00022 references preserve
their complete WUSS pair sets. This is a revised development dataset, not an
independent test or a post hoc repair of the earlier frozen runs.

The final derived dataset has **130 selected records**, including **83 complete
computational pair references**: 61 training and 22 validation. The other 47
selected records retain unsupported status. All 12 training and four validation
family/clan groups have at least one complete reference, so the declared
48/16 aggregate and one-per-family gates pass. `train.json` and
`validation.json` are hash-bound in
`results/family_coverage_development_runs/20261016T011555.025711Z/`.
No model fitting, inference, checkpoint selection or independent biological
validation was performed. Label-informed selection limits any future accuracy
claim from these records to development use. The old 59-unsupported and
seven-unsupported denominators remain visible in their prior runs.

The RF00022 source was downloaded only after the first extension protocol was
frozen. The sandbox DNS attempt failed; an approved network retry succeeded.
The final coverage protocol performed no new downloads. UTC run-directory
timestamps correspond to the local October 15 work date.

The focused extension/coverage tests passed (three tests). The full suite passed
**826 tests in 216.40 seconds**; see
[`family-coverage-full-suite-2026-10-15.log`](family-coverage-full-suite-2026-10-15.log).

Verification commands:

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/extend_family_provenance_dataset.py --verify results/family_provenance_extension_summary.json
.venv/bin/python scripts/derive_coverage_development_dataset.py --verify results/family_coverage_development_summary.json
.venv/bin/python -m pytest -q tests/test_family_provenance_extension.py tests/test_family_coverage_development.py
```
