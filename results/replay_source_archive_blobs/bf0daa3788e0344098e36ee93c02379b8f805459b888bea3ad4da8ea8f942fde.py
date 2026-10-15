"""Matched-seed development comparison of baseline, stack, and local-helix pair heads."""
import json
from pathlib import Path
from .context_training import train_context
from .exact_sparse_pairs import decode_exact_sparse
from .exposures import record_exposure,read_exposure,exposure_records
from .full_pair_supervision import full_supervision
from .global_sparse_pairs import make_global_model,sparse_candidates
from .helix_pairs import make_helix_model
from .stack_pairs import make_stack_model
from .native_journal import atomic_json
from .reference import digest,run_reference_evaluation
from .reference_audit import require,audit_reference
from .scoring import structure_agreement
from .structure_model import tokens

HEADS=('baseline','stack','helix')
FEATURES={'baseline':None,'stack':'adjacent_stackability','helix':'local_helix_context_v1'}
FACTORIES={'baseline':make_global_model,'stack':make_stack_model,'helix':make_helix_model}
METHODS={'baseline':('untrained_exact_sparse','trained_exact_sparse'),'stack':('untrained_stack_sparse','trained_stack_sparse'),'helix':('untrained_helix_sparse','trained_helix_sparse')}


def head_config(base,head,seed):
    if head not in HEADS or type(seed) is not int or not 0<=seed<2**32:raise ValueError('Invalid development head/seed')
    config={**base,'seed':seed};config.pop('pair_features',None)
    if FEATURES[head]:config['pair_features']=FEATURES[head]
    return config


def predictions(model,records,method,config):
    rows=[]
    for record in records:
        candidates=sparse_candidates(model,record['sequence'],config['top_k'],config['block_size'])
        result=decode_exact_sparse(record['sequence'],candidates['pairs'],candidates['scores'])
        rows.append({'id':record['id'],'sequence':record['sequence'],'method':method,'status':'ok','structure':result['structure']})
    return rows


def train_component(run):
    run=Path(run).resolve();manifest=json.loads((run/'manifest.json').read_text());parent=run.parents[1];plan=json.loads((parent/'manifest.json').read_text())
    require(manifest['study_manifest_sha256']==digest((parent/'manifest.json').read_bytes()),'Study binding changed')
    for name,expected in plan['code_sha256'].items():require(digest(Path(name).read_bytes())==expected,'Study execution source changed')
    for name,expected in plan['snapshot_sha256'].items():require(digest((parent/name).read_bytes())==expected,'Study inputs changed')
    head=manifest['head'];config=manifest['config'];require(config==head_config(plan['base_config'],head,manifest['seed']),'Study head config differs')
    for name in ('train','validation'):(run/(name+'.json')).write_bytes((parent/(name+'.json')).read_bytes())
    splits={name:json.loads((run/(name+'.json')).read_text())['records'] for name in ('train','validation')}
    events=[record_exposure(run,'training_started',splits['train']),record_exposure(run,'validation_started',splits['validation'])]
    initial,model,training=train_context(splits['train'],splits['validation'],config,run,model_factory=FACTORIES[head],labeler=lambda record:full_supervision(record,config['training_max_length']),predictor=lambda m,records,method:predictions(m,records,method,config))
    methods=METHODS[head];rows=predictions(initial,splits['validation'],methods[0],config)+predictions(model,splits['validation'],methods[1],config)
    atomic_json(run/'predictions.json',{'schema_version':1,'methods':list(methods),'records':rows});evaluation=run_reference_evaluation(run,run/'validation.json',run/'predictions.json')
    summary={'complete':True,'run_dir':str(run),'mode':config['mode'],'config':config,'head':head,'seed':manifest['seed'],'test_evaluated':False,'manifest_sha256':digest((run/'manifest.json').read_bytes()),
             'counts':{name:len(records) for name,records in splits.items()},**training,'predictions_sha256':digest((run/'predictions.json').read_bytes()),'exposure_events':events,'aggregates':evaluation['aggregates'],
             'limitations':['Same reused development cohort; matched seeds compare heads, not independent biological samples.','Validation checkpoint selection is development tuning; no fresh test or generalization claim.','All heads use full pair BCE, identical base initialization, optimizer and exact top-16 sparse decoding.','Local helix features use only nucleotide identities and offsets, not reference labels.']}
    atomic_json(run/'summary.json',summary);return summary


def audit_component(path):
    import torch
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir']);manifest=json.loads((run/'manifest.json').read_text());parent=run.parents[1];plan=json.loads((parent/'manifest.json').read_text());head=manifest['head'];config=manifest['config']
    require(summary['complete'] is True and summary['test_evaluated'] is False and summary==json.loads((run/'summary.json').read_text()),'Study component identity differs')
    require(digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'] and digest((parent/'manifest.json').read_bytes())==manifest['study_manifest_sha256'],'Study component manifest changed')
    require(summary['head']==head and summary['seed']==manifest['seed'] and config==summary['config']==head_config(plan['base_config'],head,manifest['seed']),'Study head/seed/config differs')
    splits={name:json.loads((run/(name+'.json')).read_text())['records'] for name in ('train','validation')}
    for name in ('train','validation'):require((run/(name+'.json')).read_bytes()==(parent/(name+'.json')).read_bytes(),'Study split differs')
    require(summary['counts']=={name:len(records) for name,records in splits.items()},'Study count differs')
    labels=[full_supervision(record,config['training_max_length']) for record in splits['train']];positive=sum(int(y.sum()) for _,y,_ in labels);negative=sum(len(y)-int(y.sum()) for _,y,_ in labels)
    require(summary['train_positive_pairs']==positive and summary['train_negative_pairs']==negative and summary['train_only_positive_weight']==(negative/positive)**config['positive_weight_exponent'],'Study supervision denominator differs')
    require(summary['excluded_train_contacts']==sum(row[2] for row in labels) and summary['excluded_validation_contacts']==sum(full_supervision(record,config['training_max_length'])[2] for record in splits['validation']),'Study unsupported contacts differ')
    events=summary['exposure_events'];require(len(events)==2 and set(Path(event['path']) for event in events)==set((run/'exposures').glob('*.json')),'Study exposure inventory differs')
    for event,name,stage in zip(events,('train','validation'),('training_started','validation_started')):
        path=Path(event['path']);require(digest(path.read_bytes())==event['sha256'] and read_exposure(path)['records']==exposure_records(splits[name],str(run)+' '+stage) and event['stage']==stage,'Study exposure changed')
    history=summary['history'];require(history==[json.loads(line) for line in (run/'epochs.jsonl').read_text().splitlines()] and [row['epoch'] for row in history]==list(range(1,config['epochs']+1)),'Study epoch history differs')
    chosen=max(history,key=lambda row:(row['validation_mean_pair_f1'],-row['mean_validation_loss']));require(chosen['epoch']==summary['selected_epoch'] and chosen['validation_mean_pair_f1']==summary['selected_validation_pair_f1'],'Study checkpoint selection differs')
    torch.set_num_threads(config['cpu_threads']);replayed=[]
    for filename,method in zip(('initial_context_model.pt','best_context_model.pt'),METHODS[head]):
        checkpoint=run/filename;require(digest(checkpoint.read_bytes())==summary['checkpoint_sha256'][filename],'Study checkpoint changed')
        torch.manual_seed(config['seed']);model=FACTORIES[head](config);state=torch.load(checkpoint,map_location='cpu',weights_only=True)
        if filename.startswith('initial'):require(all(torch.equal(value,state[key]) for key,value in model.state_dict().items()),'Study initialization differs')
        model.load_state_dict(state);require(sum(parameter.numel() for parameter in model.parameters())==summary['parameters'],'Study model size differs');rows=predictions(model,splits['validation'],method,config);replayed+=rows
        if filename.startswith('best'):
            f1=sum(structure_agreement(row['structure'],record['structure'])['pair_f1'] for row,record in zip(rows,splits['validation']))/len(rows);require(f1==summary['selected_validation_pair_f1'],'Study selected validation score differs')
            model.eval();losses=[];loss_fn=torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(summary['train_only_positive_weight']))
            with torch.inference_mode():
                for record in splits['validation']:
                    edges,y,_=full_supervision(record,config['training_max_length'])
                    if len(y):losses.append(loss_fn(model(tokens(record['sequence']),edges),y).item())
            require(sum(losses)/len(losses)==chosen['mean_validation_loss'],'Study validation BCE differs')
    require(digest((run/'predictions.json').read_bytes())==summary['predictions_sha256'] and json.loads((run/'predictions.json').read_text())['records']==replayed,'Study checkpoint prediction replay differs')
    evaluation_path=run/'results/reference_evaluation_summary.json';audit_reference(evaluation_path)
    evaluation=json.loads(evaluation_path.read_text())
    require(evaluation['aggregates']==summary['aggregates'],'Study reference aggregate differs')
    for key,name in [('references','validation.json'),('predictions','predictions.json')]:require(Path(evaluation['sources'][key]['path']).read_bytes()==(run/name).read_bytes(),'Study reference export binding differs')
    print(f"Pair-head component audit passed: seed {summary['seed']}, {head}, {summary['counts']}, full BCE and exact development checkpoint replay.")
    return summary


def paired_initialization(components):
    import torch
    if not components:return False
    complete=True
    for seed in sorted({summary['seed'] for summary in components}):
        same=[s for s in components if s['seed']==seed];states={s['head']:torch.load(Path(s['run_dir'])/'initial_context_model.pt',map_location='cpu',weights_only=True) for s in same}
        if set(states)!=set(HEADS):complete=False
        if 'baseline' not in states:continue
        for head,state in states.items():
            if head=='baseline':continue
            require(all(torch.equal(value,state['base.'+key]) for key,value in states['baseline'].items()),'Matched-seed base initialization differs')
            name='stack_weights.weight' if head=='stack' else 'helix_weights.weight';require(bool((state[name]==0).all()),'Feature head initialization is not zero')
    return complete
