"""Posthoc logit-penalty comparison on frozen, already exposed development checkpoints."""
import json
from pathlib import Path
from .context_inference import load_checkpoint
from .exact_sparse_pairs import decode_exact_sparse
from .exposures import record_exposure,read_exposure,exposure_records
from .global_sparse_pairs import sparse_candidates
from .native_journal import atomic_json
from .pair_penalty import penalize_candidates
from .reference import digest
from .reference_audit import require
from .scoring import structure_agreement

PENALTIES=(0,.5,1,2,4)


def source_group(record):
    if record.get('pdb_accession'):return 'PDB-derived annotation'
    if record.get('family_id'):return 'Rfam comparative'
    if 'CRW' in record.get('bpseq_member',''):return 'CRW comparative'
    return 'other development'


def evaluate(model,records,config):
    rows=[]
    for record in records:
        candidates=sparse_candidates(model,record['sequence'],config['top_k'],config['block_size'])
        for penalty in PENALTIES:
            adjusted=penalize_candidates(candidates,penalty);result=decode_exact_sparse(record['sequence'],adjusted['pairs'],adjusted['scores'])
            rows.append({'id':record['id'],'sequence_sha256':digest(record['sequence'].encode()),'group':source_group(record),'penalty':penalty,'structure':result['structure'],
                         'objective':result['objective'],'accepted_pairs':result['accepted_pairs'],'candidate_count':candidates['candidate_count'],'retained_after_penalty':adjusted.get('retained_after_penalty',candidates['candidate_count']),
                         **structure_agreement(result['structure'],record['structure'])})
    return rows


def aggregate_rows(rows):
    groups=['all',*sorted({row['group'] for row in rows})];aggregates=[]
    for penalty in PENALTIES:
        for group in groups:
            selected=[row for row in rows if row['penalty']==penalty and (group=='all' or row['group']==group)]
            aggregates.append({'group':group,'penalty':penalty,'records':len(selected),'mean_pair_f1':sum(row['pair_f1'] for row in selected)/len(selected),
                               'mean_predicted_pairs':sum(row['predicted_pairs'] for row in selected)/len(selected),'mean_reference_pairs':sum(row['reference_pairs'] for row in selected)/len(selected)})
    return aggregates


def run_component(run,source_path):
    run=Path(run);run.mkdir(parents=True,exist_ok=False);source_path=Path(source_path);source_bytes,config,checkpoint,model=load_checkpoint(source_path)
    source=json.loads(source_bytes);source_run=Path(source['run_dir']);validation_bytes=(source_run/'validation.json').read_bytes();records=json.loads(validation_bytes)['records']
    (run/'source_summary.json').write_bytes(source_bytes);(run/'validation.json').write_bytes(validation_bytes)
    event=record_exposure(run,'validation_started',records)
    manifest={'run_dir':str(run),'source_summary_sha256':digest(source_bytes),'checkpoint':str(checkpoint),'checkpoint_sha256':digest(checkpoint.read_bytes()),'validation_sha256':digest(validation_bytes),
              'config':config,'penalties':list(PENALTIES),'exposure_event':event,'source_search_seed':source['seed'],'head':source['head'],
              'policy':'Frozen checkpoint selected at zero penalty; posthoc nonnegative decoder penalties on the same exposed development validation. No fitting or fresh test.'}
    atomic_json(run/'manifest.json',manifest);rows=evaluate(model,records,config);atomic_json(run/'predictions.json',rows);aggregates=aggregate_rows(rows)
    baseline=next(row for row in aggregates if row['group']=='all' and row['penalty']==0)
    require(baseline['mean_pair_f1']==source['selected_validation_pair_f1'],'Zero-penalty source checkpoint did not replay')
    chosen=max((row for row in aggregates if row['group']=='all'),key=lambda row:(row['mean_pair_f1'],-row['penalty']))
    summary={'complete':True,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'model_fitted':False,'test_evaluated':False,'development_only':True,
             'predictions_sha256':digest((run/'predictions.json').read_bytes()),'aggregates':aggregates,'selected_penalty':chosen['penalty'],'selected_development_f1':chosen['mean_pair_f1'],
             'zero_penalty_development_f1':baseline['mean_pair_f1'],'source_epoch':source['selected_epoch'],'seed':source['seed'],'head':source['head']}
    atomic_json(run/'summary.json',summary);return summary


def audit_component(path):
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir']);manifest=json.loads((run/'manifest.json').read_text())
    require(summary['complete'] is True and summary['model_fitted'] is False and summary['test_evaluated'] is False and summary['development_only'] is True,'Penalty study scope differs')
    require(summary==json.loads((run/'summary.json').read_text()) and digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'],'Penalty component manifest differs')
    require(manifest['penalties']==list(PENALTIES) and digest((run/'validation.json').read_bytes())==manifest['validation_sha256'] and digest((run/'source_summary.json').read_bytes())==manifest['source_summary_sha256'],'Penalty snapshots/grid changed')
    source_bytes,config,checkpoint,model=load_checkpoint(run/'source_summary.json');source=json.loads(source_bytes);source_run=Path(source['run_dir']);records=json.loads((run/'validation.json').read_text())['records']
    require(config==manifest['config'] and str(checkpoint)==manifest['checkpoint'] and digest(checkpoint.read_bytes())==manifest['checkpoint_sha256'],'Penalty checkpoint differs')
    require((run/'validation.json').read_bytes()==(source_run/'validation.json').read_bytes() and summary['seed']==source['seed']==manifest['source_search_seed'] and summary['head']==source['head']==manifest['head'] and summary['source_epoch']==source['selected_epoch'],'Penalty source cohort/selection differs')
    event=manifest['exposure_event'];path=Path(event['path']);require(digest(path.read_bytes())==event['sha256'] and read_exposure(path)['records']==exposure_records(records,str(run)+' validation_started') and event['stage']=='validation_started','Penalty exposure differs')
    rows=evaluate(model,records,config);require(digest((run/'predictions.json').read_bytes())==summary['predictions_sha256'] and rows==json.loads((run/'predictions.json').read_text()),'Penalty candidate/decoder/metric replay differs')
    aggregates=aggregate_rows(rows);require(aggregates==summary['aggregates'],'Penalty group/denominator differs')
    baseline=next(row for row in aggregates if row['group']=='all' and row['penalty']==0);chosen=max((row for row in aggregates if row['group']=='all'),key=lambda row:(row['mean_pair_f1'],-row['penalty']))
    require(summary['zero_penalty_development_f1']==baseline['mean_pair_f1']==source['selected_validation_pair_f1'] and summary['selected_penalty']==chosen['penalty'] and summary['selected_development_f1']==chosen['mean_pair_f1'],'Penalty selection/tie policy differs')
    print(f"Penalty component audit passed: {summary['seed']}, {summary['head']}, {len(records)} reused records, {len(PENALTIES)} frozen-checkpoint penalties.")
    return summary
