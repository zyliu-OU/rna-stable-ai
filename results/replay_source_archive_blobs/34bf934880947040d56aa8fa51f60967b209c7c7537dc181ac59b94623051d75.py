"""Evaluate supplied structures on exact sequences; never infer missing evidence."""
from collections import Counter
import hashlib
import json
from pathlib import Path

from .artifacts import publish, timestamp
from .scoring import paired_fraction, structure_agreement
from .sequences import validate_sequence

REFERENCE_KINDS = {'synthetic_control', 'computational', 'experimental'}
PREDICTION_STATUSES = {'ok', 'error', 'timeout', 'unavailable'}
METRICS = ['reference_pairs', 'predicted_pairs', 'shared_pairs', 'pair_precision',
           'pair_recall', 'pair_f1', 'pair_jaccard', 'base_pair_distance']
FIELDS = ['reference_id', 'method', 'reference_kind', 'source', 'length',
          'sequence_sha256', 'status', 'error', *METRICS]
NAME = 'reference_evaluation'
LIMITATIONS = [
    'Reference kinds and source descriptions are supplied by the caller, not independently verified.',
    'Only complete, pseudoknot-free dot-bracket structures using .() are supported; no projection or imputation.',
    'Metrics use exact base-pair coordinates; no alignment, offset tolerance or sequence mutation is permitted.',
    'Missing and failed predictions stay in planned denominators and have no metric values.',
    'Means describe measured inputs only, with one vote per reference within each method and reference kind.',
    'Agreement with supplied structures does not measure biological stability or experimental fitness.',
    'No folding, optimization, neural training or dataset download is performed.',
]


def digest(content):
    return hashlib.sha256(content).hexdigest()


def text_field(value, label):
    if not isinstance(value, str) or not value.strip() or any(c in value for c in '\n\r\t|'):
        raise ValueError(f'{label} must be nonempty single-line text without table separators')
    return value


def structure_field(value, sequence, label):
    if not isinstance(value, str):
        raise ValueError(f'{label} must be a dot-bracket string')
    paired_fraction(value, len(sequence))
    return value


def validate_inputs(references, predictions):
    """Validate the complete plan before creating any output directories."""
    for label, data in [('references', references), ('predictions', predictions)]:
        if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data['schema_version'] != 1:
            raise ValueError(f'{label} requires schema_version=1')
        if not isinstance(data.get('records'), list):
            raise ValueError(f'{label}.records must be a list')
    text_field(references.get('dataset_id'), 'dataset_id')
    if not references['records']:
        raise ValueError('At least one reference is required')
    index = {}
    for record in references['records']:
        if not isinstance(record, dict):
            raise ValueError('Reference records must be objects')
        identity = text_field(record.get('id'), 'reference id')
        if identity in index:
            raise ValueError(f'Duplicate reference id: {identity}')
        sequence = validate_sequence(record.get('sequence'))
        structure_field(record.get('structure'), sequence, 'reference structure')
        if not isinstance(record.get('reference_kind'), str) or record['reference_kind'] not in REFERENCE_KINDS:
            raise ValueError('reference_kind must be synthetic_control, computational or experimental')
        text_field(record.get('source'), 'reference source')
        index[identity] = record
    methods = predictions.get('methods')
    if not isinstance(methods, list) or not methods:
        raise ValueError('predictions.methods must be a nonempty list')
    for method in methods:
        text_field(method, 'method')
    if len(set(methods)) != len(methods):
        raise ValueError('Prediction methods must be unique')
    seen = set()
    for record in predictions['records']:
        if not isinstance(record, dict):
            raise ValueError('Prediction records must be objects')
        identity = text_field(record.get('id'), 'prediction id')
        method = text_field(record.get('method'), 'prediction method')
        if identity not in index or method not in methods:
            raise ValueError('Prediction id or method is outside the declared plan')
        if (identity, method) in seen:
            raise ValueError(f'Duplicate prediction: {identity}, {method}')
        seen.add((identity, method))
        sequence = validate_sequence(record.get('sequence'))
        if sequence != index[identity]['sequence']:
            raise ValueError(f'Prediction sequence differs from reference: {identity}, {method}')
        status = record.get('status')
        if not isinstance(status, str) or status not in PREDICTION_STATUSES:
            raise ValueError('Unsupported prediction status')
        if status == 'ok':
            structure_field(record.get('structure'), sequence, 'prediction structure')
            if record.get('error'):
                raise ValueError('Successful predictions cannot carry an error')
        else:
            text_field(record.get('error'), 'prediction failure reason')
            if record.get('structure') is not None:
                raise ValueError('Failed predictions cannot carry a scored structure')
    return references, predictions


def evaluate_rows(references, predictions):
    index = {(r['id'], r['method']): r for r in predictions['records']}
    rows = []
    for reference in references['records']:
        for method in predictions['methods']:
            record = index.get((reference['id'], method))
            row = dict.fromkeys(METRICS)
            row.update(reference_id=reference['id'], method=method,
                       reference_kind=reference['reference_kind'], source=reference['source'],
                       length=len(reference['sequence']), sequence_sha256=digest(reference['sequence'].encode()),
                       status=record['status'] if record else 'missing',
                       error=record.get('error', '') if record else 'No prediction supplied')
            if row['status'] == 'ok':
                row.update(structure_agreement(record['structure'], reference['structure']))
            rows.append(row)
    return rows


def aggregate_rows(rows):
    aggregates = []
    for method, kind in sorted({(r['method'], r['reference_kind']) for r in rows}):
        group = [r for r in rows if (r['method'], r['reference_kind']) == (method, kind)]
        measured = [r for r in group if r['status'] == 'ok']
        aggregates.append({
            'method': method, 'reference_kind': kind, 'planned_inputs': len(group),
            'measured_inputs': len(measured), 'missing_inputs': sum(r['status'] == 'missing' for r in group),
            'failed_inputs': sum(r['status'] not in ('ok', 'missing') for r in group),
            'status_counts': dict(Counter(r['status'] for r in group)),
            'mean_pair_precision': sum(r['pair_precision'] for r in measured)/len(measured) if measured else None,
            'mean_pair_recall': sum(r['pair_recall'] for r in measured)/len(measured) if measured else None,
            'mean_pair_f1': sum(r['pair_f1'] for r in measured)/len(measured) if measured else None,
        })
    return aggregates


def load_inputs(reference_path, prediction_path):
    content = [Path(p).read_bytes() for p in (reference_path, prediction_path)]
    try:
        references, predictions = [json.loads(c) for c in content]
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f'Invalid reference/prediction JSON: {exc}') from exc
    validate_inputs(references, predictions)
    return references, predictions, content


def render_report(summary):
    lines = ['# Supplied-reference structure evaluation', '',
             f'Dataset: `{summary["dataset_id"]}`', '',
             'Reference labels and sources are caller declarations. This report scores supplied structures.', '',
             '| Method | Reference kind | Planned | Measured | Missing | Failed | Mean pair F1 |',
             '|---|---|---:|---:|---:|---:|---:|']
    for group in summary['aggregates']:
        lines.append('| ' + ' | '.join('unknown' if group[k] is None else str(group[k]) for k in
                     ('method', 'reference_kind', 'planned_inputs', 'measured_inputs',
                      'missing_inputs', 'failed_inputs', 'mean_pair_f1')) + ' |')
    lines += ['', 'A mean is over measured references only; compare coverage before comparing means.',
              'Two all-unpaired structures score one; if only one structure has pairs, pair F1 is zero.', '',
              *summary['limitations'], '']
    return '\n'.join(lines)


def run_reference_evaluation(root, reference_path, prediction_path, dry_run=False):
    references, predictions, content = load_inputs(reference_path, prediction_path)
    rows = evaluate_rows(references, predictions)
    aggregates = aggregate_rows(rows)
    if dry_run:
        result = {'mode': 'reference_validation_no_folding', 'dataset_id': references['dataset_id'],
                  'planned_predictions': len(rows), 'aggregates': aggregates}
        print(json.dumps(result, indent=2, allow_nan=False))
        return result
    from .cli import versions
    root = Path(root).resolve()
    run = root/'results/reference_runs'/timestamp()
    run.mkdir(parents=True, exist_ok=False)
    sources = {}
    for name, path, data in zip(('references', 'predictions'), (reference_path, prediction_path), content):
        saved = run/(name + '.json')
        saved.write_bytes(data)
        sources[name] = {'original_path': str(Path(path).resolve()), 'path': str(saved), 'sha256': digest(data)}
    source_paths = [Path(__file__), Path(__file__).with_name('scoring.py'), Path(__file__).with_name('sequences.py')]
    manifest = {'schema_version': 1, 'utc': run.name, 'run_dir': str(run),
                'dataset_id': references['dataset_id'], 'sources': sources,
                'methods': predictions['methods'], 'reference_ids': [r['id'] for r in references['records']],
                'provenance': {'versions': versions(), 'source_sha256': {str(p): digest(p.read_bytes()) for p in source_paths}},
                'policy': 'exact_pairs_complete_dot_bracket_macro_by_method_and_reference_kind_v1'}
    manifest_path = run/'manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    summary = {'mode': 'supplied_reference_structure_evaluation', 'complete': True, 'run_dir': str(run),
               'utc': run.name, 'dataset_id': references['dataset_id'], 'manifest_sha256': digest(manifest_path.read_bytes()),
               'sources': sources, 'provenance': manifest['provenance'], 'policy': manifest['policy'],
               'rows': rows, 'aggregates': aggregates, 'limitations': LIMITATIONS}
    report = render_report(summary)
    # Immutable per-run exports allow auditing even after the latest report is replaced.
    publish(run, NAME, summary, rows, FIELDS, report)
    publish(root, NAME, summary, rows, FIELDS, report)
    print(json.dumps({'run_dir': str(run), 'dataset_id': references['dataset_id'], 'aggregates': aggregates}, indent=2))
    return summary
