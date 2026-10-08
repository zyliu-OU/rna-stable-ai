import json
from pathlib import Path
import pytest
import torch
from rnastable.cli import ROOT
from rnastable.context_training import train_context
from rnastable.full_pair_supervision import full_supervision
from rnastable.global_sparse_pairs import make_global_model


def test_custom_loss_receives_training_only_and_validation_stays_full_bce(tmp_path):
    config=json.loads((ROOT/'configs/exact_comparative_development.json').read_text());config['epochs']=2
    train=[{'id':'train','sequence':'GGAAAACC','structure':'((....))'}];validation=[{'id':'validation','sequence':'GGGAAACCC','structure':'(((...)))'}];seen=[]
    edges,y,_=full_supervision(train[0]);weight=(len(y)-int(y.sum()))/int(y.sum());bce=torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(weight))
    def custom(logits,indices,target,record):
        seen.append(record['id']);return bce(logits,target)
    def predict(model,records,method):return [{'structure':'.'*len(r['sequence'])} for r in records]
    initial,model,result=train_context(train,validation,config,tmp_path,model_factory=make_global_model,labeler=full_supervision,predictor=predict,training_loss_fn=custom)
    assert seen==['train','train']
    from rnastable.structure_model import tokens
    edges,y,_=full_supervision(validation[0])
    with torch.inference_mode():expected=bce(model(tokens(validation[0]['sequence']),edges),y).item()
    chosen=result['history'][result['selected_epoch']-1]
    assert chosen['mean_validation_loss']==expected


def test_invalid_training_loss_callback_rejects_before_output(tmp_path):
    with pytest.raises(ValueError,match='callback'):train_context([],[],{},tmp_path,training_loss_fn=42)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('kind',['missing','reordered','sequence','failed','method','structure'])
def test_invalid_validation_predictions_cannot_select_a_checkpoint(tmp_path,kind):
    config=json.loads((ROOT/'configs/exact_comparative_development.json').read_text());config['epochs']=1
    train=[{'id':'train','sequence':'GGAAAACC','structure':'((....))'}]
    validation=[{'id':'first','sequence':'GGGAAACCC','structure':'(((...)))'},{'id':'second','sequence':'GGAAAACC','structure':'((....))'}]
    def predict(model,records,method):
        rows=[{'id':r['id'],'sequence':r['sequence'],'structure':'.'*len(r['sequence']),'status':'ok','method':method} for r in records]
        if kind=='missing':rows.pop()
        if kind=='reordered':rows.reverse()
        if kind=='sequence':rows[0]['sequence']='A'*len(rows[0]['sequence'])
        if kind=='failed':rows[0]['status']='error'
        if kind=='method':rows[0]['method']='training'
        if kind=='structure':rows[0]['structure']='.'
        return rows
    with pytest.raises(ValueError):train_context(train,validation,config,tmp_path,model_factory=make_global_model,labeler=full_supervision,predictor=predict)
    assert not (tmp_path/'best_context_model.pt').exists() and not (tmp_path/'epochs.jsonl').exists()


def test_callback_mutation_cannot_change_frozen_validation_or_loss_records(tmp_path):
    config=json.loads((ROOT/'configs/exact_comparative_development.json').read_text());config['epochs']=2
    train=[{'id':'train','sequence':'GGAAAACC','structure':'((....))'}];validation=[{'id':'validation','sequence':'GGGAAACCC','structure':'(((...)))'}]
    seen=[];calls=[]
    def labeler(record):calls.append(record['id']);return full_supervision(record)
    def predict(model,records,method):
        seen.append(records[0]['structure']);records[0]['structure']='.'*9
        return [{'structure':'.'*9}]
    def loss(logits,indices,target,record):
        record['structure']='.'*len(record['sequence'])
        return torch.nn.functional.binary_cross_entropy_with_logits(logits,target)
    train_context(train,validation,config,tmp_path,model_factory=make_global_model,labeler=labeler,predictor=predict,training_loss_fn=loss)
    assert seen==['(((...)))','(((...)))'] and calls==['train','validation']
    assert train[0]['structure']=='((....))' and validation[0]['structure']=='(((...)))'


def test_validation_without_legal_pairs_rejects_before_checkpoint_output(tmp_path):
    config=json.loads((ROOT/'configs/exact_comparative_development.json').read_text());config['epochs']=1
    train=[{'id':'train','sequence':'GGAAAACC','structure':'((....))'}];validation=[{'id':'validation','sequence':'AAAAAAAA','structure':'........'}]
    with pytest.raises(ValueError,match='legal supervised'):train_context(train,validation,config,tmp_path,model_factory=make_global_model,labeler=full_supervision,predictor=lambda *args:[])
    assert not list(tmp_path.iterdir())


def test_population_weight_uses_full_training_counts_and_full_validation_bce(tmp_path):
    from rnastable.population_sampling import population_supervision,population_bce
    config=json.loads((ROOT/'configs/exact_comparative_development.json').read_text());config['epochs']=1
    train=[{'id':'train','sequence':'GGGGAAAACCCC','structure':'((((....))))'}];validation=[{'id':'validation','sequence':'GGGAAACCC','structure':'(((...)))'}]
    sample,metadata=population_supervision(train[0],seed=7,negatives_per_positive=1,minimum_negatives=1);weight=metadata['population_negative']/metadata['population_positive']
    labeler=lambda record:sample if record['id']=='train' else full_supervision(record)
    loss=lambda logits,indices,labels,record:population_bce(logits,labels,metadata,weight)
    _,model,result=train_context(train,validation,config,tmp_path,model_factory=make_global_model,labeler=labeler,predictor=lambda m,rs,method:[{'structure':'.'*len(r['sequence'])} for r in rs],training_loss_fn=loss,train_population_counts={'train':metadata})
    assert result['train_only_positive_weight']==weight and result['train_population_negative_pairs']==metadata['population_negative']>result['train_negative_pairs']
    from rnastable.structure_model import tokens
    edges,y,_=full_supervision(validation[0])
    with torch.inference_mode():expected=torch.nn.functional.binary_cross_entropy_with_logits(model(tokens(validation[0]['sequence']),edges),y,pos_weight=torch.tensor(weight)).item()
    assert result['history'][0]['mean_validation_loss']==expected


def test_wrong_population_counts_fail_before_output(tmp_path):
    from rnastable.population_sampling import population_supervision
    config=json.loads((ROOT/'configs/exact_comparative_development.json').read_text());config['epochs']=1
    train=[{'id':'train','sequence':'GGGGAAAACCCC','structure':'((((....))))'}];validation=[{'id':'validation','sequence':'GGGAAACCC','structure':'(((...)))'}]
    sample,metadata=population_supervision(train[0],seed=7,negatives_per_positive=1,minimum_negatives=1);metadata['population_negative']+=1
    with pytest.raises(ValueError,match='population counts'):train_context(train,validation,config,tmp_path,model_factory=make_global_model,labeler=lambda r:sample if r['id']=='train' else full_supervision(r),predictor=lambda *args:[],train_population_counts={'train':metadata})
    assert not list(tmp_path.iterdir())
