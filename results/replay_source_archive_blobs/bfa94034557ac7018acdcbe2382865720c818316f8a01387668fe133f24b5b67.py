"""Uniform negative-pair sampling by population rank, without a dense label matrix."""
from bisect import bisect_left,bisect_right
import hashlib
import random
from .pair_model import CANONICAL
from .reference import digest
from .scoring import base_pairs
from .sequences import validate_sequence

PARTNERS={'A':('U',),'C':('G',),'G':('C','U'),'U':('A','G')}


def kth_merged(first,n_first,second,n_second,rank):
    if not 0<=rank<n_first+n_second:raise ValueError('Invalid pair population rank')
    if not n_first:return second[rank]
    if not n_second:return first[rank]
    total=rank+1;low=max(0,total-n_second);high=min(total,n_first)
    while low<=high:
        take_first=(low+high)//2;take_second=total-take_first
        a=first[take_first-1] if take_first else -1;b=second[take_second-1] if take_second else -1
        next_a=first[take_first] if take_first<n_first else float('inf');next_b=second[take_second] if take_second<n_second else float('inf')
        if a>next_b:high=take_first-1
        elif b>next_a:low=take_first+1
        else:return max(a,b)
    raise ValueError('Invalid sorted pair population')


class PairPopulation:
    def __init__(self,record,max_length=10000):
        sequence=validate_sequence(record['sequence'])
        if type(max_length) is not int or not 1<=max_length<=10000 or len(sequence)>max_length:raise ValueError('Population supervision supports at most10000 nt')
        if len(record['structure'])!=len(sequence):raise ValueError('Reference length differs')
        reference=base_pairs(record['structure']);self.sequence=sequence;self.positions={base:[] for base in PARTNERS}
        for index,base in enumerate(sequence):self.positions[base].append(index)
        self.positives={pair for pair in reference if pair[1]-pair[0]>=4 and sequence[pair[0]]+sequence[pair[1]] in CANONICAL};self.excluded=len(reference-self.positives)
        self.positive_by_right={right:left for left,right in self.positives};self.prefix=[0];self.counts=[]
        for right,base in enumerate(sequence):
            partners=PARTNERS[base];counts=[bisect_left(self.positions[partner],max(0,right-3)) for partner in partners];self.counts.append(counts)
            self.prefix.append(self.prefix[-1]+sum(counts)-int(right in self.positive_by_right))
        self.negative_count=self.prefix[-1];self.positive_count=len(self.positives)
    def negative_at(self,rank):
        if type(rank) is not int or not 0<=rank<self.negative_count:raise ValueError('Negative rank outside population')
        right=bisect_right(self.prefix,rank)-1;local=rank-self.prefix[right];partners=PARTNERS[self.sequence[right]];counts=self.counts[right]
        if right in self.positive_by_right:
            positive_left=self.positive_by_right[right];positive_rank=sum(bisect_left(self.positions[partner],positive_left) for partner in partners)
            if local>=positive_rank:local+=1
        if len(partners)==1:left=self.positions[partners[0]][local]
        else:left=kth_merged(self.positions[partners[0]],counts[0],self.positions[partners[1]],counts[1],local)
        return left,right


def population_supervision(record,seed=20261006,negatives_per_positive=32,minimum_negatives=128,max_length=10000):
    import torch
    if type(seed) is not int or not 0<=seed<2**32 or type(negatives_per_positive) is not int or not 1<=negatives_per_positive<=64 or type(minimum_negatives) is not int or not 1<=minimum_negatives<=256:raise ValueError('Invalid bounded population sampling plan')
    population=PairPopulation(record,max_length);count=min(population.negative_count,max(minimum_negatives,negatives_per_positive*population.positive_count))
    material=f'{seed}\n{record["id"]}\n{record["sequence"]}'.encode();rng=random.Random(int.from_bytes(hashlib.sha256(material).digest(),'big'))
    ranks=rng.sample(range(population.negative_count),count);pairs=sorted([*population.positives,*[population.negative_at(rank) for rank in ranks]],key=lambda pair:(pair[1],pair[0]))
    indices=torch.tensor(pairs,dtype=torch.long).reshape(-1,2);labels=torch.tensor([float(pair in population.positives) for pair in pairs])
    metadata={'id':record['id'],'seed':seed,'population_positive':population.positive_count,'population_negative':population.negative_count,'sampled_positive':population.positive_count,'sampled_negative':count,
              'excluded_contacts':population.excluded,'negative_inclusion_probability':count/population.negative_count if population.negative_count else None,
              'indices_sha256':digest(indices.numpy().tobytes()),'labels_sha256':digest(labels.numpy().tobytes()),'retained_tensor_bytes':indices.numel()*indices.element_size()+labels.numel()*labels.element_size(),
              'policy':'All representable positives and a uniform sample without replacement from canonical negatives; rank counting/unranking avoids dense pair enumeration. Tensor bytes exclude Python metadata and model allocations.'}
    return (indices,labels,population.excluded),metadata


def population_bce(logits,labels,metadata,positive_weight):
    import torch
    if logits.ndim!=1 or labels.shape!=logits.shape or not bool(torch.isfinite(logits).all()) or not bool(torch.isfinite(labels).all()) or bool(((labels!=0)&(labels!=1)).any()):raise ValueError('Expected finite binary sampled labels and logits')
    positive=metadata['population_positive'];negative=metadata['population_negative'];sampled_negative=metadata['sampled_negative']
    if any(type(value) is not int or value<0 for value in (positive,negative,sampled_negative)) or positive!=int(labels.sum()) or sampled_negative!=len(labels)-positive or sampled_negative>negative or (negative and not sampled_negative) or not positive+negative:raise ValueError('Invalid population loss denominators')
    if type(positive_weight) not in (int,float) or not 0<positive_weight<float('inf'):raise ValueError('Invalid train-only positive weight')
    losses=torch.nn.functional.binary_cross_entropy_with_logits(logits,labels,reduction='none',pos_weight=torch.tensor(positive_weight,dtype=logits.dtype,device=logits.device))
    weights=torch.where(labels==1,torch.ones_like(labels),torch.full_like(labels,negative/sampled_negative if sampled_negative else 0))
    return (losses*weights).sum()/(positive+negative)
