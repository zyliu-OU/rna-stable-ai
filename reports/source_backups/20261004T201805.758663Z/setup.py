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
            run(install + ['numpy', 'scipy', 'pandas', 'biopython', 'psutil', 'tqdm', 'pyyaml', 'pytest', 'matplotlib', 'ViennaRNA'], local_env)
            # CUDA wheel runtime is project-local. Driver visibility must be verified separately.
            run(install + ['torch', '--index-url', 'https://download.pytorch.org/whl/cu130'], local_env)
            result = run(install + ['--no-deps', '--no-build-isolation', '-e', '.'], local_env)
            if result.returncode:
                run(install + ['setuptools'], local_env)
                run(install + ['--no-deps', '--no-build-isolation', '-e', '.'], local_env)
            run([str(python), '-c', 'import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())'], local_env)
            freeze = run([uv, 'pip', 'freeze', '--python', str(python)] if uv else [str(python), '-m', 'pip', 'freeze'], local_env)
            if freeze.returncode == 0:
                stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')
                (ROOT/'reports'/f'environment-{stamp}.lock.txt').write_text(freeze.stdout)
    else:
        print('Python 3.12 unavailable; .venv not created. Continuing tool attempts.')
    for name, url, builddir in (
        ('LinearFold', 'https://github.com/LinearFold/LinearFold.git', ''),
        ('LinearPartition', 'https://github.com/LinearFold/LinearPartition.git', ''),
        ('EternaFold', 'https://github.com/WaymentSteeleLab/EternaFold.git', 'src')):
        target = ROOT/'external'/name
        if not target.exists():
            run(['git', 'clone', url, str(target)], local_env)
        if (target/'.git').exists():
            run(['git', '-C', str(target), 'rev-parse', 'HEAD'], local_env)
            run(['make', '-C', str(target/builddir), '-j4'], local_env)
    print('Inspect reports/commands.jsonl for exact failures; no system installation changed.')

if __name__ == '__main__':
    main()
