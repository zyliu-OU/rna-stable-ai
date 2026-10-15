#!/usr/bin/env python3
"""Train global-distance sparse scoring on frozen reused development only."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp
from rnastable.context_training import train_context
from rnastable.exposures import record_exposure
from rnastable.global_sparse_pairs import make_global_model,global_supervision,sparse_candidates,decode_sparse
from rnastable.reference import digest,run_reference_evaluation
from train_context_development import inputs


def predictions(model,records,method,config):
    rows=[]
    for r in records:
        candidates=sparse_candidates(model,r['sequence'],config['top_k'],config['block_size'])
        decoded=decode_sparse(r['sequence'],candidates['pairs'],candidates['scores'])
        rows.append({'id':r['id'],'sequence':r['sequence'],'method':method,'status':'ok','structure':decoded['structure']})
    return rows


def main():
    config=json.loads((ROOT/'configs/global_sparse_development.json').read_text())
    expected={'mode':'global_sparse_development_only','seed':20261006,'epochs':10,'learning_rate':.001,'embedding_dim':16,'channels':32,'pair_dim':16,'dilations':[1,2,4,8],'cpu_threads':2,'training_max_length':256,'top_k':16,'block_size':64,'positive_weight_exponent':1.}
    if config!=expected:raise ValueError('Expected fixed prototype configuration')
    train,validation,sources=inputs()
    if any(len(r['sequence'])>256 for r in train+validation):raise ValueError('Full supervised pair enumeration is bounded to256 nt')
    run=ROOT/'results/global_sparse_development_runs'/timestamp();run.mkdir(parents=True)
    for name,records in [('train.json',train),('validation.json',validation)]:(run/name).write_text(json.dumps({'schema_version':1,'dataset_id':'global_sparse_'+name.removesuffix('.json'),'records':records},indent=2)+'\n')
    paths=[Path(__file__),ROOT/'scripts/train_context_development.py',*[ROOT/'src/rnastable'/n for n in ('global_sparse_pairs.py','context_training.py','context_pairs.py','exposures.py','reference.py','scoring.py')]]
    manifest={'run_dir':str(run),'config':config,'sources':sources,'input_sha256':{name:digest((run/name).read_bytes()) for name in ('train.json','validation.json')},'code_sha256':{str(p):digest(p.read_bytes()) for p in paths},'policy':'Already exposed development only. Unrestricted distance head, exact tiled top-k retention, approximate greedy noncrossing decoding. No test predictions.'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    events=[record_exposure(run,'training_started',train),record_exposure(run,'validation_started',validation)]
    initial,model,training=train_context(train,validation,config,run,model_factory=make_global_model,labeler=global_supervision,predictor=lambda m,rs,method:predictions(m,rs,method,config))
    pred=predictions(initial,validation,'untrained_global_sparse',config)+predictions(model,validation,'trained_global_sparse',config)
    (run/'predictions.json').write_text(json.dumps({'schema_version':1,'methods':['untrained_global_sparse','trained_global_sparse'],'records':pred},indent=2)+'\n')
    evaluation=run_reference_evaluation(run,run/'validation.json',run/'predictions.json')
    summary={'complete':True,'mode':config['mode'],'test_evaluated':False,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'config':config,'counts':{'train':len(train),'validation':len(validation)},**training,'exposure_events':events,'predictions_sha256':digest((run/'predictions.json').read_bytes()),'aggregates':evaluation['aggregates'],'limitations':['One seed, fixed configuration, already reused development data: no independent accuracy claim.','All-distance scoring has quadratic work; fixed tile/top-k retention bounds inference storage.','Greedy decoder is approximate and can miss the optimum.','Short labels supervise distances only within observed development lengths; extrapolation to distant contacts is unvalidated.']}
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(ROOT/'results/global_sparse_development_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
