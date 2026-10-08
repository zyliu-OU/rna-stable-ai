import copy
import json
import subprocess
import sys

import pytest

from rnastable.cli import ROOT
from rnastable.portfolio import build_portfolio, choose_candidate


def candidate(job='a', after=-11., before=-10., status='completed', sequence='CAGU'):
    return {'job_id': job, 'sequence': sequence, 'search_status': status,
            'reference': {'status': 'ok', 'mfe_kcal_mol': before},
            'validation': {'status': 'ok', 'mfe_kcal_mol': after}}


def test_lowest_reference_energy_wins_even_in_reverse_order():
    candidates = [candidate('a', -11.), candidate('b', -12.), candidate('c', -9.)]
    chosen = choose_candidate('ACGU', candidates)
    assert chosen['selected_job_id'] == 'b'
    assert chosen['selected_vienna_delta_kcal_mol'] == -2.
    assert chosen['eligible_candidates'] == 2
    assert chosen['search_count'] == 3
    assert choose_candidate('ACGU', list(reversed(candidates))) == chosen


def test_equal_energy_tie_uses_job_id():
    chosen = choose_candidate('ACGU', [candidate('z', -12., sequence='AGCU'), candidate('a', -12.)])
    assert chosen['selected_job_id'] == 'a'
    assert chosen['selected_sequence'] == 'CAGU'


@pytest.mark.parametrize('entry', [candidate(after=-9.), candidate(after=-10.),
                                 candidate(status='failed'), candidate(sequence='ACGU')])
def test_ineligible_output_returns_original(entry):
    chosen = choose_candidate('ACGU', [entry])
    assert chosen['selection_source'] == 'input'
    assert chosen['selected_sequence'] == 'ACGU'
    assert chosen['selected_vienna_delta_kcal_mol'] == 0.


@pytest.mark.parametrize('value', [None, float('nan'), float('inf'), True, '-10'])
def test_unknown_reference_is_not_zero(value):
    entry = candidate(before=value)
    chosen = choose_candidate('ACGU', [entry])
    assert chosen['selection_source'] == 'input'
    assert chosen['selected_vienna_delta_kcal_mol'] is None
    assert chosen['input_vienna_energy_kcal_mol'] is None


def test_failed_validation_does_not_hide_other_valid_search():
    failed = candidate('a', -100.)
    failed['validation']['status'] = 'timeout'
    assert choose_candidate('ACGU', [failed, candidate('b')])['selected_job_id'] == 'b'


def test_inconsistent_references_fail():
    with pytest.raises(ValueError, match='references disagree'):
        choose_candidate('ACGU', [candidate('a'), candidate('b', before=-9.)])


def test_duplicates_and_empty_fail():
    with pytest.raises(ValueError, match='Duplicate'):
        choose_candidate('ACGU', [candidate(), candidate()])
    with pytest.raises(ValueError, match='At least one'):
        choose_candidate('ACGU', [])


def test_candidate_records_unchanged():
    entries = [candidate('b'), candidate('a')]
    before = copy.deepcopy(entries)
    choose_candidate('ACGU', entries)
    assert entries == before


def test_incomplete_source_creates_no_output(tmp_path):
    source = tmp_path/'bad.json'
    source.write_text(json.dumps({'complete': False, 'rows': []}))
    with pytest.raises(ValueError, match='complete sweep'):
        build_portfolio(tmp_path/'output', source)
    assert not (tmp_path/'output').exists()


def test_cli_invalid_source_exits_cleanly(tmp_path):
    source = tmp_path/'bad.json'
    source.write_text(json.dumps({'complete': False, 'rows': []}))
    result = subprocess.run([sys.executable, '-m', 'rnastable.cli', 'select-portfolio',
                             '--summary', str(source), '--output-root', str(tmp_path/'output')],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 2 and 'complete sweep' in result.stderr
    assert not (tmp_path/'output').exists()


def test_failed_source_audit_creates_no_artifacts(tmp_path, monkeypatch):
    source = tmp_path/'source.json'
    source.write_text(json.dumps({'complete': True, 'rows': [{'job_id': 'test_only'}]}))
    monkeypatch.setattr('rnastable.portfolio.subprocess.run', lambda *a, **k:
                        subprocess.CompletedProcess(a, 1, 'test-only audit failure', 'missing raw output'))
    with pytest.raises(ValueError, match='missing raw output'):
        build_portfolio(tmp_path/'output', source)
    assert not (tmp_path/'output').exists()


def test_source_change_during_audit_rejected(tmp_path, monkeypatch):
    source = tmp_path/'source.json'
    source.write_text(json.dumps({'complete': True, 'rows': [{'job_id': 'test_only'}]}))
    def audit(*args, **kwargs):
        source.write_text('{}')
        return subprocess.CompletedProcess(args, 0, 'test-only audit response', '')
    monkeypatch.setattr('rnastable.portfolio.subprocess.run', audit)
    with pytest.raises(ValueError, match='changed during'):
        build_portfolio(tmp_path/'output', source)
    assert not (tmp_path/'output').exists()
