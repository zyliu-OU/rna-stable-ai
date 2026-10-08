#!/usr/bin/env python3
"""Audit sparse-context development training and validation-only checkpoint replay."""
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.context_pairs import band_supervision,make_context_model
from rnastable.exposures import exposure_records,read_exposure
from rnastable.experimental_data import sequence_similarity
from rnastable.reference import digest
from rnastable.reference_audit import audit_reference,require
from rnastable.scoring import structure_agreement
from rnastable.structure_model import tokens
from train_context_development import predictions


def audit_context(path):
    import torch
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir']);config=summary['config']
    require(summary['complete'] is True and summary['test_evaluated'] is False and summary['mode']=='development_validation_only','not development-only')
    require(json.loads((run/'summary.json').read_text())==summary,'retained summary differs')
    require(digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'],'manifest changed')
    manifest=json.loads((run/'manifest.json').read_text());require(manifest['run_dir']==str(run) and manifest['config']==config,'manifest identity differs')
    splits=[]
    for name in ('train.json','validation.json'):
        require(digest((run/name).read_bytes())==manifest['input_sha256'][name],'snapshot changed')
        splits.append(json.loads((run/name).read_text())['records'])
    train,validation=splits
    sources=list(manifest['sources'])
    require(len(sources)==3,'source inventory differs')
    for p,sha in manifest['sources'].items():require(digest(Path(p).read_bytes())==sha,'source changed')
    source_family=json.loads(Path(sources[2]).read_text())
    require(train==json.loads(Path(sources[0]).read_text())['records']+source_family['splits']['train'] and validation==json.loads(Path(sources[1]).read_text())['records']+source_family['splits']['validation'],'development source selection differs')
    require(summary['counts']=={'train':len(train),'validation':len(validation)},'counts differ')
    for first in train:
        for second in validation:require(sequence_similarity(first['sequence'],second['sequence'])<.8,'cross-split overlap')
    events=summary['exposure_events'];require([e['stage'] for e in events]==['training_started','validation_started'],'unexpected exposure stage')
    require(set(Path(e['path']).resolve() for e in events)==set(p.resolve() for p in (run/'exposures').glob('*.json')),'exposure inventory differs')
    for event,records in zip(events,splits):
        p=Path(event['path']);require(p.resolve().parent==(run/'exposures').resolve() and digest(p.read_bytes())==event['sha256'],'exposure changed')
        data=read_exposure(p);require(data['stage']==event['stage'] and data['records']==exposure_records(records,str(run)+' '+event['stage']),'exposure input differs')
    labels=[band_supervision(r,config['max_pair_span']) for r in train]
    pos=sum(int(y.sum()) for _,y,_ in labels);neg=sum(len(y)-int(y.sum()) for _,y,_ in labels)
    require(pos==summary['train_positive_pairs'] and neg==summary['train_negative_pairs'] and (neg/pos)**config.get('positive_weight_exponent',.5)==summary['train_only_positive_weight'],'supervision weight/counts differ')
    require(sum(x[2] for x in labels)==summary['excluded_train_contacts'] and sum(band_supervision(r,config['max_pair_span'])[2] for r in validation)==summary['excluded_validation_contacts'],'excluded contacts differ')
    history=summary['history'];require([json.loads(line) for line in (run/'epochs.jsonl').read_text().splitlines()]==history,'epoch ledger differs')
    require([r['epoch'] for r in history]==list(range(1,config['epochs']+1)),'epoch count differs')
    best=max(history,key=lambda r:(r['validation_mean_pair_f1'],-r['mean_validation_loss']));require(best['epoch']==summary['selected_epoch'],'selection differs')
    torch.set_num_threads(config['cpu_threads']);pred=[]
    for name,method in [('initial_context_model.pt','untrained_context'),('best_context_model.pt','trained_context')]:
        p=run/name;require(digest(p.read_bytes())==summary['checkpoint_sha256'][name],'checkpoint changed')
        model=make_context_model(config);model.load_state_dict(torch.load(p,map_location='cpu',weights_only=True))
        rows=predictions(model,validation,method,config['max_pair_span']);pred+=rows
        require(sum(p.numel() for p in model.parameters())==summary['parameters'] and 1+6*sum(config['dilations'])==summary['encoder_receptive_field_nt'],'architecture size differs')
        if method=='trained_context':
            score=sum(structure_agreement(p['structure'],r['structure'])['pair_f1'] for p,r in zip(rows,validation))/len(validation)
            require(score==summary['selected_validation_pair_f1']==best['validation_mean_pair_f1'],'selected score differs')
            loss_fn=torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(summary['train_only_positive_weight']));losses=[]
            with torch.inference_mode():
                for r in validation:
                    edges,y,_=band_supervision(r,config['max_pair_span'])
                    if len(y):losses.append(loss_fn(model(tokens(r['sequence']),edges),y).item())
            require(sum(losses)/len(losses)==best['mean_validation_loss'],'selected validation loss differs')
    require(digest((run/'predictions.json').read_bytes())==summary['predictions_sha256'] and json.loads((run/'predictions.json').read_text())['records']==pred,'checkpoint predictions differ')
    p=run/'results/reference_evaluation_summary.json';audit_reference(p);evaluation=json.loads(p.read_text())
    for key,name in [('references','validation.json'),('predictions','predictions.json')]:require(Path(evaluation['sources'][key]['path']).read_bytes()==(run/name).read_bytes(),'evaluation split differs')
    require(evaluation['aggregates']==summary['aggregates'],'aggregates differ')
    print(f'Context development audit passed: {len(train)} train / {len(validation)} validation; selected epoch {summary["selected_epoch"]}; no test evaluation.')
    return summary

if __name__=='__main__':audit_context(ROOT/'results/context_development_summary.json')
