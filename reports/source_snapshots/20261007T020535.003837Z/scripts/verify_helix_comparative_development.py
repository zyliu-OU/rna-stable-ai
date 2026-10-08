#!/usr/bin/env python3
"""Replay sequence-only contiguous local helix features, full labels and exact development checkpoint."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.exposures import exposure_records,read_exposure
from rnastable.full_pair_supervision import full_supervision
from rnastable.helix_pairs import make_helix_model,FEATURE_NAMES
from rnastable.reference import digest
from rnastable.reference_audit import require,audit_reference
from rnastable.scoring import structure_agreement
from rnastable.structure_model import tokens
from train_exact_comparative_development import predictions
from train_sampled_comparative_development import frozen_inputs


def audit_helix(path):
    import numpy as np
    import torch
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir']);config=summary['config']
    require(summary['complete'] is True and summary['test_evaluated'] is False and summary['mode']=='long_comparative_development_only','Not development-only')
    require(summary==json.loads((run/'summary.json').read_text()),'Retained summary differs')
    require(digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'],'Manifest changed')
    manifest=json.loads((run/'manifest.json').read_text());require(manifest['config']==config and manifest['run_dir']==str(run),'Manifest identity differs')
    for name,sha in manifest['snapshot_sha256'].items():require(digest((run/name).read_bytes())==sha,'Snapshot changed: '+name)
    source_bytes,source,snapshots,splits=frozen_inputs(run/'source_summary.json')
    require(digest(source_bytes)==manifest['source_summary_sha256'],'Source summary changed')
    expected={**source['config'],'pair_features':'local_helix_context_v1'};require(config==expected,'Other training settings changed')
    require(summary['counts']==source['counts'],'Frozen split counts differ')
    for name,data in snapshots.items():require((run/(name+'.json')).read_bytes()==data,'Frozen split differs')
    samples=[full_supervision(r,config['training_max_length']) for r in splits['train']]
    positive=sum(int(y.sum()) for _,y,_ in samples);negative=sum(len(y)-int(y.sum()) for _,y,_ in samples)
    require(positive==summary['train_positive_pairs'] and negative==summary['train_negative_pairs'] and (negative/positive)**config['positive_weight_exponent']==summary['train_only_positive_weight'],'Sample counts/weight differ')
    require(sum(x[2] for x in samples)==summary['excluded_train_contacts'] and sum(full_supervision(r,config['training_max_length'])[2] for r in splits['validation'])==summary['excluded_validation_contacts'],'Excluded contacts differ')
    events=summary['exposure_events'];require([e['stage'] for e in events]==['training_started','validation_started'],'Unexpected exposure stage')
    require(set(Path(e['path']).resolve() for e in events)==set(p.resolve() for p in (run/'exposures').glob('*.json')),'Exposure inventory differs')
    for event,name in zip(events,('train','validation')):
        p=Path(event['path']);require(p.resolve().parent==(run/'exposures').resolve() and digest(p.read_bytes())==event['sha256'],'Exposure event changed')
        data=read_exposure(p);require(data['stage']==event['stage'] and data['records']==exposure_records(splits[name],str(run)+' '+event['stage']),'Exposure records differ')
    require(summary['feature_names']==list(FEATURE_NAMES),'Helix feature inventory differs')
    history=summary['history'];require([json.loads(line) for line in (run/'epochs.jsonl').read_text().splitlines()]==history,'Epoch ledger differs')
    require([r['epoch'] for r in history]==list(range(1,config['epochs']+1)),'Epoch inventory differs')
    best=max(history,key=lambda r:(r['validation_mean_pair_f1'],-r['mean_validation_loss']));require(best['epoch']==summary['selected_epoch'],'Checkpoint selection differs')
    torch.set_num_threads(config['cpu_threads']);pred=[]
    for filename,method in [('initial_context_model.pt','untrained_helix_sparse'),('best_context_model.pt','trained_helix_sparse')]:
        p=run/filename;require(digest(p.read_bytes())==summary['checkpoint_sha256'][filename],'Checkpoint changed')
        torch.manual_seed(config['seed']);model=make_helix_model(config);state=torch.load(p,map_location='cpu',weights_only=True)
        if method=='untrained_helix_sparse':
            require(all(torch.equal(v,state[k]) for k,v in model.state_dict().items()),'Random initialization differs')
            source_initial=Path(source['run_dir'])/'initial_context_model.pt';require(digest(source_initial.read_bytes())==source['checkpoint_sha256'][source_initial.name],'Source initialization changed');base_state=torch.load(source_initial,map_location='cpu',weights_only=True)
            require(all(torch.equal(v,base_state[k]) for k,v in model.base.state_dict().items()) and bool((model.helix_weights.weight==0).all()),'Base initialization or zero feature weights differ')
        model.load_state_dict(state);rows=predictions(model,splits['validation'],method,config);pred+=rows
        require(sum(p.numel() for p in model.parameters())==summary['parameters'],'Model size differs')
        if method=='trained_helix_sparse':
            require(model.helix_weights.weight.detach().tolist()[0]==summary['helix_weights'],'Learned feature weights differ')
            score=sum(structure_agreement(p['structure'],r['structure'])['pair_f1'] for p,r in zip(rows,splits['validation']))/len(rows);require(score==summary['selected_validation_pair_f1']==best['validation_mean_pair_f1'],'Selected validation score differs')
            losses=[];loss_fn=torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(summary['train_only_positive_weight']))
            with torch.inference_mode():
                for r in splits['validation']:
                    edges,y,_=full_supervision(r,config['training_max_length'])
                    if len(y):losses.append(loss_fn(model(tokens(r['sequence']),edges),y).item())
            require(sum(losses)/len(losses)==best['mean_validation_loss'],'Full validation loss differs')
    require(digest((run/'predictions.json').read_bytes())==summary['predictions_sha256'] and json.loads((run/'predictions.json').read_text())['records']==pred,'Checkpoint predictions differ')
    p=run/'results/reference_evaluation_summary.json';audit_reference(p);evaluation=json.loads(p.read_text())
    for key,name in [('references','validation.json'),('predictions','predictions.json')]:require(Path(evaluation['sources'][key]['path']).read_bytes()==(run/name).read_bytes(),'Evaluation split differs')
    require(evaluation['aggregates']==summary['aggregates'],'Metrics differ')
    print(f'Local-helix training audit passed: {summary["counts"]}; {positive} positives/{negative} full negatives; selected epoch {summary["selected_epoch"]}; full validation labels, no test inference.')
    return summary

if __name__=='__main__':audit_helix(ROOT/'results/helix_comparative_development_summary.json')
