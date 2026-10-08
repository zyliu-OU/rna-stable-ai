#!/usr/bin/env python3
"""Replay band-limited predictions and audit the measured scalability artifacts."""
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.banded_pairs import band_scores, decode_band
from rnastable.pair_model import make_pair_model
from rnastable.reference import digest
from rnastable.reference_audit import require
from rnastable.scoring import base_pairs, structure_agreement


def audit_banded(path):
    import torch
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir'])
    require(summary['complete'] is True and summary['test_evaluated'] is False,'development identity differs')
    require(summary==json.loads((run/'summary.json').read_text()),'retained summary differs')
    for name,key in [('manifest.json','manifest_sha256'),('predictions.json','predictions_sha256')]:require(digest((run/name).read_bytes())==summary[key],name+' changed')
    manifest=json.loads((run/'manifest.json').read_text());config=manifest['config']
    require(config=={'max_pair_span':64,'cpu_threads':2,'synthetic_seed':20261006} and config==summary['config'],'fixed configuration differs')
    require(digest((run/'inputs.json').read_bytes())==manifest['inputs_sha256'],'inputs changed')
    checkpoint=Path(manifest['source_checkpoint']);require(digest(checkpoint.read_bytes())==manifest['source_checkpoint_sha256'],'checkpoint changed')
    original=json.loads((checkpoint.parent/'training.json').read_text())
    require(original['config']==manifest['model_config'] and original['best_checkpoint_sha256']==manifest['source_checkpoint_sha256'],'source model binding differs')
    inputs=json.loads((run/'inputs.json').read_text());results=json.loads((run/'predictions.json').read_text())
    prior_validation=json.loads((checkpoint.parent/'validation.json').read_text())['records']
    rng=np.random.default_rng(config['synthetic_seed'])
    expected=[{**r,'purpose':'reused_development_validation'} for r in prior_validation]+[{'id':'synthetic_'+str(n),'sequence':''.join(rng.choice(list('ACGU'),n)),'purpose':'synthetic_scalability_only'} for n in (1000,5000,10000)]
    require(inputs==expected and len(results)==len(inputs),'development input plan differs')
    torch.set_num_threads(2);model=make_pair_model(manifest['model_config']);model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True))
    scores=[];outside=0;synthetic=[]
    for record,row in zip(inputs,results):
        require(row['id']==record['id'] and row['length']==len(record['sequence']) and row['purpose']==record['purpose'],'prediction identity differs')
        decoded=decode_band(record['sequence'],band_scores(model,record['sequence'],64),64)
        require(all(row[k]==v for k,v in decoded.items()),'decoded result or allocation bytes differ')
        require(all(type(row[k]) in (int,float) and np.isfinite(row[k]) and row[k]>=0 for k in ('scoring_wall_seconds','decoding_wall_seconds')),'invalid timing')
        if 'structure' in record:
            metrics=structure_agreement(row['structure'],record['structure']);excluded=sum(j-i>64 for i,j in base_pairs(record['structure']))
            require(row['agreement']==metrics and row['reference_contacts_outside_band']==excluded,'development score/coverage differs')
            scores.append(metrics['pair_f1']);outside+=excluded
        else:synthetic.append({k:v for k,v in row.items() if k!='structure'})
    require(len(scores)==summary['validation_records'] and sum(scores)/len(scores)==summary['validation_mean_pair_f1'] and outside==summary['reference_contacts_outside_band'],'validation summary differs')
    require(synthetic==summary['synthetic'],'synthetic summary differs')
    print(f'Banded development audit passed: {len(scores)} reused validation records; synthetic lengths 1000/5000/10000; exact replay and array storage verified; no test evaluation.')
    return summary

if __name__=='__main__': audit_banded(ROOT/'results/banded_development_summary.json')
