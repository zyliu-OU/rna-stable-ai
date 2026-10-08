#!/usr/bin/env python3
"""Train a fresh context model on Rfam development families and evaluate RF00017 once."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import publish,timestamp
from rnastable.context_training import train_context,predictions
from rnastable.context_pairs import band_supervision
from rnastable.exposures import collect_known_exposures,record_exposure
from rnastable.family_plan import plan_families,save_family_plan
from rnastable.folding import fold_sequence
from rnastable.reference import digest,run_reference_evaluation
from rnastable.rfam_data import cohort_inputs,load_rfam_candidates,select_cohort


def prepare_trial():
    source=ROOT/'results/family_trial_runs/20261006T020448.519769Z/family_plan/summary.json'
    old=json.loads(source.read_text())
    imported_config={'min_length':20,'max_length':1024,'max_records_per_family':24,'families':{'train':[],'validation':[],'test':['RF00017']}}
    exposed=collect_known_exposures(ROOT);candidates,imported=load_rfam_candidates(ROOT/'external/EternaFold',imported_config)
    test,excluded=select_cohort(candidates,imported_config,exposed);imported['selection_exclusions']=excluded
    families={'train':['RF00001'],'validation':['RF00169'],'test':['RF00017']}
    refs,assignments,plan=cohort_inputs(old['splits']['train']+old['splits']['validation']+test,{'families':families})
    planned=plan_families(refs,assignments,plan,exposed)
    config=json.loads((ROOT/'configs/context_development_balanced.json').read_text());config['mode']='family_disjoint_comparative_trial'
    return refs,assignments,plan,exposed,planned,imported,imported_config,config,source


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    try:refs,assignments,families,exposed,planned,imported,import_config,config,source=prepare_trial()
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.exit(2,f'Context family trial rejected: {exc}\n')
    print(json.dumps({'families':families,'counts':planned['counts'],'prior_exposures':len(exposed)},indent=2),flush=True)
    if args.dry_run:return
    run=ROOT/'results/context_family_trial_runs'/timestamp();run.mkdir(parents=True)
    inputs=run/'inputs';inputs.mkdir()
    for name,data in [('references.json',refs),('assignments.json',assignments),('plan.json',families),('exposure.json',exposed)]:(inputs/name).write_text(json.dumps(data,indent=2)+'\n')
    frozen=save_family_plan(run/'family_plan',*[inputs/name for name in ('references.json','assignments.json','plan.json','exposure.json')])
    (run/'import.json').write_text(json.dumps(imported,indent=2)+'\n')
    (run/'source_development_families.json').write_bytes(source.read_bytes())
    selection=ROOT/'results/context_development_comparison_summary.json';selected=json.loads(selection.read_text())
    selected_source=Path(selected['selected_run_dir'])/'summary.json';selected_training=json.loads(selected_source.read_text())
    require_config={**config,'mode':'development_validation_only'}
    if require_config!=selected_training['config']:raise ValueError('Trial configuration does not match frozen development selection')
    (run/'development_selection.json').write_bytes(selection.read_bytes())
    paths=[Path(__file__),*[ROOT/'src/rnastable'/p for p in ('context_training.py','context_pairs.py','banded_pairs.py','exposures.py','rfam_data.py','family_plan.py','reference.py','scoring.py','folding.py')]]
    folding={'temperature_c':37,'beam_size':100,'timeout_seconds':30,'memory_limit_gib':4}
    manifest={'schema_version':1,'run_dir':str(run),'config':config,'folding':folding,'import_config':import_config,'prior_development_source':str(source),'prior_development_source_sha256':digest(source.read_bytes()),'family_plan_sha256':digest((run/'family_plan/summary.json').read_bytes()),'import_sha256':digest((run/'import.json').read_bytes()),'selection_sha256':digest((run/'development_selection.json').read_bytes()),'selected_development_summary':str(selected_source),'selected_development_summary_sha256':digest(selected_source.read_bytes()),'code_sha256':{str(p):digest(p.read_bytes()) for p in paths},'methods':['trained_context','untrained_context','all_unpaired','ViennaRNA','LinearFold'],'policy':'Fresh random model. Existing RF00001/RF00169 development families only. New RF00017 test exposure recorded before inference. Processed comparative references, not direct experimental measurements.'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(f'Frozen context family trial: {run}',flush=True)
    splits=frozen['splits'];events=[record_exposure(run,'training_started',splits['train']),record_exposure(run,'validation_started',splits['validation'])]
    model_dir=run/'model';model_dir.mkdir();initial,model,training=train_context(splits['train'],splits['validation'],config,model_dir)
    (model_dir/'training.json').write_text(json.dumps(training,indent=2)+'\n')
    events.append(record_exposure(run,'test_started',splits['test']))
    pred=predictions(model,splits['test'],'trained_context',config['max_pair_span'])+predictions(initial,splits['test'],'untrained_context',config['max_pair_span'])
    pred+=[{'id':r['id'],'sequence':r['sequence'],'method':'all_unpaired','status':'ok','structure':'.'*len(r['sequence'])} for r in splits['test']]
    folds=[]
    for r in splits['test']:
        for tool in ('ViennaRNA','LinearFold'):
            fold=fold_sequence(ROOT,r['sequence'],folding,tool,run/'raw'/f'{r["id"]}_{tool}.txt')
            if 'raw_output' in fold:fold['raw_sha256']=digest(Path(fold['raw_output']).read_bytes())
            folds.append({'reference_id':r['id'],**fold});row={'id':r['id'],'sequence':r['sequence'],'method':tool,'status':fold['status'] if fold['status'] in ('ok','timeout','unavailable') else 'error'}
            if row['status']=='ok':row['structure']=fold['structure']
            else:row['error']=fold.get('error') or fold['status']
            pred.append(row);print(f'Context family test fold: {tool} {r["id"]}: {row["status"]}',flush=True)
    for name,data in [('test_references.json',{'schema_version':1,'dataset_id':'rf00017_context_trial_test','records':splits['test']}),('test_predictions.json',{'schema_version':1,'methods':manifest['methods'],'records':pred}),('folds.json',folds)]:(run/name).write_text(json.dumps(data,indent=2)+'\n')
    evaluation=run_reference_evaluation(run,run/'test_references.json',run/'test_predictions.json')
    summary={'complete':True,'mode':'family_disjoint_comparative_context_trial','run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'counts':frozen['counts'],'families':families,'training':training,'test_excluded_reference_contacts':sum(band_supervision(r,config['max_pair_span'])[2] for r in splits['test']),'exposure_events':events,'aggregates':evaluation['aggregates'],'artifact_sha256':{name:digest((run/name).read_bytes()) for name in ('model/training.json','test_references.json','test_predictions.json','folds.json','results/reference_evaluation_summary.json')},'limitations':['Processed comparative references, not new experimental measurements.','One family per split; no population-wide family/clan or biological stability claim.','Legacy tool-training overlap and prior PDB family identities remain unresolved.','Max pair span128 excludes distant contacts; test lengths290–317 do not establish long-RNA accuracy.','RF00017 is consumed after this test; no test-driven model/threshold selection.']}
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    report=['# Context comparative family trial','',f'Run: `{run}`','',f'Counts: {frozen["counts"]}',f'Families: {families}','',f'Excluded test reference contacts: {summary["test_excluded_reference_contacts"]}','','| Method | Planned | Measured | Mean test pair F1 |','|---|---:|---:|---:|']
    for a in evaluation['aggregates']:report.append(f'| {a["method"]} | {a["planned_inputs"]} | {a["measured_inputs"]} | {a["mean_pair_f1"]} |')
    report+=['',*summary['limitations'],''];publish(ROOT,'context_family_trial',summary,evaluation['aggregates'],list(evaluation['aggregates'][0]),'\n'.join(report));print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
