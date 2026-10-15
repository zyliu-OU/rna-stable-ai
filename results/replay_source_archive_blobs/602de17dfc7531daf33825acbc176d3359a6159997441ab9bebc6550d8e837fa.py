#!/usr/bin/env python3
"""Extend development training with frozen longer CRW annotations, never upstream test records."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp
from rnastable.context_training import train_context
from rnastable.crw_development_data import load_crw_development,select_crw
from rnastable.exposures import collect_known_exposures,record_exposure
from rnastable.full_pair_supervision import full_supervision
from rnastable.global_sparse_pairs import make_global_model,sparse_candidates
from rnastable.sparse_refinement import refine_sparse
from rnastable.reference import digest,run_reference_evaluation
from train_context_development import inputs


def predictions(model,records,method,config):
    rows=[]
    for record in records:
        candidates=sparse_candidates(model,record['sequence'],config['top_k'],config['block_size'])
        result=refine_sparse(record['sequence'],candidates['pairs'],candidates['scores'],**config['refinement'])
        rows.append({'id':record['id'],'sequence':record['sequence'],'method':method,'status':'ok','structure':result['structure']})
    return rows


def main():
    config=json.loads((ROOT/'configs/long_comparative_development.json').read_text());data_config=json.loads((ROOT/'configs/crw_development_data.json').read_text())
    if config['mode']!='long_comparative_development_only' or config['training_max_length']!=1024 or config['top_k']!=16 or config['block_size']!=64 or config['refinement']!={'passes':2,'max_remove':2,'group_cap':8,'include_subsets':True}:raise ValueError('Invalid fixed longer-development configuration')
    train,validation,original_sources=inputs();exposed=collect_known_exposures(ROOT)
    candidates,imported=load_crw_development(ROOT/'external/EternaFold',data_config)
    new,exclusions=select_crw(candidates,data_config,exposed,{'train':train,'validation':validation});imported['selection_exclusions']=exclusions
    print(json.dumps({'new_counts':{s:len(rows) for s,rows in new.items()},'lengths':{s:[min(len(r['sequence']) for r in rows),max(len(r['sequence']) for r in rows)] for s,rows in new.items()}},indent=2),flush=True)
    train+=new['train'];validation+=new['validation']
    run=ROOT/'results/long_comparative_development_runs'/timestamp();run.mkdir(parents=True)
    for name,data in [('train.json',{'schema_version':1,'dataset_id':'expanded_comparative_train','records':train}),('validation.json',{'schema_version':1,'dataset_id':'expanded_comparative_validation','records':validation}),('exposure.json',exposed),('import.json',imported),('new_crw.json',new)]:(run/name).write_text(json.dumps(data,indent=2)+'\n')
    paths=[Path(__file__),ROOT/'scripts/train_context_development.py',*[ROOT/'src/rnastable'/n for n in ('crw_development_data.py','full_pair_supervision.py','global_sparse_pairs.py','sparse_refinement.py','context_training.py','context_pairs.py','exposures.py','reference.py','scoring.py')]]
    manifest={'run_dir':str(run),'config':config,'data_config':data_config,'original_development_sources':original_sources,'snapshot_sha256':{name:digest((run/name).read_bytes()) for name in ('train.json','validation.json','exposure.json','import.json','new_crw.json')},'code_sha256':{str(p):digest(p.read_bytes()) for p in paths},'policy':'Development only; exact CRW source binding; prior sequence exposure filtering and validation-priority external-ID/sequence separation. Broad RNA types do not establish family independence. No upstream test import or test predictions.'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');events=[record_exposure(run,'training_started',train),record_exposure(run,'validation_started',validation)]
    initial,model,training=train_context(train,validation,config,run,model_factory=make_global_model,labeler=lambda r:full_supervision(r,config['training_max_length']),predictor=lambda m,rs,method:predictions(m,rs,method,config))
    pred=predictions(initial,validation,'untrained_expanded_sparse',config)+predictions(model,validation,'trained_expanded_sparse',config)
    (run/'predictions.json').write_text(json.dumps({'schema_version':1,'methods':['untrained_expanded_sparse','trained_expanded_sparse'],'records':pred},indent=2)+'\n')
    evaluation=run_reference_evaluation(run,run/'validation.json',run/'predictions.json')
    summary={'complete':True,'mode':config['mode'],'test_evaluated':False,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'config':config,'counts':{'train':len(train),'validation':len(validation)},'new_crw_counts':{s:len(rows) for s,rows in new.items()},'length_ranges':{s:[min(len(r['sequence']) for r in rows),max(len(r['sequence']) for r in rows)] for s,rows in new.items()},**training,'exposure_events':events,'predictions_sha256':digest((run/'predictions.json').read_bytes()),'aggregates':evaluation['aggregates'],'limitations':['Comparative longer records are not new experimental measurements.','Sequence/external-ID separation does not establish family/clan independence.','Expanded validation is development-only, and is exposed after this run.','Quadratic bounded full pair-label training; tiled/top-k inference with approximate refinement.','Synthetic long inference remains an extrapolation beyond observed labelled lengths; no biological stability claim.']}
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(ROOT/'results/long_comparative_development_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
