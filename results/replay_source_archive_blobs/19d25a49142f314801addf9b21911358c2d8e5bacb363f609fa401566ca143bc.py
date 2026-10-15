"""Exact noncrossing maximum-logit decoding on short retained sparse candidate sets."""
import numpy as np
from .pair_model import CANONICAL
from .sequences import validate_sequence


def decode_exact_sparse(sequence,pairs,scores):
    validate_sequence(sequence);n=len(sequence)
    if n>1024:raise ValueError('Exact sparse decoding is bounded to1024 nt')
    pairs=np.asarray(pairs);scores=np.asarray(scores,dtype=np.float64)
    if pairs.ndim!=2 or pairs.shape[1]!=2 or not np.issubdtype(pairs.dtype,np.integer) or scores.shape!=(len(pairs),) or not np.isfinite(scores).all():raise ValueError('Expected integer pairs with finite scores')
    if len({tuple(map(int,p)) for p in pairs})!=len(pairs):raise ValueError('Duplicate candidate pairs')
    by_right=[[] for _ in range(n)]
    for (i,j),score in zip(pairs,scores):
        i,j=int(i),int(j)
        if not 0<=i<j<n or j-i<4 or sequence[i]+sequence[j] not in CANONICAL:raise ValueError('Illegal sparse pair')
        if score>0:by_right[j].append((i,float(score)))
    if any(len(rows)>64 for rows in by_right):raise ValueError('Exact sparse decoding supports at most64 positive candidates per right endpoint')
    dp=np.zeros((n,n),dtype=np.float64);choice=np.full((n,n),-1,dtype=np.int32)
    for right in range(n):
        if right:dp[:right,right]=dp[:right,right-1]
        for partner,score in sorted(by_right[right]):
            before=dp[:partner+1,partner-1].copy() if partner else np.zeros(1)
            before[partner]=0
            candidate=before+score+dp[partner+1,right-1]
            better=candidate>dp[:partner+1,right]
            dp[:partner+1,right][better]=candidate[better]
            choice[:partner+1,right][better]=partner
    structure=['.']*n;intervals=[(0,n-1)]
    while intervals:
        left,right=intervals.pop()
        if left>=right:continue
        partner=int(choice[left,right])
        if partner<0:intervals.append((left,right-1))
        else:
            structure[partner],structure[right]='(',')'
            intervals.extend([(left,partner-1),(partner+1,right-1)])
    return {'structure':''.join(structure),'objective':float(dp[0,n-1]),'accepted_pairs':structure.count('('),'dp_array_bytes':dp.nbytes+choice.nbytes,'interpretation':'Exact maximum summed positive logits over retained candidates, not unrestricted pairs or maximum reference agreement. O(n*m) work and O(n²) storage; bounded to1024 nt/64 candidates per right endpoint.'}
