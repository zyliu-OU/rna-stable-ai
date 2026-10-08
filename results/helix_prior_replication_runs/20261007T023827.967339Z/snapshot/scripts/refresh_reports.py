#!/usr/bin/env python3
"""Update installation/report prose from recorded evidence, retaining old files."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.artifacts import write_artifact
from rnastable.reporting import render_benchmark_report

setup = json.loads((ROOT/'reports/setup_status.json').read_text())
summary = json.loads((ROOT/'results/benchmark_summary.json').read_text())
logs = [json.loads(line) for line in (ROOT/'reports/commands.jsonl').read_text().splitlines() if line.strip()]
lines = ['## Installation status from recorded evidence', '',
         f'Setup UTC: {setup["utc"]}; status: **{setup["status"]}**.', '',
         f'Benchmark UTC: {summary["utc"]}. Interpreter: `{summary["versions"]["executable"]}`.', '',
         '| Package | Recorded version |', '|---|---|']
for name, version in summary['versions'].items():
    if name not in ('platform','executable'):
        lines.append(f'| {name} | {version} |')
lines += ['', '### CPU tool builds', '']
for tool in ('LinearFold','LinearPartition','EternaFold'):
    builds = [row for row in logs if row.get('command', [''])[0] == 'make' and
              any(value.endswith('/'+tool) or value.endswith('/'+tool+'/src') for value in row.get('command', []))]
    commits = [row for row in logs if row.get('command', [''])[0] == 'git' and 'rev-parse' in row.get('command', []) and
               any(value.endswith('/'+tool) for value in row.get('command', []))]
    if builds:
        lines.append(f'- {tool}: latest recorded build exit code {builds[-1]["returncode"]}; Git commit `{commits[-1].get("output", "").strip() if commits else "unrecorded"}`.')
    else:
        lines.append(f'- {tool}: no recorded build result.')
lines += ['', f'Folding status counts: {summary["folding_status"]}. GPU encoder status counts: {summary["gpu_status"]}.', '']
gpu = summary['gpu']
if gpu:
    lines.append(f'The saved encoder run reports CUDA available: {gpu[0].get("cuda_available")}; GPU: {gpu[0].get("gpu_name", "unknown")}. This describes that run, not a fresh device probe in the restricted session.')
lines += ['', 'ViennaRNA was benchmarked through its CPU Python bindings; a standalone RNAfold binary was not used in this run. EternaFold was built but not benchmarked.', '',
          'Earlier session DNS/device failures are historical. Their exact outputs remain in commands.jsonl, and prior prose is archived before replacement. The original system_info.txt is the initial system snapshot.', '',
          'Successful package freeze: '+', '.join('`'+p.name+'`' for p in (ROOT/'reports').glob('environment-*.lock.txt'))+'.', '',
          'No driver, system CUDA, kernel/boot, system Python or other-project changes were made by these scripts. No training was performed.', '']
write_artifact(ROOT/'reports/installation_summary.md', '\n'.join(lines))
render_benchmark_report(ROOT, summary)
print('Installation summary and benchmark report refreshed; prior prose archived; measurements retained.')
