#!/usr/bin/env python3
"""Audit raw sweep evidence and the published paired replication artifacts."""
import csv
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
path = ROOT/'results/evaluation_replication_summary.json'
subprocess.run([sys.executable, str(ROOT/'scripts/verify_sweep.py'), '--summary', str(path)], check=True)
summary = json.loads(path.read_text())
rows = summary['rows']
assert len(rows) == 18
pairs = summary['paired_comparisons']
assert len(pairs) == 9
csv_rows = list(csv.DictReader((ROOT/'results/evaluation_replication_pairs.csv').open()))
assert len(csv_rows) == len(pairs)
for pair, csv_row in zip(pairs, csv_rows):
    matched = [r for r in rows if all(r[k] == pair[k] for k in
               ('kind', 'length', 'sequence_seed', 'search_seed'))]
    assert len(matched) == 2
    low = next(r for r in matched if r['beam_size'] == 200)
    high = next(r for r in matched if r['beam_size'] == 400)
    assert low['input_sha256'] == high['input_sha256'] == pair['input_sha256']
    assert pair['low_status'] == low['status'] and pair['high_status'] == high['status']
    expected = {}
    for output, key in [('input_pair_f1_change', 'input_pair_f1'),
                        ('vienna_delta_difference_kcal_mol', 'vienna_delta_kcal_mol')]:
        a, b = low.get(key), high.get(key)
        expected[output] = b-a if a is not None and b is not None else None
    a, b = low.get('input_lf_wall_seconds'), high.get('input_lf_wall_seconds')
    expected['input_lf_time_ratio'] = b/a if a is not None and a > 0 and b is not None else None
    for key, value in expected.items():
        if value is None:
            assert pair[key] is None and csv_row[key] == ''
        else:
            assert math.isclose(pair[key], value, abs_tol=1e-10)
            assert math.isclose(float(csv_row[key]), value, abs_tol=1e-10)
    for key, value in pair.items():
        assert csv_row[key] == ('' if value is None else str(value))
print('Replication audit passed: 9 matched pairs; differences, timing ratios and CSV verified.')
