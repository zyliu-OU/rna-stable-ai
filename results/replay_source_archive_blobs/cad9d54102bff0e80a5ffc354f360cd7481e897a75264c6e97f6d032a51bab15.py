#!/usr/bin/env python3
"""Compare retained expanded checkpoints with measured native development baselines."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp,publish
from rnastable.exposures import record_exposure
from rnastable.folding import fold_sequence
from rnastable.reference import digest,run_reference_evaluation
from rnastable.reference_audit import require
from rnastable.scoring import structure_agreement


def source_group(record):
    if 'Gutell Lab CRW' in record['source']:return 'CRW comparative'
    if 'Rfam' in record['source']:return 'Rfam comparative'
    if record['reference_kind']=='experimental':return 'PDB-derived annotation'
    raise ValueError('Unrecognized development source')


def grouped_metrics(records,predictions,methods):
    index={(r['id'],r['method']):r for r in predictions};require(len(index)==len(predictions),'Duplicate prediction rows')
    rows=[]
    groups={'all':records}
    for record in records:groups.setdefault(source_group(record),[]).append(record)
    for group,refs in groups.items():
        for method in methods:
            scores=[];failed=0;missing=0
            for record in refs:
                pred=index.get((record['id'],method))
                if pred is None:missing+=1
                elif pred['status']!='ok':failed+=1
                else:
                    require(pred['sequence']==record['sequence'],'Sequence binding differs')
                    scores.append(structure_agreement(pred['structure'],record['structure'])['pair_f1'])
            rows.append({'group':group,'method':method,'planned':len(refs),'measured':len(scores),'failed':failed,'missing':missing,'mean_pair_f1':sum(scores)/len(scores) if scores else None})
    return rows


def main():
    sources={};pred=[];frozen=None
    for name,method in [('long_comparative_development','trained_expanded_sparse'),('sampled_comparative_development','trained_sampled_sparse')]:
        path=ROOT/'results'/(name+'_summary.json');data=path.read_bytes();summary=json.loads(data);run=Path(summary['run_dir'])
        require(summary['complete'] is True and summary['test_evaluated'] is False and summary==json.loads((run/'summary.json').read_text()),'Incomplete or changed development summary')
        require(digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'],'Source manifest changed')
        manifest=json.loads((run/'manifest.json').read_text());refs=(run/'validation.json').read_bytes();require(digest(refs)==manifest['snapshot_sha256']['validation.json'],'Validation snapshot changed')
        if frozen is None:frozen=refs
        require(refs==frozen,'Comparison validation differs')
        require(digest((run/'predictions.json').read_bytes())==summary['predictions_sha256'],'Source predictions changed')
        rows=[r for r in json.loads((run/'predictions.json').read_text())['records'] if r['method']==method]
        require(len(rows)==summary['counts']['validation'],'Incomplete source predictions')
        pred+=rows;sources[name]={'summary':str(run/'summary.json'),'sha256':digest(data),'method':method,'selected_epoch':summary['selected_epoch']}
    records=json.loads(frozen)['records'];run=ROOT/'results/expanded_comparison_runs'/timestamp();run.mkdir(parents=True,exist_ok=False)
    (run/'validation.json').write_bytes(frozen)
    for name,item in sources.items():(run/(name+'.json')).write_bytes(Path(item['summary']).read_bytes())
    methods=['trained_expanded_sparse','trained_sampled_sparse','all_unpaired','ViennaRNA','LinearFold']
    folding={'temperature_c':37,'beam_size':100,'timeout_seconds':30,'memory_limit_gib':4}
    manifest={'run_dir':str(run),'sources':sources,'validation_sha256':digest(frozen),'methods':methods,'folding':folding,'code_sha256':{str(p):digest(p.read_bytes()) for p in (Path(__file__),ROOT/'src/rnastable/folding.py',ROOT/'src/rnastable/reference.py',ROOT/'src/rnastable/scoring.py')},'policy':'Reused development only. Compare identical validation references without fitting or test evaluation. Native failures remain in planned denominators.'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');event=record_exposure(run,'validation_started',records)
    pred+=[{'id':r['id'],'sequence':r['sequence'],'method':'all_unpaired','status':'ok','structure':'.'*len(r['sequence'])} for r in records];folds=[]
    for record in records:
        for tool in ('ViennaRNA','LinearFold'):
            fold=fold_sequence(ROOT,record['sequence'],folding,tool,run/'raw'/f'{record["id"]}_{tool}.txt')
            if 'raw_output' in fold:fold['raw_sha256']=digest(Path(fold['raw_output']).read_bytes())
            folds.append({'reference_id':record['id'],**fold});row={'id':record['id'],'sequence':record['sequence'],'method':tool,'status':fold['status'] if fold['status'] in ('ok','timeout','unavailable') else 'error'}
            if row['status']=='ok':row['structure']=fold['structure']
            else:row['error']=fold.get('error') or fold['status']
            pred.append(row);print(f'Development baseline {tool}: {record["id"]}: {row["status"]}',flush=True)
    (run/'folds.json').write_text(json.dumps(folds,indent=2)+'\n');(run/'predictions.json').write_text(json.dumps({'schema_version':1,'methods':methods,'records':pred},indent=2)+'\n')
    evaluation=run_reference_evaluation(run,run/'validation.json',run/'predictions.json');rows=grouped_metrics(records,pred,methods)
    summary={'complete':True,'test_evaluated':False,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'artifacts_sha256':{n:digest((run/n).read_bytes()) for n in ('folds.json','predictions.json','results/reference_evaluation_summary.json')},'validation_records':len(records),'exposure_event':event,'rows':rows,'aggregates':evaluation['aggregates'],'interpretation':'Same exposed development cohort. One seed and validation-selected checkpoints; no generalization, assay, family independence or biological stability claim.'}
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');report=['# Expanded development comparison','',f'Run: `{run}`','',summary['interpretation'],'','| Source group | Method | Planned | Measured | Failed | Missing | Mean pair F1 |','|---|---|---:|---:|---:|---:|---:|']
    for r in rows:report.append(f'| {r["group"]} | {r["method"]} | {r["planned"]} | {r["measured"]} | {r["failed"]} | {r["missing"]} | {r["mean_pair_f1"]} |')
    publish(ROOT,'expanded_development_comparison',summary,rows,list(rows[0]),'\n'.join(report)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
