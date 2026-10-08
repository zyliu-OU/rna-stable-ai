#!/usr/bin/env python3
"""Verify component provenance, exact merged rows and logged CPU concurrency."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rnastable.sweep import load_sweep_config,plan_jobs
from rnastable.batch_audit import concurrency_evidence


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary',type=Path,default=ROOT/'results/evaluation_robustness_long_summary.json')
    args=parser.parse_args()
    summary=json.loads(args.summary.read_text());run=Path(summary['run_dir'])
    subprocess.run([sys.executable,str(ROOT/'scripts/verify_sweep.py'),'--summary',str(args.summary)],check=True)
    manifest=json.loads((run/'manifest.json').read_text())
    status=json.loads((run/'driver_status.json').read_text())
    assert len(status['component_exit_codes'])==len(manifest['components'])
    assert status['complete'] and all(code==0 for code in status['component_exit_codes'])
    assert status['saved_searches']==len(summary['rows'])
    assert summary['execution']==manifest['execution']
    all_rows={}
    for task in manifest['components']:
        directory=Path(task['root'])
        assert directory.is_relative_to(run/'components')
        component=json.loads((directory/'results/evaluation_sweep_summary.json').read_text())
        assert component['complete'] and component['provenance']==manifest['provenance']
        spec=load_sweep_config(task['config'])
        assert component['config']==spec
        for key in ('optimization','search_seeds','beam_sizes'):
            assert spec[key]==summary['config'][key]
        assert [r['job_id'] for r in component['rows']]==[j['job_id'] for j in plan_jobs(spec)]
        for row in component['rows']:
            assert row['job_id'] not in all_rows
            all_rows[row['job_id']]=row
    assert [j['job_id'] for j in manifest['jobs']]==[r['job_id'] for r in summary['rows']]
    assert set(all_rows)=={r['job_id'] for r in summary['rows']}
    assert all(all_rows[row['job_id']]==row for row in summary['rows'])
    peak,evidence=concurrency_evidence(run,manifest,status,ROOT/'reports/commands.jsonl')
    print(f'Batch audit passed: {len(manifest["components"])} components, {len(all_rows)} exact merged rows; '
          f'peak {peak} within the recorded limit. Evidence: {evidence}.')


if __name__=='__main__':main()
