#!/usr/bin/env python3
"""Training-only pruned structured hinge plus fixed BCE on frozen expanded development."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp
from rnastable.context_training import train_context
from rnastable.exposures import record_exposure
from rnastable.full_pair_supervision import full_supervision
from rnastable.global_sparse_pairs import make_global_model
from rnastable.structured_pair_loss import structured_hinge
from rnastable.reference import digest,run_reference_evaluation
from rnastable.reference_audit import require
from train_sampled_comparative_development import frozen_inputs
from train_exact_comparative_development import predictions


def make_loss(config,weight,record_decision):
    import numpy as np
    import torch
    cfg=config['structured_loss'];require(cfg=={'top_k':16,'margin':1.0,'bce_coefficient':.1,'validation_loss':'full_weighted_bce','normalizer':'supported_gold_count'},'Invalid fixed structured objective')
    bce=torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(weight))
    def loss_fn(logits,edges,target,record):
        hinge,decision=structured_hinge(record['sequence'],edges,target,logits,cfg['top_k'],cfg['margin']);weighted=bce(logits,target);mixed=hinge+cfg['bce_coefficient']*weighted.double()
        record_decision({'id':record['id'],'sequence_sha256':digest(record['sequence'].encode()),'target_sha256':digest(target.numpy().tobytes()),'logits_sha256':digest(logits.detach().numpy().tobytes()),'candidate_indices_sha256':digest(np.asarray(decision['candidate_indices'],dtype=np.int64).tobytes()),'selected_indices_sha256':digest(np.asarray(decision['selected_indices'],dtype=np.int64).tobytes()),'gold_pairs':decision['gold_pairs'],'candidate_count':len(decision['candidate_indices']),'symmetric_pair_difference':decision['symmetric_pair_difference'],'augmented_objective':decision['augmented_objective'],'raw_margin_violation':decision['raw_margin_violation'],'normalizer':decision['normalizer'],'hinge_loss':hinge.item(),'weighted_bce':weighted.item(),'mixed_loss':mixed.item()})
        return mixed
    return loss_fn


def main():
    config=json.loads((ROOT/'configs/structured_comparative_development.json').read_text());source_bytes,source,snapshots,splits=frozen_inputs(ROOT/'results/exact_comparative_development_summary.json')
    require({k:v for k,v in config.items() if k!='structured_loss'}==source['config'],'Other structured comparison settings changed')
    labels=[full_supervision(r,config['training_max_length']) for r in splits['train']];positive=sum(int(y.sum()) for _,y,_ in labels);negative=sum(len(y)-int(y.sum()) for _,y,_ in labels);weight=(negative/positive)**config['positive_weight_exponent']
    run=ROOT/'results/structured_comparative_development_runs'/timestamp();run.mkdir(parents=True,exist_ok=False);(run/'source_summary.json').write_bytes(source_bytes)
    for name,data in snapshots.items():(run/(name+'.json')).write_bytes(data)
    paths=[Path(__file__),ROOT/'scripts/train_exact_comparative_development.py',ROOT/'scripts/train_sampled_comparative_development.py',*[ROOT/'src/rnastable'/n for n in ('structured_pair_loss.py','exact_sparse_pairs.py','full_pair_supervision.py','global_sparse_pairs.py','context_training.py','context_pairs.py','exposures.py','reference.py','scoring.py')]]
    manifest={'run_dir':str(run),'config':config,'source_summary_sha256':digest(source_bytes),'snapshot_sha256':{name:digest((run/name).read_bytes()) for name in ('train.json','validation.json')},'code_sha256':{str(p):digest(p.read_bytes()) for p in paths},'policy':'Same frozen development records, fresh random initialization. Label-informed pruned margin hinge only during training, all supported positives retained. Full unchanged validation BCE and exact inference selection; no test evaluation.'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');events=[record_exposure(run,'training_started',splits['train']),record_exposure(run,'validation_started',splits['validation'])];decisions=[]
    def record_decision(row):
        row={'step':len(decisions)+1,**row};decisions.append(row)
        with (run/'loss_decisions.jsonl').open('a') as file:file.write(json.dumps(row)+'\n')
    loss_fn=make_loss(config,weight,record_decision)
    initial,model,training=train_context(splits['train'],splits['validation'],config,run,model_factory=make_global_model,labeler=lambda r:full_supervision(r,config['training_max_length']),predictor=lambda m,rs,method:predictions(m,rs,method,config),training_loss_fn=loss_fn)
    pred=predictions(initial,splits['validation'],'untrained_structured_sparse',config)+predictions(model,splits['validation'],'trained_structured_sparse',config)
    (run/'predictions.json').write_text(json.dumps({'schema_version':1,'methods':['untrained_structured_sparse','trained_structured_sparse'],'records':pred},indent=2)+'\n');evaluation=run_reference_evaluation(run,run/'validation.json',run/'predictions.json')
    summary={'complete':True,'mode':config['mode'],'test_evaluated':False,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'config':config,'counts':source['counts'],**training,'exposure_events':events,'loss_decisions_sha256':digest((run/'loss_decisions.jsonl').read_bytes()),'training_decisions':len(decisions),'predictions_sha256':digest((run/'predictions.json').read_bytes()),'aggregates':evaluation['aggregates'],'limitations':['Pruned structured objective, not full-graph SVM optimization or a calibrated energy.','One seed, exposed validation and approximate candidate pruning; no independent generalization claim.','Gold and margin augmentation are training-only; prediction uses unaugmented positive top16 candidates.','Exact sparse inference bounded to1024 nt; comparative annotations are not new experimental assays.']}
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(ROOT/'results/structured_comparative_development_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
