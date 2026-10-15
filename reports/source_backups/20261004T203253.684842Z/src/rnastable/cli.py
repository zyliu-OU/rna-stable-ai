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
    lines = ['# RNA-StableAI V1 benchmark report', '', f'Run UTC: {stamp}', '',
             '## CPU folding benchmarks', '',
             f'Status counts: {summary["folding_status"]}. Timeout: {config["timeout_seconds"]} s/tool/sequence; address-space cap: {config["memory_limit_gib"]} GiB/process.', '',
             '| Tool | Sequence | Status | Wall seconds | Peak RSS MiB | MFE kcal/mol | Ensemble energy kcal/mol |',
             '|---|---|---|---:|---:|---:|---:|']
    for row in folding:
        lines.append('| ' + ' | '.join(str(row.get(k, '')) for k in ('tool', 'sequence_id', 'status', 'wall_seconds', 'peak_rss_mib', 'mfe_kcal_mol', 'ensemble_free_energy_kcal_mol'))+' |')
    lines += ['', '## Separate PyTorch encoder baseline', '',
              'Median forward times after warmup. CPU wall time excludes tokenization; GPU CUDA event time excludes H2D transfer. Transfer measures pinned-memory H2D copy into a preallocated tensor. GPU memory includes model, inputs and inference activations; reserved memory is reported separately. Batch size is fixed by configuration.', '',
              f'Interpreter: `{gpu_python or sys.executable}`', '',
              '| Length | Batch | Status | CPU seconds | GPU seconds | Transfer seconds | Peak GPU MiB |',
              '|---:|---:|---|---:|---:|---:|---:|']
    for row in gpu:
        lines.append('| ' + ' | '.join(str(row.get(k, '')) for k in ('length', 'batch_size', 'status', 'cpu_seconds', 'gpu_seconds', 'transfer_seconds', 'peak_gpu_memory_mib'))+' |')
    lines += ['', '## Errors and limitations', '']
    lines += ['- '+s for s in summary['limitations']]
    lines += ['- '+s for s in sorted(set(row['error'] for row in folding+gpu if row.get('error')))]
    if (reports/'installation_summary.md').exists():
        lines += ['', (reports/'installation_summary.md').read_text()]
    lines += ['', '## Reproduce', '', '```bash', 'cd '+str(ROOT),
              './scripts/rnastable benchmark --config configs/benchmark.json' + (f' --gpu-python {gpu_python}' if gpu_python else ''), '```', '',
              'Next: install the missing folding tools and Python 3.12 once downloads are accessible, then rerun and assess approximate fold quality against ViennaRNA at shorter lengths before adding optimization.']
    (reports/'benchmark_report.md').write_text('\n'.join(lines)+'\n')
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
    commands.add_parser('doctor')
    args = parser.parse_args(argv)
    try:
        if args.command == 'doctor':
            print(json.dumps(versions(), indent=2))
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
