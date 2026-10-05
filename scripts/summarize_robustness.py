#!/usr/bin/env python3
"""Publish search-seed variability from an audited, complete CPU sweep."""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp, write_artifact
from rnastable.replication import paired_comparisons, PAIR_FIELDS
from rnastable.robustness import search_variability, INPUT_FIELDS, GROUP_FIELDS
from rnastable.sweep import load_sweep_config, plan_jobs, FIELDS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary',type=Path,default=ROOT/'results/evaluation_sweep_summary.json')
    parser.add_argument('--config',type=Path,default=ROOT/'configs/evaluation_robustness.json')
    parser.add_argument('--name',choices=['robustness','robustness_long'],default='robustness')
    args=parser.parse_args()
    summary=json.loads(args.summary.read_text())
    config=load_sweep_config(args.config)
    if not summary['complete'] or summary['config']!=config:
        parser.error('Expected a complete study matching --config')
    if config['kinds']!=['mixed'] or config['beam_sizes']!=[200,400]:
        parser.error('This reporter requires mixed inputs and paired beams 200/400')
    if [r['job_id'] for r in summary['rows']]!=[j['job_id'] for j in plan_jobs(config)]:
        parser.error('Rows differ from the complete planned grid')
    subprocess.run([sys.executable,str(ROOT/'scripts/verify_sweep.py'),'--summary',str(args.summary)],check=True)
    inputs,groups=search_variability(summary['rows'])
    pairs=paired_comparisons(summary['rows'])
    run=Path(summary['run_dir'])
    os.environ.setdefault('MPLCONFIGDIR',str(run/'matplotlib-cache'))
    os.environ.setdefault('XDG_CACHE_HOME',str(ROOT/'external/cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,len(config['lengths']),figsize=(12,4),squeeze=False)
    for ax,length in zip(axes[0],config['lengths']):
        for beam,color in [(200,'#3268ab'),(400,'#bd5b35')]:
            rows=[r for r in summary['rows'] if r['length']==length and r['beam_size']==beam]
            for seed_index,seed in enumerate(config['sequence_seeds']):
                measured=[r for r in rows if r['sequence_seed']==seed and r.get('selected_vienna_delta_kcal_mol') is not None]
                count=len(config['search_seeds'])
                offsets=[.14*(i-(count-1)/2)/max(1,count-1) for i in range(count)]
                x=[seed_index+(0 if beam==200 else .28)+offsets[config['search_seeds'].index(r['search_seed'])] for r in measured]
                ax.scatter(x,[r['selected_vienna_delta_kcal_mol'] for r in measured],color=color,
                           label=f'beam {beam}' if seed_index==0 else None)
        ax.set_xticks([i+.14 for i in range(len(config['sequence_seeds']))],config['sequence_seeds'])
        ax.set_xlabel('Input seed; dots are repeated search seeds');ax.set_ylabel('Selected Vienna energy change (kcal/mol)')
        ax.set_title(f'{length} nt');ax.axhline(0,color='gray',lw=1);ax.grid(alpha=.2);ax.legend()
    fig.suptitle(f'CPU search variability: {len(config["sequence_seeds"])} inputs/length, '
                 f'{len(config["search_seeds"])} searches/input/beam; {config["optimization"]["steps"]} proposals')
    fig.tight_layout();plot=run/'search_variability.png'
    if plot.exists():
        backup=run/'archive'/timestamp()/plot.name;backup.parent.mkdir(parents=True);shutil.copy2(plot,backup)
    fig.savefig(plot,dpi=160);plt.close(fig)
    lines=['# CPU search-seed robustness study','',f'Run: `{run}`','',
           f'{summary["completed_runs"]}/{summary["planned_runs"]} complete; statuses: {summary["status_counts"]}.','',
           f'{len(config["sequence_seeds"])} mixed input seeds, {len(config["search_seeds"])} search seeds per input, paired beams 200/400, '
           f'{config["optimization"]["steps"]} proposals/search, mutation cap {config["optimization"]["max_mutations"]} positions. Each selected output requires independent '
           'ViennaRNA improvement. Input references are shared within the run; repeated searches are '
           'not independent input samples. CPU folds only; no training.','',
           '| Length | Beam | Inputs | Searches | Validated candidates | Selected finalists | Returned inputs | Mean input-mean selected change | SD across input means |',
           '|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    def fmt(v):return 'unavailable' if v is None else f'{v:.4f}'
    for row in groups:
        values=[str(row[k]) for k in ['length','beam_size','input_count','search_runs','validated_candidates','selected_finalists','returned_inputs']]
        values += [fmt(row[k]) for k in ['mean_input_mean_selected_delta_kcal_mol','sd_input_mean_selected_delta_kcal_mol']]
        lines.append('| '+' | '.join(values)+' |')
    lines+=['',f'![Search variability]({os.path.relpath(plot,ROOT/"reports")})','',
            '## Within-input variation','',
            '| Length | Beam | Input seed | Selected / searches | Mean selected change | SD across searches | Best | Worst | Candidate worsenings | Distinct selected sequences |',
            '|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|']
    for row in inputs:
        values=[str(row[k]) for k in ['length','beam_size','sequence_seed']]
        values += [f'{row["selected_finalists"]}/{row["search_runs"]}']
        values += [fmt(row[k]) for k in ['mean_selected_delta_kcal_mol','sd_selected_delta_kcal_mol','min_selected_delta_kcal_mol','max_selected_delta_kcal_mol']]
        values += [str(row['candidate_worsenings']),str(row['distinct_selected_sequences'])]
        lines.append('| '+' | '.join(values)+' |')
    execution=summary.get('execution',{})
    rerun=(f'.venv/bin/python scripts/run_robustness_batches.py --config {args.config} --workers {execution["max_cpu_jobs"]}'
           if execution.get('mode')=='independent_input_batches' else f'./scripts/rnastable evaluate --config {args.config}')
    lines += ['', 'Energy changes are kcal/mol; lower is better. Candidate worsenings remain visible '
              'even though selection returns the input. Unknown measurements stay missing; denominator '
              'fields in the CSV expose failures and known selected energies. Group means give each '
              'measured input equal weight after averaging its search repeats. Standard deviations are '
              'descriptive, not confidence intervals or significance tests.','',
              f'Only {len(config["sequence_seeds"])} synthetic inputs at each of {config["lengths"]} nt were studied. This study does not establish '
              'biological stability or generalize to other inputs/lengths. One fold per '
              'timing observation includes startup; reference reuse is not repeated timing.','',
              '```bash',rerun,
              f'.venv/bin/python scripts/summarize_robustness.py --config {args.config} --name {args.name}',
              f'.venv/bin/python scripts/verify_robustness.py --summary results/evaluation_{args.name}_summary.json','```','']
    if summary.get('execution'):
        lines+=['','Execution: '+json.dumps(summary['execution']),
                'Concurrent CPU wall times include contention and must not be compared with isolated folding benchmarks.','']
    prefix='evaluation_'+args.name
    for name,rows,fields in [(prefix+'.csv',summary['rows'],FIELDS),
                            (prefix+'_inputs.csv',inputs,INPUT_FIELDS),
                            (prefix+'_groups.csv',groups,GROUP_FIELDS),
                            (prefix+'_pairs.csv',pairs,PAIR_FIELDS)]:
        buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=fields,extrasaction='ignore')
        writer.writeheader();writer.writerows(rows);write_artifact(ROOT/'results'/name,buf.getvalue())
    write_artifact(ROOT/'results'/(prefix+'_summary.json'),json.dumps({**summary,
        'per_input_variability':inputs,'input_weighted_groups':groups,'paired_comparisons':pairs,
        'variability_plot':str(plot)},indent=2,allow_nan=False)+'\n')
    report=ROOT/'reports'/('search_'+args.name+'_report.md')
    write_artifact(report,'\n'.join(lines))
    print('Search robustness report saved:',report)


if __name__=='__main__':main()
