import json
from pathlib import Path
import numpy as np
import pytest
from rnastable.native_journal import atomic_json
from rnastable.population_development import SAMPLING_POLICY,fit_component,audit_component,samples_for
from rnastable.reference import digest
from rnastable.exact_sparse_pairs import decode_exact_sparse
from rnastable.global_sparse_pairs import sparse_candidates


def config():
    return {'mode':'long_comparative_development_only','seed':20261006,'epochs':1,'learning_rate':.001,'embedding_dim':4,'channels':4,'pair_dim':4,'dilations':[1,2,4,8],'cpu_threads':2,'training_max_length':1024,'top_k':4,'block_size':3,'positive_weight_exponent':1.,'inference_decoder':'exact_sparse','pair_features':'local_helix_context_v1','population_sampling':{'seed':7,'negatives_per_positive':1,'minimum_negatives':1,'max_length':1024,'policy':SAMPLING_POLICY}}


def predictor(model,records,method,config):
    rows=[]
    for record in records:
        candidates=sparse_candidates(model,record['sequence'],config['top_k'],config['block_size']);structure=decode_exact_sparse(record['sequence'],candidates['pairs'],candidates['scores'])['structure'];rows.append({**record,'method':method,'status':'ok','structure':structure})
    return rows


def fixture():
    cfg=config();base={k:v for k,v in cfg.items() if k not in ('population_sampling','pair_features')};splits={name:[{'id':name,'sequence':'GGGGAAAACCCC','structure':'((((....))))','source':'Synthetic unit fixture','reference_kind':'computational'}] for name in ('train','validation')};source={'config':base,'counts':{name:1 for name in splits}};data=json.dumps(source).encode();snapshots={name:json.dumps({'schema_version':1,'dataset_id':name,'records':records}).encode() for name,records in splits.items()};return cfg,data,source,snapshots,splits


def test_population_component_replays_full_validation_and_sample_inventory(tmp_path):
    cfg,data,source,snapshots,splits=fixture();run=tmp_path/'fit';summary=fit_component(run,data,source,snapshots,splits,cfg,predictor,[])
    frozen=lambda path:(data,source,snapshots,splits)
    assert audit_component(run/'summary.json',frozen,predictor)==summary
    assert summary['train_negative_pairs']<summary['train_population_negative_pairs']
    assert summary['test_evaluated'] is False
    from rnastable.context_inference import load_checkpoint,method_name
    _,loaded_config,_,_=load_checkpoint(run/'summary.json')
    assert method_name(loaded_config)=='trained_population_helix_sparse'
    with np.load(run/'training_samples.npz') as stored:arrays={key:stored[key] for key in stored.files}
    arrays['indices_0']=arrays['indices_0'].copy();arrays['indices_0'][0,0]+=1;np.savez_compressed(run/'training_samples.npz',**arrays)
    manifest=json.loads((run/'manifest.json').read_text());manifest['snapshot_sha256']['training_samples.npz']=digest((run/'training_samples.npz').read_bytes());atomic_json(run/'manifest.json',manifest);summary['manifest_sha256']=digest((run/'manifest.json').read_bytes());atomic_json(run/'summary.json',summary)
    with pytest.raises(ValueError,match='Sample tensors'):audit_component(run/'summary.json',frozen,predictor)


def test_population_sampling_policy_must_be_explicit():
    with pytest.raises(ValueError,match='policy'):samples_for([],{'policy':'unweighted'})
