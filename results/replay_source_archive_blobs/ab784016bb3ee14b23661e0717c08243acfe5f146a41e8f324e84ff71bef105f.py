#!/usr/bin/env python3
"""Replay global sparse development checkpoints, labels, exposure events and metrics."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.exposures import exposure_records,read_exposure
from rnastable.global_sparse_pairs import make_global_model,global_supervision
from rnastable.reference import digest
from rnastable.reference_audit import require,audit_reference
from rnastable.experimental_data import sequence_similarity
from rnastable.scoring import structure_agreement
from rnastable.structure_model import tokens
from train_global_sparse_development import predictions


def audit_global(path):
    import torch
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir']);config=summary['config']
    require(summary['complete'] is True and summary['test_evaluated'] is False and summary['mode']=='global_sparse_development_only','not development-only')
    require(json.loads((run/'summary.json').read_text())==summary,'retained summary differs')
    require(digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'],'manifest changed')
    manifest=json.loads((run/'manifest.json').read_text());require(manifest['config']==config and manifest['run_dir']==str(run),'manifest identity differs')
    splits=[]
    for name in ('train.json','validation.json'):
        require(digest((run/name).read_bytes())==manifest['input_sha256'][name],'snapshot changed');splits.append(json.loads((run/name).read_text())['records'])
    train,validation=splits;require(summary['counts']=={'train':len(train),'validation':len(validation)},'counts differ')
    sources=list(manifest['sources']);require(len(sources)==3,'source inventory differs')
    for p,sha in manifest['sources'].items():require(digest(Path(p).read_bytes())==sha,'source changed')
    original=json.loads(Path(sources[2]).read_text())
    require(train==json.loads(Path(sources[0]).read_text())['records']+original['splits']['train'] and validation==json.loads(Path(sources[1]).read_text())['records']+original['splits']['validation'],'development source selection differs')
    for first in train:
        for second in validation:require(sequence_similarity(first['sequence'],second['sequence'])<.8,'cross-split overlap')
    events=summary['exposure_events'];require([e['stage'] for e in events]==['training_started','validation_started'],'unexpected exposure stage')
    require(set(Path(e['path']).resolve() for e in events)==set(p.resolve() for p in (run/'exposures').glob('*.json')),'exposure inventory differs')
    for event,records in zip(events,splits):
        p=Path(event['path']);require(p.resolve().parent==(run/'exposures').resolve() and digest(p.read_bytes())==event['sha256'],'exposure event changed')
        data=read_exposure(p);require(data['stage']==event['stage'] and data['records']==exposure_records(records,str(run)+' '+event['stage']),'exposure records differ')
    labels=[global_supervision(r) for r in train];positive=sum(int(y.sum()) for _,y,_ in labels);negative=sum(len(y)-int(y.sum()) for _,y,_ in labels)
    require(positive==summary['train_positive_pairs'] and negative==summary['train_negative_pairs'] and (negative/positive)**config['positive_weight_exponent']==summary['train_only_positive_weight'],'supervision counts/weight differ')
    require(sum(x[2] for x in labels)==summary['excluded_train_contacts'] and sum(global_supervision(r)[2] for r in validation)==summary['excluded_validation_contacts'],'excluded contacts differ')
    history=summary['history'];require([json.loads(line) for line in (run/'epochs.jsonl').read_text().splitlines()]==history,'epoch ledger differs')
    require([r['epoch'] for r in history]==list(range(1,config['epochs']+1)),'epoch inventory differs')
    best=max(history,key=lambda r:(r['validation_mean_pair_f1'],-r['mean_validation_loss']));require(best['epoch']==summary['selected_epoch'],'selection differs')
    torch.set_num_threads(config['cpu_threads']);pred=[]
    for name,method in [('initial_context_model.pt','untrained_global_sparse'),('best_context_model.pt','trained_global_sparse')]:
        p=run/name;require(digest(p.read_bytes())==summary['checkpoint_sha256'][name],'checkpoint changed')
        torch.manual_seed(config['seed']);model=make_global_model(config);state=torch.load(p,map_location='cpu',weights_only=True)
        if method=='untrained_global_sparse':require(all(torch.equal(v,state[k]) for k,v in model.state_dict().items()),'initialization differs from fixed random seed')
        model.load_state_dict(state);rows=predictions(model,validation,method,config);pred+=rows
        require(sum(p.numel() for p in model.parameters())==summary['parameters'],'model size differs')
        if method=='trained_global_sparse':
            f1=sum(structure_agreement(p['structure'],r['structure'])['pair_f1'] for p,r in zip(rows,validation))/len(validation)
            require(f1==summary['selected_validation_pair_f1']==best['validation_mean_pair_f1'],'selected validation score differs')
            loss_fn=torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(summary['train_only_positive_weight']));losses=[]
            with torch.inference_mode():
                for r in validation:
                    edges,y,_=global_supervision(r)
                    if len(y):losses.append(loss_fn(model(tokens(r['sequence']),edges),y).item())
            require(sum(losses)/len(losses)==best['mean_validation_loss'],'selected validation loss differs')
    require(digest((run/'predictions.json').read_bytes())==summary['predictions_sha256'] and json.loads((run/'predictions.json').read_text())['records']==pred,'checkpoint predictions differ')
    p=run/'results/reference_evaluation_summary.json';audit_reference(p);evaluation=json.loads(p.read_text())
    for key,name in [('references','validation.json'),('predictions','predictions.json')]:require(Path(evaluation['sources'][key]['path']).read_bytes()==(run/name).read_bytes(),'evaluation split differs')
    require(evaluation['aggregates']==summary['aggregates'],'metrics differ')
    print(f'Global sparse audit passed: {len(train)} train / {len(validation)} reused validation; selected epoch {summary["selected_epoch"]}; no test predictions.')
    return summary

if __name__=='__main__':audit_global(ROOT/'results/global_sparse_development_summary.json')
