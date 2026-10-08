from itertools import product
import random
import numpy as np
import pytest
import torch
from rnastable.full_pair_supervision import full_supervision
from rnastable.population_sampling import PairPopulation,population_supervision,population_bce,kth_merged
from rnastable.scoring import base_pairs


def test_negative_rank_inventory_matches_dense_oracle_for_small_sequences():
    rng=random.Random(7)
    records=[{'sequence':'GGAAAACC','structure':'((....))'},{'sequence':'GGGGAAAACCCC','structure':'((((....))))'}]
    records += [{'sequence':''.join(rng.choice('ACGU') for _ in range(n)),'structure':'.'*n} for n in range(4,35)]
    for record in records:
        population=PairPopulation(record);indices,labels,excluded=full_supervision(record)
        expected=[tuple(pair) for pair,label in zip(indices.tolist(),labels.tolist()) if label==0]
        assert [population.negative_at(rank) for rank in range(population.negative_count)]==expected
        assert population.positive_count==int(labels.sum()) and population.excluded==excluded


def test_merge_rank_matches_sorted_prefix_oracle():
    first=[0,2,5,9];second=[1,3,6,8]
    for n_a,n_b in product(range(5),repeat=2):
        expected=sorted(first[:n_a]+second[:n_b])
        for rank,value in enumerate(expected):assert kth_merged(first,n_a,second,n_b,rank)==value


def test_sample_is_reproducible_unique_and_keeps_all_positive_contacts():
    record={'id':'fixture','sequence':'GGGGAAAACCCC','structure':'((((....))))'}
    first,meta=population_supervision(record,seed=7,negatives_per_positive=1,minimum_negatives=1);second,other=population_supervision(record,seed=7,negatives_per_positive=1,minimum_negatives=1)
    assert torch.equal(first[0],second[0]) and torch.equal(first[1],second[1]) and meta==other
    pairs=first[0].tolist();assert len({tuple(pair) for pair in pairs})==len(pairs)
    assert {tuple(pair) for pair,label in zip(pairs,first[1].tolist()) if label==1}==base_pairs(record['structure'])
    assert meta['sampled_negative']==meta['population_positive'] and meta['population_negative']>=meta['sampled_negative']


def test_population_bce_expectation_equals_full_weighted_bce_for_exhaustive_one_negative_draws():
    record={'sequence':'GGAAAACC','structure':'((....))'};indices,labels,_=full_supervision(record);logits=torch.arange(len(labels),dtype=torch.float64)/3-1
    positive=torch.nonzero(labels==1).flatten();negative=torch.nonzero(labels==0).flatten();weight=2.
    full=torch.nn.functional.binary_cross_entropy_with_logits(logits,labels.double(),pos_weight=torch.tensor(weight,dtype=torch.float64))
    losses=[]
    for selected in negative:
        chosen=torch.cat((positive,selected.reshape(1)));metadata={'population_positive':len(positive),'population_negative':len(negative),'sampled_negative':1}
        losses.append(population_bce(logits[chosen],labels[chosen].double(),metadata,weight))
    assert torch.allclose(torch.stack(losses).mean(),full,atol=1e-12)


def test_ten_thousand_nt_population_is_counted_without_dense_supervision(monkeypatch):
    record={'id':'long_fixture','sequence':'G'*4997+'A'*6+'C'*4997,'structure':'('*4997+'.'*6+')'*4997}
    monkeypatch.setattr('rnastable.full_pair_supervision.full_supervision',lambda *args:pytest.fail('Dense labels invoked'))
    sample,metadata=population_supervision(record,seed=7,negatives_per_positive=1,minimum_negatives=1)
    assert metadata['population_positive']==4997 and metadata['population_negative']==4997**2-4997
    assert len(sample[1])==9994 and metadata['retained_tensor_bytes']==9994*20 and metadata['excluded_contacts']==0


@pytest.mark.parametrize('changed',[{'population_negative':0},{'sampled_negative':0},{'population_positive':True}])
def test_population_loss_rejects_wrong_denominators(changed):
    metadata={'population_positive':1,'population_negative':5,'sampled_negative':1,**changed}
    with pytest.raises(ValueError):population_bce(torch.tensor([0.,1.]),torch.tensor([1.,0.]),metadata,2.)


def test_population_gradient_expectation_matches_full_bce():
    record={'sequence':'GGAAAACC','structure':'((....))'};_,labels,_=full_supervision(record);values=torch.arange(len(labels),dtype=torch.float64)/4
    full_logits=values.clone().requires_grad_();full_loss=torch.nn.functional.binary_cross_entropy_with_logits(full_logits,labels.double(),pos_weight=torch.tensor(3.,dtype=torch.float64));full_loss.backward()
    positive=torch.nonzero(labels==1).flatten();negative=torch.nonzero(labels==0).flatten();gradients=[]
    for chosen in negative:
        logits=values.clone().requires_grad_();keep=torch.cat((positive,chosen.reshape(1)));metadata={'population_positive':len(positive),'population_negative':len(negative),'sampled_negative':1}
        population_bce(logits[keep],labels[keep].double(),metadata,3.).backward();gradients.append(logits.grad)
    assert torch.allclose(torch.stack(gradients).mean(0),full_logits.grad,atol=1e-12)
