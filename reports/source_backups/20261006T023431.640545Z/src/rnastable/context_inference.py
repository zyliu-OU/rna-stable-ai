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
from .reference_audit import require
from .sequences import read_fasta


def load_checkpoint(summary_path):
    import torch
    source_bytes=Path(summary_path).read_bytes();source=json.loads(source_bytes);run=Path(source['run_dir'])
    require(source.get('complete') is True,'source training incomplete')
    require(json.loads((run/'summary.json').read_text())==source,'source summary differs from retained run')
    require(digest((run/'manifest.json').read_bytes())==source['manifest_sha256'],'source manifest changed')
    manifest=json.loads((run/'manifest.json').read_text());config=manifest['config']
    if source.get('mode')=='development_validation_only':
        checkpoint=run/'best_context_model.pt';hashes=source['checkpoint_sha256'];require(source['config']==config,'source model config differs')
    elif source.get('mode')=='family_disjoint_comparative_context_trial':
        checkpoint=run/'model/best_context_model.pt';hashes=source['training']['checkpoint_sha256']
    else:raise ValueError('Expected a context development or context family-trial summary')
    require(config['dilations']==[1,2,4,8] and type(config['max_pair_span']) is int and 4<=config['max_pair_span']<=255,'invalid model span/context')
    for key,upper in [('embedding_dim',64),('channels',64),('pair_dim',64),('cpu_threads',2)]:
        require(type(config[key]) is int and 1<=config[key]<=upper,'invalid model dimension/thread count')
    require(digest(checkpoint.read_bytes())==hashes[checkpoint.name],'source checkpoint changed')
    torch.set_num_threads(config['cpu_threads']);model=make_context_model(config)
    model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True));model.eval()
    return source_bytes,config,checkpoint,model


def infer_fasta(root,summary_path,fasta_path):
    fasta_path=Path(fasta_path);input_bytes=fasta_path.read_bytes()
    with tempfile.TemporaryDirectory(prefix='rnastable-fasta-') as temporary:
        frozen=Path(temporary)/'input.fasta';frozen.write_bytes(input_bytes)
        records=[{'id':name,'sequence':seq} for name,seq in read_fasta(frozen)]
    if len({r['id'] for r in records})!=len(records):raise ValueError('Duplicate FASTA identifiers')
    if len(records)>10 or any(len(r['sequence'])>10000 for r in records) or sum(len(r['sequence']) for r in records)>20000:raise ValueError('Inference supports at most 10 records, 10000 nt each, 20000 nt total')
    source_bytes,config,checkpoint,model=load_checkpoint(summary_path)
    run=Path(root)/'results/context_inference_runs'/timestamp();run.mkdir(parents=True,exist_ok=False)
    (run/'input.fasta').write_bytes(input_bytes);(run/'source_summary.json').write_bytes(source_bytes)
    manifest={'schema_version':1,'run_dir':str(run.resolve()),'config':config,'source_summary_sha256':digest(source_bytes),'checkpoint':str(checkpoint),'checkpoint_sha256':digest(checkpoint.read_bytes()),'input_sha256':digest((run/'input.fasta').read_bytes()),'code_sha256':{str(Path(__file__).resolve()):digest(Path(__file__).read_bytes())},'policy':'Inference only, no reference labels or accuracy evaluation. Sequences conservatively recorded as test-start exposure before inference.'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    event=record_exposure(run,'test_started',records);rows=[]
    for record in records:
        print(f'Context inference: {record["id"]} ({len(record["sequence"])} nt)',flush=True)
        begin=time.monotonic();result=decode_band(record['sequence'],band_scores(model,record['sequence'],config['max_pair_span']),config['max_pair_span'])
        rows.append({**record,**result,'wall_seconds':time.monotonic()-begin})
    (run/'predictions.json').write_text(json.dumps(rows,indent=2)+'\n')
    (run/'predictions.dbn').write_text(''.join(f'>{r["id"]}\n{r["sequence"]}\n{r["structure"]}\n' for r in rows))
    summary={'complete':True,'run_dir':str(run.resolve()),'purpose':'checkpoint_inference_only','accuracy_evaluated':False,'records':len(rows),'config':config,'manifest_sha256':digest((run/'manifest.json').read_bytes()),'predictions_sha256':digest((run/'predictions.json').read_bytes()),'dbn_sha256':digest((run/'predictions.dbn').read_bytes()),'exposure_event':event,'limitations':['Fixed pair span excludes distant contacts.','Predicted scores are logits, not free energy or measured stability.','Input references and accuracy metrics are absent.']}
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


def audit_inference(summary_path):
    summary=json.loads(Path(summary_path).read_text());run=Path(summary['run_dir'])
    require(summary['complete'] is True and summary['purpose']=='checkpoint_inference_only' and summary['accuracy_evaluated'] is False,'inference identity differs')
    require(json.loads((run/'summary.json').read_text())==summary,'retained inference summary differs')
    for name,key in [('manifest.json','manifest_sha256'),('predictions.json','predictions_sha256'),('predictions.dbn','dbn_sha256')]:require(digest((run/name).read_bytes())==summary[key],'inference artifact changed: '+name)
    manifest=json.loads((run/'manifest.json').read_text());require(manifest['run_dir']==str(run) and manifest['config']==summary['config'],'manifest identity differs')
    require(digest((run/'input.fasta').read_bytes())==manifest['input_sha256'] and digest((run/'source_summary.json').read_bytes())==manifest['source_summary_sha256'],'frozen input or source changed')
    source_bytes,config,checkpoint,model=load_checkpoint(run/'source_summary.json')
    require(config==manifest['config'] and str(checkpoint)==manifest['checkpoint'] and digest(checkpoint.read_bytes())==manifest['checkpoint_sha256'],'checkpoint identity differs')
    records=[{'id':name,'sequence':seq} for name,seq in read_fasta(run/'input.fasta')];rows=json.loads((run/'predictions.json').read_text())
    require(len(records)==len(rows)==summary['records'],'inference inventory differs')
    from .exposures import read_exposure,exposure_records
    event=summary['exposure_event'];p=Path(event['path'])
    require(p.resolve().parent==(run/'exposures').resolve() and list((run/'exposures').glob('*.json'))==[p] and digest(p.read_bytes())==event['sha256'],'inference exposure event changed')
    data=read_exposure(p);require(data['stage']==event['stage']=='test_started' and data['records']==exposure_records(records,str(run)+' test_started'),'inference exposure records differ')
    import math
    for record,row in zip(records,rows):
        require(row['id']==record['id'] and row['sequence']==record['sequence'],'inference sequence binding differs')
        expected=decode_band(record['sequence'],band_scores(model,record['sequence'],config['max_pair_span']),config['max_pair_span'])
        require(all(row[k]==v for k,v in expected.items()),'checkpoint inference differs')
        require(type(row['wall_seconds']) in (int,float) and math.isfinite(row['wall_seconds']) and row['wall_seconds']>=0,'invalid inference timing')
    require((run/'predictions.dbn').read_text()==''.join(f'>{r["id"]}\n{r["sequence"]}\n{r["structure"]}\n' for r in rows),'DBN export differs')
    print(f'Context inference audit passed: {len(records)} exact sequence-bound predictions; exposure event and exports verified.')
    return summary
