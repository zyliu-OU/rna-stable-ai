#!/usr/bin/env python3
"""Compare audited context configurations on identical reused development splits."""
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import publish,timestamp
from rnastable.reference import digest
from rnastable.reference_audit import require
from verify_context_development import audit_context


def main():
    paths=sorted((ROOT/'results/context_development_runs').glob('*/summary.json'))
    if len(paths)!=3:raise ValueError('Expected the three planned context configurations')
    summaries=[audit_context(p) for p in paths]
    inputs=None;rows=[]
    for p,s in zip(paths,summaries):
        run=Path(s['run_dir']);fingerprints={name:digest((run/name).read_bytes()) for name in ('train.json','validation.json')}
        if inputs is None:inputs=fingerprints
        require(fingerprints==inputs,'comparison development splits differ')
        trained={a['reference_kind']:a for a in s['aggregates'] if a['method']=='trained_context'}
        rows.append({'run_dir':s['run_dir'],'max_pair_span':s['config']['max_pair_span'],'positive_weight_exponent':s['config'].get('positive_weight_exponent',.5),'selected_epoch':s['selected_epoch'],'validation_records':s['counts']['validation'],'validation_mean_pair_f1':s['selected_validation_pair_f1'],'pdb_validation_pair_f1':trained['experimental']['mean_pair_f1'],'comparative_validation_pair_f1':trained['computational']['mean_pair_f1'],'comparative_validation_recall':trained['computational']['mean_pair_recall'],'excluded_train_contacts':s['excluded_train_contacts'],'excluded_validation_contacts':s['excluded_validation_contacts'],'summary_sha256':digest(p.read_bytes())})
    # Configuration ranking uses validation mean F1 only; stable input order breaks ties.
    best=max(range(len(rows)),key=lambda i:rows[i]['validation_mean_pair_f1'])
    run=ROOT/'results/context_comparison_runs'/timestamp();run.mkdir(parents=True)
    summary={'complete':True,'run_dir':str(run),'test_evaluated':False,'split_sha256':inputs,'rows':rows,'selected_run_dir':rows[best]['run_dir'],'selection_policy':'Highest record-weighted reused-validation pair F1; ties prefer earlier run. This is development selection, not independent evaluation.','sources':{str(p):digest(p.read_bytes()) for p in paths},'limitations':['Three configurations, one fixed seed, reused validation: no significance or fresh-test accuracy claim.','64-span and 128-span candidate coverage differs and is reported.','PDB-derived and comparative annotations are mixed; family identities of PDB records remain unresolved.']}
    os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'results/.matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for row,s in zip(rows,summaries):
        label=f"span {row['max_pair_span']}, weight power {row['positive_weight_exponent']}"
        axes[0].plot([h['epoch'] for h in s['history']],[h['validation_mean_pair_f1'] for h in s['history']],marker='o',label=label)
    axes[0].set(xlabel='Epoch',ylabel='Mean pair F1',title='Reused development validation');axes[0].legend(fontsize=8)
    labels=[f"{r['max_pair_span']} / {r['positive_weight_exponent']}" for r in rows];positions=list(range(len(rows)))
    axes[1].bar([x-.18 for x in positions],[r['pdb_validation_pair_f1'] for r in rows],width=.36,label='PDB-derived (12)')
    axes[1].bar([x+.18 for x in positions],[r['comparative_validation_pair_f1'] for r in rows],width=.36,label='Comparative (23)')
    axes[1].set(xticks=positions,xticklabels=labels,xlabel='Pair span / weight exponent',ylabel='Mean pair F1',ylim=(0,1),title='Selected checkpoints by annotation source');axes[1].legend(fontsize=8)
    figure=run/'development_comparison.png';fig.savefig(figure,dpi=160);plt.close(fig)
    summary['figure']=str(figure);summary['figure_sha256']=digest(figure.read_bytes())
    (run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    report=['# Context development comparison','',f'Selected development run: `{summary["selected_run_dir"]}`','',summary['selection_policy'],'','| Span | Weight power | Mean validation F1 | PDB-derived F1 | Comparative F1 | Excluded val contacts |','|---|---|---|---|---|---|']
    for r in rows:report.append(f"| {r['max_pair_span']} | {r['positive_weight_exponent']} | {r['validation_mean_pair_f1']:.4f} | {r['pdb_validation_pair_f1']:.4f} | {r['comparative_validation_pair_f1']:.4f} | {r['excluded_validation_contacts']} |")
    report+=['',f'Figure: `{figure}`','',*summary['limitations'],'']
    publish(ROOT,'context_development_comparison',summary,rows,list(rows[0]),'\n'.join(report))
    print(json.dumps({'run_dir':str(run),'selected_run_dir':summary['selected_run_dir'],'rows':rows},indent=2))

if __name__=='__main__':main()
