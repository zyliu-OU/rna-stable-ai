#!/usr/bin/env python3
"""Replay checkpoint-derived development candidate coverage and labelled oracle bounds."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.exposures import read_exposure,exposure_records
from rnastable.reference import digest
from rnastable.reference_audit import require
from diagnose_expanded_candidates import measure,aggregate


def audit_diagnostics(path):
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir'])
    require(summary['complete'] is True and summary['test_evaluated'] is False and summary==json.loads((run/'summary.json').read_text()),'Diagnostic identity differs')
    require(digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'] and digest((run/'rows.json').read_bytes())==summary['rows_sha256'],'Diagnostic artifact changed')
    manifest=json.loads((run/'manifest.json').read_text());require(manifest['run_dir']==str(run) and summary['interpretation']==manifest['policy'],'Manifest identity differs')
    require(digest((run/'validation.json').read_bytes())==manifest['validation_sha256'],'Validation changed')
    require(set(manifest['source_sha256'])=={'long_comparative_development','sampled_comparative_development'},'Source inventory differs');rows=[]
    for name,sha in manifest['source_sha256'].items():
        source_path=run/(name+'.json');require(digest(source_path.read_bytes())==sha,'Source summary changed')
        _,data,records,measured=measure(source_path);require(data==(run/'validation.json').read_bytes(),'Diagnostic validation differs');rows+=measured
    require(rows==json.loads((run/'rows.json').read_text()) and aggregate(rows)==summary['groups'],'Candidate diagnostic replay differs')
    event=summary['exposure_event'];p=Path(event['path']);require(p.resolve().parent==(run/'exposures').resolve() and list((run/'exposures').glob('*.json'))==[p] and digest(p.read_bytes())==event['sha256'],'Exposure event changed')
    data=read_exposure(p);require(data['stage']==event['stage']=='validation_started' and data['records']==exposure_records(records,str(run)+' validation_started'),'Diagnostic exposure differs')
    print(f'Candidate diagnostic audit passed: {len(rows)} exact checkpoint/validation rows; positive, top-k and decoder losses and oracle bounds verified.')
    return summary

if __name__=='__main__':audit_diagnostics(ROOT/'results/expanded_candidate_diagnostics_summary.json')
