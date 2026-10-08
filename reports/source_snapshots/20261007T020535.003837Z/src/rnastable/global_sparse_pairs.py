"""Unrestricted-distance pair scoring in bounded tiles; approximate sparse decoding."""
import math
import numpy as np
from .context_pairs import make_context_model,band_supervision
from .pair_model import CANONICAL
from .sequences import validate_sequence


def make_global_model(config):
    import torch
    class GlobalModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            base=make_context_model({**config,'max_pair_span':255})
            self.embedding=base.embedding;self.encoder=base.encoder
            self.projection=base.projection;self.endpoint=base.endpoint
            self.distance_network=torch.nn.Sequential(torch.nn.Linear(2,8),torch.nn.GELU(),torch.nn.Linear(8,1))
        def encode(self,tokens):
            if tokens.ndim!=2 or tokens.shape[0]!=1 or not 1<=tokens.shape[1]<=10000:raise ValueError('Expected one sequence of length1..10000')
            h=self.encoder(self.embedding(tokens).transpose(1,2)).transpose(1,2)[0]
            return self.projection(h),self.endpoint(h).squeeze(-1)
        def distance_logits(self,distance):
            d=distance.to(torch.float32).clamp_min(4)
            features=torch.stack((torch.log1p(d)/math.log(10001),torch.rsqrt(d)),dim=-1)
            return self.distance_network(features).squeeze(-1)
        def forward(self,tokens,indices):
            if indices.ndim!=2 or indices.shape[1]!=2 or indices.dtype!=torch.long:raise ValueError('Expected integer pair index rows')
            if len(indices) and (int(indices.min())<0 or int(indices.max())>=tokens.shape[1] or bool((indices[:,1]-indices[:,0]<4).any())):raise ValueError('Invalid pair indices')
            projected,endpoints=self.encode(tokens);i,j=indices[:,0],indices[:,1]
            return (projected[i]*projected[j]).sum(-1)/math.sqrt(projected.shape[-1])+endpoints[i]+endpoints[j]+self.distance_logits(j-i)
    return GlobalModel()


def global_supervision(record):
    # The current labelled development cohort is short. Full pair supervision is
    # deliberately bounded while long inference uses tile/candidate storage.
    if len(record['sequence'])>256:raise ValueError('Global development supervision is bounded to256 nt')
    return band_supervision(record,255)


def sparse_candidates(model,sequence,top_k=16,block_size=64):
    import torch
    from .structure_model import tokens
    validate_sequence(sequence)
    if len(sequence)>10000:raise ValueError('Sparse inference supports at most10000 nt')
    if type(top_k) is not int or not 1<=top_k<=64 or type(block_size) is not int or not 1<=block_size<=128:raise ValueError('Invalid bounded candidate/tile settings')
    n=len(sequence);model.eval();pair_parts=[];score_parts=[];peak=0
    with torch.inference_mode():
        tokenized=tokens(sequence);projected,endpoints=model.encode(tokenized)
        positions=torch.arange(n);codes=tokenized[0]
        canonical=torch.tensor([[False,False,False,True],[False,False,True,False],[False,True,False,True],[True,False,True,False]])
        for begin in range(0,n,block_size):
            stop=min(n,begin+block_size);right=positions[begin:stop];distance=right[None,:]-positions[:,None]
            values=projected@projected[begin:stop].T/math.sqrt(projected.shape[-1])+endpoints[:,None]+endpoints[None,begin:stop]+model.distance_logits(distance)
            if hasattr(model,'pair_context_logits'):values=values+model.pair_context_logits(codes,positions[:,None],right[None,:])
            if not torch.isfinite(values).all():raise ValueError('Nonfinite global pair scores')
            eligible=(distance>=4)&canonical[codes[:,None],codes[None,begin:stop]]
            values=values.masked_fill(~eligible,-torch.inf);peak=max(peak,values.numel())
            # Stable sorting preserves ascending left partner on equal scores.
            order=torch.argsort(values,dim=0,descending=True,stable=True)[:min(top_k,n)]
            chosen=values.gather(0,order);positive=chosen>0
            left=order[positive];rights=right.expand_as(order)[positive]
            pair_parts.append(torch.stack((left,rights),dim=1).cpu().numpy().astype(np.int32))
            score_parts.append(chosen[positive].cpu().numpy().astype(np.float64))
    pairs=np.concatenate(pair_parts) if pair_parts else np.empty((0,2),dtype=np.int32)
    scores=np.concatenate(score_parts) if score_parts else np.empty(0,dtype=np.float64)
    return {'pairs':pairs,'scores':scores,'top_k':top_k,'block_size':block_size,'peak_score_tile_elements':peak,
            'candidate_array_bytes':pairs.nbytes+scores.nbytes,'candidate_count':len(scores),
            **({'pair_context_feature_tile_elements':getattr(model,'pair_context_feature_count',2)*peak} if hasattr(model,'pair_context_logits') else {}),
            'interpretation':'All distances scored in tiles; retain top-k positive legal partners per right endpoint. Quadratic scoring work; bounded tile/candidate storage.'}


def decode_sparse(sequence,pairs,scores):
    """Greedily accept highest scores when endpoints and noncrossing constraints permit.

    Deterministic ties prefer smaller left, then right endpoints. This is a heuristic,
    not the exact dynamic-programming optimum. Crossing checks scan accepted pairs;
    worst-case work is quadratic in retained candidates/sequence, with O(n+m) storage.
    """
    validate_sequence(sequence);n=len(sequence)
    if n>10000:raise ValueError('Sparse decoder supports at most10000 nt')
    pairs=np.asarray(pairs);scores=np.asarray(scores,dtype=np.float64)
    if pairs.ndim!=2 or pairs.shape[1]!=2 or not np.issubdtype(pairs.dtype,np.integer) or scores.shape!=(len(pairs),) or not np.isfinite(scores).all():raise ValueError('Expected integer pairs with finite score vector')
    for i,j in pairs:
        if not 0<=i<j<n or j-i<4 or sequence[i]+sequence[j] not in CANONICAL:raise ValueError('Illegal sparse pair')
    order=np.lexsort((pairs[:,1],pairs[:,0],-scores));used=np.zeros(n,dtype=bool)
    left=np.empty(n//2,dtype=np.int32);right=np.empty(n//2,dtype=np.int32)
    count=0;objective=0.;structure=['.']*n
    for offset in order:
        if scores[offset]<=0:continue
        i,j=pairs[offset]
        if used[i] or used[j]:continue
        a,b=left[:count],right[:count]
        if np.any((a<i)&(i<b)&(b<j)) or np.any((i<a)&(a<j)&(j<b)):continue
        used[i]=used[j]=True;left[count]=i;right[count]=j;count+=1
        structure[i],structure[j]='(',')';objective+=float(scores[offset])
    return {'structure':''.join(structure),'objective':objective,'accepted_pairs':count,
            'interpretation':'Approximate greedy noncrossing selection from sparse candidates; distant pairs permitted; scores are logits, not energy.'}
