import numpy as np
import pytest
from rnastable.sparse_refinement import refine_sparse
from rnastable.global_sparse_pairs import decode_sparse
from rnastable.pair_model import CANONICAL
from rnastable.scoring import base_pairs


def test_two_pair_exchange_repairs_greedy_counterexample():
    pairs=np.array([[0,6],[1,7],[0,7],[1,6]]);scores=np.array([5.,5.,4.,4.]);seq='GGAAAACC'
    result=refine_sparse(seq,pairs,scores)
    assert result['structure']=='((....))' and result['objective']==8
    assert result['objective_history']==[5.,8.] and result['accepted_moves']==1


def test_refinement_preserves_constraints_and_never_lowers_objective():
    rng=np.random.default_rng(61)
    for _ in range(10):
        seq=''.join(rng.choice(list('ACGU'),40));pairs=np.array([(i,j) for j in range(40) for i in range(j-3) if seq[i]+seq[j] in CANONICAL]);scores=rng.normal(size=len(pairs))
        before=decode_sparse(seq,pairs,scores);result=refine_sparse(seq,pairs,scores)
        selected=base_pairs(result['structure'])
        assert result['objective']>=before['objective']-1e-8
        assert result['objective_history']==sorted(result['objective_history'])
        assert len(selected)==result['accepted_pairs']
        assert result['objective']==pytest.approx(sum(scores[k] for k,p in enumerate(pairs) if tuple(p) in selected))
        endpoints=[p for pair in selected for p in pair]
        assert len(endpoints)==len(set(endpoints))
        assert all(not(i<k<j<l) for i,j in selected for k,l in selected)


def test_empty_candidates_and_duplicate_rejection():
    assert refine_sparse('AAAA',np.empty((0,2),dtype=int),np.empty(0))['structure']=='....'
    with pytest.raises(ValueError,match='unique'):refine_sparse('GAAAC',np.array([[0,4],[0,4]]),np.array([1.,2.]))


@pytest.mark.parametrize('settings',[{'passes':0},{'passes':True},{'max_remove':3},{'group_cap':1}])
def test_invalid_refinement_settings_rejected(settings):
    with pytest.raises(ValueError):refine_sparse('GAAAC',np.array([[0,4]]),np.array([1.]),**settings)


def test_distant_pair_refinement_preserves_large_sequence_constraints():
    seq='GG'+'A'*296+'CC';pairs=np.array([[0,298],[1,299],[0,299],[1,298]]);scores=np.array([5.,5.,4.,4.])
    result=refine_sparse(seq,pairs,scores)
    assert base_pairs(result['structure'])=={(0,299),(1,298)}
    assert result['objective']==8 and len(result['structure'])==300


def test_union_of_conflict_sets_recovers_missed_exchange():
    seq='GAAGGAAACACCC';pairs=np.array([[0,10],[3,8],[4,11],[0,12]]);scores=np.array([5.,1.,4.,4.])
    assert refine_sparse(seq,pairs,scores)['objective']==6
    result=refine_sparse(seq,pairs,scores,include_subsets=True)
    assert result['objective']==8 and base_pairs(result['structure'])=={(0,12),(4,11)}
    assert result['include_subsets'] is True
