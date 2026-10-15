"""Prospective, paired proposal-budget comparison with explicit CPU costs."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

from .artifacts import publish, timestamp, write_artifact
from .portfolio import build_portfolio
from .sweep import fingerprint, load_sweep_config, plan_jobs, provenance, run_sweep


def arm_specs(spec, base_path):
    if spec.get('schema_version') != 1:
        raise ValueError('Expected equal-budget schema_version 1')
    seeds = spec['restart_search_seeds']
    if (not isinstance(seeds, list) or len(seeds) < 2 or len(seeds) != len(set(seeds))
            or any(type(s) is not int or s < 0 for s in seeds)):
        raise ValueError('At least two unique nonnegative restart seeds are required')
    short, long = spec['steps_per_restart'], spec['long_steps']
    if type(short) is not int or type(long) is not int or short < 1 or long != short*len(seeds):
        raise ValueError('Long steps must equal restart count times steps_per_restart')
    if type(spec['beam_size']) is not int or spec['beam_size'] < 1:
        raise ValueError('One fixed positive beam is required')
    overrides = spec.get('optimization_overrides', {})
    if set(overrides) & {'steps', 'seed', 'beam_size'}:
        raise ValueError('Set steps, seeds and beam through the study fields')
    common = {k: spec[k] for k in ('lengths', 'kinds', 'sequence_seeds')}
    common.update(beam_sizes=[spec['beam_size']], optimization_config=str(base_path))
    return {
        'long': {**common, 'search_seeds': [seeds[0]],
                 'optimization_overrides': {**overrides, 'steps': long}},
        'restarts': {**common, 'search_seeds': seeds,
                     'optimization_overrides': {**overrides, 'steps': short}}}


def measured_sum(rows, key):
    values = [r.get(key) for r in rows]
    return (sum(values) if all(type(v) in (int, float) and math.isfinite(v) and v >= 0
                               for v in values) else None)


def fold_requests(rows):
    """Count requests to folding adapters; unavailable tools may not spawn a process."""
    if any(not r.get('summary_path') for r in rows):
        return {'baseline': None, 'proposals': None, 'reference': None, 'validation': None}
    baseline = proposals = validation = 0
    for row in rows:
        evidence = json.loads(Path(row['summary_path']).read_text())
        baseline += 1
        proposals += sum(h['status'] not in ('duplicate', 'no_legal_proposal') for h in evidence['search']['history'])
        validation += int(evidence['search']['status'] == 'completed'
                          and row['finalist_sha256'] != row['input_sha256'])
    return {'baseline': baseline, 'proposals': proposals,
            'reference': sum(not r['reference_reused'] for r in rows), 'validation': validation}


def compare_arms(spec, sweeps, portfolios):
    maps = {name: {(r['kind'], r['length'], r['sequence_seed']): r for r in portfolios[name]['rows']}
            for name in ('long', 'restarts')}
    expected = {(k, n, s) for k in spec['kinds'] for n in spec['lengths'] for s in spec['sequence_seeds']}
    if any(set(maps[name]) != expected or len(maps[name]) != len(portfolios[name]['rows']) for name in maps):
        raise ValueError('Portfolio input coverage does not match the prespecified study')
    rows = []
    for key in sorted(expected):
        left, right = maps['long'][key], maps['restarts'][key]
        if left['input_sha256'] != right['input_sha256']:
            raise ValueError('Arms must use the exact same input sequence')
        before = [r['input_vienna_energy_kcal_mol'] for r in (left, right)]
        if all(v is not None for v in before) and abs(before[0]-before[1]) > 1e-9:
            raise ValueError('Arm reference energies disagree')
        result = dict(zip(('kind', 'length', 'sequence_seed'), key), input_sha256=left['input_sha256'])
        valid = True
        for name, portfolio in [('long', left), ('restarts', right)]:
            group = [r for r in sweeps[name]['rows'] if (r['kind'], r['length'], r['sequence_seed']) == key]
            planned_count = 1 if name == 'long' else len(spec['restart_search_seeds'])
            expected_seeds = [spec['restart_search_seeds'][0]] if name == 'long' else spec['restart_search_seeds']
            if (len(group) != planned_count or sorted(r['search_seed'] for r in group) != sorted(expected_seeds)
                    or any(r['beam_size'] != spec['beam_size'] or r['input_sha256'] != left['input_sha256'] for r in group)):
                raise ValueError('Search observations differ from the fixed study plan')
            attempted = sum(r.get('steps_attempted', 0) for r in group)
            if attempted > spec['long_steps']:
                raise ValueError('Attempted proposals exceed the study budget')
            validated = sum(r['status'] == 'validated' for r in group)
            valid &= validated == planned_count and portfolio['selected_vienna_delta_kcal_mol'] is not None
            result.update({f'{name}_searches': len(group), f'{name}_validated_candidates': validated,
                           f'{name}_planned_proposals': spec['long_steps'],
                           f'{name}_attempted_proposals': attempted,
                           f'{name}_selected_delta_kcal_mol': portfolio['selected_vienna_delta_kcal_mol'],
                           f'{name}_selected_fasta': portfolio['selected_fasta'],
                           f'{name}_selected_job_id': portfolio['selected_job_id'],
                           f'{name}_search_wall_seconds': measured_sum(group, 'search_wall_seconds'),
                           f'{name}_validation_wall_seconds': measured_sum(group, 'finalist_validation_wall_seconds'),
                           f'{name}_reference_wall_seconds': measured_sum([r for r in group if not r['reference_reused']], 'reference_wall_seconds')})
            result.update({f'{name}_{key}_fold_requests': value for key, value in fold_requests(group).items()})
        delta = (right['selected_vienna_delta_kcal_mol']-left['selected_vienna_delta_kcal_mol']) if valid else None
        result.update(comparison_status='measured' if valid else 'incomplete_validation',
                      restart_minus_long_kcal_mol=delta,
                      winner=('restarts' if delta < -1e-9 else 'long' if delta > 1e-9 else 'tie') if delta is not None else 'unknown')
        rows.append(result)
    aggregates = []
    for length in sorted(spec['lengths']):
        group = [r for r in rows if r['length'] == length]
        values = [r['restart_minus_long_kcal_mol'] for r in group if r['comparison_status'] == 'measured']
        aggregates.append({'length': length, 'planned_inputs': len(group), 'measured_pairs': len(values),
                           'unknown_pairs': len(group)-len(values),
                           'winners': dict(Counter(r['winner'] for r in group)),
                           'mean_restart_minus_long_kcal_mol': statistics.mean(values) if values else None})
    return rows, aggregates


def run_budget_study(root, config_path, resume=None):
    root, config_path = Path(root).resolve(), Path(config_path).resolve()
    spec = json.loads(config_path.read_text())
    arms = arm_specs(spec, (config_path.parent/spec['optimization_config']).resolve())
    signature = fingerprint(spec)
    current = {**provenance(), 'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'portfolio_sha256': hashlib.sha256(Path(__file__).with_name('portfolio.py').read_bytes()).hexdigest()}
    if resume:
        run = Path(resume).resolve()
        if not run.is_relative_to(root/'results/equal_budget_runs'):
            raise ValueError('Resume must be under this output root/results/equal_budget_runs')
        manifest = json.loads((run/'manifest.json').read_text())
        if manifest['config_sha256'] != signature or manifest['provenance'] != current:
            raise ValueError('Resume rejected: study, code or environment changed')
        for name in arms:
            if json.loads((run/name/'config.json').read_text()) != arms[name]:
                raise ValueError('Resume rejected: frozen arm configuration changed')
    else:
        run = root/'results/equal_budget_runs'/timestamp()
        run.mkdir(parents=True, exist_ok=False)
        validated = {}
        for name, arm in arms.items():
            directory = run/name
            directory.mkdir()
            (directory/'config.json').write_text(json.dumps(arm, indent=2)+'\n')
            validated[name] = load_sweep_config(directory/'config.json')
        manifest = {'utc': timestamp(), 'run_dir': str(run), 'config': spec,
                    'config_path': str(config_path), 'config_sha256': signature,
                    'provenance': current, 'arm_order': ['long', 'restarts'],
                    'arms': {name: {'config': arms[name], 'jobs': plan_jobs(validated[name])} for name in arms},
                    'selection_policy': 'lowest_confirmed_vienna_energy_then_job_id_v1',
                    'budget_definition': 'Equal proposed-mutation attempt caps; baseline folds and reference validations are extra.'}
        (run/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(f'Prespecified CPU equal-budget study: {run}', flush=True)
    sweeps, portfolios, attempts, errors = {}, {}, {}, {}
    for name in manifest['arm_order']:
        directory = run/name
        prior = sorted((directory/'results/sweep_runs').glob('*/manifest.json'))
        start = time.perf_counter()
        write_artifact(run/'status.json', json.dumps({'complete': False, 'active_arm': name,
                                                     'errors': errors}, indent=2)+'\n')
        try:
            print(f'CPU budget arm: {name}', flush=True)
            sweeps[name] = run_sweep(directory, directory/'config.json', prior[-1].parent if prior else None)
            portfolios[name] = build_portfolio(directory, directory/'results/evaluation_sweep_summary.json')
        except (ValueError, OSError, KeyError) as exc:
            errors[name] = f'{type(exc).__name__}: {exc}'
            print(f'Arm {name} failed: {errors[name]}', flush=True)
        except KeyboardInterrupt:
            write_artifact(run/'status.json', json.dumps({'complete': False, 'interrupted_arm': name}, indent=2)+'\n')
            raise
        finally:
            attempts[name] = {'wall_seconds': time.perf_counter()-start, 'resumed': bool(prior)}
            write_artifact(run/'attempts'/timestamp()/f'{name}.json', json.dumps(attempts[name], indent=2)+'\n')
    if errors:
        write_artifact(run/'status.json', json.dumps({'complete': False, 'errors': errors}, indent=2)+'\n')
        raise ValueError(f'Study has failed arms; evidence preserved at {run}: {errors}')
    rows, aggregates = compare_arms(spec, sweeps, portfolios)
    sources = {name: {} for name in arms}
    for name in arms:
        for kind, relative in [('sweep', 'results/evaluation_sweep_summary.json'),
                               ('portfolio', 'results/portfolio_summary.json')]:
            path = run/name/relative
            sources[name][kind] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    summary = {'utc': timestamp(), 'run_dir': str(run), 'mode': 'prospective_cpu_equal_proposal_budget',
               'complete': True, 'config': spec, 'config_sha256': signature,
               'manifest_sha256': hashlib.sha256((run/'manifest.json').read_bytes()).hexdigest(),
               'sources': sources, 'latest_execution_attempts': attempts,
               'rows': rows, 'aggregates': aggregates,
               'limitations': ['Equal proposal caps do not imply equal CPU time or total folding calls.',
                               'Search wall time includes LinearFold baseline; do not add it twice.',
                               'Restarts require additional baselines and candidate validations; both arms include one input reference per input.',
                               'Duplicate and no-legal-proposal events need not invoke a fold; actual fold counts are audited separately.',
                               'Serial fixed arm order and single timing observations preclude a speedup claim.',
                               'Unknown or failed candidate validations exclude a paired outcome, even when input fallback is available.',
                               'Synthetic 1,000/2,000-nt pilot only; no generalization to long RNA or biological stability.',
                               'No neural training or GPU folding.']}
    (run/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    lines = ['# Prospective equal-proposal-budget CPU pilot', '', f'Run: `{run}`', '',
             f'One {spec["long_steps"]}-proposal search versus {len(spec["restart_search_seeds"])} '
             f'restarts of {spec["steps_per_restart"]} proposals; beam {spec["beam_size"]}.', '',
             '| Length | Input seed | Long change | Restart change | Restart minus long | Winner |',
             '|---:|---:|---:|---:|---:|---|']
    for row in rows:
        lines.append('| '+' | '.join('unknown' if row[k] is None else str(round(row[k], 4)) if isinstance(row[k], float) else str(row[k])
                                    for k in ('length','sequence_seed','long_selected_delta_kcal_mol',
                                              'restarts_selected_delta_kcal_mol','restart_minus_long_kcal_mol','winner'))+' |')
    lines += ['', 'Energy changes are kcal/mol; negative restart minus long favors restarts. '
              'Repeated searches are selected within each input before paired comparison.', '',
              'Per-input search/reference/validation seconds are separate columns in equal_budget.csv. '
              'Full proposal and folding-call budgets are independently audited.', '', *summary['limitations'], '']
    publish(root, 'equal_budget', summary, rows, list(rows[0]), '\n'.join(lines))
    write_artifact(run/'status.json', json.dumps({'complete': True, 'errors': {}}, indent=2)+'\n')
    print(json.dumps({'run_dir': str(run), 'paired_inputs': len(rows), 'aggregates': aggregates}, indent=2))
    return summary
