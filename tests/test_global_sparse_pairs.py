import numpy as np
import pytest
from rnastable.global_sparse_pairs import make_global_model,sparse_candidates,decode_sparse,global_supervision
from rnastable.pair_model import CANONICAL,decode_pairs
from rnastable.structure_model import tokens
from rnastable.scoring import base_pairs
CONFIG={'embedding_dim':8,'channels':8,'pair_dim':8,'dilations':[1,2,4,8]}


def test_tiled_topk_matches_dense_pair_scoring():
    import torch
    torch.set_num_threads(2);torch.manual_seed(19);model=make_global_model(CONFIG)
    with torch.no_grad():model.endpoint.bias.fill_(2)
    seq='ACGU'*10;indices=np.array([(i,j) for j in range(len(seq)) for i in range(j-3) if seq[i]+seq[j] in CANONICAL])
    with torch.inference_mode():scores=model(tokens(seq),torch.tensor(indices)).numpy()
    expected=[]
    for j in range(len(seq)):
        choices=sorted([(int(i),float(s)) for (i,right),s in zip(indices,scores) if right==j and s>0],key=lambda row:(-row[1],row[0]))[:3]
        expected.extend((i,j,s) for i,s in choices)
    result=sparse_candidates(model,seq,3,7)
    actual=sorted([(int(i),int(j),float(s)) for (i,j),s in zip(result['pairs'],result['scores'])],key=lambda row:(row[1],-row[2],row[0]))
    assert [(i,j) for i,j,_ in actual]==[(i,j) for i,j,_ in expected]
    assert np.allclose([s for _,_,s in actual],[s for _,_,s in expected],atol=1e-6,rtol=1e-6)
    assert result['peak_score_tile_elements']<=len(seq)*7 and result['candidate_count']<=len(seq)*3


def test_tied_candidates_prefer_smallest_partner_and_support_distant_pairs():
    import torch
    model=make_global_model(CONFIG)
    with torch.no_grad():
        for parameter in model.parameters():parameter.zero_()
        model.endpoint.bias.fill_(1)
    seq='G'*5+'A'*300+'C'*5
    result=sparse_candidates(model,seq,2,16)
    for j in range(305,310):assert result['pairs'][result['pairs'][:,1]==j][:,0].tolist()==[0,1]
    decoded=decode_sparse(seq,result['pairs'],result['scores'])
    assert any(j-i>255 for i,j in base_pairs(decoded['structure']))
    assert result['candidate_array_bytes']==result['candidate_count']*16


def test_greedy_decoder_is_valid_but_not_claimed_optimal():
    seq='GGAAAACC';pairs=np.array([[0,6],[1,7],[0,7],[1,6]]);scores=np.array([5.,5.,4.,4.])
    result=decode_sparse(seq,pairs,scores)
    assert base_pairs(result['structure'])=={(0,6)} and result['objective']==5
    dense=np.zeros((8,8))
    for (i,j),score in zip(pairs,scores):dense[i,j]=dense[j,i]=score
    assert decode_pairs(seq,dense)=='((....))'
    nested=decode_sparse(seq,np.array([[0,7],[1,6]]),np.array([2.,1.]))
    assert nested['structure']=='((....))'


def test_global_distance_head_backpropagates_and_training_is_bounded():
    import torch
    model=make_global_model(CONFIG);seq='G'+'A'*298+'C';score=model(tokens(seq),torch.tensor([[0,299]]))
    assert torch.isfinite(score).all();score.sum().backward()
    assert model.distance_network[0].weight.grad.abs().sum()>0
    with pytest.raises(ValueError,match='bounded'):global_supervision({'sequence':seq,'structure':'('+'.'*298+')'})


@pytest.mark.parametrize('pairs,scores',[(np.array([[0,3]]),[1]),(np.array([[0,5]]),[np.nan]),(np.array([[0.,5.]]),[1]),(np.array([[0,6]]),[1])])
def test_invalid_sparse_candidates_rejected(pairs,scores):
    with pytest.raises(ValueError):decode_sparse('GAAAAC',pairs,scores)


def test_measured_global_development_replays(monkeypatch):
    import importlib.util
    from rnastable.cli import ROOT
    path=ROOT/'results/global_sparse_development_summary.json'
    if not path.exists():pytest.skip('No measured global development')
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('verify_global_sparse_development',ROOT/'scripts/verify_global_sparse_development.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.audit_global(path)
