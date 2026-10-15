#!/usr/bin/env python3
"""Publish a separate measured long-RNA scaling report and standalone figure."""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp,write_artifact
from rnastable.sweep import FIELDS,AGG_FIELDS
parser=argparse.ArgumentParser()
parser.add_argument('--summary',type=Path,default=ROOT/'results/evaluation_sweep_summary.json')
args=parser.parse_args()
s=json.loads(args.summary.read_text())
if sorted(s['config']['lengths']) != [2000,5000,10000] or s['config']['beam_sizes'] != [200]:
    parser.error('Expected the beam-200 long pilot at 2000, 5000, 10000 nt')
if not s['complete']:
    parser.error('Sweep is incomplete; resume it before publishing the final report')
config=s['config']
opt=config['optimization']
if len(config['sequence_seeds'])!=1 or len(config['search_seeds'])!=1:
    parser.error('This scaling report requires one sequence/search seed per kind and length')
run=Path(s['run_dir'])
os.environ.setdefault('MPLCONFIGDIR',str(run/'matplotlib-cache'))
os.environ.setdefault('XDG_CACHE_HOME',str(ROOT/'external/cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(1,3,figsize=(13,4))
for kind,color in [('structured','#bd5b35'),('mixed','#3268ab')]:
    rows=sorted((r for r in s['rows'] if r['kind']==kind),key=lambda r:r['length'])
    for ax,key in [(axes[0],'input_lf_wall_seconds'),(axes[1],'input_pair_f1'),(axes[2],'vienna_delta_kcal_mol_per_nt')]:
        measured=[r for r in rows if r.get(key) is not None]
        ax.plot([r['length'] for r in measured],[r[key] for r in measured],'o-',color=color,label=kind)
        ax.set_xlabel('Sequence length (nt)');ax.grid(alpha=0.2)
axes[0].set_ylabel('Input LinearFold CPU wall time (s)');axes[0].legend()
axes[1].set_ylabel('Input pair F1 vs ViennaRNA');axes[1].set_ylim(0,1.05)
axes[2].set_ylabel('ViennaRNA energy change (kcal/mol/nt)');axes[2].axhline(0,color='gray',lw=1)
fig.suptitle(f'Beam 200, {opt["steps"]} proposals per search: one synthetic input per kind/length')
fig.tight_layout()
plot=run/'long_scaling.png'
if plot.exists():
    backup=run/'archive'/timestamp()/plot.name;backup.parent.mkdir(parents=True);shutil.copy2(plot,backup)
fig.savefig(plot,dpi=160);plt.close(fig)
lines=['# Long-RNA CPU scaling pilot','',f'Run: `{run}`','',
       f'Completed: {s["completed_runs"]}/{s["planned_runs"]}; statuses: {s["status_counts"]}.','',
       f'Beam 200; {opt["steps"]} mutation proposals; input seed {config["sequence_seeds"][0]}; search seed {config["search_seeds"][0]}. Mutation limit {opt["max_mutations"]} positions. GC and nucleotide counts are preserved. LinearFold timeout {opt["timeout_seconds"]} s; ViennaRNA timeout {opt["finalist_timeout_seconds"]} s; address-space limit {opt["memory_limit_gib"]} GiB/process.','',
       '| Kind | Length | Status | LF seconds | Input Vienna seconds | Final Vienna seconds | Input pair F1 | Finalist pair F1 | LF delta kcal/mol | Vienna delta kcal/mol | Changes |',
       '|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|']
def fmt(value):
    return '' if value is None else f'{value:.4f}'
for row in s['rows']:
    values=[row['kind'],str(row['length']),row['status']]
    values += [fmt(row.get(key)) for key in ['input_lf_wall_seconds','reference_wall_seconds',
               'finalist_validation_wall_seconds','input_pair_f1','finalist_pair_f1','linearfold_delta_kcal_mol','vienna_delta_kcal_mol']]
    values.append(str(row.get('mutations_from_input','')))
    lines.append('| '+' | '.join(values)+' |')
lines += ['',f'![Long sequence scaling]({os.path.relpath(plot,ROOT/"reports")})','',
          'Negative energy changes mean lower computed MFE, not demonstrated biological stability. Zero finalist validation time means an unchanged sequence reused its input result. Unknown/failed results remain blank. Individual raw folds, mutation histories, hashes and constraints are retained in each job summary.','',
          '## Limits and next step','',
          'This pilot uses one sequence/search seed per kind and length. No confidence intervals or population claims are supported. Its budget differs from the earlier 24-step 1,000-nt sweep. These are CPU folds; the GPU encoder remains a separate inference baseline. No training was performed.','',
          'Next, replicate the long inputs across seeds and application-specific constraints before treating the optimizer as a biological design tool. Keep ViennaRNA validation even when the LinearFold surrogate improves.','',
          '```bash','./scripts/rnastable evaluate --config configs/evaluation_long.json',
          '.venv/bin/python scripts/verify_sweep.py','.venv/bin/python scripts/summarize_long.py','```','']
for suffix,rows,fields in [('.csv',s['rows'],FIELDS),('_aggregate.csv',s['aggregates'],AGG_FIELDS)]:
    buf=io.StringIO(newline='')
    writer=csv.DictWriter(buf,fieldnames=fields,extrasaction='ignore')
    writer.writeheader();writer.writerows(rows)
    write_artifact(ROOT/'results'/('evaluation_long'+suffix),buf.getvalue())
write_artifact(ROOT/'results/evaluation_long_summary.json',json.dumps({**s,'long_scaling_plot':str(plot)},indent=2,allow_nan=False)+'\n')
write_artifact(ROOT/'reports/long_sequence_report.md','\n'.join(lines))
print('Long-pilot report saved:',ROOT/'reports/long_sequence_report.md')
print('Scaling figure:',plot)
