#!/usr/bin/env python3
"""Compare training-only negative sampling on the exact retained expanded splits."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp
from rnastable.context_training import train_context
from rnastable.exposures import record_exposure
from rnastable.full_pair_supervision import full_supervision
from rnastable.global_sparse_pairs import make_global_model
from rnastable.negative_sampling import sampled_supervision
from rnastable.reference import digest,run_reference_evaluation
from rnastable.reference_audit import require
from train_long_comparative_development import predictions


def frozen_inputs(path):
    source_bytes=Path(path).read_bytes();source=json.loads(source_bytes);run=Path(source['run_dir'])
    require(source.get('complete') is True and source.get('test_evaluated') is False and source['mode']=='long_comparative_development_only','Expected completed development-only source')
    require(source==json.loads((run/'summary.json').read_text()),'Retained source summary differs')
    require(digest((run/'manifest.json').read_bytes())==source['manifest_sha256'],'Source manifest changed')
    manifest=json.loads((run/'manifest.json').read_text());splits={};snapshots={}
    for name in ('train','validation'):
        data=(run/(name+'.json')).read_bytes();require(digest(data)==manifest['snapshot_sha256'][name+'.json'],'Source split changed')
        snapshots[name]=data;splits[name]=json.loads(data)['records']
    ids=[r['id'] for rows in splits.values() for r in rows];require(len(ids)==len(set(ids)),'Identifiers must be unique across frozen splits')
    require(source['counts']=={s:len(rs) for s,rs in splits.items()},'Source split counts differ')
    return source_bytes,source,snapshots,splits


def training_samples(train,config):
    settings=config['sampling'];require(set(settings)=={'seed','negatives_per_positive','minimum_negatives','validation_loss'} and settings['validation_loss']=='full_pair_labels','Invalid sampling policy')
    return [sampled_supervision(r,**{k:settings[k] for k in ('seed','negatives_per_positive','minimum_negatives')}) for r in train]


def sample_export(samples,train):
    arrays={};inventory=[]
    for index,(record,(edges,labels,excluded)) in enumerate(zip(train,samples)):
        arrays[f'indices_{index}']=edges.numpy();arrays[f'labels_{index}']=labels.numpy()
        inventory.append({'id':record['id'],'positive':int(labels.sum()),'negative':len(labels)-int(labels.sum()),'excluded_contacts':excluded,'indices_sha256':digest(edges.numpy().tobytes()),'labels_sha256':digest(labels.numpy().tobytes())})
    return arrays,inventory


def main():
    import numpy as np
    config=json.loads((ROOT/'configs/sampled_comparative_development.json').read_text())
    source_bytes,source,snapshots,splits=frozen_inputs(ROOT/'results/long_comparative_development_summary.json')
    require({k:v for k,v in config.items() if k!='sampling'}==source['config'],'Sampling comparison changes other training settings')
    samples=training_samples(splits['train'],config);arrays,inventory=sample_export(samples,splits['train'])
    run=ROOT/'results/sampled_comparative_development_runs'/timestamp();run.mkdir(parents=True,exist_ok=False)
    (run/'source_summary.json').write_bytes(source_bytes)
    for name,data in snapshots.items():(run/(name+'.json')).write_bytes(data)
    np.savez_compressed(run/'training_samples.npz',**arrays)
    (run/'sampling_inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    paths=[Path(__file__),ROOT/'scripts/train_long_comparative_development.py',*[ROOT/'src/rnastable'/n for n in ('negative_sampling.py','full_pair_supervision.py','global_sparse_pairs.py','sparse_refinement.py','context_training.py','context_pairs.py','exposures.py','reference.py','scoring.py')]]
    manifest={'run_dir':str(run),'config':config,'source_summary_sha256':digest(source_bytes),'snapshot_sha256':{name:digest((run/name).read_bytes()) for name in ('train.json','validation.json','training_samples.npz','sampling_inventory.json')},'code_sha256':{str(p):digest(p.read_bytes()) for p in paths},'policy':'Same frozen development records; retain every representable positive training pair, deterministically sample negatives. Validation loss uses full labels. No curation or test inference.'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    events=[record_exposure(run,'training_started',splits['train']),record_exposure(run,'validation_started',splits['validation'])]
    cached={r['id']:sample for r,sample in zip(splits['train'],samples)}
    labeler=lambda r:cached[r['id']] if r['id'] in cached else full_supervision(r,config['training_max_length'])
    initial,model,training=train_context(splits['train'],splits['validation'],config,run,model_factory=make_global_model,labeler=labeler,predictor=lambda m,rs,method:predictions(m,rs,method,config))
    pred=predictions(initial,splits['validation'],'untrained_sampled_sparse',config)+predictions(model,splits['validation'],'trained_sampled_sparse',config)
    (run/'predictions.json').write_text(json.dumps({'schema_version':1,'methods':['untrained_sampled_sparse','trained_sampled_sparse'],'records':pred},indent=2)+'\n')
    evaluation=run_reference_evaluation(run,run/'validation.json',run/'predictions.json')
    summary={'complete':True,'mode':config['mode'],'test_evaluated':False,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'config':config,'counts':source['counts'],**training,'exposure_events':events,'predictions_sha256':digest((run/'predictions.json').read_bytes()),'aggregates':evaluation['aggregates'],'limitations':['Same exposed development records, one seed; validation results do not establish generalization.','Sampling reduces scored training negatives, but full label enumeration remains quadratic and bounded to1024 nt.','Full validation loss uses the sampled-training positive weight; it is not comparable with prior differently weighted loss.','Comparative annotations are not new experimental assays; approximate decoder and family independence remain limitations.']}
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(ROOT/'results/sampled_comparative_development_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
