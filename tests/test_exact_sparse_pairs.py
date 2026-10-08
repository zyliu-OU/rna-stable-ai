import numpy as np
import pytest
from rnastable.exact_sparse_pairs import decode_exact_sparse
from rnastable.pair_model import decode_pairs,CANONICAL
from rnastable.global_sparse_pairs import decode_sparse
from rnastable.scoring import base_pairs


def test_exact_sparse_matches_dense_on_random_legal_subset():
    rng=np.random.default_rng(81)
    for n in (8,17,45):
        for _ in range(5):
            seq=''.join(rng.choice(list('ACGU'),n));pairs=np.array([(i,j) for i in range(n) for j in range(i+4,n) if seq[i]+seq[j] in CANONICAL and rng.random()<.5],dtype=np.int32).reshape(-1,2)
            scores=rng.integers(-2,6,len(pairs)).astype(float);dense=np.zeros((n,n))
            for (i,j),v in zip(pairs,scores):dense[i,j]=dense[j,i]=v
            a=decode_exact_sparse(seq,pairs,scores);b=decode_pairs(seq,dense)
            assert a['structure']==b and a['objective']==sum(dense[i,j] for i,j in base_pairs(b))


def test_exact_recovers_greedy_counterexample_and_distant_nested_pairs():
    seq='GGAAAACC';pairs=np.array([[0,6],[0,7],[1,6]],dtype=np.int32);scores=np.array([5.,4.,4.])
    assert decode_sparse(seq,pairs,scores)['objective']==5
    assert decode_exact_sparse(seq,pairs,scores)['objective']==8
    seq='GG'+'A'*296+'CC';pairs=np.array([[0,298],[0,299],[1,298]],dtype=np.int32)
    result=decode_exact_sparse(seq,pairs,scores)
    assert result['objective']==8 and base_pairs(result['structure'])=={(0,299),(1,298)}
    assert result['dp_array_bytes']==12*300**2


def test_empty_negative_and_invalid_inputs():
    assert decode_exact_sparse('AAAA',np.empty((0,2),dtype=np.int32),np.empty(0))['structure']=='....'
    assert decode_exact_sparse('GGAAAACC',np.array([[0,7]]),np.array([-1.]))['objective']==0
    with pytest.raises(ValueError,match='1024'):decode_exact_sparse('A'*1025,np.empty((0,2),dtype=np.int32),np.empty(0))
    with pytest.raises(ValueError,match='Duplicate'):decode_exact_sparse('GGAAAACC',np.array([[0,7],[0,7]]),np.ones(2))
    with pytest.raises(ValueError,match='Illegal'):decode_exact_sparse('GGAAAACC',np.array([[0,1]]),np.ones(1))
    with pytest.raises(ValueError,match='64'):decode_exact_sparse('G'*66+'A'*4+'C',np.array([[i,70] for i in range(66)]),np.ones(66))


def test_measured_exact_decoder_replays(monkeypatch):
    import importlib.util
    from rnastable.cli import ROOT
    path=ROOT/'results/exact_sparse_development_summary.json'
    if not path.exists():pytest.skip('No completed exact sparse development')
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('verify_exact_sparse_development',ROOT/'scripts/verify_exact_sparse_development.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.audit_exact(path)


def test_measured_exact_validation_selection_replays(monkeypatch):
    import importlib.util
    from rnastable.cli import ROOT
    path=ROOT/'results/exact_comparative_development_summary.json'
    if not path.exists():pytest.skip('No completed exact-decoder training')
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('verify_exact_comparative_development',ROOT/'scripts/verify_exact_comparative_development.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.audit_exact_training(path)
