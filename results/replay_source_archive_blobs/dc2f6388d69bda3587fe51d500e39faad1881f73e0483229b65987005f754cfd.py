"""Replayable synthetic sampled-training step, without biological accuracy claims."""
import math
import random
from pathlib import Path
from .helix_pairs import make_helix_model
from .native_journal import atomic_json
from .population_sampling import population_supervision,population_bce
from .reference import digest
from .structure_model import tokens


def toy_record(length,seed=20261006):
    if type(length) is not int or not 8<=length<=10000 or length%2:raise ValueError('Synthetic resource length must be even,8..10000')
    rng=random.Random(seed);half=''.join(rng.choice('ACGU') for _ in range((length-4)//2));complement=str.maketrans('ACGU','UGCA');sequence=half+'AAAA'+half.translate(complement)[::-1]
    return {'id':'synthetic_nested_'+str(length),'sequence':sequence,'structure':'('*len(half)+'....'+')'*len(half),'reference_kind':'computational','source':'Constructed reverse-complement nested toy; not a biological annotation','conditions':'Synthetic sampled training resource demonstration only; no prediction accuracy evaluated'}


def tensor_digest(state):
    import hashlib
    total=hashlib.sha256()
    for key,value in sorted(state.items()):total.update(key.encode()+b'\0');total.update(value.detach().cpu().contiguous().numpy().tobytes())
    return total.hexdigest()


def training_step(record,config,settings):
    import torch
    torch.set_num_threads(config['cpu_threads']);torch.manual_seed(config['seed']);torch.use_deterministic_algorithms(True);model=make_helix_model(config);sample,metadata=population_supervision(record,**settings);edges,labels,_=sample;weight=(metadata['population_negative']/metadata['population_positive'])**config['positive_weight_exponent'];initial=tensor_digest(model.state_dict());optimizer=torch.optim.Adam(model.parameters(),lr=config['learning_rate']);logits=model(tokens(record['sequence']),edges);loss=population_bce(logits,labels,metadata,weight);optimizer.zero_grad(set_to_none=True);loss.backward();norm=math.sqrt(sum(float(p.grad.double().square().sum()) for p in model.parameters() if p.grad is not None))
    if not math.isfinite(norm) or norm<=0:raise ValueError('Invalid synthetic gradient')
    optimizer.step();model.eval()
    with torch.inference_mode():after=population_bce(model(tokens(record['sequence']),edges),labels,metadata,weight).item()
    return sample,metadata,{'initial_state_tensor_sha256':initial,'final_state_tensor_sha256':tensor_digest(model.state_dict()),'initial_sampled_population_loss':loss.item(),'after_step_sampled_population_loss':after,'gradient_l2_norm':norm,'train_only_positive_weight':weight,'parameters':sum(p.numel() for p in model.parameters()),'full_label_tensor_bytes_if_materialized':20*(metadata['population_positive']+metadata['population_negative']),'full_pair_labels_materialized':False,'accuracy_evaluated':False,'optimizer_steps':1}
