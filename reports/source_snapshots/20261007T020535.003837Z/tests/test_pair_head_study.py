import importlib.util
import json
from pathlib import Path
import pytest
import torch
from rnastable.global_sparse_pairs import make_global_model
from rnastable.helix_pairs import make_helix_model
from rnastable.stack_pairs import make_stack_model
from rnastable.native_journal import atomic_json
from rnastable.pair_head_study import head_config,paired_initialization,train_component,audit_component
from rnastable.reference import digest
from rnastable.reference_audit import require


def base():return {'mode':'long_comparative_development_only','seed':20261006,'epochs':1,'learning_rate':.001,'embedding_dim':4,'channels':4,'pair_dim':4,'dilations':[1,2,4,8],'cpu_threads':2,'training_max_length':1024,'top_k':4,'block_size':3,'positive_weight_exponent':1.,'inference_decoder':'exact_sparse'}


def parent(tmp_path):
    plan=tmp_path/'study';plan.mkdir()
    for name,record in [('train',{'id':'train','sequence':'GGAAAACC','structure':'((....))'}),('validation',{'id':'validation','sequence':'GGGAAACCC','structure':'(((...)))'})]:
        atomic_json(plan/(name+'.json'),{'schema_version':1,'dataset_id':name,'records':[{**record,'reference_kind':'computational','source':'Synthetic unit fixture'}]})
    manifest={'base_config':base(),'code_sha256':{},'snapshot_sha256':{name:digest((plan/name).read_bytes()) for name in ('train.json','validation.json')}}
    atomic_json(plan/'manifest.json',manifest)
    return plan


def test_head_variants_only_change_seed_and_declared_feature_head():
    cfg=base()
    for head,features in [('baseline',None),('stack','adjacent_stackability'),('helix','local_helix_context_v1')]:
        result=head_config(cfg,head,7);assert result['seed']==7 and result.get('pair_features')==features
        assert {k:v for k,v in result.items() if k not in ('seed','pair_features')}=={k:v for k,v in cfg.items() if k!='seed'}
    with pytest.raises(ValueError):head_config(cfg,'unknown',7)
    with pytest.raises(ValueError):head_config(cfg,'baseline',True)


def test_matched_initialization_rejects_changed_base_or_nonzero_feature_head(tmp_path):
    components=[]
    for head,factory in [('baseline',make_global_model),('stack',make_stack_model),('helix',make_helix_model)]:
        path=tmp_path/head;path.mkdir();torch.manual_seed(7);model=factory(head_config(base(),head,7));torch.save(model.state_dict(),path/'initial_context_model.pt');components.append({'seed':7,'head':head,'run_dir':str(path)})
    assert paired_initialization(components)
    path=tmp_path/'helix'/'initial_context_model.pt';state=torch.load(path,weights_only=True);state['helix_weights.weight'][0,0]=1;torch.save(state,path)
    with pytest.raises(ValueError,match='not zero'):paired_initialization(components)
    state['helix_weights.weight'].zero_();state['base.endpoint.bias']+=1;torch.save(state,path)
    with pytest.raises(ValueError,match='base initialization'):paired_initialization(components)


def test_tiny_component_training_and_audit_preserve_full_validation_contract(tmp_path):
    plan=parent(tmp_path);run=plan/'components'/'7_helix';run.mkdir(parents=True)
    atomic_json(run/'manifest.json',{'study_manifest_sha256':digest((plan/'manifest.json').read_bytes()),'head':'helix','seed':7,'config':head_config(base(),'helix',7)})
    result=train_component(run);assert result['test_evaluated'] is False and result['counts']=={'train':1,'validation':1}
    assert audit_component(run/'summary.json')==result
    payload=json.loads((run/'summary.json').read_text());payload['selected_epoch']+=1;atomic_json(run/'summary.json',payload)
    with pytest.raises(ValueError,match='selection'):audit_component(run/'summary.json')
