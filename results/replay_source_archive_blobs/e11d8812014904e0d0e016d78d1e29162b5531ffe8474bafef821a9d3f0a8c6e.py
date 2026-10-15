#!/usr/bin/env python3
"""Render an audited, standalone energy/cost figure and measured CPU cost report."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.artifacts import timestamp, write_artifact
from rnastable.budget_study import measured_sum
from rnastable.cli import versions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, default=ROOT/'results/equal_budget_summary.json')
    parser.add_argument('--name', default='equal_budget', help='Output prefix, e.g. equal_budget_long')
    parser.add_argument('--output-root', type=Path, default=ROOT)
    args = parser.parse_args()
    import re
    if not re.fullmatch(r'[a-z][a-z0-9_]*', args.name):
        parser.error('Output name must contain lowercase letters, digits and underscores')
    report_root=args.output_root.resolve()
    path = args.summary.resolve()
    subprocess.run([sys.executable, str(ROOT/'scripts/verify_equal_budget.py'), '--summary', str(path)], check=True)
    source = json.loads(path.read_text())
    rows = source['rows']
    totals = {}
    for arm in ['long','restarts']:
        totals[arm] = {'searches': sum(r[f'{arm}_searches'] for r in rows),
                      'validated_candidates': sum(r[f'{arm}_validated_candidates'] for r in rows),
                      'planned_proposals': sum(r[f'{arm}_planned_proposals'] for r in rows),
                      'attempted_proposals': sum(r[f'{arm}_attempted_proposals'] for r in rows)}
        for measure in ['search','reference','validation']:
            totals[arm][measure+'_wall_seconds'] = measured_sum(rows, f'{arm}_{measure}_wall_seconds')
        for kind in ['baseline','proposals','reference','validation']:
            values = [r[f'{arm}_{kind}_fold_requests'] for r in rows]
            totals[arm][kind+'_fold_requests'] = sum(values) if all(v is not None for v in values) else None
    output = Path(source['run_dir'])/'figures'/timestamp()
    output.mkdir(parents=True, exist_ok=False)
    os.environ.setdefault('MPLCONFIGDIR', str(output/'matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1,2,figsize=(12,5))
    colors = {'long':'#3268ab','restarts':'#bd5b35'}
    for arm, offset in [('long',-.18),('restarts',.18)]:
        values = [(-r[f'{arm}_selected_delta_kcal_mol']
                   if r['comparison_status']=='measured' and r[f'{arm}_selected_delta_kcal_mol'] is not None
                   else float('nan')) for r in rows]
        axes[0].barh([i+offset for i in range(len(rows))], values, height=.33, label=arm, color=colors[arm])
    axes[0].set_yticks(range(len(rows)), [f'{r["length"]} nt / seed {r["sequence_seed"]}' for r in rows])
    axes[0].invert_yaxis()
    axes[0].set_xlabel('Selected ViennaRNA energy reduction (kcal/mol)')
    axes[0].set_title('Paired synthetic inputs; larger reduction is better')
    axes[0].legend()
    axes[0].grid(axis='x', alpha=.2)
    bottom = [0.,0.]
    for measure, color in [('search','#3268ab'),('reference','#999999'),('validation','#bd5b35')]:
        values = [totals[arm][measure+'_wall_seconds'] for arm in ['long','restarts']]
        known = [float('nan') if v is None else v for v in values]
        axes[1].bar(['long','restarts'],known,bottom=bottom,label=measure,color=color)
        bottom = [b+v if v is not None else b for b,v in zip(bottom,values)]
    axes[1].set_ylabel('Sum of recorded component wall times (seconds)')
    axes[1].set_title('CPU cost includes extra restart validation')
    axes[1].legend()
    axes[1].grid(axis='y',alpha=.2)
    concurrent=source.get('execution',{}).get('mode')=='independent_input_budget_batches'
    fig.suptitle('Equal proposal caps; concurrent CPU costs include contention' if concurrent
                 else 'Equal proposal caps; unequal folding requests and CPU work')
    fig.tight_layout()
    figure = output/'equal_budget.png'
    fig.savefig(figure,dpi=180)
    plt.close(fig)
    result = {'mode':'audited_equal_budget_cost_report','source_summary':str(path),
              'source_summary_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'versions':versions(),'totals':totals,'figure':str(figure),
              'figure_sha256':hashlib.sha256(figure.read_bytes()).hexdigest(),
              'timing_scope':'Sum of search (including baseline), nonreused input references and finalist validations; excludes plotting/reporting/driver overhead. One observation per request; no speedup claim.'}
    if concurrent:
        result['timing_scope']+=' '+source['execution']['timing_scope']
    lines = ['# Audited equal-budget CPU costs', '',
             f'Source study: `{source["run_dir"]}`', '',
             'Both arms have the same proposed-mutation cap. Restarts have extra baseline folds and candidate validations.', '',
             '| Arm | Searches | Attempted / planned proposals | Baseline requests | Proposal requests | Reference requests | Candidate validation requests | Search seconds | Reference seconds | Validation seconds |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    def fmt(value):
        return 'unknown' if value is None else f'{value:.3f}' if isinstance(value,float) else str(value)
    for arm in ['long','restarts']:
        t=totals[arm]
        values=[arm,t['searches'],f'{t["attempted_proposals"]}/{t["planned_proposals"]}',
                *[t[k+'_fold_requests'] for k in ['baseline','proposals','reference','validation']],
                *[t[k+'_wall_seconds'] for k in ['search','reference','validation']]]
        lines.append('| '+' | '.join(fmt(v) for v in values)+' |')
    relative=os.path.relpath(figure,report_root/'reports')
    lines += ['',f'![Paired energy reductions and CPU costs]({relative})','',result['timing_scope'],'',
              'Requests are calls to folding adapters. An unavailable tool can receive a request without spawning a process. '
              'Missing costs remain unknown; failed validations are excluded from paired energy outcomes. '
              'This small synthetic study does not establish biological stability or population performance. No training.','']
    write_artifact(report_root/'results'/(args.name+'_cost_summary.json'),json.dumps(result,indent=2,allow_nan=False)+'\n')
    write_artifact(report_root/'reports'/(args.name+'_cost_report.md'),'\n'.join(lines))
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'totals':totals,'figure':str(figure)},indent=2))


if __name__=='__main__':
    main()
