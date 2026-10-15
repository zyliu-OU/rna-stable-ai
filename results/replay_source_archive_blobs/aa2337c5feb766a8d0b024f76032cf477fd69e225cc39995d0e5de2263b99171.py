#!/usr/bin/env python3
"""Train sequence-only local-helix head on frozen expanded development only."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp
from rnastable.context_training import train_context
from rnastable.exact_sparse_pairs import decode_exact_sparse
from rnastable.exposures import record_exposure
from rnastable.full_pair_supervision import full_supervision
from rnastable.global_sparse_pairs import sparse_candidates
from rnastable.helix_pairs import make_helix_model,FEATURE_NAMES
from rnastable.reference import digest,run_reference_evaluation
from rnastable.reference_audit import require
from train_sampled_comparative_development import frozen_inputs


def predictions(model,records,method,config):
    rows=[]
    for record in records:
        candidates=sparse_candidates(model,record['sequence'],config['top_k'],config['block_size'])
        result=decode_exact_sparse(record['sequence'],candidates['pairs'],candidates['scores'])
        rows.append({'id':record['id'],'sequence':record['sequence'],'method':method,'status':'ok','structure':result['structure']})
    return rows


def main():
    config=json.loads((ROOT/'configs/helix_comparative_development.json').read_text());source_bytes,source,snapshots,splits=frozen_inputs(ROOT/'results/exact_comparative_development_summary.json')
    expected={**source['config'],'pair_features':'local_helix_context_v1'};require(config==expected,'Other training settings changed')
    require(all(len(r['sequence'])<=1024 for rs in splits.values() for r in rs),'Exact sparse bound exceeded')
    run=ROOT/'results/helix_comparative_development_runs'/timestamp();run.mkdir(parents=True,exist_ok=False);(run/'source_summary.json').write_bytes(source_bytes)
    for name,data in snapshots.items():(run/(name+'.json')).write_bytes(data)
    paths=[Path(__file__),ROOT/'scripts/train_sampled_comparative_development.py',*[ROOT/'src/rnastable'/n for n in ('helix_pairs.py','exact_sparse_pairs.py','full_pair_supervision.py','global_sparse_pairs.py','context_training.py','context_pairs.py','exposures.py','reference.py','scoring.py')]]
    manifest={'run_dir':str(run),'config':config,'source_summary_sha256':digest(source_bytes),'snapshot_sha256':{name:digest((run/name).read_bytes()) for name in ('train.json','validation.json')},'code_sha256':{str(p):digest(p.read_bytes()) for p in paths},'policy':'Same frozen89/47 development records, full labels and optimizer settings. Fresh random initialization. Eight sequence-only contiguous local-helix/pair-type indicators with zero initial weights; full BCE and exact sparse validation selection. No fresh test.'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');events=[record_exposure(run,'training_started',splits['train']),record_exposure(run,'validation_started',splits['validation'])]
    initial,model,training=train_context(splits['train'],splits['validation'],config,run,model_factory=make_helix_model,labeler=lambda r:full_supervision(r,config['training_max_length']),predictor=lambda m,rs,method:predictions(m,rs,method,config))
    pred=predictions(initial,splits['validation'],'untrained_helix_sparse',config)+predictions(model,splits['validation'],'trained_helix_sparse',config)
    (run/'predictions.json').write_text(json.dumps({'schema_version':1,'methods':['untrained_helix_sparse','trained_helix_sparse'],'records':pred},indent=2)+'\n');evaluation=run_reference_evaluation(run,run/'validation.json',run/'predictions.json')
    summary={'complete':True,'mode':config['mode'],'test_evaluated':False,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'config':config,'counts':source['counts'],'feature_names':list(FEATURE_NAMES),'helix_weights':model.helix_weights.weight.detach().tolist()[0],**training,'exposure_events':events,'predictions_sha256':digest((run/'predictions.json').read_bytes()),'aggregates':evaluation['aggregates'],'limitations':['One seed on already exposed development; validation selection does not establish generalization.','Exact maximum logits over top16 positive candidates, not all legal pairs or reference agreement; bounded to1024 nt with quadratic storage.','Comparative annotation is not an experimental assay; biological stability/family independence remain unresolved.']}
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(ROOT/'results/helix_comparative_development_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
