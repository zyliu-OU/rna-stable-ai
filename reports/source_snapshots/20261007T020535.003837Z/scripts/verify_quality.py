#!/usr/bin/env python3
"""Audit saved structure comparison metrics against retained raw outputs."""
import json
import math
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.artifacts import sha256
from rnastable.folding import parse_output
from rnastable.scoring import structure_agreement
from rnastable.sequences import read_fasta
quality = json.loads((ROOT/'results/folding_quality_summary.json').read_text())
source = json.loads(Path(quality['source_benchmark']).read_text())
assert source['utc'] == quality['source_utc']
manifest = {m['id']: m for m in source['synthetic_manifest']}
assert len(quality['rows']) == len(manifest)
for row, detail in zip(quality['rows'], quality['evidence']):
    assert row['sequence_id'] == detail['sequence_id']
    assert row['status'] == 'ok', row
    item = manifest[row['sequence_id']]
    sequence = read_fasta(item['path'])[0][1]
    assert sha256(sequence) == item['sha256']
    ref = detail['reference']; pred = detail['prediction']
    for tool, record in [('ViennaRNA', ref), ('LinearFold', pred)]:
        raw = Path(record['raw_output']).read_text()
        assert sequence in raw.splitlines()
        parsed = parse_output(tool, raw, len(sequence))
        assert parsed['structure'] == record['structure']
        assert parsed['mfe_kcal_mol'] == record['mfe_kcal_mol']
    scores = structure_agreement(pred['structure'], ref['structure'])
    for key, value in scores.items():
        assert math.isclose(row[key], value, abs_tol=1e-10)
    assert math.isclose(row['reported_energy_gap_kcal_mol'], pred['mfe_kcal_mol']-ref['mfe_kcal_mol'], abs_tol=1e-8)
    assert math.isclose(row['reevaluated_gap_kcal_mol'], detail['vienna_evaluation']['energy_kcal_mol']-ref['mfe_kcal_mol'], abs_tol=1e-8)
print(f'Quality audit passed: {len(quality["rows"])} exact-input comparisons, raw structures and all pair/energy metrics verified.')
