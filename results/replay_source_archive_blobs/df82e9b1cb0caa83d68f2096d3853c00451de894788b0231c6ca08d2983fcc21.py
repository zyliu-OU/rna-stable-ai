"""Render saved measurements without rerunning or replacing benchmark data."""
import json
from pathlib import Path
from .artifacts import write_artifact


def render_benchmark_report(root, summary):
    root = Path(root)
    reports = root/'reports'
    config = summary['config']
    stamp = summary['utc']
    folding, gpu = summary['folding'], summary['gpu']
    gpu_python = summary['gpu_interpreter']
    ROOT = root
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
              'Next: compare computational structures with `rnastable compare-folds` and test constrained CPU mutation search with `rnastable optimize`. Training remains deferred.']
    quality_path = root/'results/folding_quality_summary.json'
    if quality_path.exists():
        quality = json.loads(quality_path.read_text())
        if quality.get('source_utc') == summary['utc']:
            compared = [r for r in quality['rows'] if r['status']=='ok']
            lines += ['', '## Subsequent folding-quality assessment', '',
                      f'{len(compared)}/{len(quality["rows"])} reference comparisons completed. See [folding_quality_report.md](folding_quality_report.md). The original benchmark measurements above remain unchanged.', '']
            for kind in ('structured', 'mixed'):
                scores = [r['pair_f1'] for r in compared if r['kind']==kind]
                if scores:
                    lines.append(f'- {kind}: pair F1 range {min(scores):.3f}–{max(scores):.3f} against ViennaRNA computed structures.')
            retried = [r['sequence_id'] for r in compared if r['baseline_origin']=='retry']
            if retried:
                lines.append('- Successful longer-timeout reference retries: '+', '.join(retried)+'.')
    optimization_path = root/'results/optimization_history_summary.json'
    if optimization_path.exists():
        opt = json.loads(optimization_path.read_text())
        if opt.get('input_sha256') in {m['sha256'] for m in summary['synthetic_manifest']}:
            lines += ['', '## Subsequent constrained search', '',
                      f'{opt["length"]} nt; {opt["search"]["accepted_steps"]} accepted proposals; {opt["mutations_from_input"]} changed positions. LinearFold energy change: {opt.get("linearfold_energy_delta_kcal_mol")} kcal/mol; ViennaRNA change: {opt["vienna_energy_delta_kcal_mol"]} kcal/mol. Constraints passed: {opt["constraints_passed"]}.', '',
                      'See [optimization_history_report.md](optimization_history_report.md). This is one synthetic example of computed-energy optimization, with no training or biological validation.', '']
    sweep_path = root/'results/evaluation_sweep_summary.json'
    if sweep_path.exists():
        sweep = json.loads(sweep_path.read_text())
        lines += ['', '## Supplemental CPU seed/beam evaluation', '',
                  f'{sweep["completed_runs"]}/{sweep["planned_runs"]} runs; statuses: {sweep["status_counts"]}. Lengths: {sweep["config"]["lengths"]}; proposal budget: {sweep["config"]["optimization"]["steps"]}.', '',
                  'See [evaluation_sweep_report.md](evaluation_sweep_report.md) for per-beam quality, independent ViennaRNA energy validation, timing, and paired-sample limitations. The original benchmark remains unchanged.', '']
    write_artifact(reports/'benchmark_report.md', '\n'.join(lines)+'\n')
