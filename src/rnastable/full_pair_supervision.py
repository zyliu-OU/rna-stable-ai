"""Bounded full canonical pair supervision for the larger comparative development cohort."""
from .pair_model import CANONICAL
from .scoring import base_pairs
from .sequences import validate_sequence


def full_supervision(record,max_length=1024):
    import torch
    sequence=validate_sequence(record['sequence'])
    if type(max_length) is not int or not 1<=max_length<=1024 or len(sequence)>max_length:raise ValueError('Full development pair labels are bounded to1024 nt')
    if len(record['structure'])!=len(sequence):raise ValueError('Reference length differs')
    reference=base_pairs(record['structure'])
    pairs=[(i,j) for j in range(len(sequence)) for i in range(j-3) if sequence[i]+sequence[j] in CANONICAL]
    indices=torch.tensor(pairs,dtype=torch.long).reshape(-1,2)
    labels=torch.tensor([float(p in reference) for p in pairs])
    return indices,labels,len(reference-set(pairs))
