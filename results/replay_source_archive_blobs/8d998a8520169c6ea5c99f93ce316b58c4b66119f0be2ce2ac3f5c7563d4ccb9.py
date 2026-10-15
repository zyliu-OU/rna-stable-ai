"""Reproducible training-only negative subsampling; retain every representable positive."""
import hashlib
import random
from .full_pair_supervision import full_supervision


def sampled_supervision(record,seed=20261006,negatives_per_positive=16,minimum_negatives=64):
    import torch
    if type(seed) is not int or not 0<=seed<2**32 or type(negatives_per_positive) is not int or not 1<=negatives_per_positive<=64 or type(minimum_negatives) is not int or not 1<=minimum_negatives<=256:raise ValueError('Invalid fixed negative sampling configuration')
    indices,labels,excluded=full_supervision(record)
    positives=torch.nonzero(labels,as_tuple=False).flatten().tolist();negatives=torch.nonzero(labels==0,as_tuple=False).flatten().tolist()
    material=f'{seed}\n{record["id"]}\n{record["sequence"]}'.encode()
    rng=random.Random(int.from_bytes(hashlib.sha256(material).digest(),'big'))
    count=min(len(negatives),max(minimum_negatives,negatives_per_positive*len(positives)))
    chosen=sorted(positives+rng.sample(negatives,count))
    return indices[chosen],labels[chosen],excluded
