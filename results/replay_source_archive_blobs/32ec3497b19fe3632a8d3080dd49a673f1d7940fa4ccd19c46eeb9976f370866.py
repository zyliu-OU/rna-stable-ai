"""Audit frozen supplied-reference inputs, metrics, coverage and exports."""
import csv
import json
from pathlib import Path

from .reference import (FIELDS, LIMITATIONS, NAME, aggregate_rows, digest,
                        evaluate_rows, load_inputs, render_report)


def require(condition, message):
    if not condition:
        raise ValueError(f'Reference audit rejected: {message}')


def audit_reference(summary_path):
    summary_path = Path(summary_path).resolve()
    summary = json.loads(summary_path.read_text())
    require(summary.get('mode') == 'supplied_reference_structure_evaluation' and summary.get('complete') is True,
            'not a completed supplied-reference evaluation')
    run = Path(summary['run_dir']).resolve()
    manifest_path = run/'manifest.json'
    require(digest(manifest_path.read_bytes()) == summary['manifest_sha256'], 'frozen manifest hash changed')
    manifest = json.loads(manifest_path.read_text())
    require(manifest['schema_version'] == 1 and manifest['run_dir'] == str(run), 'manifest identity differs')
    for key in ('utc', 'dataset_id', 'sources', 'provenance', 'policy'):
        require(summary[key] == manifest[key], f'{key} differs from frozen manifest')
    require(manifest['policy'] == 'exact_pairs_complete_dot_bracket_macro_by_method_and_reference_kind_v1',
            'unsupported scoring policy')
    for name in ('references', 'predictions'):
        record = manifest['sources'][name]
        require(Path(record['path']).resolve() == run/(name + '.json'), 'input snapshot is outside the run')
        require(digest(Path(record['path']).read_bytes()) == record['sha256'], f'frozen {name} changed')
    references, predictions, _ = load_inputs(run/'references.json', run/'predictions.json')
    require(references['dataset_id'] == summary['dataset_id'], 'dataset identity differs')
    require(manifest['methods'] == predictions['methods'], 'method plan differs')
    require(manifest['reference_ids'] == [r['id'] for r in references['records']], 'reference plan differs')
    expected_rows = evaluate_rows(references, predictions)
    require(summary['rows'] == expected_rows, 'rows, metrics or missing/failed denominators differ')
    require(summary['aggregates'] == aggregate_rows(expected_rows), 'aggregate values or coverage differ')
    require(summary['limitations'] == LIMITATIONS, 'interpretation differs')
    frozen_summary = run/'results'/f'{NAME}_summary.json'
    require(json.loads(frozen_summary.read_text()) == summary, 'summary differs from per-run export')
    # Check retained exports as well as the requested publication.
    expected = [{k: '' if row[k] is None else str(row[k]) for k in FIELDS} for row in expected_rows]
    for csv_path in {summary_path.parent/f'{NAME}.csv', run/'results'/f'{NAME}.csv'}:
        with csv_path.open(newline='') as stream:
            reader = csv.DictReader(stream)
            require(reader.fieldnames == FIELDS, 'CSV columns differ')
            actual = list(reader)
        require(actual == expected, 'CSV rows differ')
    for report_path in {summary_path.parent.parent/'reports'/f'{NAME}_report.md',
                        run/'reports'/f'{NAME}_report.md'}:
        require(report_path.read_text() == render_report(summary), 'report differs')
    result = {'audit': 'passed', 'planned_predictions': len(expected_rows),
              'measured_predictions': sum(r['status'] == 'ok' for r in expected_rows),
              'run_dir': str(run)}
    print(json.dumps(result, indent=2))
    return result
