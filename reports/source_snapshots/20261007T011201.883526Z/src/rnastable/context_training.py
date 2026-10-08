"""Reusable context training API with training and validation inputs only."""
import copy
import math
import random
from pathlib import Path
from .banded_pairs import band_scores,decode_band
from .context_pairs import band_supervision,make_context_model
from .reference import digest
from .scoring import structure_agreement
from .structure_model import tokens
import json


def predictions(model, records, method, span):
    return [{'id':r['id'],'sequence':r['sequence'],'method':method,'status':'ok','structure':decode_band(r['sequence'],band_scores(model,r['sequence'],span),span)['structure']} for r in records]


def train_context(train,validation,config,run,*,model_factory=None,labeler=None,predictor=None,training_loss_fn=None):
    import torch
    if training_loss_fn is not None and not callable(training_loss_fn):raise ValueError('Training loss callback must be callable')
    if not train or not validation:raise ValueError('Training and validation must be nonempty')
    for key,upper in [('epochs',20),('embedding_dim',64),('channels',64),('pair_dim',64),('cpu_threads',2)]:
        if type(config.get(key)) is not int or not 1<=config[key]<=upper:raise ValueError('Invalid training setting: '+key)
    callbacks=(model_factory,labeler,predictor)
    if any(f is not None for f in callbacks) and not all(callable(f) for f in callbacks):raise ValueError('Provide all three scorer callbacks together')
    if model_factory is None and (type(config.get('max_pair_span')) is not int or not 4<=config['max_pair_span']<=255):raise ValueError('Invalid span')
    if type(config.get('positive_weight_exponent',.5)) not in (int,float) or config.get('positive_weight_exponent',.5) not in (.5,1.):raise ValueError('Invalid weighting')
    factory=model_factory or make_context_model
    labeler=labeler or (lambda r:band_supervision(r,config['max_pair_span']))
    predictor=predictor or (lambda m,rs,method:predictions(m,rs,method,config['max_pair_span']))
    if config.get('dilations')!=[1,2,4,8] or type(config.get('seed')) is not int or not 0<=config['seed']<2**32 or type(config.get('learning_rate')) not in (int,float) or not 0<config['learning_rate']<1:raise ValueError('Invalid context configuration')
    run=Path(run)
    torch.set_num_threads(config['cpu_threads']);torch.manual_seed(config['seed']);torch.use_deterministic_algorithms(True)
    rng=random.Random(config['seed']);model=factory(config);initial=copy.deepcopy(model)
    torch.save(initial.state_dict(),run/'initial_context_model.pt')
    labels=[labeler(r) for r in train]
    positive=sum(int(y.sum()) for _,y,_ in labels);negative=sum(len(y)-int(y.sum()) for _,y,_ in labels)
    if not positive or not negative:raise ValueError('Need both positive and negative training pairs')
    weight=(negative/positive)**config.get('positive_weight_exponent',.5);loss_fn=torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(weight));optimizer=torch.optim.Adam(model.parameters(),lr=config['learning_rate'])
    history=[];best=None;chosen=None
    for epoch in range(1,config['epochs']+1):
        order=list(range(len(train)));rng.shuffle(order);model.train();losses=[]
        for index in order:
            edges,target,_=labels[index]
            if not len(target):continue
            optimizer.zero_grad(set_to_none=True);logits=model(tokens(train[index]['sequence']),edges)
            loss=loss_fn(logits,target) if training_loss_fn is None else training_loss_fn(logits,edges,target,train[index])
            if not isinstance(loss,torch.Tensor) or loss.ndim!=0:raise ValueError('Training loss must be a scalar tensor')
            if not torch.isfinite(loss):raise ValueError('Nonfinite training loss')
            loss.backward();optimizer.step();losses.append(loss.item())
        pred=predictor(model,validation,'validation')
        f1=sum(structure_agreement(p['structure'],r['structure'])['pair_f1'] for p,r in zip(pred,validation))/len(validation)
        model.eval();val_losses=[]
        with torch.inference_mode():
            for record in validation:
                edges,target,_=labeler(record)
                if len(target):val_losses.append(loss_fn(model(tokens(record['sequence']),edges),target).item())
        row={'epoch':epoch,'mean_train_loss':sum(losses)/len(losses),'validation_mean_pair_f1':f1,'mean_validation_loss':sum(val_losses)/len(val_losses)};history.append(row)
        key=(f1,-row['mean_validation_loss'])
        if best is None or key>best:
            best=key;chosen=epoch;torch.save(model.state_dict(),run/'best_context_model.pt')
        with (run/'epochs.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        print(f'Context epoch {epoch}/{config["epochs"]}: loss {row["mean_train_loss"]:.4f}, reused validation F1 {f1:.4f}',flush=True)
    model.load_state_dict(torch.load(run/'best_context_model.pt',map_location='cpu',weights_only=True))
    return initial,model,{'history':history,'selected_epoch':chosen,'selected_validation_pair_f1':best[0],'train_positive_pairs':positive,'train_negative_pairs':negative,'train_only_positive_weight':weight,'excluded_train_contacts':sum(x[2] for x in labels),'excluded_validation_contacts':sum(labeler(r)[2] for r in validation),'parameters':sum(p.numel() for p in model.parameters()),'encoder_receptive_field_nt':1+6*sum(config['dilations']),'checkpoint_sha256':{name:digest((run/name).read_bytes()) for name in ('initial_context_model.pt','best_context_model.pt')}}
