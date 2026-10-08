"""Sequence-only checkpoint logits as a proposal-ranking proxy, never folding energy."""
import math
from .context_inference import load_checkpoint,method_name
from .pair_model import CANONICAL
from .reference import digest
from .scoring import base_pairs
from .sequences import validate_sequence
from .structure_model import tokens


def template_pairs(sequence,structure):
    validate_sequence(sequence)
    if len(sequence)>10000 or len(structure)!=len(sequence):raise ValueError('Invalid bounded target template length')
    pairs=sorted(base_pairs(structure),key=lambda p:(p[1],p[0]))
    if any(j-i<4 or sequence[i]+sequence[j] not in CANONICAL for i,j in pairs):raise ValueError('Template requires canonical pairs and minimum loop distance4')
    return pairs


def compatibility(sequence,pairs):
    validate_sequence(sequence)
    if len(sequence)>10000 or any(not 0<=i<j<len(sequence) or j-i<4 for i,j in pairs):raise ValueError('Invalid target pair coordinates')
    return [p for p in pairs if sequence[p[0]]+sequence[p[1]] in CANONICAL]


class TargetScorer:
    def __init__(self,source_summary,sequence,structure):
        self.pairs=template_pairs(sequence,structure);self.length=len(sequence)
        source_bytes,self.config,checkpoint,self.model=load_checkpoint(source_summary)
        if self.config['mode'] not in ('global_sparse_development_only','long_comparative_development_only'):raise ValueError('Target scorer requires a global sparse checkpoint')
        self.binding={'source_summary_sha256':digest(source_bytes),'checkpoint':str(checkpoint),'checkpoint_sha256':digest(checkpoint.read_bytes()),'model_method':method_name(self.config),'target_sequence_sha256':digest(sequence.encode()),'target_structure_sha256':digest(structure.encode()),'target_pairs':len(self.pairs),'purpose':'compatible_template_pair_logits_for_proposal_ranking_only'}
    def score(self,sequence):
        import torch
        validate_sequence(sequence,self.length);compatible=compatibility(sequence,self.pairs)
        if compatible:
            with torch.inference_mode():values=self.model(tokens(sequence),torch.tensor(compatible,dtype=torch.long))
            if not bool(torch.isfinite(values).all()):raise ValueError('Nonfinite checkpoint proxy score')
            mean=values.double().mean().item();sha=digest(values.numpy().tobytes())
        else:mean=None;sha=digest(b'')
        return {'sequence_sha256':digest(sequence.encode()),'compatible_target_pairs':len(compatible),'target_pairs':len(self.pairs),'mean_compatible_logit':mean,'logits_sha256':sha,'interpretation':'Compatible-contact count and mean learned pair logits are ranking proxies, not folding energy or stability. No all-pair decoding or labels.'}


def choose_pool(pool,policy,pairs,selector_rng,scorer=None):
    if policy not in ('random_pool','compatibility_only','checkpoint_prior') or not pool or len(pool)>64 or len(set(pool))!=len(pool):raise ValueError('Invalid unique proposal pool or ranking policy')
    if len({len(s) for s in pool})!=1:raise ValueError('Proposal pool length differs')
    rows=[]
    for sequence in pool:
        contacts=len(compatibility(sequence,pairs))
        row={'sequence_sha256':digest(sequence.encode()),'compatible_target_pairs':contacts,'mean_compatible_logit':None}
        if policy=='checkpoint_prior':
            if scorer is None:raise ValueError('Checkpoint ranking requires a scorer')
            scored=scorer.score(sequence)
            if scored['sequence_sha256']!=row['sequence_sha256'] or scored['compatible_target_pairs']!=contacts or scored['target_pairs']!=len(pairs):raise ValueError('Proxy score binding differs')
            value=scored['mean_compatible_logit']
            if (contacts>0 and (type(value) not in (int,float) or not math.isfinite(value))) or (contacts==0 and value is not None):raise ValueError('Invalid proxy score')
            row.update(scored)
        rows.append(row)
    if policy=='random_pool':selected=selector_rng.randrange(len(pool))
    elif policy=='compatibility_only':selected=max(range(len(pool)),key=lambda i:(rows[i]['compatible_target_pairs'],-i))
    else:selected=max(range(len(pool)),key=lambda i:(rows[i]['compatible_target_pairs'],rows[i]['mean_compatible_logit'] if rows[i]['mean_compatible_logit'] is not None else -math.inf,-i))
    return selected,rows
