"""Global pair head with two sequence-only adjacent stackability indicators."""
from .global_sparse_pairs import make_global_model


def stack_features(codes,left,right):
    import torch
    if codes.ndim!=1 or codes.dtype!=torch.long or not 1<=len(codes)<=10000 or left.dtype!=torch.long or right.dtype!=torch.long:raise ValueError('Expected bounded sequence codes and integer pair indices')
    n=len(codes)
    if len(codes) and (bool((codes<0).any()) or bool((codes>3).any())):raise ValueError('Invalid nucleotide codes')
    if left.numel() and (bool((left<0).any()) or bool((left>=n).any())) or right.numel() and (bool((right<0).any()) or bool((right>=n).any())):raise ValueError('Pair indices outside sequence')
    canonical=torch.tensor([[False,False,False,True],[False,False,True,False],[False,True,False,True],[True,False,True,False]])
    outside=(left>=1)&(right+1<n)&(right-left+2>=4)&canonical[codes[(left-1).clamp(0,n-1)],codes[(right+1).clamp(0,n-1)]]
    inside=(left+1<n)&(right>=1)&(right-left-2>=4)&canonical[codes[(left+1).clamp(0,n-1)],codes[(right-1).clamp(0,n-1)]]
    return torch.stack(torch.broadcast_tensors(outside,inside),dim=-1).to(torch.float32)


def make_stack_model(config):
    import torch
    if config.get('pair_features')!='adjacent_stackability':raise ValueError('Expected fixed adjacent-stackability configuration')
    class StackModel(torch.nn.Module):
        def __init__(self):
            super().__init__();self.base=make_global_model(config);self.stack_weights=torch.nn.Linear(2,1,bias=False);torch.nn.init.zeros_(self.stack_weights.weight)
        def encode(self,tokens):return self.base.encode(tokens)
        def distance_logits(self,distance):return self.base.distance_logits(distance)
        def pair_context_logits(self,codes,left,right):return self.stack_weights(stack_features(codes,left,right)).squeeze(-1)
        def forward(self,tokens,indices):return self.base(tokens,indices)+self.pair_context_logits(tokens[0],indices[:,0],indices[:,1])
    return StackModel()
