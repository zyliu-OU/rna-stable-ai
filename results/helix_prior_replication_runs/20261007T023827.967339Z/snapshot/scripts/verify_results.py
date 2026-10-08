#!/usr/bin/env python3
"""Check benchmark artifact integrity without treating unavailable runs as measured."""
import csv
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
summary = json.loads((ROOT/'results/benchmark_summary.json').read_text())
for item in summary['synthetic_manifest']:
    sequence = ''.join(Path(item['path']).read_text().splitlines()[1:])
    assert len(sequence) == item['length']
    assert set(sequence) <= set('ACGU')
    assert hashlib.sha256(sequence.encode()).hexdigest() == item['sha256']
folding = list(csv.DictReader((ROOT/'results/folding_benchmark.csv').open()))
gpu = list(csv.DictReader((ROOT/'results/gpu_benchmark.csv').open()))
assert len(folding) == len(summary['synthetic_manifest'])*3
assert len(gpu) == len(summary['config']['lengths'])
for row in folding:
    assert row['device'] == 'CPU'
    if row['status'] == 'unavailable':
        assert row['wall_seconds'] == '' and row['mfe_kcal_mol'] == ''
    if row['tool'] == 'LinearPartition':
        assert row['mfe_kcal_mol'] == ''
for row in gpu:
    if row['cuda_available'] == 'False':
        assert row['gpu_seconds'] == '' and row['peak_gpu_memory_mib'] == '' and row['transfer_seconds'] == ''
print(f'Artifact verification passed: {len(summary["synthetic_manifest"])} FASTA records, {len(folding)} CPU folding rows, {len(gpu)} encoder rows.')
