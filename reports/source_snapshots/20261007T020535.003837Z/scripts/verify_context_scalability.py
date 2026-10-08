#!/usr/bin/env python3
"""Replay synthetic long-sequence inference for the frozen context checkpoint."""
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.banded_pairs import band_scores,decode_band
from rnastable.context_pairs import make_context_model
from rnastable.reference import digest
from rnastable.reference_audit import require


def audit_scalability(path):
    import torch
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir'])
    require(summary['complete'] is True and summary['test_evaluated'] is False and summary['purpose']=='synthetic_scalability_only','not a synthetic scalability run')
    require(json.loads((run/'summary.json').read_text())==summary,'retained summary differs')
    for name,key in [('manifest.json','manifest_sha256'),('predictions.json','predictions_sha256')]:require(digest((run/name).read_bytes())==summary[key],name+' changed')
    manifest=json.loads((run/'manifest.json').read_text())
    require(manifest['run_dir']==str(run) and manifest['purpose']==summary['purpose'] and manifest['test_evaluated'] is False,'manifest identity differs')
    require(digest((run/'inputs.json').read_bytes())==manifest['input_sha256'] and digest((run/'development_summary.json').read_bytes())==manifest['development_summary_sha256'],'frozen inputs changed')
    development=json.loads((run/'development_summary.json').read_text());config=manifest['config'];checkpoint=Path(manifest['checkpoint'])
    require(config==development['config'] and checkpoint==Path(development['run_dir'])/'best_context_model.pt','checkpoint identity differs')
    require(digest(checkpoint.read_bytes())==manifest['checkpoint_sha256']==development['checkpoint_sha256'][checkpoint.name],'checkpoint changed')
    rng=np.random.default_rng(manifest['seed']);records=[{'id':'synthetic_'+str(n),'sequence':''.join(rng.choice(list('ACGU'),n))} for n in (1000,5000,10000)]
    require(records==json.loads((run/'inputs.json').read_text()),'synthetic plan differs')
    rows=json.loads((run/'predictions.json').read_text());require(len(rows)==len(records),'prediction inventory differs')
    torch.set_num_threads(config['cpu_threads']);model=make_context_model(config);model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True))
    for record,row in zip(records,rows):
        require(row['id']==record['id'] and row['length']==len(record['sequence']),'sequence identity differs')
        expected=decode_band(record['sequence'],band_scores(model,record['sequence'],config['max_pair_span']),config['max_pair_span'])
        require(all(row[k]==v for k,v in expected.items()),'context prediction or allocation bytes differ')
        require(all(type(row[k]) in (int,float) and np.isfinite(row[k]) and row[k]>=0 for k in ('scoring_wall_seconds','decoding_wall_seconds')),'invalid timing')
    require([{k:v for k,v in row.items() if k!='structure'} for row in rows]==summary['rows'],'scalability summary differs')
    print('Context scalability audit passed: exact frozen checkpoint replay on synthetic 1000/5000/10000 nt; no accuracy evaluation.')
    return summary

if __name__=='__main__':audit_scalability(ROOT/'results/context_scalability_summary.json')
