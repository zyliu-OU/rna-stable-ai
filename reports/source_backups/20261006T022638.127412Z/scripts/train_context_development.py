#!/usr/bin/env python3
"""Train a wider-context band-scoring model on already exposed development records only."""
import argparse
import copy
import json
import math
from pathlib import Path
import random
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp
from rnastable.banded_pairs import band_scores,decode_band
from rnastable.context_pairs import band_supervision,make_context_model
from rnastable.experimental_data import sequence_similarity
from rnastable.exposures import record_exposure
from rnastable.reference import digest,run_reference_evaluation,validate_inputs
from rnastable.scoring import structure_agreement
from rnastable.structure_model import tokens


def predictions(model, records, method, span):
    return [{'id':r['id'],'sequence':r['sequence'],'method':method,'status':'ok','structure':decode_band(r['sequence'],band_scores(model,r['sequence'],span),span)['structure']} for r in records]


def inputs():
    prior=json.loads((ROOT/'results/pair_development_summary.json').read_text());pair_run=Path(prior['run_dir'])
    family=json.loads((ROOT/'results/family_trial_summary.json').read_text());family_run=Path(family['run_dir'])
    paths=[pair_run/'train.json',pair_run/'validation.json',family_run/'family_plan/summary.json']
    frozen_family=json.loads(paths[2].read_text())
    train=json.loads(paths[0].read_text())['records']+frozen_family['splits']['train']
    validation=json.loads(paths[1].read_text())['records']+frozen_family['splits']['validation']
    # The test split is never passed to training/prediction. Both development sources
    # are already exposed; no independent family-generalization claim is made here.
    for first in train:
        for second in validation:
            if sequence_similarity(first['sequence'],second['sequence'])>=.8:raise ValueError('Cross-source development split overlap')
    return train,validation,{str(p):digest(p.read_bytes()) for p in paths}


def main():
    import torch
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,default=ROOT/'configs/context_development.json');args=parser.parse_args()
    config=json.loads(args.config.read_text())
    expected={'mode':'development_validation_only','seed':20261006,'epochs':10,'learning_rate':.001,'embedding_dim':16,'channels':32,'pair_dim':16,'dilations':[1,2,4,8],'cpu_threads':2,'max_pair_span':config.get('max_pair_span'),'decoder_threshold':0}
    if 'positive_weight_exponent' in config: expected['positive_weight_exponent']=config['positive_weight_exponent']
    if config.get('max_pair_span') not in (64,128) or config.get('positive_weight_exponent',.5) not in (.5,1.) or config!=expected:raise ValueError('Expected fixed reviewed development config')
    train,validation,sources=inputs();run=ROOT/'results/context_development_runs'/timestamp();run.mkdir(parents=True)
    for name,records in [('train.json',train),('validation.json',validation)]:
        data={'schema_version':1,'dataset_id':'reused_context_'+name.removesuffix('.json'),'records':records}
        validate_inputs(data,{'schema_version':1,'methods':['context'],'records':[]})
        (run/name).write_text(json.dumps(data,indent=2)+'\n')
    paths=[Path(__file__),*[ROOT/'src/rnastable'/p for p in ('context_pairs.py','banded_pairs.py','exposures.py','reference.py','scoring.py')]]
    manifest={'run_dir':str(run),'config':config,'sources':sources,'input_sha256':{name:digest((run/name).read_bytes()) for name in ('train.json','validation.json')},'code_sha256':{str(p):digest(p.read_bytes()) for p in paths},'policy':'Reused development only. No test predictions. Prior PDB family identities unresolved; no independent family claim.'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    events=[record_exposure(run,'training_started',train),record_exposure(run,'validation_started',validation)]
    torch.set_num_threads(2);torch.manual_seed(config['seed']);torch.use_deterministic_algorithms(True)
    rng=random.Random(config['seed']);model=make_context_model(config);initial=copy.deepcopy(model)
    torch.save(initial.state_dict(),run/'initial_context_model.pt')
    labels=[band_supervision(r,config['max_pair_span']) for r in train]
    positive=sum(int(y.sum()) for _,y,_ in labels);negative=sum(len(y)-int(y.sum()) for _,y,_ in labels)
    if not positive or not negative:raise ValueError('Need both positive and negative training pairs')
    weight=(negative/positive)**config.get('positive_weight_exponent',.5);loss_fn=torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(weight));optimizer=torch.optim.Adam(model.parameters(),lr=config['learning_rate'])
    history=[];best=None;chosen=None
    for epoch in range(1,11):
        order=list(range(len(train)));rng.shuffle(order);model.train();losses=[]
        for index in order:
            edges,target,_=labels[index]
            if not len(target):continue
            optimizer.zero_grad(set_to_none=True);loss=loss_fn(model(tokens(train[index]['sequence']),edges),target)
            if not torch.isfinite(loss):raise ValueError('Nonfinite training loss')
            loss.backward();optimizer.step();losses.append(loss.item())
        pred=predictions(model,validation,'validation',config['max_pair_span'])
        f1=sum(structure_agreement(p['structure'],r['structure'])['pair_f1'] for p,r in zip(pred,validation))/len(validation)
        model.eval();val_losses=[]
        with torch.inference_mode():
            for record in validation:
                edges,target,_=band_supervision(record,config['max_pair_span'])
                if len(target):val_losses.append(loss_fn(model(tokens(record['sequence']),edges),target).item())
        row={'epoch':epoch,'mean_train_loss':sum(losses)/len(losses),'validation_mean_pair_f1':f1,'mean_validation_loss':sum(val_losses)/len(val_losses)};history.append(row)
        key=(f1,-row['mean_validation_loss'])
        if best is None or key>best:
            best=key;chosen=epoch;torch.save(model.state_dict(),run/'best_context_model.pt')
        with (run/'epochs.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        print(f'Context epoch {epoch}/10: loss {row["mean_train_loss"]:.4f}, reused validation F1 {f1:.4f}',flush=True)
    model.load_state_dict(torch.load(run/'best_context_model.pt',map_location='cpu',weights_only=True))
    pred=predictions(initial,validation,'untrained_context',config['max_pair_span'])+predictions(model,validation,'trained_context',config['max_pair_span'])
    (run/'predictions.json').write_text(json.dumps({'schema_version':1,'methods':['untrained_context','trained_context'],'records':pred},indent=2)+'\n')
    evaluation=run_reference_evaluation(run,run/'validation.json',run/'predictions.json')
    summary={'complete':True,'mode':'development_validation_only','test_evaluated':False,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'config':config,'counts':{'train':len(train),'validation':len(validation)},'history':history,'selected_epoch':chosen,'selected_validation_pair_f1':best[0],'train_positive_pairs':positive,'train_negative_pairs':negative,'train_only_positive_weight':weight,'excluded_train_contacts':sum(x[2] for x in labels),'excluded_validation_contacts':sum(band_supervision(r,config['max_pair_span'])[2] for r in validation),'parameters':sum(p.numel() for p in model.parameters()),'encoder_receptive_field_nt':1+6*sum(config['dilations']),'exposure_events':events,'checkpoint_sha256':{name:digest((run/name).read_bytes()) for name in ('initial_context_model.pt','best_context_model.pt')},'predictions_sha256':digest((run/'predictions.json').read_bytes()),'aggregates':evaluation['aggregates'],'limitations':['All development records are already exposed; no fresh test evaluation or test-driven checkpoint selection.','Combined PDB/comparative development labels; PDB family identities unresolved.',f'Fixed maximum pair span{config["max_pair_span"]} excludes longer contacts; no unrestricted long-RNA accuracy claim.']}
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(ROOT/'results/context_development_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
