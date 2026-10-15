import argparse
from collections import Counter
import csv
import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import os
from .sequences import generate_dataset
from .folding import benchmark_folding, FIELDS as FOLD_FIELDS
from .gpu import benchmark_gpu, FIELDS as GPU_FIELDS

ROOT = Path(__file__).resolve().parents[2]

def load_config(path):
    config = json.loads(Path(path).read_text())
    for key in ('lengths', 'kinds'):
        if not config[key] or len(config[key]) != len(set(config[key])):
            raise ValueError(f'{key} must be nonempty and unique')
    if any(type(n) is not int or not 1 <= n <= 10000 for n in config['lengths']):
        raise ValueError('V1 supports integer lengths from 1 to 10000')
    if set(config['kinds']) - {'structured', 'mixed'}:
        raise ValueError('Unsupported sequence kind')
    for key in ('batch_size', 'repeats', 'cpu_threads', 'beam_size', 'embedding_dim', 'channels'):
        if type(config[key]) is not int or config[key] < 1:
            raise ValueError(f'{key} must be a positive integer')
    if type(config['warmup']) is not int or config['warmup'] < 0:
        raise ValueError('warmup must be nonnegative integer')
    for key in ('timeout_seconds', 'memory_limit_gib'):
        if not isinstance(config[key], (int, float)) or not 0 < config[key] < float('inf'):
            raise ValueError(f'{key} must be finite and positive')
    # LinearFold-V/LinearPartition-V use their fixed 37 C parameterization.
    if config['temperature_c'] != 37:
        raise ValueError('V1 comparison requires temperature_c=37')
    return config

def preserve(path, archive):
    if path.exists():
        archive.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, archive / path.name)

def write_csv(path, rows, fields):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)

def versions():
    result = {'python': platform.python_version(), 'executable': sys.executable, 'platform': platform.platform()}
    for package in ('RNA-StableAI', 'numpy', 'scipy', 'pandas', 'biopython', 'psutil', 'tqdm', 'pyyaml', 'pytest', 'matplotlib', 'torch', 'ViennaRNA'):
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result[package] = 'not installed in this interpreter'
    return result

def run_benchmarks(root, config, gpu_python=None):
    results, reports = root / 'results', root / 'reports'
    results.mkdir(parents=True, exist_ok=True); reports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    archive = results / 'runs' / stamp
    for path in (results / 'folding_benchmark.csv', results / 'gpu_benchmark.csv', results / 'benchmark_summary.json', reports / 'benchmark_report.md'):
        preserve(path, archive)
    manifest = generate_dataset(root / 'data/synthetic', config)
    folding = benchmark_folding(ROOT, manifest, config, results / 'raw' / stamp)
    if gpu_python:
        command = [gpu_python, '-m', 'rnastable.gpu', json.dumps(config)]
        try:
            r = subprocess.run(command, capture_output=True, text=True, timeout=max(120, config['timeout_seconds']),
                               env={**os.environ, 'PYTHONPATH': str(ROOT/'src'), 'PYTHONDONTWRITEBYTECODE': '1'})
            with (reports / 'commands.jsonl').open('a') as f:
                f.write(json.dumps({'command': command, 'returncode': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr})+'\n')
            if r.returncode:
                raise RuntimeError(r.stderr)
            gpu = json.loads(r.stdout)
        except Exception as exc:
            gpu = [dict(length=n, batch_size=config['batch_size'], status='error', error=str(exc)) for n in config['lengths']]
    else:
        gpu = benchmark_gpu(config)
    write_csv(results/'folding_benchmark.csv', folding, FOLD_FIELDS)
    write_csv(results/'gpu_benchmark.csv', gpu, GPU_FIELDS)
    summary = {'utc': stamp, 'config': config, 'config_sha256': hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
               'versions': versions(), 'gpu_interpreter': gpu_python or sys.executable,
               'synthetic_manifest': manifest, 'folding_status': dict(Counter(row['status'] for row in folding)),
               'gpu_status': dict(Counter(row['status'] for row in gpu)),
               'folding': folding, 'gpu': gpu,
               'limitations': ['CPU folding tools do not use GPU.',
                              'LinearFold-V energy is an approximate minimum; LinearPartition ensemble free energy is not MFE.',
                              'Synthetic structured controls contain designed stems, not verified secondary structures.',
                              'Encoder uses random fixed weights; inference throughput does not measure RNA stability.',
                              'No training performed; single folding replicate per sequence; no statistical speedup claim.']}
    (results/'benchmark_summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    from .reporting import render_benchmark_report
    render_benchmark_report(root, summary)
    print(json.dumps({k: summary[k] for k in ('folding_status', 'gpu_status')}, indent=2))
    return summary

def main(argv=None):
    parser = argparse.ArgumentParser(prog='rnastable')
    parser.add_argument('--version', action='version', version='RNA-StableAI 0.1.0')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('generate', 'benchmark'):
        sub = commands.add_parser(name)
        sub.add_argument('--config', type=Path, default=ROOT/'configs/benchmark.json')
        sub.add_argument('--output-root', type=Path, default=ROOT)
        if name == 'benchmark':
            sub.add_argument('--gpu-python', help='Optional read-only interpreter for encoder baseline; recorded separately')
    evaluation = commands.add_parser('evaluate', help='Paired CPU sweep over sequences, search seeds and beam sizes')
    evaluation.add_argument('--config',type=Path,default=ROOT/'configs/evaluation_sweep.json')
    evaluation.add_argument('--output-root',type=Path,default=ROOT)
    evaluation.add_argument('--resume',type=Path,help='Reuse completed cells only when inputs, config, code and tool versions match')
    portfolio = commands.add_parser('select-portfolio', help='Select the best validated output per input from a saved CPU sweep')
    portfolio.add_argument('--summary', type=Path, default=ROOT/'results/evaluation_robustness_long_summary.json')
    portfolio.add_argument('--output-root', type=Path, default=ROOT)
    budget = commands.add_parser('compare-search-budgets', help='Prospective CPU long-search versus restart study at equal proposal caps')
    budget.add_argument('--config', type=Path, default=ROOT/'configs/evaluation_equal_budget.json')
    budget.add_argument('--output-root', type=Path, default=ROOT)
    budget.add_argument('--resume', type=Path)
    budget.add_argument('--workers', type=int, choices=[1, 2], help='Batch independent inputs with this bounded CPU worker count')
    quality = commands.add_parser('compare-folds', help='Compare saved CPU folds against ViennaRNA')
    quality.add_argument('--summary', type=Path, default=ROOT/'results/benchmark_summary.json')
    quality.add_argument('--retry-timeout', type=float, help='Retry missing ViennaRNA references with this timeout')
    quality.add_argument('--output-root', type=Path, default=ROOT)
    reference = commands.add_parser('evaluate-reference', help='Score supplied reference structures and saved predictions; no folding')
    reference.add_argument('--references', type=Path, required=True)
    reference.add_argument('--predictions', type=Path, required=True)
    reference.add_argument('--dry-run', action='store_true', help='Validate exact input identity and the scoring plan without writing outputs')
    reference.add_argument('--output-root', type=Path, default=ROOT)
    optimize = commands.add_parser('optimize', help='Constrained CPU mutation search; no training')
    optimize.add_argument('--input', type=Path, default=ROOT/'data/synthetic/mixed_1000_seed1729.fasta')
    optimize.add_argument('--config', type=Path, default=ROOT/'configs/optimization.json')
    optimize.add_argument('--coding', action='store_true', help='Preserve translated protein in frame 0/code 1; full codons required')
    optimize.add_argument('--constraints',type=Path,help='Sequence-bound protected positions/regions JSON')
    optimize.add_argument('--dry-run',action='store_true',help='Validate input and constraints without folding')
    optimize.add_argument('--output-root', type=Path, default=ROOT)
    report = commands.add_parser('report', help='Refresh report from saved benchmark measurements')
    report.add_argument('--summary', type=Path, default=ROOT/'results/benchmark_summary.json')
    report.add_argument('--output-root', type=Path, default=ROOT)
    commands.add_parser('doctor')
    args = parser.parse_args(argv)
    try:
        if args.command == 'doctor':
            print(json.dumps(versions(), indent=2))
        elif args.command == 'select-portfolio':
            from .portfolio import build_portfolio
            build_portfolio(args.output_root, args.summary)
        elif args.command == 'compare-search-budgets':
            if args.workers is not None:
                from .budget_batches import run_budget_batches
                run_budget_batches(args.output_root, args.config, args.workers, args.resume)
            else:
                from .budget_study import run_budget_study
                run_budget_study(args.output_root, args.config, args.resume)
        elif args.command == 'evaluate':
            from .sweep import run_sweep
            run_sweep(args.output_root,args.config,args.resume)
        elif args.command == 'compare-folds':
            from .quality import compare_saved
            compare_saved(args.output_root.resolve(), args.summary, args.retry_timeout)
        elif args.command == 'evaluate-reference':
            from .reference import run_reference_evaluation
            run_reference_evaluation(args.output_root, args.references, args.predictions, args.dry_run)
        elif args.command == 'optimize':
            from .optimization import load_optimization_config, run_optimization
            config = load_optimization_config(args.config)
            if args.coding:
                config['preserve_protein'] = True
            if args.constraints or args.dry_run:
                from .sequences import read_fasta
                from .optimization import check_constraints
                records=read_fasta(args.input)
                if len(records)!=1:
                    raise ValueError('Optimization requires exactly one FASTA record')
                name,sequence=records[0]
                if not 1000<=len(sequence)<=10000:
                    raise ValueError('V1 optimization supports 1000–10000 nt')
                if args.constraints:
                    from .annotations import apply_constraints
                    config=apply_constraints(config,sequence,args.constraints)
                check_constraints(sequence,sequence,config)
            if args.dry_run:
                print(json.dumps({'mode':'input_validation_no_folding','input_id':name,
                    'length':len(sequence),'input_sha256':hashlib.sha256(sequence.encode()).hexdigest(),
                    'config':config},indent=2))
            else:
                run_optimization(args.output_root.resolve(), args.input, config)
        elif args.command == 'report':
            from .reporting import render_benchmark_report
            render_benchmark_report(args.output_root.resolve(), json.loads(args.summary.read_text()))
            print('Benchmark report refreshed from saved measurements')
        else:
            config = load_config(args.config)
            root = args.output_root.resolve()
            if args.command == 'generate':
                print(json.dumps(generate_dataset(root/'data/synthetic', config), indent=2))
            else:
                run_benchmarks(root, config, args.gpu_python)
    except (ValueError, OSError) as exc:
        parser.exit(2, f'rnastable: {exc}\n')
    return 0

if __name__ == '__main__':
    main()
