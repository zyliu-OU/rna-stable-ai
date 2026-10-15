#!/usr/bin/env python3
"""Audit both full sweeps, portfolios, prospective plan, paired outcomes and costs."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.sweep import fingerprint, plan_jobs
from rnastable.batch_audit import event_peak


def audit_batches(summary, summary_path):
    run=Path(summary['run_dir'])
    manifest_path=run/'manifest.json'
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest()==summary['manifest_sha256']
    manifest=json.loads(manifest_path.read_text())
    assert summary['complete'] and summary['config']==manifest['config']
    assert summary['config_sha256']==manifest['config_sha256']==fingerprint(summary['config'])
    assert summary['provenance']==manifest['provenance']
    assert summary['execution']==manifest['execution']
    spec=manifest['config']
    assert spec['long_steps']==spec['steps_per_restart']*len(spec['restart_search_seeds'])
    assert manifest['selection_policy']=='lowest_confirmed_vienna_energy_then_job_id_v1'
    expected={(k,n,s) for n in spec['lengths'] for k in spec['kinds'] for s in spec['sequence_seeds']}
    assert len(manifest['components'])==len(summary['sources'])==len(expected)
    merged=[]
    for task,record in zip(manifest['components'],summary['sources']):
        directory=Path(task['root'])
        assert directory.is_relative_to(run/'components')
        assert record['component']==task['id']
        config_path=Path(task['config'])
        assert hashlib.sha256(config_path.read_bytes()).hexdigest()==task['config_sha256']
        config=json.loads(config_path.read_text())
        assert config['lengths']==[task['length']] and config['kinds']==[task['kind']] and config['sequence_seeds']==[task['sequence_seed']]
        for key in spec:
            if key not in ('lengths','kinds','sequence_seeds','optimization_config'):
                assert config[key]==spec[key]
        assert Path(config['optimization_config'])==(Path(manifest['config_path']).parent/spec['optimization_config']).resolve()
        path=Path(record['path'])
        assert path==directory/'results/equal_budget_summary.json'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256']
        child=json.loads(path.read_text())
        assert child['mode']=='prospective_cpu_equal_proposal_budget' and child['complete']
        assert child['config']==config and len(child['rows'])==1
        child_manifest=json.loads((Path(child['run_dir'])/'manifest.json').read_text())
        assert child_manifest['utc']>=manifest['utc']
        for key in ('versions','file_sha256'):
            assert child_manifest['provenance'][key]==manifest['provenance'][key]
        for path_string,sha in manifest['provenance']['batch_code_sha256'].items():
            if path_string.endswith('/budget_study.py'):assert child_manifest['provenance']['driver_sha256']==sha
            if path_string.endswith('/portfolio.py'):assert child_manifest['provenance']['portfolio_sha256']==sha
        subprocess.run([sys.executable,str(Path(__file__).resolve()),'--summary',str(path)],check=True)
        merged.extend(child['rows'])
    assert summary['rows']==merged
    assert len(merged)==len(expected)
    assert {(r['kind'],r['length'],r['sequence_seed']) for r in merged}==expected
    for aggregate in summary['aggregates']:
        group=[r for r in merged if r['length']==aggregate['length']]
        values=[r['restart_minus_long_kcal_mol'] for r in group if r['comparison_status']=='measured']
        assert aggregate['planned_inputs']==len(group)
        assert aggregate['measured_pairs']==len(values) and aggregate['unknown_pairs']==len(group)-len(values)
        assert aggregate['winners']==dict(Counter(r['winner'] for r in group))
        assert aggregate['mean_restart_minus_long_kcal_mol']==(sum(values)/len(values) if values else None)
    status=json.loads((run/'driver_status.json').read_text())
    assert status['complete'] and status['component_exit_codes']==[0]*len(expected)
    event_path=Path(status['event_log'])
    assert event_path.is_relative_to(run/'driver_events')
    peak=event_peak([json.loads(line) for line in event_path.read_text().splitlines()],
                    {t['id'] for t in manifest['components']},manifest['execution']['max_cpu_jobs'])
    assert summary['peak_cpu_jobs']==peak
    assert json.loads((run/'summary.json').read_text())==summary
    with (summary_path.parent/(summary['report_name']+'.csv')).open() as stream:
        reader=csv.DictReader(stream);rows=list(reader)
        assert len(rows)==len(merged)
        for actual,row in zip(rows,merged):
            assert actual=={k:'' if row[k] is None else str(row[k]) for k in reader.fieldnames}
    print(f'Batched equal-budget audit passed: {len(merged)} exact paired inputs; peak {peak}; child plans, raw folds, costs, merged denominators and native concurrency verified.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, default=ROOT/'results/equal_budget_summary.json')
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text())
    if summary['mode']=='batched_cpu_equal_proposal_budget':
        audit_batches(summary,args.summary)
        return
    run = Path(summary['run_dir'])
    assert summary['complete'] and summary['mode'] == 'prospective_cpu_equal_proposal_budget'
    manifest_path = run/'manifest.json'
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == summary['manifest_sha256']
    manifest = json.loads(manifest_path.read_text())
    spec = manifest['config']
    assert summary['config'] == spec
    assert summary['config_sha256'] == manifest['config_sha256'] == fingerprint(spec)
    assert spec['long_steps'] == spec['steps_per_restart']*len(spec['restart_search_seeds'])
    assert manifest['selection_policy'] == 'lowest_confirmed_vienna_energy_then_job_id_v1'
    assert manifest['arm_order'] == ['long', 'restarts']
    sources = {}
    for name in ['long', 'restarts']:
        sources[name] = {}
        arm = manifest['arms'][name]
        assert json.loads((run/name/'config.json').read_text()) == arm['config']
        for kind in ['sweep', 'portfolio']:
            record = summary['sources'][name][kind]
            path = Path(record['path'])
            assert hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256']
            sources[name][kind] = json.loads(path.read_text())
        sweep = sources[name]['sweep']
        assert sweep['provenance'] == {k: v for k, v in manifest['provenance'].items()
                                       if k not in ('driver_sha256','portfolio_sha256')}
        assert arm['jobs'] == plan_jobs(sweep['config'])
        assert [r['job_id'] for r in sweep['rows']] == [j['job_id'] for j in arm['jobs']]
        assert sweep['utc'] >= manifest['utc']
        assert sweep['config']['optimization']['steps'] == (spec['long_steps'] if name == 'long' else spec['steps_per_restart'])
        assert sweep['config']['beam_sizes'] == [spec['beam_size']]
        assert sweep['config']['search_seeds'] == ([spec['restart_search_seeds'][0]] if name == 'long' else spec['restart_search_seeds'])
        portfolio = sources[name]['portfolio']
        assert portfolio['source_summary'] == summary['sources'][name]['sweep']['path']
        assert portfolio['source_summary_sha256'] == summary['sources'][name]['sweep']['sha256']
        # The portfolio auditor already runs the full source trajectory/fold audit.
        subprocess.run([sys.executable, str(ROOT/'scripts/verify_portfolio.py'),
                        '--summary', summary['sources'][name]['portfolio']['path']], check=True)
    expected = {(k, n, s) for k in spec['kinds'] for n in spec['lengths'] for s in spec['sequence_seeds']}
    assert {(r['kind'],r['length'],r['sequence_seed']) for r in summary['rows']} == expected
    assert len(summary['rows']) == len(expected)
    totals = Counter()
    for row in summary['rows']:
        key = (row['kind'], row['length'], row['sequence_seed'])
        fully_measured = True
        references = []
        for name in ['long','restarts']:
            group = [r for r in sources[name]['sweep']['rows'] if (r['kind'],r['length'],r['sequence_seed']) == key]
            portfolio = next(r for r in sources[name]['portfolio']['rows'] if (r['kind'],r['length'],r['sequence_seed']) == key)
            assert row['input_sha256'] == portfolio['input_sha256']
            references.append(portfolio['input_vienna_energy_kcal_mol'])
            assert row[f'{name}_selected_delta_kcal_mol'] == portfolio['selected_vienna_delta_kcal_mol']
            assert row[f'{name}_selected_fasta'] == portfolio['selected_fasta']
            assert row[f'{name}_selected_job_id'] == portfolio['selected_job_id']
            assert row[f'{name}_searches'] == len(group) == (1 if name == 'long' else len(spec['restart_search_seeds']))
            validated = sum(r['status'] == 'validated' for r in group)
            assert row[f'{name}_validated_candidates'] == validated
            fully_measured &= validated == len(group) and portfolio['selected_vienna_delta_kcal_mol'] is not None
            assert row[f'{name}_planned_proposals'] == spec['long_steps']
            assert row[f'{name}_attempted_proposals'] == sum(r.get('steps_attempted',0) for r in group) <= spec['long_steps']
            for measure, field, measured in [
                ('search','search_wall_seconds',group),
                ('validation','finalist_validation_wall_seconds',group),
                ('reference','reference_wall_seconds',[r for r in group if not r['reference_reused']])]:
                values = [r.get(field) for r in measured]
                expected_cost = (sum(values) if all(type(v) in (int,float) and math.isfinite(v) and v >= 0 for v in values) else None)
                assert row[f'{name}_{measure}_wall_seconds'] == expected_cost
            counts = Counter(baseline=0, proposals=0, validation=0, reference=0)
            if all(r.get('summary_path') for r in group):
                for candidate in group:
                    evidence = json.loads(Path(candidate['summary_path']).read_text())
                    counts['baseline'] += 1
                    counts['reference'] += int(not candidate['reference_reused'])
                    counts['validation'] += int(evidence['search']['status']=='completed' and candidate['input_sha256'] != candidate['finalist_sha256'])
                    counts['proposals'] += sum(h['status'] not in ('duplicate','no_legal_proposal') for h in evidence['search']['history'])
                for field in counts:
                    assert row[f'{name}_{field}_fold_requests'] == counts[field]
                    totals[name+'_'+field] += counts[field]
            else:
                assert all(row[f'{name}_{field}_fold_requests'] is None for field in counts)
        if all(v is not None for v in references):
            assert abs(references[0]-references[1]) <= 1e-9
        delta = row['restarts_selected_delta_kcal_mol']-row['long_selected_delta_kcal_mol'] if fully_measured else None
        assert row['restart_minus_long_kcal_mol'] == delta
        assert row['comparison_status'] == ('measured' if fully_measured else 'incomplete_validation')
        assert row['winner'] == ('unknown' if delta is None else 'restarts' if delta < -1e-9 else 'long' if delta > 1e-9 else 'tie')
    for aggregate in summary['aggregates']:
        group = [r for r in summary['rows'] if r['length'] == aggregate['length']]
        values = [r['restart_minus_long_kcal_mol'] for r in group if r['comparison_status'] == 'measured']
        assert aggregate['planned_inputs'] == len(group)
        assert aggregate['measured_pairs'] == len(values)
        assert aggregate['unknown_pairs'] == len(group)-len(values)
        assert aggregate['winners'] == dict(Counter(r['winner'] for r in group))
        if values:
            assert math.isclose(aggregate['mean_restart_minus_long_kcal_mol'], sum(values)/len(values), abs_tol=1e-10)
        else:
            assert aggregate['mean_restart_minus_long_kcal_mol'] is None
    assert json.loads((run/'summary.json').read_text()) == summary
    assert json.loads((run/'status.json').read_text())['complete']
    with (args.summary.parent/'equal_budget.csv').open() as stream:
        reader = csv.DictReader(stream); rows = list(reader)
        assert len(rows) == len(summary['rows'])
        for actual, expected_row in zip(rows, summary['rows']):
            assert actual == {k: '' if expected_row[k] is None else str(expected_row[k]) for k in reader.fieldnames}
    print(f'Equal-budget audit passed: {len(expected)} paired inputs; request counts {dict(totals)}; plan, raw folds, selections, costs and denominators verified.')


if __name__ == '__main__':
    main()
