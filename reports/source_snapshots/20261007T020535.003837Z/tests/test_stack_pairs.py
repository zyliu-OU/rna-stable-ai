import pytest
import torch
from rnastable.stack_pairs import stack_features,make_stack_model
from rnastable.global_sparse_pairs import make_global_model
from rnastable.structure_model import tokens


def config():return {'embedding_dim':16,'channels':32,'pair_dim':16,'dilations':[1,2,4,8],'pair_features':'adjacent_stackability'}


def test_adjacent_features_respect_sequence_boundary_and_minimum_loop():
    codes=tokens('GGAAAACC')[0];features=stack_features(codes,torch.tensor([0,1]),torch.tensor([7,6]))
    assert features.tolist()==[[0.,1.],[1.,0.]]
    assert stack_features(tokens('GAAAC')[0],torch.tensor([0]),torch.tensor([4])).tolist()==[[0.,0.]]
    assert stack_features(codes,torch.tensor([[0],[1]]),torch.tensor([[6,7]])).shape==(2,2,2)
    with pytest.raises(ValueError,match='outside'):stack_features(codes,torch.tensor([-1]),torch.tensor([7]))


def test_zero_stack_initialization_preserves_base_logits_and_receives_gradients():
    torch.manual_seed(83);model=make_stack_model(config());torch.manual_seed(83);base=make_global_model(config());sequence=tokens('GGAAAACC');edges=torch.tensor([[0,7],[1,6]])
    assert all(torch.equal(v,base.state_dict()[k]) for k,v in model.base.state_dict().items())
    assert torch.equal(model(sequence,edges),base(sequence,edges))
    model(sequence,edges).sum().backward();assert model.stack_weights.weight.grad.tolist()==[[1.,1.]]
    with torch.no_grad():model.stack_weights.weight.copy_(torch.tensor([[.25,.75]]))
    assert torch.allclose(model(sequence,edges)-base(sequence,edges),torch.tensor([.75,.25]))


def test_tiled_scores_include_stack_context_and_match_sparse_forward():
    import numpy as np
    from rnastable.global_sparse_pairs import sparse_candidates
    torch.manual_seed(83);model=make_stack_model(config())
    with torch.no_grad():model.stack_weights.weight.copy_(torch.tensor([[.5,.75]]))
    sequence='GGGAAACCCGGAAAACC';result=sparse_candidates(model,sequence,top_k=16,block_size=3)
    with torch.inference_mode():expected=model(tokens(sequence),torch.from_numpy(result['pairs'].astype(np.int64))).numpy()
    assert np.allclose(result['scores'],expected,atol=1e-6)
    assert result['pair_context_feature_tile_elements']==2*len(sequence)*3


def test_measured_stack_training_replays(monkeypatch):
    import importlib.util
    from rnastable.cli import ROOT
    path=ROOT/'results/stack_comparative_development_summary.json'
    if not path.exists():pytest.skip('No completed stackability development')
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('verify_stack_comparative_development',ROOT/'scripts/verify_stack_comparative_development.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.audit_stack(path)


def test_measured_stack_resource_scoring_replays(monkeypatch):
    import importlib.util
    from rnastable.cli import ROOT
    path=ROOT/'results/stack_scalability_summary.json'
    if not path.exists():pytest.skip('No completed stack resource benchmark')
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('run_stack_scalability',ROOT/'scripts/run_stack_scalability.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.audit_scalability(path)
