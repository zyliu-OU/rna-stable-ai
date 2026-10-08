#!/usr/bin/env python3
"""Explicit posthoc decoder-penalty development grid for nine frozen checkpoints."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp,publish
from rnastable.native_journal import atomic_json,exclusive_driver
from rnastable.penalty_development import PENALTIES,run_component,audit_component
from rnastable.reference import digest
from rnastable.reference_audit import require
from run_pair_head_development_study import audit as audit_study
NAME='pair_penalty_development'


def aggregate(run,manifest,components):
    rows=[{'seed':s['seed'],'head':s['head'],'source_epoch':s['source_epoch'],'zero_penalty_development_f1':s['zero_penalty_development_f1'],'selected_penalty':s['selected_penalty'],'selected_development_f1':s['selected_development_f1'],'development_f1_delta':s['selected_development_f1']-s['zero_penalty_development_f1']} for s in components]
    return {'complete':True,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'model_fitted':False,'test_evaluated':False,'development_only':True,'penalties':list(PENALTIES),
            'components':[{'summary':str(Path(s['run_dir'])/'summary.json'),'sha256':digest((Path(s['run_dir'])/'summary.json').read_bytes())} for s in components],'rows':rows,
            'limitations':['All checkpoints and penalties use the same exposed validation cohort; posthoc selection is development tuning, not independent accuracy.',
                           'Checkpoints were originally selected at zero penalty; this is not joint epoch-and-penalty selection and does not retrain models.',
                           'Uniform nonnegative penalties alter logit objectives over the original top-16 retained pools. Scores are not native folding energy.',
                           'Tie policy prefers the smallest penalty. Inference remains zero penalty unless explicitly requested.',
                           'Three seeds share the same biological annotations; no family/clan independence or generalization claim.']}


def audit(path):
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir']);manifest=json.loads((run/'manifest.json').read_text())
    require(summary==json.loads((run/'summary.json').read_text()) and digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'],'Penalty study summary differs')
    require(digest((run/'source_summary.json').read_bytes())==manifest['source_summary_sha256'] and manifest['penalties']==list(PENALTIES),'Penalty study source/grid differs')
    components=[]
    require(len(summary['components'])==len(manifest['components'])==9,'Penalty checkpoint inventory differs')
    for item,binding in zip(summary['components'],manifest['components']):
        path=Path(item['summary']);require(digest(path.read_bytes())==item['sha256'],'Penalty component changed');component=audit_component(path);source=json.loads((path.parent/'source_summary.json').read_text())
        require(digest((path.parent/'source_summary.json').read_bytes())==binding['sha256'] and source['run_dir']==str(Path(binding['summary']).parent),'Penalty source component binding differs');components.append(component)
    require(aggregate(run,manifest,components)==summary,'Penalty aggregate differs')
    print('Penalty development audit passed: nine frozen checkpoints, five penalties each; zero-penalty source scores and exposed-validation selection verified.')
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true');parser.add_argument('--resume',type=Path);args=parser.parse_args()
    if args.verify:return audit(ROOT/'results'/f'{NAME}_summary.json')
    if args.resume:run=args.resume.resolve();manifest=json.loads((run/'manifest.json').read_text())
    else:
        source_path=ROOT/'results/pair_head_development_study_summary.json';source=audit_study(source_path);require(source['completed_fits']==source['planned_fits']==9,'Penalty comparison needs all planned matched fits')
        run=ROOT/'results'/f'{NAME}_runs'/timestamp();run.mkdir(parents=True);(run/'source_summary.json').write_bytes(source_path.read_bytes())
        paths=[Path(__file__),*[ROOT/'src/rnastable'/name for name in ('penalty_development.py','pair_penalty.py','context_inference.py','helix_pairs.py','stack_pairs.py','global_sparse_pairs.py','exact_sparse_pairs.py','scoring.py','exposures.py','reference.py')]]
        manifest={'run_dir':str(run),'source_summary_sha256':digest(source_path.read_bytes()),'components':source['components'],'penalties':list(PENALTIES),'code_sha256':{str(path.resolve()):digest(path.read_bytes()) for path in paths}}
        atomic_json(run/'manifest.json',manifest)
    with exclusive_driver(run/'.driver.lock'):
        if (run/'summary.json').exists():return audit(run/'summary.json')
        components=[]
        for index,item in enumerate(manifest['components']):
            directory=run/'components'/str(index)
            if (directory/'summary.json').exists():components.append(audit_component(directory/'summary.json'));continue
            require(not directory.exists(),'Incomplete penalty component retained; restart with a new declared run rather than overwrite it')
            for name,expected in manifest['code_sha256'].items():require(digest(Path(name).read_bytes())==expected,'Penalty execution source changed')
            print(f'Penalty checkpoint {index+1}/9: {item["summary"]}',flush=True);components.append(run_component(directory,item['summary']))
        summary=aggregate(run,manifest,components);atomic_json(run/'summary.json',summary)
        report=['# Frozen-checkpoint pair-penalty development','',*summary['limitations'],'','| Seed | Head | Zero-penalty F1 | Selected penalty | Selected development F1 |','|---:|---|---:|---:|---:|']
        for row in summary['rows']:report.append(f"| {row['seed']} | {row['head']} | {row['zero_penalty_development_f1']} | {row['selected_penalty']} | {row['selected_development_f1']} |")
        publish(ROOT,NAME,summary,summary['rows'],list(summary['rows'][0]),'\n'.join(report)+'\n');print(json.dumps(summary,indent=2));return summary

if __name__=='__main__':main()
