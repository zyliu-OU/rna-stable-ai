"""Paired CPU evaluation across synthetic inputs, search seeds and beam sizes."""
from collections import Counter
import csv
import hashlib
import io
import itertools
import json
import os
from pathlib import Path
import statistics
import time

from .artifacts import publish, sha256, timestamp, write_artifact
from .folding import fold_sequence
from .optimization import (check_constraints, hamming, load_optimization_config,
                           optimize_sequence, validate_optimization_config)
from .scoring import structure_agreement
from .sequences import generate_sequence, read_fasta, write_fasta
from .selection import select_finalist

TOOLS_ROOT = Path(__file__).resolve().parents[2]
FIELDS = ['job_id', 'kind', 'length', 'sequence_seed', 'search_seed', 'beam_size', 'status', 'error',
          'input_sha256', 'finalist_sha256', 'steps_attempted', 'accepted_steps', 'failed_proposals',
          'mutations_from_input', 'constraints_passed', 'input_pair_f1', 'finalist_pair_f1',
          'input_energy_gap_kcal_mol', 'finalist_energy_gap_kcal_mol',
          'linearfold_delta_kcal_mol', 'vienna_delta_kcal_mol', 'vienna_delta_kcal_mol_per_nt',
          'vienna_improvement_confirmed', 'input_lf_wall_seconds', 'search_wall_seconds',
          'reference_wall_seconds', 'reference_reused', 'finalist_validation_wall_seconds',
          'summary_path', 'finalist_fasta', 'selected_fasta', 'selected_sha256',
          'selected_mutations_from_input', 'selection_source', 'selection_reason',
          'selected_vienna_delta_kcal_mol']
AGG_FIELDS = ['kind', 'length', 'beam_size', 'planned_runs', 'completed_runs', 'validated_runs',
              'failed_runs', 'confirmed_improvements', 'unchanged', 'worsened', 'improvement_fraction_validated',
              'mean_vienna_delta_kcal_mol_per_nt', 'sd_vienna_delta_kcal_mol_per_nt',
              'median_input_pair_f1', 'median_finalist_pair_f1', 'median_input_lf_wall_seconds',
              'median_search_wall_seconds', 'median_mutations_from_input']


def fingerprint(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':')))


def load_sweep_config(path):
    path = Path(path).resolve()
    spec = json.loads(path.read_text())
    for key in ('lengths', 'sequence_seeds', 'search_seeds', 'beam_sizes', 'kinds'):
        values = spec[key]
        if not isinstance(values, list) or not values or len(values) != len(set(values)):
            raise ValueError(f'{key} must be a nonempty unique list')
    if any(type(n) is not int or not 1000 <= n <= 10000 for n in spec['lengths']):
        raise ValueError('Sweep lengths must be integer values from 1000 to 10000')
    for key in ('sequence_seeds', 'search_seeds', 'beam_sizes'):
        lower = 1 if key == 'beam_sizes' else 0
        if any(type(n) is not int or n < lower for n in spec[key]):
            raise ValueError(f'Invalid {key}')
    if set(spec['kinds']) - {'structured', 'mixed'}:
        raise ValueError('Unsupported synthetic kind')
    base = load_optimization_config(path.parent/spec['optimization_config'])
    overrides = spec.get('optimization_overrides', {})
    if set(overrides)-set(base):
        raise ValueError('Unknown optimization override')
    spec['optimization'] = validate_optimization_config({**base, **overrides})
    if spec['optimization']['preserve_protein']:
        raise ValueError('Synthetic sweep uses noncoding controls; use optimize --coding for annotated CDS inputs')
    return spec


def plan_jobs(spec):
    return [{'job_id': f'{kind}_{n}_seq{seed}_search{search}_beam{beam}', 'kind': kind,
             'length': n, 'sequence_seed': seed, 'search_seed': search, 'beam_size': beam}
            for n, kind, seed, search, beam in itertools.product(spec['lengths'], spec['kinds'],
            spec['sequence_seeds'], spec['search_seeds'], spec['beam_sizes'])]


def provenance():
    from .cli import versions
    paths = [TOOLS_ROOT/'src/rnastable'/name for name in
             ('sweep.py','optimization.py','folding.py','scoring.py','sequences.py','selection.py')]
    paths += [TOOLS_ROOT/'external/LinearFold/bin/linearfold_v']
    return {'versions': versions(), 'file_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                                   for p in paths if p.is_file()}}


def aggregate_rows(rows, jobs):
    """Keep planned/failed denominators explicit; missing validation is never a zero."""
    aggregates = []
    for kind, length, beam in sorted({(j['kind'], j['length'], j['beam_size']) for j in jobs}):
        group = [r for r in rows if (r['kind'], r['length'], r['beam_size']) == (kind,length,beam)]
        validated = [r for r in group if r['status']=='validated']
        delta = [r['vienna_delta_kcal_mol_per_nt'] for r in validated]
        improved = sum(r['vienna_delta_kcal_mol'] < -1e-9 for r in validated)
        worsened = sum(r['vienna_delta_kcal_mol'] > 1e-9 for r in validated)
        row = dict(kind=kind, length=length, beam_size=beam,
                   planned_runs=sum((j['kind'],j['length'],j['beam_size'])==(kind,length,beam) for j in jobs),
                   completed_runs=len(group), validated_runs=len(validated), failed_runs=len(group)-len(validated),
                   confirmed_improvements=improved, unchanged=len(validated)-improved-worsened, worsened=worsened,
                   improvement_fraction_validated=improved/len(validated) if validated else None,
                   mean_vienna_delta_kcal_mol_per_nt=statistics.mean(delta) if delta else None,
                   sd_vienna_delta_kcal_mol_per_nt=statistics.stdev(delta) if len(delta)>1 else None)
        for output, key in [('median_input_pair_f1','input_pair_f1'), ('median_finalist_pair_f1','finalist_pair_f1'),
                            ('median_input_lf_wall_seconds','input_lf_wall_seconds'),
                            ('median_search_wall_seconds','search_wall_seconds'), ('median_mutations_from_input','mutations_from_input')]:
            values = [r[key] for r in validated if r.get(key) is not None]
            row[output] = statistics.median(values) if values else None
        aggregates.append(row)
    return aggregates


def run_cell(job, original, spec, run_dir, reference, reference_reused):
    config = {**spec['optimization'], 'seed': job['search_seed'], 'beam_size': job['beam_size']}
    attempt = run_dir/'jobs'/job['job_id']/timestamp()
    attempt.mkdir(parents=True)
    write_fasta(attempt/'input.fasta', job['job_id']+'_input', original)
    row = {**job, 'status': 'error', 'input_sha256': sha256(original),
           'reference_reused': reference_reused, 'reference_wall_seconds': reference.get('wall_seconds')}
    def evaluator(sequence, step):
        return fold_sequence(TOOLS_ROOT, sequence, config, 'LinearFold', attempt/f'step_{step:04d}.txt')
    start = time.perf_counter()
    search = optimize_sequence(original, config, evaluator)
    row['search_wall_seconds'] = time.perf_counter()-start
    finalist = search.pop('sequence')
    check_constraints(finalist, original, config)
    path = write_fasta(attempt/'finalist.fasta', job['job_id']+'_finalist', finalist)
    row.update(finalist_sha256=sha256(finalist), finalist_fasta=str(path), constraints_passed=True,
               steps_attempted=len(search['history']), accepted_steps=search['accepted_steps'],
               failed_proposals=sum(r['status'] not in ('ok','duplicate','no_legal_proposal') for r in search['history']),
               mutations_from_input=hamming(original, finalist), input_lf_wall_seconds=search['baseline'].get('wall_seconds'))
    validated = None
    if search['status'] != 'completed':
        row.update(status='search_failed', error=search['baseline'].get('error', search['baseline']['status']))
    else:
        row['linearfold_delta_kcal_mol'] = search['best']['mfe_kcal_mol']-search['baseline']['mfe_kcal_mol']
        if reference['status']=='ok':
            row['input_pair_f1'] = structure_agreement(search['baseline']['structure'], reference['structure'])['pair_f1']
            row['input_energy_gap_kcal_mol'] = search['baseline']['mfe_kcal_mol']-reference['mfe_kcal_mol']
        if finalist == original:
            validated = dict(reference, reused_input_result=True)
            row['finalist_validation_wall_seconds'] = 0.0
        else:
            validation_config = {**config, 'timeout_seconds': config['finalist_timeout_seconds']}
            validated = fold_sequence(TOOLS_ROOT, finalist, validation_config, 'ViennaRNA', attempt/'finalist_ViennaRNA.txt')
            row['finalist_validation_wall_seconds'] = validated.get('wall_seconds')
        if reference['status']=='ok' and validated['status']=='ok':
            delta = validated['mfe_kcal_mol']-reference['mfe_kcal_mol']
            row.update(status='validated', vienna_delta_kcal_mol=delta, vienna_delta_kcal_mol_per_nt=delta/len(original),
                       vienna_improvement_confirmed=delta < -1e-9,
                       finalist_pair_f1=structure_agreement(search['best']['structure'],validated['structure'])['pair_f1'],
                       finalist_energy_gap_kcal_mol=search['best']['mfe_kcal_mol']-validated['mfe_kcal_mol'])
        else:
            row.update(status='validation_failed', error=f'Input ViennaRNA={reference["status"]}: {reference.get("error", "")}; finalist={validated["status"]}: {validated.get("error", "")}')
    selection = select_finalist(original, finalist, search['status'], reference, validated)
    selected = finalist if selection['source'] == 'finalist' else original
    check_constraints(selected, original, config)
    selected_path = write_fasta(attempt/'selected.fasta', job['job_id']+'_selected', selected)
    row.update(selected_fasta=str(selected_path), selected_sha256=sha256(selected),
               selected_mutations_from_input=hamming(selected, original),
               selection_source=selection['source'], selection_reason=selection['reason'],
               selected_vienna_delta_kcal_mol=selection['selected_vienna_delta_kcal_mol'])
    evidence = {'job': job, 'config': config, 'input_sha256': sha256(original), 'row': row,
                'selection': selection,
                'reference': reference, 'validation': validated, 'search': search}
    row['summary_path'] = str(attempt/'summary.json')
    (attempt/'summary.json').write_text(json.dumps(evidence, indent=2, allow_nan=False)+'\n')
    return row


def plot_tradeoffs(run_dir, rows, aggregates):
    os.environ.setdefault('MPLCONFIGDIR', str(run_dir/'matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    lengths = sorted({r['length'] for r in aggregates})
    fig, axes = plt.subplots(len(lengths),3, figsize=(13,4*len(lengths)), squeeze=False)
    for index, length in enumerate(lengths):
        for kind, color in [('mixed','#3268ab'), ('structured','#bd5b35')]:
            group = [r for r in aggregates if r['length']==length and r['kind']==kind]
            beams = [r['beam_size'] for r in group]
            for ax, key in [(axes[index,0],'median_input_pair_f1'), (axes[index,1],'median_input_lf_wall_seconds'),
                            (axes[index,2],'mean_vienna_delta_kcal_mol_per_nt')]:
                ax.plot(beams, [r[key] for r in group], 'o-', color=color, label=kind)
                ax.set_xlabel('Beam size'); ax.grid(alpha=0.2)
        axes[index,0].set_ylabel('Median input pair F1 vs ViennaRNA'); axes[index,0].set_ylim(0,1.05)
        axes[index,1].set_ylabel('Median input LinearFold wall time (s)')
        axes[index,2].set_ylabel('Mean ViennaRNA energy change / nt'); axes[index,2].axhline(0,color='gray',lw=1)
        axes[index,0].set_title(f'{length} nt'); axes[index,0].legend()
    fig.suptitle('CPU synthetic pilot: lower energy change is better; small paired sample')
    fig.tight_layout()
    path = run_dir/'sweep_tradeoffs.png'
    if path.exists():
        import shutil
        backup = run_dir/'archive'/timestamp()/path.name
        backup.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,backup)
    fig.savefig(path,dpi=160); plt.close(fig)
    return str(path)


def export_sweep(root, spec, run_dir, rows, jobs, manifest, complete):
    aggregates = aggregate_rows(rows,jobs)
    summary = {'utc': manifest['utc'], 'config': spec, 'config_sha256': manifest['config_sha256'],
               'provenance': manifest['provenance'], 'run_dir': str(run_dir),
               'planned_runs': len(jobs), 'completed_runs': len(rows), 'complete': complete,
               'status_counts': dict(Counter(r['status'] for r in rows)), 'rows': rows, 'aggregates': aggregates,
               'limitations': ['CPU folding/search only; no neural training.',
                  'Synthetic pilot, not experimental stability validation.',
                  'Beam comparisons share input sequences and search seeds; observations are paired.',
                  'Search seeds repeat the same input, so runs are not independent biological samples.',
                  'Single timed fold per input/beam; startup is included. Reference times are reused, not independent timing replicates.',
                  'Missing validation is excluded from energy averages and exposed in failure counts. No statistical significance claim.']}
    if complete and any(r['status']=='validated' for r in rows):
        try:
            summary['plot'] = plot_tradeoffs(run_dir,rows,aggregates)
        except (ImportError,OSError,ValueError) as exc:
            summary['plot_error'] = str(exc)
    lines = ['# CPU evaluation sweep', '', f'Run: `{run_dir}`', '',
             f'{len(rows)}/{len(jobs)} runs completed; statuses: {summary["status_counts"]}.', '',
             f'Lengths: {spec["lengths"]}; sequence seeds: {spec["sequence_seeds"]}; search seeds: {spec["search_seeds"]}; beam sizes: {spec["beam_sizes"]}; proposal budget: {spec["optimization"]["steps"]}.', '',
             '| Kind | Length | Beam | Validated / planned | Improved | Unchanged | Worsened | Median input pair F1 | Median LF seconds | Mean Vienna delta / nt |',
             '|---|---:|---:|---|---:|---:|---:|---:|---:|---:|']
    def fmt(v):
        return '' if v is None else f'{v:.5f}'
    for row in aggregates:
        lines.append(f'| {row["kind"]} | {row["length"]} | {row["beam_size"]} | {row["validated_runs"]}/{row["planned_runs"]} | {row["confirmed_improvements"]} | {row["unchanged"]} | {row["worsened"]} | {fmt(row["median_input_pair_f1"])} | {fmt(row["median_input_lf_wall_seconds"])} | {fmt(row["mean_vienna_delta_kcal_mol_per_nt"])} |')
    if summary.get('plot'):
        relative = os.path.relpath(summary['plot'], Path(root)/'reports')
        lines += ['', f'![CPU sweep tradeoffs]({relative})', '']
    lines += ['', 'Negative ViennaRNA deltas mean lower computed MFE. Independent validation can contradict the LinearFold surrogate. Aggregation is separated by sequence kind, length and beam; unknown results stay missing.', '',
              'Use each job\'s selected.fasta as the output: only a confirmed ViennaRNA improvement selects the finalist. Otherwise it contains the original input. Retained finalist scores, failure statuses and aggregate improvement/worsening counts above describe search candidates before selection.', '', '## Limitations', '']
    lines += ['- '+s for s in summary['limitations']]
    lines += ['', '## Resume this run', '', '```bash', f'./scripts/rnastable evaluate --config {manifest["config_path"]} --resume {run_dir}', '```', '']
    publish(root,'evaluation_sweep',summary,rows,FIELDS,'\n'.join(lines))
    buf = io.StringIO(newline=''); writer=csv.DictWriter(buf,fieldnames=AGG_FIELDS)
    writer.writeheader(); writer.writerows(aggregates)
    write_artifact(Path(root)/'results/evaluation_sweep_aggregate.csv',buf.getvalue())
    write_artifact(run_dir/'summary.json',json.dumps(summary,indent=2,allow_nan=False)+'\n')
    return summary


def run_sweep(root, config_path, resume=None):
    root = Path(root).resolve()
    spec = load_sweep_config(config_path)
    signature = fingerprint(spec)
    jobs = plan_jobs(spec)
    current_provenance = provenance()
    if resume:
        run_dir = Path(resume).resolve()
        if not run_dir.is_relative_to(root/'results/sweep_runs'):
            raise ValueError('Resume directory must be under this output root/results/sweep_runs')
        manifest = json.loads((run_dir/'manifest.json').read_text())
        if manifest['config_sha256'] != signature or manifest['provenance'] != current_provenance:
            raise ValueError('Resume rejected: configuration, code, tool binary or environment versions changed')
    else:
        stamp = timestamp()
        run_dir = root/'results/sweep_runs'/stamp
        run_dir.mkdir(parents=True)
        manifest = {'utc': stamp, 'config': spec, 'config_sha256': signature, 'provenance': current_provenance,
                    'jobs': jobs, 'config_path': str(Path(config_path).resolve())}
        (run_dir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    rows = []
    references = {}
    for job in jobs:
        cell_dir = run_dir/'jobs'/job['job_id']
        existing = sorted(cell_dir.glob('*/summary.json')) if cell_dir.exists() else []
        if existing:
            evidence = json.loads(existing[-1].read_text())
            row = evidence['row']
            original = generate_sequence(job['length'],job['kind'],job['sequence_seed'])
            if evidence['job'] != job or row['input_sha256'] != sha256(original):
                raise ValueError('Resume rejected: saved job identity/input changed')
            candidate = read_fasta(row['finalist_fasta'])[0][1]
            if sha256(candidate) != row['finalist_sha256']:
                raise ValueError('Resume rejected: finalist FASTA changed')
            check_constraints(candidate,original,evidence['config'])
            if 'selection' in evidence:
                decision = select_finalist(original,candidate,evidence['search']['status'],
                                           evidence['reference'],evidence['validation'])
                selected = read_fasta(row['selected_fasta'])[0][1]
                expected = candidate if decision['source']=='finalist' else original
                if evidence['selection'] != decision or selected != expected or sha256(selected) != row['selected_sha256']:
                    raise ValueError('Resume rejected: selected output or decision changed')
                check_constraints(selected,original,evidence['config'])
            rows.append(row)
            print(f'Sweep resume {len(rows)}/{len(jobs)}: {job["job_id"]}',flush=True)
            continue
        original = generate_sequence(job['length'],job['kind'],job['sequence_seed'])
        digest = sha256(original)
        write_fasta(run_dir/'inputs'/f'{job["kind"]}_{job["length"]}_seed{job["sequence_seed"]}.fasta',
                    f'{job["kind"]}_{job["length"]}_seed{job["sequence_seed"]}',original)
        reference_path = run_dir/'references'/f'{digest}.json'
        reference_path.parent.mkdir(parents=True,exist_ok=True)
        reused = digest in references or reference_path.exists()
        if digest not in references:
            if reference_path.exists():
                stored = json.loads(reference_path.read_text())
                if stored['sequence_sha256'] != digest:
                    raise ValueError('Cached reference input hash mismatch')
                references[digest] = stored['result']
            else:
                reference_config = {**spec['optimization'],'timeout_seconds': spec['optimization']['finalist_timeout_seconds']}
                ref = fold_sequence(TOOLS_ROOT,original,reference_config,'ViennaRNA',run_dir/'references'/f'{digest}.txt')
                reference_path.write_text(json.dumps({'sequence_sha256':digest,'result':ref},indent=2)+'\n')
                references[digest] = ref
        print(f'Sweep {len(rows)+1}/{len(jobs)}: {job["job_id"]}',flush=True)
        try:
            row = run_cell(job,original,spec,run_dir,references[digest],reused)
        except (ValueError,OSError,KeyError) as exc:
            row = {**job,'status':'error','input_sha256':digest,'error':f'{type(exc).__name__}: {exc}'}
        rows.append(row)
        with (run_dir/'progress.jsonl').open('a') as f:
            f.write(json.dumps({'utc':timestamp(),'row':row})+'\n')
        write_artifact(run_dir/'checkpoint.json',json.dumps({'completed_jobs':len(rows),'rows':rows},indent=2)+'\n')
    summary = export_sweep(root,spec,run_dir,rows,jobs,manifest,complete=True)
    print(json.dumps({k:summary[k] for k in ('run_dir','planned_runs','completed_runs','status_counts')},indent=2))
    return summary
