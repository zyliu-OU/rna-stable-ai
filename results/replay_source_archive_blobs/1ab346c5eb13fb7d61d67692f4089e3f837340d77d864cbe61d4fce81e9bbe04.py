#!/usr/bin/env python3
"""Publish a single same-cohort development comparison without fitting or refolding."""
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp,publish
from rnastable.reference import digest,run_reference_evaluation
from rnastable.reference_audit import require,audit_reference
from compare_expanded_development import grouped_metrics


def compose(sources):
    baseline=sources['expanded_development_comparison'];base=Path(baseline['run_dir']);manifest=json.loads((base/'manifest.json').read_text());validation=(base/'validation.json').read_bytes()
    require(digest(validation)==manifest['validation_sha256'],'Baseline validation changed')
    require(digest((base/'predictions.json').read_bytes())==baseline['artifacts_sha256']['predictions.json'],'Baseline predictions changed');data=json.loads((base/'predictions.json').read_text());methods=list(data['methods']);pred=list(data['records'])
    selected=sources['exact_comparative_development'];run=Path(selected['run_dir']);manifest=json.loads((run/'manifest.json').read_text())
    require((run/'validation.json').read_bytes()==validation and digest(validation)==manifest['snapshot_sha256']['validation.json'],'Selected model validation differs')
    require(digest((run/'predictions.json').read_bytes())==selected['predictions_sha256'],'Exact-selected predictions changed')
    extra=[r for r in json.loads((run/'predictions.json').read_text())['records'] if r['method']=='trained_exact_sparse'];require(len(extra)==len(json.loads(validation)['records']),'Selected predictions incomplete');pred+=extra;methods.append('trained_exact_sparse')
    posthoc=sources['exact_sparse_development'];run=Path(posthoc['run_dir']);manifest=json.loads((run/'manifest.json').read_text());require((run/'validation.json').read_bytes()==validation and digest(validation)==manifest['validation_sha256'],'Posthoc validation differs')
    require(digest((run/'rows.json').read_bytes())==posthoc['rows_sha256'],'Posthoc decoder rows changed');rows=[r for r in json.loads((run/'rows.json').read_text()) if r['model']=='trained_expanded_sparse' and r['decoder']=='exact_sparse'];records={r['id']:r for r in json.loads(validation)['records']};require(len(rows)==len(records) and {r['id'] for r in rows}==set(records),'Posthoc prediction inventory differs')
    method='trained_expanded_sparse_posthoc_exact';methods.append(method);pred+=[{'id':r['id'],'sequence':records[r['id']]['sequence'],'method':method,'status':'ok','structure':r['structure']} for r in rows]
    if 'structured_comparative_development' in sources:
        structured=sources['structured_comparative_development'];run=Path(structured['run_dir']);manifest=json.loads((run/'manifest.json').read_text())
        require((run/'validation.json').read_bytes()==validation and digest(validation)==manifest['snapshot_sha256']['validation.json'],'Structured model validation differs')
        require(digest((run/'predictions.json').read_bytes())==structured['predictions_sha256'],'Structured predictions changed');extra=[r for r in json.loads((run/'predictions.json').read_text())['records'] if r['method']=='trained_structured_sparse'];require(len(extra)==len(records),'Structured predictions incomplete');pred+=extra;methods.append('trained_structured_sparse')
    if 'stack_comparative_development' in sources:
        stacked=sources['stack_comparative_development'];run=Path(stacked['run_dir']);manifest=json.loads((run/'manifest.json').read_text())
        require((run/'validation.json').read_bytes()==validation and digest(validation)==manifest['snapshot_sha256']['validation.json'],'Stack model validation differs')
        require(digest((run/'predictions.json').read_bytes())==stacked['predictions_sha256'],'Stack predictions changed');extra=[r for r in json.loads((run/'predictions.json').read_text())['records'] if r['method']=='trained_stack_sparse'];require(len(extra)==len(records),'Stack predictions incomplete');pred+=extra;methods.append('trained_stack_sparse')
    return validation,{'schema_version':1,'methods':methods,'records':pred}


def audit_report(path):
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir']);require(summary['complete'] is True and summary['test_evaluated'] is False and summary==json.loads((run/'summary.json').read_text()),'Report identity differs')
    require(digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'],'Report manifest changed');manifest=json.loads((run/'manifest.json').read_text());sources={}
    required={'expanded_development_comparison','exact_comparative_development','exact_sparse_development'};require(required<=set(manifest['sources']) and set(manifest['sources'])-required<={'structured_comparative_development','stack_comparative_development'},'Report source inventory differs')
    for name,item in manifest['sources'].items():
        p=run/(name+'.json');require(p.read_bytes()==Path(item['path']).read_bytes() and digest(p.read_bytes())==item['sha256'],'Report source changed');source=json.loads(p.read_text());require(source['complete'] is True and source['test_evaluated'] is False and source==json.loads((Path(source['run_dir'])/'summary.json').read_text()),'Source incomplete or changed');require(digest((Path(source['run_dir'])/'manifest.json').read_bytes())==source['manifest_sha256'],'Source manifest changed');sources[name]=source
    validation,pred=compose(sources);require((run/'validation.json').read_bytes()==validation and json.loads((run/'predictions.json').read_text())==pred,'Report composition differs')
    rows=grouped_metrics(json.loads(validation)['records'],pred['records'],pred['methods']);require(rows==summary['rows'],'Report subgroup metrics differ')
    evaluation_path=run/'results/reference_evaluation_summary.json';audit_reference(evaluation_path);evaluation=json.loads(evaluation_path.read_text());require(summary['aggregates']==evaluation['aggregates'],'Report aggregates differ')
    for key,name in [('references','validation.json'),('predictions','predictions.json')]:require(Path(evaluation['sources'][key]['path']).read_bytes()==(run/name).read_bytes(),'Report evaluation input differs')
    for name,sha in summary['exports_sha256'].items():require(digest((run/name).read_bytes())==sha,'Report export changed')
    print(f'Expanded selection report audit passed: {len(json.loads(validation)["records"])} identical development references, {len(pred["records"])} exact composed predictions, subgroup metrics and exports verified.')
    return summary


def main():
    sources={};bindings={}
    for name in ('expanded_development_comparison','exact_comparative_development','exact_sparse_development','structured_comparative_development','stack_comparative_development'):
        path=ROOT/'results'/(name+'_summary.json');source=json.loads(path.read_text());require(source['complete'] is True and source['test_evaluated'] is False,'Incomplete report source');sources[name]=source;bindings[name]={'path':str(Path(source['run_dir'])/'summary.json'),'sha256':digest(path.read_bytes())}
    validation,pred=compose(sources);run=ROOT/'results/expanded_selection_report_runs'/timestamp();run.mkdir(parents=True,exist_ok=False)
    for name,item in bindings.items():(run/(name+'.json')).write_bytes(Path(item['path']).read_bytes())
    (run/'validation.json').write_bytes(validation);(run/'predictions.json').write_text(json.dumps(pred,indent=2)+'\n');manifest={'run_dir':str(run),'sources':bindings,'code_sha256':{str(Path(__file__)):digest(Path(__file__).read_bytes())},'policy':'Same exposed47-record development cohort. Original models selected with refinement; posthoc exact uses that frozen checkpoint; exact-selected model uses exact decoding during validation selection. Structured training uses a pruned margin hinge plus0.1BCE; stack model adds2 sequence-only adjacent pair compatibility weights; both use exact validation selection. One seed; no new fitting, folding or test evaluation in this report.'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');evaluation=run_reference_evaluation(run,run/'validation.json',run/'predictions.json');rows=grouped_metrics(json.loads(validation)['records'],pred['records'],pred['methods'])
    os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'results/.matplotlib-cache'))
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    fig,axes=plt.subplots(1,2,figsize=(13,4.7),layout='constrained');groups=list(dict.fromkeys(r['group'] for r in rows));shown=['trained_expanded_sparse','trained_expanded_sparse_posthoc_exact','trained_exact_sparse','trained_structured_sparse','trained_stack_sparse','ViennaRNA','LinearFold'];labels=['Full / refinement','Full / posthoc exact','Full / exact-selected','Structured / exact','Stackability / exact','ViennaRNA','LinearFold'];x=np.arange(len(groups));width=.115
    for i,(method,label) in enumerate(zip(shown,labels)):
        values=[next(r['mean_pair_f1'] for r in rows if r['group']==g and r['method']==method) for g in groups];axes[0].bar(x+(i-3)*width,values,width,label=label)
    axes[0].set_xticks(x,['All (47)','PDB (12)','Rfam (23)','CRW (12)']);axes[0].set_ylim(0,1);axes[0].set_ylabel('Mean development pair F1');axes[0].set_title('Identical exposed validation records');axes[0].legend(fontsize=8)
    old=json.loads((Path(sources['exact_comparative_development']['run_dir'])/'source_summary.json').read_text());new=sources['exact_comparative_development'];require([r['mean_train_loss'] for r in old['history']]==[r['mean_train_loss'] for r in new['history']],'Training trajectory changed')
    for summary,label in [(old,'Refinement validation'),(new,'Exact sparse validation')]:
        history=summary['history'];axes[1].plot([r['epoch'] for r in history],[r['validation_mean_pair_f1'] for r in history],marker='o',label=label);axes[1].scatter(summary['selected_epoch'],summary['selected_validation_pair_f1'],s=120,facecolors='none',edgecolors='black')
    axes[1].set_xlabel('Epoch');axes[1].set_ylabel('Mean development pair F1');axes[1].set_title('Same training losses; different selection decoder');axes[1].legend(fontsize=8);axes[1].set_ylim(0,.5);fig.suptitle('RNA-StableAI development evidence — no fresh test',fontsize=13)
    figure=run/'development_selection.png';fig.savefig(figure,dpi=180);plt.close(fig)
    summary={'complete':True,'test_evaluated':False,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'rows':rows,'aggregates':evaluation['aggregates'],'exports_sha256':{'development_selection.png':digest(figure.read_bytes())},'interpretation':manifest['policy']};(run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');report=['# Expanded checkpoint selection comparison','',summary['interpretation'],'',f'Figure: `{figure}`','','| Group | Method | Planned | Measured | Failed | Missing | Mean pair F1 |','|---|---|---:|---:|---:|---:|---:|']
    for r in rows:report.append(f'| {r["group"]} | {r["method"]} | {r["planned"]} | {r["measured"]} | {r["failed"]} | {r["missing"]} | {r["mean_pair_f1"]} |')
    publish(ROOT,'expanded_checkpoint_selection',summary,rows,list(rows[0]),'\n'.join(report)+'\n');audit_report(run/'summary.json');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
