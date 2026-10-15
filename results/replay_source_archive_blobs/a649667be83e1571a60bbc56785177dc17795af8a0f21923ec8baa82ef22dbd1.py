"""Checkpoint-bound FASTA inference with frozen inputs and conservative exposure events."""
import json
from pathlib import Path
import time
import tempfile
from .artifacts import timestamp
from .banded_pairs import band_scores,decode_band
from .context_pairs import make_context_model
from .exposures import record_exposure
from .reference import digest
from .pair_penalty import validate_pair_penalty,penalize_candidates
from .reference_audit import require
from .sequences import read_fasta

DECODERS=('source','exact_sparse','greedy','refined')
REFINEMENT_OVERRIDE={'passes':2,'max_remove':2,'group_cap':8,'include_subsets':True}


def effective_decoder(config,decoder):
    if decoder not in DECODERS:raise ValueError('Unknown inference decoder')
    return config.get('inference_decoder','source') if decoder=='source' else decoder


def validate_inference_plan(records,config,decoder):
    actual=effective_decoder(config,decoder)
    if len({r['id'] for r in records})!=len(records):raise ValueError('Duplicate FASTA identifiers')
    if not records or len(records)>10 or any(len(r['sequence'])>10000 for r in records) or sum(len(r['sequence']) for r in records)>20000:raise ValueError('Inference supports at most10 records,10000 nt each,20000 nt total')
    if actual!='source' and config['mode'] not in ('global_sparse_development_only','long_comparative_development_only'):raise ValueError('Sparse decoder override requires a global sparse checkpoint')
    if actual=='exact_sparse' and any(len(r['sequence'])>1024 for r in records):raise ValueError('Exact sparse inference is bounded to1024 nt')


def load_checkpoint(summary_path):
    import torch
    source_bytes=Path(summary_path).read_bytes();source=json.loads(source_bytes);run=Path(source['run_dir'])
    require(source.get('complete') is True,'source training incomplete')
    require(json.loads((run/'summary.json').read_text())==source,'source summary differs from retained run')
    require(digest((run/'manifest.json').read_bytes())==source['manifest_sha256'],'source manifest changed')
    manifest=json.loads((run/'manifest.json').read_text());config=manifest['config']
    source_mode=source.get('mode')
    global_mode=source_mode in ('global_sparse_development_only','long_comparative_development_only')
    if source_mode=='development_validation_only' or global_mode:
        checkpoint=run/'best_context_model.pt';hashes=source['checkpoint_sha256'];require(source['config']==config,'source model config differs')
    elif source.get('mode')=='family_disjoint_comparative_context_trial':
        checkpoint=run/'model/best_context_model.pt';hashes=source['training']['checkpoint_sha256']
    else:raise ValueError('Expected a supported development or context family-trial summary')
    require(config['dilations']==[1,2,4,8],'invalid model context')
    if global_mode:
        require(config['mode']==source_mode,'global model mode differs')
        for key,upper in [('top_k',64),('block_size',128)]:require(type(config[key]) is int and 1<=config[key]<=upper,'invalid sparse inference setting')
        if 'inference_decoder' in config:require(config['inference_decoder']=='exact_sparse','invalid frozen inference decoder')
        if 'pair_features' in config:require(config.get('inference_decoder')=='exact_sparse' and config['pair_features'] in ('adjacent_stackability','local_helix_context_v1'),'invalid frozen pair features')
        if 'structured_loss' in config:require(config.get('inference_decoder')=='exact_sparse' and config['structured_loss']=={'top_k':16,'margin':1.0,'bce_coefficient':.1,'validation_loss':'full_weighted_bce','normalizer':'supported_gold_count'},'invalid frozen structured objective')
        if 'refinement' in config:require(config['refinement']=={'passes':2,'max_remove':2,'group_cap':8,'include_subsets':True},'invalid frozen refinement settings')
    else:require(type(config['max_pair_span']) is int and 4<=config['max_pair_span']<=255,'invalid model span')
    for key,upper in [('embedding_dim',64),('channels',64),('pair_dim',64),('cpu_threads',2)]:
        require(type(config[key]) is int and 1<=config[key]<=upper,'invalid model dimension/thread count')
    require(digest(checkpoint.read_bytes())==hashes[checkpoint.name],'source checkpoint changed')
    torch.set_num_threads(config['cpu_threads'])
    if global_mode:
        from .global_sparse_pairs import make_global_model
        if config.get('pair_features')=='adjacent_stackability':
            from .stack_pairs import make_stack_model
            model=make_stack_model(config)
        elif config.get('pair_features')=='local_helix_context_v1':
            from .helix_pairs import make_helix_model
            model=make_helix_model(config)
        else:model=make_global_model(config)
    else:model=make_context_model(config)
    model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True));model.eval()
    return source_bytes,config,checkpoint,model


def method_name(config,decoder="source"):
    if decoder in ('greedy','refined'):return method_name(config)+'_'+decoder
    if decoder in ("source","exact_sparse") and config.get("inference_decoder")=="exact_sparse":
        if config.get("pair_features")=="adjacent_stackability":return "trained_stack_sparse"
        if config.get("pair_features")=="local_helix_context_v1":return "trained_helix_sparse"
        return "trained_structured_sparse" if "structured_loss" in config else "trained_exact_sparse"
    if decoder=="exact_sparse":return method_name(config)+"_exact_sparse"
    if decoder!="source":raise ValueError("Unknown inference decoder")
    if config['mode']=='global_sparse_development_only':return 'trained_global_sparse'
    if config['mode']=='long_comparative_development_only':return 'trained_sampled_sparse' if 'sampling' in config else 'trained_expanded_sparse'
    return 'trained_context'


def decode_loaded(model,sequence,config,decoder="source",pair_penalty=0):
    pair_penalty=validate_pair_penalty(pair_penalty)
    decoder=effective_decoder(config,decoder)
    if decoder=="exact_sparse" and len(sequence)>1024:raise ValueError("Exact sparse inference is bounded to1024 nt")
    if decoder!='source' and config["mode"] not in ("global_sparse_development_only","long_comparative_development_only"):raise ValueError("Sparse decoder override requires a global sparse checkpoint")
    if config['mode'] in ('global_sparse_development_only','long_comparative_development_only'):
        from .global_sparse_pairs import sparse_candidates,decode_sparse
        from .sparse_refinement import refine_sparse
        candidates=penalize_candidates(sparse_candidates(model,sequence,config['top_k'],config['block_size']),pair_penalty)
        if decoder=='exact_sparse':
            from .exact_sparse_pairs import decode_exact_sparse
            decoded=decode_exact_sparse(sequence,candidates['pairs'],candidates['scores'])
        elif decoder=='greedy':decoded=decode_sparse(sequence,candidates['pairs'],candidates['scores'])
        elif decoder=='refined':decoded=refine_sparse(sequence,candidates['pairs'],candidates['scores'],**REFINEMENT_OVERRIDE)
        elif 'refinement' in config:decoded=refine_sparse(sequence,candidates['pairs'],candidates['scores'],**config['refinement'])
        else:decoded=decode_sparse(sequence,candidates['pairs'],candidates['scores'])
        return {**decoded,**{key:value for key,value in candidates.items() if key not in ('pairs','scores','interpretation')}}
    if pair_penalty:raise ValueError('Pair penalty requires a global sparse checkpoint')
    return decode_band(sequence,band_scores(model,sequence,config['max_pair_span']),config['max_pair_span'])


def infer_fasta(root,summary_path,fasta_path,decoder="source",pair_penalty=0):
    pair_penalty=validate_pair_penalty(pair_penalty)
    if decoder not in DECODERS:raise ValueError("Unknown inference decoder")
    fasta_path=Path(fasta_path);input_bytes=fasta_path.read_bytes()
    with tempfile.TemporaryDirectory(prefix='rnastable-fasta-') as temporary:
        frozen=Path(temporary)/'input.fasta';frozen.write_bytes(input_bytes)
        records=[{'id':name,'sequence':seq} for name,seq in read_fasta(frozen)]
    if len({r['id'] for r in records})!=len(records):raise ValueError('Duplicate FASTA identifiers')
    if len(records)>10 or any(len(r['sequence'])>10000 for r in records) or sum(len(r['sequence']) for r in records)>20000:raise ValueError('Inference supports at most 10 records, 10000 nt each, 20000 nt total')
    source_bytes,config,checkpoint,model=load_checkpoint(summary_path)
    validate_inference_plan(records,config,decoder)
    if pair_penalty and config['mode'] not in ('global_sparse_development_only','long_comparative_development_only'):raise ValueError('Pair penalty requires a global sparse checkpoint')
    run=Path(root)/'results/context_inference_runs'/timestamp();run.mkdir(parents=True,exist_ok=False)
    (run/'input.fasta').write_bytes(input_bytes);(run/'source_summary.json').write_bytes(source_bytes)
    manifest={'schema_version':1,'run_dir':str(run.resolve()),'config':config,'method':method_name(config,decoder),'source_summary_sha256':digest(source_bytes),'checkpoint':str(checkpoint),'checkpoint_sha256':digest(checkpoint.read_bytes()),'input_sha256':digest((run/'input.fasta').read_bytes()),'code_sha256':{str(p.resolve()):digest(p.read_bytes()) for p in (Path(__file__),*[Path(__file__).parent/name for name in ('context_pairs.py','banded_pairs.py','exact_sparse_pairs.py','stack_pairs.py','helix_pairs.py','pair_penalty.py','global_sparse_pairs.py','sparse_refinement.py','exposures.py','sequences.py','reference.py')])},'policy':'Inference only, no reference labels or accuracy evaluation. Sequences conservatively recorded as test-start exposure before inference.'}
    if pair_penalty:manifest['candidate_pair_penalty']=pair_penalty
    if decoder!='source':manifest['decoder_override']=decoder
    if decoder=='refined':manifest['decoder_settings']=dict(REFINEMENT_OVERRIDE)
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    event=record_exposure(run,'test_started',records);rows=[]
    for record in records:
        print(f'Context inference: {record["id"]} ({len(record["sequence"])} nt)',flush=True)
        begin=time.monotonic();result=decode_loaded(model,record['sequence'],config,decoder,pair_penalty)
        rows.append({**record,**result,'wall_seconds':time.monotonic()-begin})
    (run/'predictions.json').write_text(json.dumps(rows,indent=2)+'\n')
    exported={'schema_version':1,'methods':[method_name(config,decoder)],'records':[{'id':r['id'],'sequence':r['sequence'],'structure':r['structure'],'method':method_name(config,decoder),'status':'ok'} for r in rows]}
    (run/'reference_predictions.json').write_text(json.dumps(exported,indent=2)+'\n')
    (run/'predictions.dbn').write_text(''.join(f'>{r["id"]}\n{r["sequence"]}\n{r["structure"]}\n' for r in rows))
    summary={'complete':True,'run_dir':str(run.resolve()),'purpose':'checkpoint_inference_only','accuracy_evaluated':False,'records':len(rows),'config':config,'manifest_sha256':digest((run/'manifest.json').read_bytes()),'predictions_sha256':digest((run/'predictions.json').read_bytes()),'dbn_sha256':digest((run/'predictions.dbn').read_bytes()),'reference_predictions_sha256':digest((run/'reference_predictions.json').read_bytes()),'exposure_event':event,'limitations':[('Sparse global decoder is approximate; distant-contact accuracy is unvalidated.' if config['mode'] in ('global_sparse_development_only','long_comparative_development_only') else 'Fixed pair span excludes distant contacts.'),'Predicted scores are logits, not free energy or measured stability.','Input references and accuracy metrics are absent.']}
    if pair_penalty:
        summary['candidate_pair_penalty']=pair_penalty
        summary['limitations'].append('Explicit logit penalty is a decoder control, not native free energy or an accuracy claim.')
    if decoder!='source':
        summary['decoder_override']=decoder
    if decoder=='refined':summary['decoder_settings']=dict(REFINEMENT_OVERRIDE)
    if effective_decoder(config,decoder)=='exact_sparse':
        summary['limitations'][0]='Exact maximum logit objective over retained sparse candidates only; inference capped at1024 nt and is not maximum reference agreement.'
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


def audit_inference(summary_path):
    summary=json.loads(Path(summary_path).read_text());run=Path(summary['run_dir'])
    require(summary['complete'] is True and summary['purpose']=='checkpoint_inference_only' and summary['accuracy_evaluated'] is False,'inference identity differs')
    require(json.loads((run/'summary.json').read_text())==summary,'retained inference summary differs')
    for name,key in [('manifest.json','manifest_sha256'),('predictions.json','predictions_sha256'),('predictions.dbn','dbn_sha256'),*([('reference_predictions.json','reference_predictions_sha256')] if 'reference_predictions_sha256' in summary else [])]:require(digest((run/name).read_bytes())==summary[key],'inference artifact changed: '+name)
    manifest=json.loads((run/'manifest.json').read_text());require(manifest['run_dir']==str(run) and manifest['config']==summary['config'],'manifest identity differs')
    require(digest((run/'input.fasta').read_bytes())==manifest['input_sha256'] and digest((run/'source_summary.json').read_bytes())==manifest['source_summary_sha256'],'frozen input or source changed')
    decoder=manifest.get('decoder_override','source');require(decoder==summary.get('decoder_override','source') and decoder in DECODERS,'Decoder identity differs')
    pair_penalty=validate_pair_penalty(manifest.get('candidate_pair_penalty',0));require(pair_penalty==summary.get('candidate_pair_penalty',0),'Pair penalty identity differs')
    expected_settings=REFINEMENT_OVERRIDE if decoder=='refined' else None
    require(manifest.get('decoder_settings')==summary.get('decoder_settings')==expected_settings,'Decoder settings differ')
    source_bytes,config,checkpoint,model=load_checkpoint(run/'source_summary.json')
    require('method' not in manifest or manifest['method']==method_name(config,decoder),'Inference method differs')
    require(config==manifest['config'] and str(checkpoint)==manifest['checkpoint'] and digest(checkpoint.read_bytes())==manifest['checkpoint_sha256'],'checkpoint identity differs')
    records=[{'id':name,'sequence':seq} for name,seq in read_fasta(run/'input.fasta')];rows=json.loads((run/'predictions.json').read_text())
    validate_inference_plan(records,config,decoder)
    require(len(records)==len(rows)==summary['records'],'inference inventory differs')
    from .exposures import read_exposure,exposure_records
    event=summary['exposure_event'];p=Path(event['path'])
    require(p.resolve().parent==(run/'exposures').resolve() and list((run/'exposures').glob('*.json'))==[p] and digest(p.read_bytes())==event['sha256'],'inference exposure event changed')
    data=read_exposure(p);require(data['stage']==event['stage']=='test_started' and data['records']==exposure_records(records,str(run)+' test_started'),'inference exposure records differ')
    import math
    for record,row in zip(records,rows):
        require(row['id']==record['id'] and row['sequence']==record['sequence'],'inference sequence binding differs')
        expected=decode_loaded(model,record['sequence'],config,decoder,pair_penalty)
        require(all(row[k]==v for k,v in expected.items()),'checkpoint inference differs')
        require(type(row['wall_seconds']) in (int,float) and math.isfinite(row['wall_seconds']) and row['wall_seconds']>=0,'invalid inference timing')
    require((run/'predictions.dbn').read_text()==''.join(f'>{r["id"]}\n{r["sequence"]}\n{r["structure"]}\n' for r in rows),'DBN export differs')
    if 'reference_predictions_sha256' in summary:
        exported={'schema_version':1,'methods':[method_name(config,decoder)],'records':[{'id':r['id'],'sequence':r['sequence'],'structure':r['structure'],'method':method_name(config,decoder),'status':'ok'} for r in rows]}
        require(json.loads((run/'reference_predictions.json').read_text())==exported,'reference-prediction export differs')
    print(f'Context inference audit passed: {len(records)} exact sequence-bound predictions; exposure event and exports verified.')
    return summary
