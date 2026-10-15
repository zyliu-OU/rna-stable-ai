#!/usr/bin/env python3
"""Project-local installation; never replace or clear an existing environment."""
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
(ROOT/'reports').mkdir(exist_ok=True)

def run(command, env=None):
    print('+ ' + ' '.join(command), flush=True)
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    with (ROOT/'reports/commands.jsonl').open('a') as f:
        f.write(json.dumps({'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            'command': command, 'returncode': result.returncode, 'output': result.stdout})+'\n')
    print(result.stdout, end='', flush=True)
    return result

def main():
    required_failures = []
    optional_failures = []
    local_env = {**os.environ, 'UV_CACHE_DIR': str(ROOT/'external/uv-cache'),
                 'UV_PYTHON_INSTALL_DIR': str(ROOT/'external/python'),
                 'PIP_CACHE_DIR': str(ROOT/'external/pip-cache'), 'PYTHONDONTWRITEBYTECODE': '1'}
    uv = shutil.which('uv')
    known = Path('/home/zyliu/anaconda3/envs/vllm-lab/bin/uv')
    if uv is None and known.is_file():
        uv = str(known)
    if uv is None:
        attempt = run([sys.executable, '-m', 'pip', 'install', '--retries', '0', '--target', 'external/uv-bootstrap', 'uv'], local_env)
        candidate = ROOT/'external/uv-bootstrap/bin/uv'
        if attempt.returncode == 0 and candidate.exists():
            uv = str(candidate)
    python = ROOT/'.venv/bin/python'
    if (ROOT/'.venv').exists():
        print('Preserving existing .venv. Check interpreter before installing.')
    elif uv:
        run([uv, 'venv', '--python', '3.12', '.venv'], local_env)
    elif shutil.which('python3.12'):
        run([shutil.which('python3.12'), '-m', 'venv', '.venv'], local_env)
    if python.exists():
        check = run([str(python), '-c', 'import sys; assert sys.version_info[:2] == (3,12); print(sys.version)'], local_env)
        if check.returncode == 0:
            install = [uv, 'pip', 'install', '--python', str(python)] if uv else [str(python), '-m', 'pip', 'install']
            core = run(install + ['numpy', 'scipy', 'pandas', 'biopython', 'psutil', 'tqdm', 'pyyaml', 'pytest', 'matplotlib', 'ViennaRNA'], local_env)
            if core.returncode:
                required_failures.append('Core Python dependencies: see commands.jsonl')
            # CUDA wheel runtime is project-local. Driver visibility must be verified separately.
            torch_install = run(install + ['torch', '--index-url', 'https://download.pytorch.org/whl/cu130'], local_env)
            if torch_install.returncode:
                required_failures.append('PyTorch installation: see commands.jsonl')
            result = run(install + ['--no-deps', '--no-build-isolation', '-e', '.'], local_env)
            if result.returncode:
                run(install + ['setuptools'], local_env)
                result = run(install + ['--no-deps', '--no-build-isolation', '-e', '.'], local_env)
            if result.returncode:
                required_failures.append('rnastable console entry point installation')
            run([str(python), '-c', 'import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())'], local_env)
            freeze = run([uv, 'pip', 'freeze', '--python', str(python)] if uv else [str(python), '-m', 'pip', 'freeze'], local_env)
            if freeze.returncode == 0:
                stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')
                (ROOT/'reports'/f'environment-{stamp}.lock.txt').write_text(freeze.stdout)
        else:
            required_failures.append('Existing .venv is not Python 3.12; preserved without installation')
    else:
        required_failures.append('Python 3.12 unavailable; .venv not created')
        print('Python 3.12 unavailable; .venv not created. Continuing tool attempts.')
    for name, url, builddir in (
        ('LinearFold', 'https://github.com/LinearFold/LinearFold.git', ''),
        ('LinearPartition', 'https://github.com/LinearFold/LinearPartition.git', ''),
        ('EternaFold', 'https://github.com/WaymentSteeleLab/EternaFold.git', 'src')):
        target = ROOT/'external'/name
        failures = optional_failures if name == 'EternaFold' else required_failures
        if not target.exists():
            clone = run(['git', 'clone', url, str(target)], local_env)
            if clone.returncode:
                failures.append(f'{name} clone failed: see commands.jsonl')
        if (target/'.git').exists():
            run(['git', '-C', str(target), 'rev-parse', 'HEAD'], local_env)
            build = run(['make', '-C', str(target/builddir), '-j4'], local_env)
            if build.returncode:
                failures.append(f'{name} build failed: see commands.jsonl')
        elif target.exists():
            failures.append(f'{name}: existing directory lacks Git checkout; preserved')
    status = {
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'incomplete' if required_failures else 'complete',
        'required_failures': required_failures,
        'optional_failures': optional_failures,
        'cuda_note': 'CUDA runtime availability is recorded in commands.jsonl; GPU unavailability does not fail CPU installation',
    }
    path = ROOT/'reports/setup_status.json'
    if path.exists():
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        shutil.copy2(path, path.with_name(f'setup_status-{stamp}.json'))
    path.write_text(json.dumps(status, indent=2)+'\n')
    print(json.dumps(status, indent=2))
    print('Inspect reports/commands.jsonl for exact failures; no system installation changed.')
    return 1 if required_failures else 0

if __name__ == '__main__':
    sys.exit(main())
