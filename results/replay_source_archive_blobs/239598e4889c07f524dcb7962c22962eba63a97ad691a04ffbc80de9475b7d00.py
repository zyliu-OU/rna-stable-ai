#!/usr/bin/env python3
"""Preserve the workspace and export a clean, auditable development snapshot."""
import hashlib
import json
from pathlib import Path
import re
import shutil
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    destination = ROOT / 'exports' / stamp / 'rna-stable-ai'
    destination.mkdir(parents=True, exist_ok=False)
    files = []
    roots = ['src', 'scripts', 'tests', 'configs', 'data', 'reports', 'results',
             'pyproject.toml', 'README.md', 'RESEARCH_USE_NOTICE.md']
    secret = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
    for item in roots:
        source = ROOT / item
        paths = sorted(source.rglob('*')) if source.is_dir() else [source]
        for path in paths:
            relative = path.relative_to(ROOT)
            if not path.is_file() or path.is_symlink():
                continue
            if any(part in {'__pycache__', '.pytest_cache', '.git', 'source_backups'}
                   or part.endswith('.egg-info') for part in relative.parts):
                continue
            if path.suffix in {'.pyc', '.pyo'}:
                continue
            content = path.read_bytes()
            if secret.search(content):
                raise RuntimeError(f'Possible credential: {relative}; export stopped')
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            files.append({'path': relative.as_posix(), 'bytes': len(content),
                          'sha256': hashlib.sha256(content).hexdigest()})
    readme = destination / 'README.md'
    text = readme.read_text()
    text = text.replace('# RNA-StableAI\n', '# RNA-StableAI\n\n**Status: work in progress — research prototype.** This repository records ongoing\n'
                        'development and measured experiments; no release or trained model is published.\n\n'
                        'The saved evidence retains its original host paths and timestamps. On another\n'
                        'machine, rerun the pipeline to produce local artifacts; historical audit scripts\n'
                        'may require those original paths. External tools and environments are installed\n'
                        'locally by setup and are not vendored in this repository.\n')
    text = text.replace('cd /home/zyliu/Documents/rna-stable-ai', 'cd rna-stable-ai')
    text = text.replace('successful installation produces a lock; this offline session did not produce a lock.',
                        'successful installation produces a lock. The recorded host freeze is included in reports/.')
    readme.write_text(text)
    (destination / '.gitignore').write_text('''# Local dependencies and machine state
.venv/
.tools/
.cache/
external/*
!external/.gitkeep
checkpoints/*
!checkpoints/.gitkeep
exports/
.agents/
.codex/
.aws/
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.env
.env.*
''')
    for folder in ['external', 'checkpoints']:
        (destination / folder).mkdir(exist_ok=True)
        (destination / folder / '.gitkeep').touch()
    manifest = {'created_utc': stamp, 'source_root': str(ROOT),
                'status': 'work_in_progress', 'release_created': False,
                'files': files, 'source_file_count': len(files),
                'source_bytes': sum(item['bytes'] for item in files),
                'notes': ['Copied files preserve original evidence. README adjusted for GitHub.',
                          'Original workspace and dependencies are untouched.',
                          'Historical absolute paths are retained; rerun artifacts on a new host.',
                          'No credential patterns found in exported content.']}
    (destination / 'EXPORT_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'snapshot': str(destination), 'files': len(files),
                      'bytes': manifest['source_bytes']}, indent=2))


if __name__ == '__main__':
    main()
