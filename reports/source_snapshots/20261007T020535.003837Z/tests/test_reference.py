import copy
import json
from pathlib import Path
import subprocess

import pytest

from rnastable.cli import ROOT
from rnastable.reference import METRICS, run_reference_evaluation, validate_inputs
from rnastable.reference_audit import audit_reference


@pytest.fixture
def inputs():
    references = {'schema_version': 1, 'dataset_id': 'test-only', 'records': [
        {'id': 'stem', 'sequence': 'GCAAGC', 'structure': '((..))',
         'reference_kind': 'synthetic_control', 'source': 'Test-only designed structure'},
        {'id': 'empty', 'sequence': 'AAAAAA', 'structure': '......',
         'reference_kind': 'synthetic_control', 'source': 'Test-only unpaired structure'},
    ]}
    predictions = {'schema_version': 1, 'methods': ['partial', 'missing-method'], 'records': [
        {'id': 'stem', 'method': 'partial', 'sequence': 'GCAAGC', 'status': 'ok', 'structure': '(....)'},
        {'id': 'empty', 'method': 'partial', 'sequence': 'AAAAAA', 'status': 'timeout', 'error': 'Test-only timeout'},
    ]}
    return references, predictions


def save_inputs(tmp_path, inputs):
    paths = [tmp_path/'reference.json', tmp_path/'prediction.json']
    for path, data in zip(paths, inputs):
        path.write_text(json.dumps(data))
    return paths


def test_scores_and_coverage_do_not_impute_failures(tmp_path, inputs):
    result = run_reference_evaluation(tmp_path, *save_inputs(tmp_path, inputs))
    scored, missing, failed, other_missing = result['rows']
    assert scored['pair_precision'] == 1
    assert scored['pair_recall'] == .5
    assert scored['pair_f1'] == pytest.approx(2/3)
    assert scored['pair_jaccard'] == .5
    assert scored['base_pair_distance'] == 1
    assert (scored['reference_pairs'], scored['predicted_pairs'], scored['shared_pairs']) == (2, 1, 1)
    for row in (missing, failed, other_missing):
        assert all(row[k] is None for k in METRICS)
    partial = next(r for r in result['aggregates'] if r['method'] == 'partial')
    assert (partial['planned_inputs'], partial['measured_inputs'], partial['failed_inputs']) == (2, 1, 1)
    assert partial['mean_pair_f1'] == pytest.approx(2/3)
    absent = next(r for r in result['aggregates'] if r['method'] == 'missing-method')
    assert absent['missing_inputs'] == 2 and absent['mean_pair_f1'] is None
    assert audit_reference(tmp_path/'results/reference_evaluation_summary.json')['planned_predictions'] == 4


def test_kinds_remain_separate_and_all_unpaired_convention(tmp_path, inputs):
    refs, preds = inputs
    refs['records'][1]['reference_kind'] = 'computational'
    preds['records'][1] = dict(id='empty', method='partial', sequence='AAAAAA', status='ok', structure='......')
    result = run_reference_evaluation(tmp_path, *save_inputs(tmp_path, inputs))
    assert len(result['aggregates']) == 4
    assert result['rows'][2]['pair_f1'] == 1
    assert result['rows'][2]['pair_precision'] == result['rows'][2]['pair_recall'] == 1


@pytest.mark.parametrize('change', [
    'wrong_sequence', 'duplicate_reference', 'duplicate_prediction', 'unknown_id',
    'unknown_method', 'duplicate_method', 'pseudoknot', 'unbalanced', 'wrong_length',
    'missing_source', 'invalid_kind', 'invalid_status', 'failed_with_structure',
    'failure_without_reason', 'no_references', 'bool_schema', 'invalid_kind_type', 'invalid_status_type',
])
def test_invalid_plan_creates_no_results(tmp_path, inputs, change):
    refs, preds = inputs
    if change == 'wrong_sequence': preds['records'][0]['sequence'] = 'GCGAGC'
    elif change == 'duplicate_reference': refs['records'].append(copy.deepcopy(refs['records'][0]))
    elif change == 'duplicate_prediction': preds['records'].append(copy.deepcopy(preds['records'][0]))
    elif change == 'unknown_id': preds['records'][0]['id'] = 'unknown'
    elif change == 'unknown_method': preds['records'][0]['method'] = 'unknown'
    elif change == 'duplicate_method': preds['methods'].append('partial')
    elif change == 'pseudoknot': refs['records'][0]['structure'] = '([..)]'
    elif change == 'unbalanced': preds['records'][0]['structure'] = '(.....'
    elif change == 'wrong_length': refs['records'][0]['structure'] = '....'
    elif change == 'missing_source': refs['records'][0].pop('source')
    elif change == 'invalid_kind': refs['records'][0]['reference_kind'] = 'biological_truth'
    elif change == 'invalid_status': preds['records'][0]['status'] = 'missing'
    elif change == 'failed_with_structure': preds['records'][1]['structure'] = '......'
    elif change == 'failure_without_reason': preds['records'][1].pop('error')
    elif change == 'no_references': refs['records'] = []
    elif change == 'bool_schema': refs['schema_version'] = True
    elif change == 'invalid_kind_type': refs['records'][0]['reference_kind'] = []
    elif change == 'invalid_status_type': preds['records'][0]['status'] = []
    with pytest.raises(ValueError):
        run_reference_evaluation(tmp_path, *save_inputs(tmp_path, inputs))
    assert not (tmp_path/'results').exists()


def test_no_predictions_is_a_complete_missing_plan(tmp_path, inputs):
    inputs[1]['records'] = []
    result = run_reference_evaluation(tmp_path, *save_inputs(tmp_path, inputs))
    assert result['complete'] and len(result['rows']) == 4
    assert all(r['status'] == 'missing' for r in result['rows'])
    assert all(g['mean_pair_f1'] is None for g in result['aggregates'])


def test_repeated_publication_preserves_run_evidence(tmp_path, inputs):
    paths = save_inputs(tmp_path, inputs)
    first = run_reference_evaluation(tmp_path, *paths)
    run = Path(first['run_dir'])
    before = {p.relative_to(run): p.read_bytes() for p in run.rglob('*') if p.is_file()}
    inputs[1]['records'][0]['structure'] = '((..))'
    paths = save_inputs(tmp_path, inputs)
    second = run_reference_evaluation(tmp_path, *paths)
    assert first['run_dir'] != second['run_dir']
    assert before == {p.relative_to(run): p.read_bytes() for p in run.rglob('*') if p.is_file()}
    for path in paths: path.unlink()  # The audit depends on frozen copies, not live inputs.
    assert audit_reference(run/'results/reference_evaluation_summary.json')['audit'] == 'passed'
    assert audit_reference(tmp_path/'results/reference_evaluation_summary.json')['audit'] == 'passed'
    assert list((tmp_path/'results/archive').glob('*/reference_evaluation_summary.json'))


@pytest.mark.parametrize('artifact', ['input', 'metric', 'coverage', 'csv', 'report', 'manifest', 'frozen_csv', 'frozen_report'])
def test_audit_rejects_changed_evidence(tmp_path, inputs, artifact):
    result = run_reference_evaluation(tmp_path, *save_inputs(tmp_path, inputs))
    summary_path = tmp_path/'results/reference_evaluation_summary.json'
    run = Path(result['run_dir'])
    if artifact == 'input':
        path = run/'predictions.json'
        data = json.loads(path.read_text()); data['records'][0]['structure'] = '((..))'
        path.write_text(json.dumps(data))
    elif artifact in ('metric', 'coverage'):
        data = json.loads(summary_path.read_text())
        if artifact == 'metric': data['rows'][0]['pair_f1'] = 1
        else: data['aggregates'][0]['measured_inputs'] = 2
        summary_path.write_text(json.dumps(data))
    elif artifact == 'csv':
        (tmp_path/'results/reference_evaluation.csv').write_text('bad\n')
    elif artifact == 'report':
        (tmp_path/'reports/reference_evaluation_report.md').write_text('changed report\n')
    elif artifact == 'frozen_csv':
        (run/'results/reference_evaluation.csv').write_text('bad\n')
    elif artifact == 'frozen_report':
        (run/'reports/reference_evaluation_report.md').write_text('changed report\n')
    else:
        (run/'manifest.json').write_text('{}')
    with pytest.raises(ValueError, match='Reference audit rejected'):
        audit_reference(summary_path)


def test_cli_dry_run_and_invalid_identity(tmp_path, inputs):
    paths = save_inputs(tmp_path, inputs)
    command = [str(ROOT/'scripts/rnastable'), 'evaluate-reference', '--references', str(paths[0]),
               '--predictions', str(paths[1]), '--output-root', str(tmp_path), '--dry-run']
    completed = subprocess.run(command, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)['planned_predictions'] == 4
    assert not (tmp_path/'results').exists()
    inputs[1]['records'][0]['sequence'] = 'GCGAGC'
    save_inputs(tmp_path, inputs)
    completed = subprocess.run(command, capture_output=True, text=True)
    assert completed.returncode == 2
    assert 'differs from reference' in completed.stderr
    assert 'Traceback' not in completed.stderr


def test_validator_requires_metadata(inputs):
    inputs[0]['records'][0]['reference_kind'] = 'experimental'
    # This is a caller label; validation never promotes it to verified experimental truth.
    assert validate_inputs(*inputs)[0]['records'][0]['reference_kind'] == 'experimental'


def test_cli_publication_and_verifier(tmp_path, inputs):
    paths = save_inputs(tmp_path, inputs)
    completed = subprocess.run([str(ROOT/'scripts/rnastable'), 'evaluate-reference',
        '--references', str(paths[0]), '--predictions', str(paths[1]), '--output-root', str(tmp_path)],
        capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    import sys
    command = [sys.executable, str(ROOT/'scripts/verify_reference.py'), '--summary',
               str(tmp_path/'results/reference_evaluation_summary.json')]
    verified = subprocess.run(command, capture_output=True, text=True)
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)['measured_predictions'] == 1
    summary = tmp_path/'results/reference_evaluation_summary.json'
    data = json.loads(summary.read_text()); data['rows'][0]['pair_f1'] = 1
    summary.write_text(json.dumps(data))
    rejected = subprocess.run(command, capture_output=True, text=True)
    assert rejected.returncode == 2 and 'Reference audit rejected' in rejected.stderr
    assert 'Traceback' not in rejected.stderr
