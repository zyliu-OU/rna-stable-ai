#!/usr/bin/env python3
"""Verify exact reused validation, source predictions, raw native folds and subgroup denominators."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.exposures import read_exposure,exposure_records
from rnastable.folding import parse_output,tool_commands
from rnastable.reference import digest
from rnastable.reference_audit import require,audit_reference
from compare_expanded_development import grouped_metrics


def audit_comparison(path):
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir'])
    require(summary['complete'] is True and summary['test_evaluated'] is False and summary==json.loads((run/'summary.json').read_text()),'Comparison identity differs')
    require(digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'],'Manifest changed')
    manifest=json.loads((run/'manifest.json').read_text());require(manifest['run_dir']==str(run),'Run identity differs')
    methods=['trained_expanded_sparse','trained_sampled_sparse','all_unpaired','ViennaRNA','LinearFold'];require(manifest['methods']==methods,'Method plan differs')
    require(digest((run/'validation.json').read_bytes())==manifest['validation_sha256'],'Validation changed')
    for name,sha in summary['artifacts_sha256'].items():require(digest((run/name).read_bytes())==sha,'Artifact changed: '+name)
    records=json.loads((run/'validation.json').read_text())['records'];require(len(records)==summary['validation_records'],'Validation count differs');pred=[]
    require(set(manifest['sources'])=={'long_comparative_development','sampled_comparative_development'},'Source inventory differs')
    for index,(name,item) in enumerate(manifest['sources'].items()):
        source_path=run/(name+'.json');require(source_path.read_bytes()==Path(item['summary']).read_bytes() and digest(source_path.read_bytes())==item['sha256'],'Source summary changed')
        source=json.loads(source_path.read_text());source_run=Path(source['run_dir']);require(source['complete'] is True and source['test_evaluated'] is False and source['selected_epoch']==item['selected_epoch'],'Source development identity differs')
        require(item['method']=={'long_comparative_development':'trained_expanded_sparse','sampled_comparative_development':'trained_sampled_sparse'}[name],'Source method differs')
        require(digest((source_run/'manifest.json').read_bytes())==source['manifest_sha256'],'Source manifest changed')
        source_manifest=json.loads((source_run/'manifest.json').read_text());require(digest((source_run/'validation.json').read_bytes())==source_manifest['snapshot_sha256']['validation.json'],'Source validation changed')
        require((source_run/'validation.json').read_bytes()==(run/'validation.json').read_bytes(),'Validation cohort differs')
        require(digest((source_run/'predictions.json').read_bytes())==source['predictions_sha256'],'Source predictions changed')
        for filename,sha in source['checkpoint_sha256'].items():require(digest((source_run/filename).read_bytes())==sha,'Source checkpoint changed')
        rows=[r for r in json.loads((source_run/'predictions.json').read_text())['records'] if r['method']==item['method']];require(len(rows)==len(records),'Source predictions incomplete');pred+=rows
    pred+=[{'id':r['id'],'sequence':r['sequence'],'method':'all_unpaired','status':'ok','structure':'.'*len(r['sequence'])} for r in records]
    event=summary['exposure_event'];p=Path(event['path']);require(p.resolve().parent==(run/'exposures').resolve() and list((run/'exposures').glob('*.json'))==[p] and digest(p.read_bytes())==event['sha256'],'Exposure event changed')
    data=read_exposure(p);require(data['stage']==event['stage']=='validation_started' and data['records']==exposure_records(records,str(run)+' validation_started'),'Exposure differs')
    folds=json.loads((run/'folds.json').read_text());commands=tool_commands(ROOT,manifest['folding']);require([(f['reference_id'],f['tool']) for f in folds]==[(r['id'],t) for r in records for t in ('ViennaRNA','LinearFold')],'Native fold inventory differs')
    for record,pair in zip(records,[folds[i:i+2] for i in range(0,len(folds),2)]):
        for fold in pair:
            require(fold['status'] in ('ok','error','parse_error','timeout','unavailable'),'Unknown native status')
            if fold['status']!='unavailable':require(fold['device']=='CPU' and fold['command']==commands[fold['tool']][0],'Native command differs')
            if 'raw_output' in fold:
                raw=Path(fold['raw_output']);require(raw.resolve().parent==(run/'raw').resolve() and digest(raw.read_bytes())==fold['raw_sha256'],'Raw fold changed')
            if fold['status']=='ok':
                require('raw_output' in fold and fold['returncode']==0,'Successful fold lacks raw evidence')
                require(raw.read_text().splitlines()[0].strip()==record['sequence'],'Native sequence differs');parsed=parse_output(fold['tool'],raw.read_text(),len(record['sequence']));require(all(fold[k]==v for k,v in parsed.items()),'Native structure/energy differs')
            row={'id':record['id'],'sequence':record['sequence'],'method':fold['tool'],'status':fold['status'] if fold['status'] in ('ok','timeout','unavailable') else 'error'}
            if row['status']=='ok':row['structure']=fold['structure']
            else:row['error']=fold.get('error') or fold['status']
            pred.append(row)
    require(json.loads((run/'predictions.json').read_text())=={'schema_version':1,'methods':methods,'records':pred},'Prediction replay differs')
    require(grouped_metrics(records,pred,methods)==summary['rows'],'Subgroup denominators/metrics differ')
    evaluation_path=run/'results/reference_evaluation_summary.json';audit_reference(evaluation_path);evaluation=json.loads(evaluation_path.read_text())
    for key,name in [('references','validation.json'),('predictions','predictions.json')]:require(Path(evaluation['sources'][key]['path']).read_bytes()==(run/name).read_bytes(),'Evaluation input differs')
    require(summary['aggregates']==evaluation['aggregates'],'Evaluation aggregates differ')
    print(f'Expanded comparison audit passed: {len(records)} exact development inputs, {len(folds)} raw native folds, all subgroup denominators verified.')
    return summary

if __name__=='__main__':audit_comparison(ROOT/'results/expanded_development_comparison_summary.json')
