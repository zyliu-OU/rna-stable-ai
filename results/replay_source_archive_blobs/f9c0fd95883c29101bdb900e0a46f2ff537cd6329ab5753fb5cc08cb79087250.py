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


from rnastable.context_training import predictions,train_context


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
    paths=[Path(__file__),*[ROOT/'src/rnastable'/p for p in ('context_pairs.py','context_training.py','banded_pairs.py','exposures.py','reference.py','scoring.py')]]
    manifest={'run_dir':str(run),'config':config,'sources':sources,'input_sha256':{name:digest((run/name).read_bytes()) for name in ('train.json','validation.json')},'code_sha256':{str(p):digest(p.read_bytes()) for p in paths},'policy':'Reused development only. No test predictions. Prior PDB family identities unresolved; no independent family claim.'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    events=[record_exposure(run,'training_started',train),record_exposure(run,'validation_started',validation)]
    initial,model,training=train_context(train,validation,config,run)
    pred=predictions(initial,validation,'untrained_context',config['max_pair_span'])+predictions(model,validation,'trained_context',config['max_pair_span'])
    (run/'predictions.json').write_text(json.dumps({'schema_version':1,'methods':['untrained_context','trained_context'],'records':pred},indent=2)+'\n')
    evaluation=run_reference_evaluation(run,run/'validation.json',run/'predictions.json')
    summary={'complete':True,'mode':'development_validation_only','test_evaluated':False,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'config':config,'counts':{'train':len(train),'validation':len(validation)},**training,'exposure_events':events,'predictions_sha256':digest((run/'predictions.json').read_bytes()),'aggregates':evaluation['aggregates'],'limitations':['All development records are already exposed; no fresh test evaluation or test-driven checkpoint selection.','Combined PDB/comparative development labels; PDB family identities unresolved.',f'Fixed maximum pair span{config["max_pair_span"]} excludes longer contacts; no unrestricted long-RNA accuracy claim.']}
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(ROOT/'results/context_development_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
