import numpy as np
import pytest
import torch
from rnastable.global_sparse_pairs import make_global_model,sparse_candidates
from rnastable.helix_pairs import FEATURE_NAMES,helix_features,make_helix_model
from rnastable.structure_model import tokens
from rnastable.stack_pairs import stack_features


def config():return {'embedding_dim':4,'channels':4,'pair_dim':4,'dilations':[1,2,4,8],'pair_features':'local_helix_context_v1'}


def test_contiguous_helix_features_boundaries_pair_types_and_minimum_loop():
    codes=tokens('GGGGAAAACCCC')[0]
    values=helix_features(codes,torch.tensor([0,1,2,3]),torch.tensor([11,10,9,8]))
    assert FEATURE_NAMES==('outer_1','inner_1','outer_2','inner_2','outer_3','inner_3','gc_pair','gu_pair')
    assert values.tolist()==[[0,1,0,1,0,1,1,0],[1,1,0,1,0,0,1,0],[1,1,1,0,0,0,1,0],[1,0,1,0,1,0,1,0]]
    codes=tokens('GGAGAAAACCCC')[0]
    # A broken second inward compatibility stops the third contiguous indicator.
    assert helix_features(codes,torch.tensor([0]),torch.tensor([11]))[0,1:6:2].tolist()==[1,0,0]
    codes=tokens('GAAAAU')[0]
    assert helix_features(codes,torch.tensor([0]),torch.tensor([5]))[0,-2:].tolist()==[0,1]


def test_broadcast_features_match_scalar_oracle_and_existing_adjacent_features():
    codes=tokens('GGGGAAAACCCC')[0];left=torch.arange(len(codes))[:,None];right=torch.arange(len(codes))[None,:]
    values=helix_features(codes,left,right)
    assert torch.equal(values[:,:,:2],stack_features(codes,left,right))
    for i in range(len(codes)):
        for j in range(len(codes)):
            assert torch.equal(values[i,j],helix_features(codes,torch.tensor(i),torch.tensor(j)))
    assert helix_features(codes,torch.empty(0,dtype=torch.long),torch.empty(0,dtype=torch.long)).shape==(0,8)


def test_zero_initial_features_preserve_base_logits_and_gradients_reach_head():
    cfg=config();torch.manual_seed(42);model=make_helix_model(cfg);torch.manual_seed(42);base=make_global_model(cfg)
    codes=tokens('GGGGAAAACCCC');indices=torch.tensor([[0,11],[1,10],[2,9],[3,8]])
    assert all(torch.equal(value,base.state_dict()[key]) for key,value in model.base.state_dict().items())
    assert torch.equal(model(codes,indices),base(codes,indices))
    model(codes,indices).sum().backward()
    assert bool(torch.isfinite(model.helix_weights.weight.grad).all()) and bool((model.helix_weights.weight.grad!=0).any())


def test_tiled_and_direct_helix_logits_agree_with_feature_accounting():
    torch.manual_seed(42);model=make_helix_model(config())
    with torch.no_grad():model.helix_weights.weight.fill_(2);model.base.endpoint.bias.fill_(2)
    sequence='GGGGAAAACCCC';result=sparse_candidates(model,sequence,top_k=12,block_size=3)
    direct=model(tokens(sequence),torch.tensor(result['pairs'].astype(np.int64))).detach().numpy()
    assert np.allclose(result['scores'],direct,atol=1e-6)
    assert result['pair_context_feature_tile_elements']==8*result['peak_score_tile_elements']


@pytest.mark.parametrize('left,right',[(torch.tensor([-1]),torch.tensor([3])),(torch.tensor([0]),torch.tensor([12])),(torch.tensor([0.]),torch.tensor([5]))])
def test_bad_indices_fail_before_scoring(left,right):
    with pytest.raises(ValueError):helix_features(tokens('GGGGAAAACCCC')[0],left,right)


def test_measured_helix_training_replays_without_retraining(monkeypatch):
    import importlib.util
    from rnastable.cli import ROOT
    path=ROOT/'results/helix_comparative_development_summary.json'
    if not path.exists():pytest.skip('No completed local-helix development')
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('verify_helix',ROOT/'scripts/verify_helix_comparative_development.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.audit_helix(path)
