#!/usr/bin/env python3
"""Audit fixed development configurations, matching split denominators and selection."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.reference import digest
from rnastable.reference_audit import require
from verify_context_development import audit_context


def audit_comparison(path):
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir'])
    require(summary['complete'] is True and summary['test_evaluated'] is False,'not development-only comparison')
    require(summary==json.loads((run/'summary.json').read_text()),'retained comparison differs')
    require(len(summary['rows'])==len(summary['sources'])==3,'configuration inventory differs')
    expected=[]
    for p,sha in summary['sources'].items():
        require(digest(Path(p).read_bytes())==sha,'comparison source changed');s=audit_context(p);source=Path(s['run_dir'])
        require({name:digest((source/name).read_bytes()) for name in ('train.json','validation.json')}==summary['split_sha256'],'comparison input denominators differ')
        trained={a['reference_kind']:a for a in s['aggregates'] if a['method']=='trained_context'}
        expected.append({'run_dir':s['run_dir'],'max_pair_span':s['config']['max_pair_span'],'positive_weight_exponent':s['config'].get('positive_weight_exponent',.5),'selected_epoch':s['selected_epoch'],'validation_records':s['counts']['validation'],'validation_mean_pair_f1':s['selected_validation_pair_f1'],'pdb_validation_pair_f1':trained['experimental']['mean_pair_f1'],'comparative_validation_pair_f1':trained['computational']['mean_pair_f1'],'comparative_validation_recall':trained['computational']['mean_pair_recall'],'excluded_train_contacts':s['excluded_train_contacts'],'excluded_validation_contacts':s['excluded_validation_contacts'],'summary_sha256':sha})
    require(expected==summary['rows'],'comparison rows differ')
    require(max(expected,key=lambda r:r['validation_mean_pair_f1'])['run_dir']==summary['selected_run_dir'],'configuration selection differs')
    require(Path(summary['figure']).resolve().parent==run.resolve() and digest(Path(summary['figure']).read_bytes())==summary['figure_sha256'],'figure changed')
    print('Context comparison audit passed: three identical reused development splits; validation-only configuration selection and figure integrity verified.')
    return summary

if __name__=='__main__':audit_comparison(ROOT/'results/context_development_comparison_summary.json')
