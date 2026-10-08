import copy
import json
import random
from pathlib import Path
import subprocess
import pytest
from rnastable.cli import ROOT
from rnastable.folding import parse_output
from rnastable.optimization import (check_constraints, hamming, load_optimization_config,
    optimize_sequence, propose_mutation, translation)
from rnastable.scoring import base_pairs, structure_agreement

@pytest.fixture
def config():
    return load_optimization_config(ROOT/'configs/optimization.json')


def test_pair_coordinates_and_metrics():
    assert base_pairs('((..))') == {(0,5), (1,4)}
    scores = structure_agreement('(....)', '((..))')
    assert scores['pair_precision'] == 1
    assert scores['pair_recall'] == 0.5
    assert scores['pair_f1'] == pytest.approx(2/3)
    assert scores['base_pair_distance'] == 1
    assert structure_agreement('....', '....')['pair_f1'] == 1
    assert structure_agreement('....', '(..)')['pair_f1'] == 0
    with pytest.raises(ValueError):
        structure_agreement('....', '...')


def test_parsed_structures_are_retained():
    assert parse_output('LinearFold', '((..)) (-3.5)', 6)['structure'] == '((..))'


def test_swaps_preserve_composition_and_protected_positions(config):
    initial = 'ACGU'*20
    config['protected_positions'] = [1,2,3,4]
    config['max_mutations'] = 8
    current = initial
    rng = random.Random(99)
    for _ in range(50):
        candidate = propose_mutation(current, initial, config, rng)
        assert candidate is not None
        assert check_constraints(candidate, initial, config)
        assert candidate[:4] == initial[:4]
        assert hamming(candidate, initial) <= 8
        current = candidate


def test_constraints_reject_invalid_changes(config):
    config['max_mutations'] = 1
    with pytest.raises(ValueError, match='Mutation budget'):
        check_constraints('CAGU', 'ACGU', config)
    config['max_mutations'] = 4
    with pytest.raises(ValueError, match='GC count'):
        check_constraints('AAGU', 'ACGU', config)
    config['protected_positions'] = [1]
    with pytest.raises(ValueError, match='Protected position changed'):
        check_constraints('CAGU', 'ACGU', config)
    config['protected_positions'] = [10]
    with pytest.raises(ValueError, match='exceeds'):
        check_constraints('ACGU', 'ACGU', config)


def test_synonymous_proposals(config):
    config['preserve_protein'] = True
    config['protected_positions'] = [1,2,3]
    initial = 'AUGGCUUCUGGCUAA'
    current = initial
    rng = random.Random(2718)
    for _ in range(20):
        current = propose_mutation(current, initial, config, rng)
        assert current is not None
        assert translation(current) == translation(initial)
        assert current[:3] == 'AUG' and current[-3:] == 'UAA'
        assert check_constraints(current, initial, config)
    with pytest.raises(ValueError, match='full codons'):
        translation('ACGU')


def test_search_deterministic_monotonic_and_budgeted(config):
    initial = 'ACGU'*20
    config.update(steps=64, max_mutations=12)
    def evaluate(sequence, step):
        # Test-only positional objective to exercise acceptance, not folding data.
        return {'status': 'ok', 'mfe_kcal_mol': -sum((i+1)*'ACGU'.index(c) for i,c in enumerate(sequence))}
    first = optimize_sequence(initial, config, evaluate)
    second = optimize_sequence(initial, config, evaluate)
    assert first == second
    assert first['accepted_steps'] > 0
    assert check_constraints(first['sequence'], initial, config)
    scores = [first['baseline']['mfe_kcal_mol']]+[r['best_energy_kcal_mol'] for r in first['history'] if 'best_energy_kcal_mol' in r]
    assert scores == sorted(scores, reverse=True)
    assert first['best']['mfe_kcal_mol'] < first['baseline']['mfe_kcal_mol']


def test_failures_continue_and_baseline_failure_is_explicit(config):
    initial = 'ACGU'*20
    config['steps'] = 4
    def evaluate(sequence, step):
        if step == 1:
            return {'status': 'timeout', 'error': 'Test-only simulated timeout'}
        return {'status': 'ok', 'mfe_kcal_mol': -100-step}
    result = optimize_sequence(initial, config, evaluate)
    assert result['history'][0]['status'] == 'timeout'
    assert len(result['history']) == 4
    assert result['status'] == 'completed'
    failed = optimize_sequence(initial, config, lambda *_: {'status': 'unavailable'})
    assert failed['status'] == 'baseline_failed' and failed['history'] == []


def test_fully_protected_search_keeps_input(config):
    sequence = 'ACGU'*10
    config['protected_positions'] = list(range(1,len(sequence)+1))
    result = optimize_sequence(sequence, config, lambda *_: {'status':'ok','mfe_kcal_mol':-10})
    assert result['sequence'] == sequence and result['accepted_steps'] == 0
    assert result['history'][0]['status'] == 'no_legal_proposal'


def test_config_rejects_nonfinite_and_boolean_budget(config, tmp_path):
    for key, value in [('timeout_seconds', float('nan')), ('steps', True), ('protected_positions', [1,1])]:
        broken = copy.deepcopy(config); broken[key] = value
        path = tmp_path/'bad.json'; path.write_text(json.dumps(broken))
        with pytest.raises(ValueError):
            load_optimization_config(path)


def test_compare_cli_rejects_changed_input(tmp_path):
    # Use original saved folds but deliberately mismatch the FASTA manifest hash.
    summary = json.loads((ROOT/'results/benchmark_summary.json').read_text())
    summary['synthetic_manifest'] = [summary['synthetic_manifest'][0]]
    summary['synthetic_manifest'][0]['sha256'] = 'tampered'
    path = tmp_path/'source.json'; path.write_text(json.dumps(summary))
    completed = subprocess.run([str(ROOT/'scripts/rnastable'), 'compare-folds', '--summary', str(path),
                                '--output-root', str(tmp_path)], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    result = json.loads((tmp_path/'results/folding_quality_summary.json').read_text())
    assert result['rows'][0]['status'] == 'error'
    assert 'changed' in result['rows'][0]['error']
