#!/usr/bin/env python3
"""Measure fixed-span inference on reused validation and synthetic long inputs only."""
import json
import resource
from pathlib import Path
import sys
import time
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.artifacts import timestamp
from rnastable.banded_pairs import band_scores, decode_band
from rnastable.pair_model import make_pair_model
from rnastable.reference import digest
from rnastable.scoring import base_pairs, structure_agreement


def main():
    import torch
    prior = json.loads((ROOT/'results/pair_development_summary.json').read_text())
    source = Path(prior['run_dir']); training = prior['training']; checkpoint = source/'best_pair_model.pt'
    if digest(checkpoint.read_bytes()) != training['best_checkpoint_sha256']: raise ValueError('Development checkpoint changed')
    torch.set_num_threads(2)
    model = make_pair_model(training['config']); model.load_state_dict(torch.load(checkpoint, map_location='cpu', weights_only=True))
    validation = json.loads((source/'validation.json').read_text())['records']
    rng = np.random.default_rng(20261006)
    records = [{**r, 'purpose': 'reused_development_validation'} for r in validation]
    records += [{'id': 'synthetic_'+str(n), 'sequence': ''.join(rng.choice(list('ACGU'), n)), 'purpose': 'synthetic_scalability_only'} for n in (1000, 5000, 10000)]
    run = ROOT/'results/banded_development_runs'/timestamp(); run.mkdir(parents=True)
    (run/'inputs.json').write_text(json.dumps(records, indent=2)+'\n')
    config = {'max_pair_span': 64, 'cpu_threads': 2, 'synthetic_seed': 20261006}
    manifest = {'run_dir': str(run), 'config': config, 'source_checkpoint': str(checkpoint), 'source_checkpoint_sha256': digest(checkpoint.read_bytes()), 'model_config': training['config'], 'inputs_sha256': digest((run/'inputs.json').read_bytes()), 'code_sha256': {str(p):digest(p.read_bytes()) for p in (Path(__file__), ROOT/'src/rnastable/banded_pairs.py', ROOT/'src/rnastable/pair_model.py')}, 'policy': 'Reused validation and synthetic inputs only. No test evaluation; no accuracy claim for synthetic long inputs.'}
    (run/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    results = []
    for record in records:
        begin = time.monotonic(); scores = band_scores(model, record['sequence'], 64); scoring_seconds = time.monotonic()-begin
        begin = time.monotonic(); decoded = decode_band(record['sequence'], scores, 64); decoding_seconds = time.monotonic()-begin
        row = {'id': record['id'], 'purpose': record['purpose'], 'length': len(record['sequence']), **decoded, 'scoring_wall_seconds': scoring_seconds, 'decoding_wall_seconds': decoding_seconds}
        if 'structure' in record:
            row['agreement'] = structure_agreement(decoded['structure'], record['structure'])
            row['reference_contacts_outside_band'] = sum(j-i>64 for i,j in base_pairs(record['structure']))
        results.append(row)
        print(json.dumps({k:v for k,v in row.items() if k not in ('structure','interpretation')}),flush=True)
    (run/'predictions.json').write_text(json.dumps(results, indent=2)+'\n')
    summary = {'complete': True, 'run_dir': str(run), 'manifest_sha256': digest((run/'manifest.json').read_bytes()), 'predictions_sha256': digest((run/'predictions.json').read_bytes()), 'config': config, 'test_evaluated': False, 'validation_records': len(validation), 'validation_mean_pair_f1': sum(r['agreement']['pair_f1'] for r in results[:len(validation)])/len(validation), 'reference_contacts_outside_band': sum(r['reference_contacts_outside_band'] for r in results[:len(validation)]), 'synthetic': [{k:v for k,v in r.items() if k!='structure'} for r in results if r['purpose']=='synthetic_scalability_only'], 'process_peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, 'memory_scope': 'DP and score arrays are exact byte counts; process peak includes Torch, input and transient scoring allocations and all prior cases in this process.', 'limitations': ['Fixed span 64 excludes longer contacts; not unrestricted global pairing.', 'One timing per input, no speedup claim.', 'Synthetic long inputs have no accuracy labels; old short validation is reused development only.']}
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (ROOT/'results/banded_development_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__ == '__main__': main()
