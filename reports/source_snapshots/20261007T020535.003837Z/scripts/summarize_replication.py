#!/usr/bin/env python3
"""Publish the measured long mixed-RNA paired beam study separately from the pilot."""
import argparse
import csv
import io
import json
import os
import shutil
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.artifacts import timestamp, write_artifact
from rnastable.replication import PAIR_FIELDS, paired_comparisons
from rnastable.sweep import FIELDS, AGG_FIELDS, load_sweep_config, plan_jobs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, default=ROOT/'results/evaluation_sweep_summary.json')
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text())
    expected = load_sweep_config(ROOT/'configs/evaluation_replication.json')
    if summary['config'] != expected or not summary['complete']:
        parser.error('Expected a complete evaluation_replication.json study')
    if [r['job_id'] for r in summary['rows']] != [j['job_id'] for j in plan_jobs(expected)]:
        parser.error('Study rows do not match the complete planned grid')
    pairs = paired_comparisons(summary['rows'])
    run = Path(summary['run_dir'])
    os.environ.setdefault('MPLCONFIGDIR', str(run/'matplotlib-cache'))
    os.environ.setdefault('XDG_CACHE_HOME', str(ROOT/'external/cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 3, figsize=(13, 10), squeeze=False)
    metrics = [('median_input_pair_f1', 'Median input pair F1 vs ViennaRNA'),
               ('median_input_lf_wall_seconds', 'Median input LinearFold CPU seconds'),
               ('mean_vienna_delta_kcal_mol_per_nt', 'Mean ViennaRNA energy change / nt')]
    for index, length in enumerate(expected['lengths']):
        group = sorted([r for r in summary['aggregates'] if r['length'] == length],
                       key=lambda r: r['beam_size'])
        for ax, (key, label) in zip(axes[index], metrics):
            measured = [r for r in group if r.get(key) is not None]
            ax.plot([r['beam_size'] for r in measured], [r[key] for r in measured], 'o-')
            ax.set_xlabel('Beam size'); ax.set_ylabel(label); ax.grid(alpha=.2)
        axes[index, 0].set_ylim(0, 1.05); axes[index, 0].set_title(f'{length} nt')
        axes[index, 2].axhline(0, color='gray', lw=1)
    fig.suptitle('Mixed synthetic RNA on CPU: three inputs per length, eight proposals per search')
    fig.tight_layout()
    plot = run/'replication_tradeoffs.png'
    if plot.exists():
        backup = run/'archive'/timestamp()/plot.name
        backup.parent.mkdir(parents=True); shutil.copy2(plot, backup)
    fig.savefig(plot, dpi=160); plt.close(fig)
    summary['replication_plot'] = str(plot)
    lines = ['# Long mixed-RNA CPU replication and beam comparison', '',
             f'Run: `{summary["run_dir"]}`', '',
             f'Completed {summary["completed_runs"]}/{summary["planned_runs"]}; statuses: {summary["status_counts"]}.', '',
             'Three seeded mixed inputs at each length; one search seed; eight mutation proposals per search. '
             'Beams 200 and 400 share the exact input and search seed. Search trajectories may diverge. '
             'All nucleotide counts, GC content and length are preserved; maximum 40 changed positions. '
             'CPU LinearFold timeout 120 s; CPU ViennaRNA validation timeout 600 s; address-space cap 8 GiB/process.', '',
             '| Length | Beam | Validated / planned | Improved | Unchanged | Worsened | Median input F1 | Median LF seconds | Mean Vienna change / nt |',
             '|---:|---:|---|---:|---:|---:|---:|---:|---:|']
    def fmt(value):
        return 'unavailable' if value is None else f'{value:.5f}'
    for row in summary['aggregates']:
        lines.append('| '+' | '.join([str(row['length']), str(row['beam_size']),
                     f'{row["validated_runs"]}/{row["planned_runs"]}', str(row['confirmed_improvements']),
                     str(row['unchanged']), str(row['worsened']), fmt(row['median_input_pair_f1']),
                     fmt(row['median_input_lf_wall_seconds']), fmt(row['mean_vienna_delta_kcal_mol_per_nt'])])+' |')
    lines += ['', f'![CPU beam tradeoffs]({os.path.relpath(plot, ROOT/"reports")})']
    lines += ['', '## Paired differences: beam 400 minus beam 200', '',
              '| Length | Input seed | Input F1 change | LF time ratio (400/200) | Vienna change difference kcal/mol |',
              '|---:|---:|---:|---:|---:|']
    for row in pairs:
        lines.append('| '+' | '.join([str(row['length']),str(row['sequence_seed']),
                     fmt(row['input_pair_f1_change']),fmt(row['input_lf_time_ratio']),
                     fmt(row['vienna_delta_difference_kcal_mol'])])+' |')
    lines += ['', 'Positive F1 differences indicate closer agreement with ViennaRNA; negative energy '
              'differences indicate a larger computed improvement at beam 400. A larger beam is not '
              'guaranteed to improve either measure. Failures remain missing and appear in status counts.', '',
              '## Limits', '',
              'Three synthetic inputs per length do not establish population performance or biological '
              'stability. One search seed does not measure search variability. Timing includes process '
              'startup and has no repeated timing trials. Shared ViennaRNA reference timings are not '
              'independent measurements. This study covers mixed RNA; structured RNA retains its earlier '
              'single-seed pilot. No training was performed.', '',
              'Retain independent ViennaRNA checks. The next implementation should return the original '
              'sequence unless the finalist has a confirmed reference-energy improvement; preserve '
              'rejected finalists and all validation failures as evidence. Select a beam only after '
              'reviewing agreement, runtime and validated energy together, then test multiple search '
              'seeds with annotated application constraints before any training decision.', '',
              '```bash', './scripts/rnastable evaluate --config configs/evaluation_replication.json',
              '.venv/bin/python scripts/summarize_replication.py',
              '.venv/bin/python scripts/verify_sweep.py --summary results/evaluation_replication_summary.json',
              '.venv/bin/python scripts/verify_replication.py',
              '```', '']
    for name, rows, fields in [('evaluation_replication.csv', summary['rows'], FIELDS),
                               ('evaluation_replication_aggregate.csv', summary['aggregates'], AGG_FIELDS),
                               ('evaluation_replication_pairs.csv', pairs, PAIR_FIELDS)]:
        buf = io.StringIO(newline='')
        writer = csv.DictWriter(buf, fieldnames=fields, extrasaction='ignore')
        writer.writeheader(); writer.writerows(rows)
        write_artifact(ROOT/'results'/name, buf.getvalue())
    write_artifact(ROOT/'results/evaluation_replication_summary.json',
                   json.dumps({**summary, 'paired_comparisons': pairs}, indent=2, allow_nan=False)+'\n')
    write_artifact(ROOT/'reports/replication_report.md', '\n'.join(lines))
    print('Replication report saved:', ROOT/'reports/replication_report.md')


if __name__ == '__main__':
    main()
