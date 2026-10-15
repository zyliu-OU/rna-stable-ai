#!/usr/bin/env python3
"""Replay exact development sparse candidates, optimal objectives and decoder scores."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.exposures import read_exposure,exposure_records
from rnastable.reference import digest
from rnastable.reference_audit import require
from compare_exact_sparse_development import measure,aggregate


def audit_exact(path):
    import numpy as np
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir'])
    require(summary['complete'] is True and summary['test_evaluated'] is False and summary==json.loads((run/'summary.json').read_text()),'Exact development identity differs')
    require(digest((run/'manifest.json').read_bytes())==summary['manifest_sha256'] and digest((run/'rows.json').read_bytes())==summary['rows_sha256'],'Decoder artifact changed')
    manifest=json.loads((run/'manifest.json').read_text());require(manifest['run_dir']==str(run) and manifest['policy']==summary['interpretation'],'Manifest identity differs')
    require(digest((run/'validation.json').read_bytes())==manifest['validation_sha256'],'Validation changed')
    require(set(manifest['sources'])==set(manifest['candidate_sha256'])=={'long_comparative_development','sampled_comparative_development'},'Source inventory differs');rows=[]
    for name,sha in manifest['sources'].items():
        source_path=run/(name+'.json');require(digest(source_path.read_bytes())==sha,'Source changed');_,data,records,arrays,measured=measure(source_path)
        require(data==(run/'validation.json').read_bytes(),'Decoder validation differs');candidate_path=run/(name+'_candidates.npz');require(digest(candidate_path.read_bytes())==manifest['candidate_sha256'][name],'Candidates changed')
        with np.load(candidate_path,allow_pickle=False) as stored:
            require(set(stored.files)==set(arrays),'Candidate inventory differs')
            for key,array in arrays.items():require(stored[key].dtype==array.dtype and np.array_equal(stored[key],array),'Checkpoint candidates differ: '+key)
        rows+=measured
    require(rows==json.loads((run/'rows.json').read_text()) and aggregate(rows)==summary['groups'],'Exact decoder replay differs')
    event=summary['exposure_event'];p=Path(event['path']);require(p.resolve().parent==(run/'exposures').resolve() and list((run/'exposures').glob('*.json'))==[p] and digest(p.read_bytes())==event['sha256'],'Exposure changed')
    data=read_exposure(p);require(data['stage']==event['stage']=='validation_started' and data['records']==exposure_records(records,str(run)+' validation_started'),'Decoder exposure differs')
    print(f'Exact sparse audit passed: {len(rows)} decoder predictions on identical development candidates; optimal objectives, source/checkpoint replay, metrics and arrays verified.')
    return summary

if __name__=='__main__':audit_exact(ROOT/'results/exact_sparse_development_summary.json')
