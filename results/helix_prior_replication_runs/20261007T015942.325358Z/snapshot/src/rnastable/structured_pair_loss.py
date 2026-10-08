"""Pruned margin-rescaled pair-set hinge; gold is retained in every candidate graph.

Inspired by structured large-margin loss, Tsochantaridis et al., JMLR6 (2005).
Training-only loss augmentation; the graph is pruned, so this is not a full-graph
structured-SVM optimizer or a calibrated probability/energy objective.
"""
import numpy as np
from .exact_sparse_pairs import decode_exact_sparse
from .pair_model import CANONICAL
from .scoring import base_pairs
from .sequences import validate_sequence


def structured_hinge(sequence,edges,labels,logits,top_k=16,margin=1.0):
    import torch
    validate_sequence(sequence);n=len(sequence)
    if n>1024 or type(top_k) is not int or not 1<=top_k<=63 or type(margin) not in (int,float) or not np.isfinite(margin) or not 0<margin<=2:raise ValueError('Invalid bounded structured-loss configuration')
    if edges.device.type!='cpu' or labels.device.type!='cpu' or logits.device.type!='cpu' or edges.dtype!=torch.long or edges.ndim!=2 or edges.shape[1]!=2 or labels.shape!=(len(edges),) or logits.shape!=(len(edges),) or not logits.is_floating_point() or not torch.isfinite(logits).all() or not bool(((labels==0)|(labels==1)).all()):raise ValueError('Expected CPU integer pairs, binary labels and finite logits')
    pairs=edges.numpy();target=labels.detach().numpy().astype(bool)
    if len({tuple(map(int,p)) for p in pairs})!=len(pairs):raise ValueError('Duplicate pair labels')
    for i,j in pairs:
        if not 0<=i<j<n or j-i<4 or sequence[i]+sequence[j] not in CANONICAL:raise ValueError('Illegal structured-loss pair')
    gold={tuple(map(int,p)) for p in pairs[target]};gold_structure=['.']*n
    for i,j in gold:
        if gold_structure[i]!='.' or gold_structure[j]!='.':raise ValueError('Gold pairs share an endpoint')
        gold_structure[i],gold_structure[j]='(',')'
    if base_pairs(''.join(gold_structure))!=gold:raise ValueError('Gold pairs must be noncrossing')
    augmented=logits.detach().numpy().astype(np.float64)+margin*(1-2*target.astype(np.int32))
    order=np.lexsort((pairs[:,0],-augmented,pairs[:,1]))
    if len(order):
        right=pairs[order,1];ranks=np.arange(len(order));starts=np.maximum.accumulate(np.where(np.r_[True,right[1:]!=right[:-1]],ranks,0));hard=order[((ranks-starts)<top_k)&(augmented[order]>0)]
    else:hard=np.empty(0,dtype=np.int64)
    candidates=np.union1d(hard,np.flatnonzero(target)).astype(np.int64)
    decoded=decode_exact_sparse(sequence,pairs[candidates],augmented[candidates]);predicted=base_pairs(decoded['structure']);lookup={tuple(map(int,pairs[index])):int(index) for index in candidates};selected=sorted(lookup[p] for p in predicted)
    delta=len(predicted^gold)
    raw=logits[selected].double().sum()-logits[labels.bool()].double().sum()+margin*delta
    loss=raw.clamp_min(0)/max(1,len(gold))
    return loss,{'structure':decoded['structure'],'selected_indices':selected,'candidate_indices':candidates.tolist(),'gold_pairs':len(gold),'symmetric_pair_difference':delta,'augmented_objective':decoded['objective'],'raw_margin_violation':float(raw.detach()),'normalizer':max(1,len(gold)),'interpretation':'Exact loss-augmented decode on a pruned training graph retaining all supported gold pairs. Label-informed training objective, not inference, full-graph optimality or measured stability.'}
