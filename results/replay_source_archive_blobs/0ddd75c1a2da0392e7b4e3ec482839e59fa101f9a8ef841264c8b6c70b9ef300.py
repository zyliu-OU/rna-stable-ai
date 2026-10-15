"""Development-only importance-weighted sampled training and artifact replay."""
import json
from pathlib import Path
from .artifacts import timestamp,publish
from .context_training import train_context
from .exposures import record_exposure,read_exposure,exposure_records
from .full_pair_supervision import full_supervision
from .helix_pairs import make_helix_model,FEATURE_NAMES
from .native_journal import atomic_json
from .population_sampling import population_supervision,population_bce
from .reference import digest,run_reference_evaluation
from .reference_audit import require,audit_reference
from .scoring import structure_agreement
from .structure_model import tokens

SAMPLING_POLICY='full_population_importance_weighted_fixed_draw_v1'


def samples_for(records,settings):
    require(set(settings)=={'seed','negatives_per_positive','minimum_negatives','max_length','policy'} and settings['policy']==SAMPLING_POLICY,'Invalid population sampling policy')
    return [population_supervision(record,**{k:v for k,v in settings.items() if k!='policy'}) for record in records]


def fit_component(run,source_bytes,source,snapshots,splits,config,predictor,code_paths):
    import numpy as np
    run=Path(run);run.mkdir(parents=True,exist_ok=False)
    require({k:v for k,v in config.items() if k!='population_sampling'}=={**source['config'],'pair_features':'local_helix_context_v1'},'Population study changes other training settings')
    samples=samples_for(splits['train'],config['population_sampling']);metadata={record['id']:item[1] for record,item in zip(splits['train'],samples)};cached={record['id']:item[0] for record,item in zip(splits['train'],samples)}
    (run/'source_summary.json').write_bytes(source_bytes)
    for name,data in snapshots.items():(run/(name+'.json')).write_bytes(data)
    arrays={}
    for index,(sample,_) in enumerate(samples):arrays['indices_'+str(index)]=sample[0].numpy();arrays['labels_'+str(index)]=sample[1].numpy()
    np.savez_compressed(run/'training_samples.npz',**arrays);atomic_json(run/'sampling_inventory.json',metadata)
    manifest={'run_dir':str(run),'config':config,'source_summary_sha256':digest(source_bytes),'snapshot_sha256':{name:digest((run/name).read_bytes()) for name in ('train.json','validation.json','training_samples.npz','sampling_inventory.json')},'code_sha256':{str(p):digest(Path(p).read_bytes()) for p in code_paths},'policy':'Same frozen train/validation records and model seed. Uniform training negatives, all positives, importance weighted full-population BCE. Fixed draw reused across epochs. Full validation labels and training population positive weight. No test.'};atomic_json(run/'manifest.json',manifest)
    events=[record_exposure(run,'training_started',splits['train']),record_exposure(run,'validation_started',splits['validation'])]
    positive=sum(m['population_positive'] for m in metadata.values());negative=sum(m['population_negative'] for m in metadata.values());weight=(negative/positive)**config['positive_weight_exponent']
    initial,model,training=train_context(splits['train'],splits['validation'],config,run,model_factory=make_helix_model,labeler=lambda r:cached[r['id']] if r['id'] in cached else full_supervision(r,config['training_max_length']),predictor=lambda m,rs,method:predictor(m,rs,method,config),training_loss_fn=lambda logits,edges,y,record:population_bce(logits,y,metadata[record['id']],weight),train_population_counts=metadata)
    methods=['untrained_population_helix_sparse','trained_population_helix_sparse'];pred=predictor(initial,splits['validation'],methods[0],config)+predictor(model,splits['validation'],methods[1],config)
    atomic_json(run/'predictions.json',{'schema_version':1,'methods':methods,'records':pred});evaluation=run_reference_evaluation(run,run/'validation.json',run/'predictions.json')
    summary={'complete':True,'mode':config['mode'],'test_evaluated':False,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'config':config,'counts':source['counts'],'feature_names':list(FEATURE_NAMES),'helix_weights':model.helix_weights.weight.detach().tolist()[0],**training,'exposure_events':events,'predictions_sha256':digest((run/'predictions.json').read_bytes()),'aggregates':evaluation['aggregates'],'sample_tensor_bytes':sum(m['retained_tensor_bytes'] for m in metadata.values()),'limitations':['Fixed sampling draw reused across epochs; unbiased loss/gradient over random draws does not make each fitted trajectory equivalent to full training.','Existing development labels and model seed reused. Sampling seeds are not independent biological replicates.','Full validation labels and exact sparse decoder remain bounded to1024nt. Long synthetic sampling is a resource demonstration, not long-RNA accuracy.','Comparative annotations are not new experimental measurements; family independence and generalization remain unresolved.']};atomic_json(run/'summary.json',summary);return summary


def audit_component(path,frozen_inputs,predictor):
    import numpy as np
    import torch
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir']);config=summary['config'];require(summary.get('complete') is True and summary.get('test_evaluated') is False,'Expected completed development-only population component')
    require(summary==json.loads((run/'summary.json').read_text()),'Retained summary differs');require(digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'],'Manifest changed');manifest=json.loads((run/'manifest.json').read_text());require(manifest['run_dir']==str(run) and manifest['config']==config,'Manifest identity differs')
    for name,sha in manifest['snapshot_sha256'].items():require(digest((run/name).read_bytes())==sha,'Snapshot changed: '+name)
    data,source,snapshots,splits=frozen_inputs(run/'source_summary.json');require(digest(data)==manifest['source_summary_sha256'],'Source binding differs');require(summary['counts']==source['counts'],'Split counts differ');require({k:v for k,v in config.items() if k!='population_sampling'}=={**source['config'],'pair_features':'local_helix_context_v1'},'Other training settings differ')
    for name,data in snapshots.items():require((run/(name+'.json')).read_bytes()==data,'Frozen split differs')
    samples=samples_for(splits['train'],config['population_sampling']);inventory={r['id']:m for r,(_,m) in zip(splits['train'],samples)};require(inventory==json.loads((run/'sampling_inventory.json').read_text()),'Sampling inventory differs')
    with np.load(run/'training_samples.npz',allow_pickle=False) as exported:
        expected={key+str(i) for i in range(len(samples)) for key in ('indices_','labels_')};require(set(exported.files)==expected,'Sample tensor inventory differs')
        for i,((edges,y,_),_) in enumerate(samples):require(np.array_equal(exported['indices_'+str(i)],edges.numpy()) and np.array_equal(exported['labels_'+str(i)],y.numpy()),'Sample tensors differ')
    positive=sum(m['population_positive'] for m in inventory.values());negative=sum(m['population_negative'] for m in inventory.values());weight=(negative/positive)**config['positive_weight_exponent'];require(summary['train_population_positive_pairs']==positive and summary['train_population_negative_pairs']==negative and summary['train_only_positive_weight']==weight,'Full population counts/weight differ');require(summary['train_positive_pairs']==positive and summary['train_negative_pairs']==sum(m['sampled_negative'] for m in inventory.values()) and summary['sample_tensor_bytes']==sum(m['retained_tensor_bytes'] for m in inventory.values()),'Retained sample totals differ');require(summary['excluded_train_contacts']==sum(m['excluded_contacts'] for m in inventory.values()),'Excluded training contacts differ');require(summary['excluded_validation_contacts']==sum(full_supervision(r,config['training_max_length'])[2] for r in splits['validation']),'Excluded validation contacts differ')
    events=summary['exposure_events'];require([e['stage'] for e in events]==['training_started','validation_started'],'Exposure stages differ');require({Path(e['path']).resolve() for e in events}=={p.resolve() for p in (run/'exposures').glob('*.json')},'Exposure inventory differs')
    for event,name in zip(events,('train','validation')):
        path=Path(event['path']);require(path.resolve().parent==(run/'exposures').resolve() and digest(path.read_bytes())==event['sha256'],'Exposure binding differs');event_data=read_exposure(path);require(event_data['stage']==event['stage'] and event_data['records']==exposure_records(splits[name],str(run)+' '+event['stage']),'Exposure records differ')
    history=summary['history'];require(history==[json.loads(line) for line in (run/'epochs.jsonl').read_text().splitlines()],'Epoch ledger differs');require([row['epoch'] for row in history]==list(range(1,config['epochs']+1)),'Epoch inventory differs');best=max(history,key=lambda row:(row['validation_mean_pair_f1'],-row['mean_validation_loss']));require(summary['selected_epoch']==best['epoch'],'Checkpoint selection differs');require(summary['feature_names']==list(FEATURE_NAMES),'Feature inventory differs')
    torch.set_num_threads(config['cpu_threads']);pred=[]
    for filename,method in [('initial_context_model.pt','untrained_population_helix_sparse'),('best_context_model.pt','trained_population_helix_sparse')]:
        path=run/filename;require(digest(path.read_bytes())==summary['checkpoint_sha256'][filename],'Checkpoint changed');torch.manual_seed(config['seed']);model=make_helix_model(config);state=torch.load(path,map_location='cpu',weights_only=True)
        if filename.startswith('initial'):require(all(torch.equal(value,state[key]) for key,value in model.state_dict().items()),'Initialization differs')
        model.load_state_dict(state);rows=predictor(model,splits['validation'],method,config);pred+=rows;require(sum(p.numel() for p in model.parameters())==summary['parameters'],'Parameter count differs')
        if filename.startswith('best'):
            require(model.helix_weights.weight.detach().tolist()[0]==summary['helix_weights'],'Learned weights differ');score=sum(structure_agreement(p['structure'],r['structure'])['pair_f1'] for p,r in zip(rows,splits['validation']))/len(rows);require(score==summary['selected_validation_pair_f1']==best['validation_mean_pair_f1'],'Selected F1 differs');losses=[];loss_fn=torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(weight));model.eval()
            with torch.inference_mode():
                for record in splits['validation']:
                    edges,y,_=full_supervision(record,config['training_max_length'])
                    if len(y):losses.append(loss_fn(model(tokens(record['sequence']),edges),y).item())
            require(sum(losses)/len(losses)==best['mean_validation_loss'],'Full validation loss differs')
    require(digest((run/'predictions.json').read_bytes())==summary['predictions_sha256'] and json.loads((run/'predictions.json').read_text())['records']==pred,'Prediction replay differs');evaluation_path=run/'results/reference_evaluation_summary.json';audit_reference(evaluation_path);evaluation=json.loads(evaluation_path.read_text());require(evaluation['aggregates']==summary['aggregates'],'Reference metrics differ')
    for key,name in [('references','validation.json'),('predictions','predictions.json')]:require(Path(evaluation['sources'][key]['path']).read_bytes()==(run/name).read_bytes(),'Reference source differs')
    return summary
