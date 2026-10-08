"""Dilated development encoder with supervised sparse pair scoring, no dense pair matrix."""
import math
from .pair_model import CANONICAL
from .scoring import base_pairs
from .sequences import validate_sequence


def make_context_model(config):
    import torch
    class ContextModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = torch.nn.Embedding(4, config['embedding_dim'])
            layers=[]; incoming=config['embedding_dim']
            for dilation in config['dilations']:
                layers.extend([torch.nn.Conv1d(incoming, config['channels'], 7, padding=3*dilation, dilation=dilation),torch.nn.GELU()]);incoming=config['channels']
            self.encoder=torch.nn.Sequential(*layers)
            self.projection=torch.nn.Linear(config['channels'],config['pair_dim'])
            self.endpoint=torch.nn.Linear(config['channels'],1)
            self.distance=torch.nn.Embedding(256,1)
        def forward(self, tokens, indices):
            if tokens.ndim!=2 or tokens.shape[0]!=1 or tokens.shape[1]<1:raise ValueError('Expected one nonempty sequence')
            if indices.ndim!=2 or indices.shape[1]!=2:raise ValueError('Expected pair index rows')
            if len(indices) and (int(indices.min())<0 or int(indices.max())>=tokens.shape[1] or bool(((indices[:,1]-indices[:,0]<4)|(indices[:,1]-indices[:,0]>config['max_pair_span'])).any())):raise ValueError('Pair indices outside fixed span')
            h=self.encoder(self.embedding(tokens).transpose(1,2)).transpose(1,2)[0]
            projected=self.projection(h);endpoints=self.endpoint(h).squeeze(-1)
            i,j=indices[:,0],indices[:,1]
            return (projected[i]*projected[j]).sum(-1)/math.sqrt(projected.shape[-1])+endpoints[i]+endpoints[j]+self.distance(j-i).squeeze(-1)
    return ContextModel()


def band_supervision(record, max_span):
    import torch
    validate_sequence(record['sequence'])
    if type(max_span) is not int or not 4<=max_span<=255:raise ValueError('Invalid pair span')
    sequence=record['sequence'];reference=base_pairs(record['structure'])
    if len(record['structure'])!=len(sequence):raise ValueError('Reference length differs')
    pairs=[(i,j) for j in range(len(sequence)) for i in range(max(0,j-max_span),j-3) if sequence[i]+sequence[j] in CANONICAL]
    indices=torch.tensor(pairs,dtype=torch.long).reshape(-1,2)
    labels=torch.tensor([float(pair in reference) for pair in pairs])
    return indices,labels,len(reference-set(pairs))
