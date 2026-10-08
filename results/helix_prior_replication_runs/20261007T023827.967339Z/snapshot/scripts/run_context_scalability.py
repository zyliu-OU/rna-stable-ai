#!/usr/bin/env python3
"""Measure the selected context checkpoint on synthetic long inputs without accuracy labels."""
import json
from pathlib import Path
import resource
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp
from rnastable.banded_pairs import band_scores,decode_band
from rnastable.context_pairs import make_context_model
from rnastable.reference import digest


def main():
    import torch
    development_path=ROOT/'results/context_development_summary.json';development=json.loads(development_path.read_text());config=development['config']
    checkpoint=Path(development['run_dir'])/'best_context_model.pt'
    if digest(checkpoint.read_bytes())!=development['checkpoint_sha256'][checkpoint.name]:raise ValueError('Context checkpoint changed')
    torch.set_num_threads(2);model=make_context_model(config);model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True))
    rng=np.random.default_rng(20261006);records=[{'id':'synthetic_'+str(n),'sequence':''.join(rng.choice(list('ACGU'),n))} for n in (1000,5000,10000)]
    run=ROOT/'results/context_scalability_runs'/timestamp();run.mkdir(parents=True)
    (run/'inputs.json').write_text(json.dumps(records,indent=2)+'\n');(run/'development_summary.json').write_bytes(development_path.read_bytes())
    paths=[Path(__file__),ROOT/'src/rnastable/context_pairs.py',ROOT/'src/rnastable/banded_pairs.py']
    manifest={'run_dir':str(run),'purpose':'synthetic_scalability_only','test_evaluated':False,'config':config,'seed':20261006,'checkpoint':str(checkpoint),'checkpoint_sha256':digest(checkpoint.read_bytes()),'input_sha256':digest((run/'inputs.json').read_bytes()),'development_summary_sha256':digest((run/'development_summary.json').read_bytes()),'code_sha256':{str(p):digest(p.read_bytes()) for p in paths}}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');rows=[]
    for record in records:
        begin=time.monotonic();scores=band_scores(model,record['sequence'],config['max_pair_span']);score_time=time.monotonic()-begin
        begin=time.monotonic();decoded=decode_band(record['sequence'],scores,config['max_pair_span']);decode_time=time.monotonic()-begin
        row={'id':record['id'],'length':len(record['sequence']),**decoded,'scoring_wall_seconds':score_time,'decoding_wall_seconds':decode_time};rows.append(row)
        print(json.dumps({k:v for k,v in row.items() if k!='structure'}),flush=True)
    (run/'predictions.json').write_text(json.dumps(rows,indent=2)+'\n')
    summary={'complete':True,'run_dir':str(run),'purpose':'synthetic_scalability_only','test_evaluated':False,'manifest_sha256':digest((run/'manifest.json').read_bytes()),'predictions_sha256':digest((run/'predictions.json').read_bytes()),'rows':[{k:v for k,v in r.items() if k!='structure'} for r in rows],'process_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limitations':['No accuracy labels; no biological stability or long-RNA generalization claim.','Fixed pair span excludes distant contacts.','Array bytes exclude Torch/process allocations; RSS peak is cumulative for this process.','One observation per length; no isolated speedup claim.']}
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(ROOT/'results/context_scalability_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
