import itertools
import numpy as np
import pytest
import torch
from rnastable.structured_pair_loss import structured_hinge
from rnastable.full_pair_supervision import full_supervision
from rnastable.scoring import base_pairs


def test_loss_and_gradient_correct_a_competing_structure():
    edges=torch.tensor([[0,6],[0,7],[1,6]]);labels=torch.tensor([0.,1.,1.]);logits=torch.tensor([6.,3.,3.],requires_grad=True)
    loss,row=structured_hinge('GGAAAACC',edges,labels,logits)
    assert loss.item()==1.5 and row['symmetric_pair_difference']==3
    assert base_pairs(row['structure'])=={(0,6)}
    loss.backward();assert logits.grad.tolist()==[.5,-.5,-.5]
    loss,row=structured_hinge('GGAAAACC',edges,labels,torch.tensor([1.,5.,5.],requires_grad=True))
    assert loss.item()==0 and row['symmetric_pair_difference']==0


def test_pruned_graph_retains_negative_scored_gold():
    edges=torch.tensor([[0,6],[0,7],[1,6]]);labels=torch.tensor([0.,1.,1.])
    loss,row=structured_hinge('GGAAAACC',edges,labels,torch.tensor([2.,-5.,-6.],requires_grad=True),top_k=1)
    assert {1,2}<=set(row['candidate_indices']) and loss.item()>=0


def test_matches_brute_force_non_crossing_loss_augmented_search():
    record={'sequence':'GGAAAACC','structure':'((....))'};edges,labels,_=full_supervision(record);rng=np.random.default_rng(34)
    for _ in range(10):
        logits=torch.tensor(rng.normal(size=len(edges)),dtype=torch.float64,requires_grad=True);loss,row=structured_hinge(record['sequence'],edges,labels,logits,top_k=16);gold={tuple(map(int,p)) for p in edges[labels.bool()].tolist()};best=-float('inf')
        for mask in itertools.product((False,True),repeat=len(edges)):
            chosen={tuple(map(int,p)) for p,yes in zip(edges.tolist(),mask) if yes};used=[i for p in chosen for i in p]
            if len(used)!=len(set(used)) or any(i<k<j<l or k<i<l<j for i,j in chosen for k,l in chosen):continue
            value=sum(float(logits[i].detach()) for i,yes in enumerate(mask) if yes)-float(logits[labels.bool()].detach().sum())+len(chosen^gold);best=max(best,value)
        assert loss.item()==pytest.approx(best/max(1,len(gold)))


def test_no_positive_or_no_candidate_labels():
    logits=torch.tensor([.5],requires_grad=True);loss,row=structured_hinge('GAAAC',torch.tensor([[0,4]]),torch.zeros(1),logits);assert loss.item()==1.5;loss.backward();assert logits.grad.item()==1
    logits=torch.empty(0,requires_grad=True);loss,row=structured_hinge('AAAA',torch.empty((0,2),dtype=torch.long),torch.empty(0),logits);assert loss.item()==0;loss.backward()


def test_invalid_labels_and_gold_constraints_reject():
    edges=torch.tensor([[0,6],[1,7]])
    with pytest.raises(ValueError,match='noncrossing'):structured_hinge('GGAAAACC',edges,torch.ones(2),torch.zeros(2))
    with pytest.raises(ValueError,match='binary'):structured_hinge('GGAAAACC',edges,torch.tensor([.5,1.]),torch.zeros(2))
    with pytest.raises(ValueError):structured_hinge('GGAAAACC',edges,torch.ones(2),torch.tensor([float('nan'),0.]))
    with pytest.raises(ValueError):structured_hinge('A'*1025,torch.empty((0,2),dtype=torch.long),torch.empty(0),torch.empty(0))


def test_measured_structured_training_replays(monkeypatch):
    import importlib.util
    from rnastable.cli import ROOT
    path=ROOT/'results/structured_comparative_development_summary.json'
    if not path.exists():pytest.skip('No completed structured development training')
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('verify_structured_comparative_development',ROOT/'scripts/verify_structured_comparative_development.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.audit_structured(path)
