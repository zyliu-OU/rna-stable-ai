#!/usr/bin/env python3
"""Independently replay saved portfolio decisions, budgets and artifact integrity."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.artifacts import sha256
from rnastable.optimization import check_constraints, hamming
from rnastable.selection import select_finalist
from rnastable.sequences import generate_sequence, read_fasta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, default=ROOT/'results/portfolio_summary.json')
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text())
    assert summary['mode'] == 'saved_cpu_restart_portfolio'
    assert summary['policy'] == 'lowest_confirmed_vienna_energy_then_job_id_v1'
    source_path = Path(summary['source_summary'])
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == summary['source_summary_sha256']
    subprocess.run([sys.executable, str(ROOT/'scripts/verify_sweep.py'), '--summary', str(source_path)], check=True)
    source = json.loads(source_path.read_text())
    assert summary['source_versions'] == source['provenance']['versions']
    keys = {(r['kind'], r['length'], r['sequence_seed'], r['input_sha256']) for r in source['rows']}
    actual_keys = [(r['kind'], r['length'], r['sequence_seed'], r['input_sha256']) for r in summary['rows']]
    assert set(actual_keys) == keys and len(actual_keys) == len(keys)
    for row in summary['rows']:
        original = generate_sequence(row['length'], row['kind'], row['sequence_seed'])
        assert sha256(original) == row['input_sha256']
        group = [r for r in source['rows'] if r['input_sha256'] == row['input_sha256']
                 and (r['kind'], r['length'], r['sequence_seed']) == (row['kind'], row['length'], row['sequence_seed'])]
        decisions, eligible, energies, expected_files = [], [], [], []
        for candidate in group:
            if not candidate.get('summary_path'):
                decision = select_finalist(original, original, 'failed', None, None)
            else:
                path = Path(candidate['summary_path'])
                evidence = json.loads(path.read_text())
                sequence = read_fasta(candidate['finalist_fasta'])[0][1]
                decision = select_finalist(original, sequence, evidence['search']['status'],
                                           evidence['reference'], evidence['validation'])
                before = evidence['reference']
                if before and before['status'] == 'ok':
                    energies.append(before['mfe_kcal_mol'])
                expected_files.append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
                if decision['source'] == 'finalist':
                    eligible.append((evidence['validation']['mfe_kcal_mol'], candidate['job_id'], sequence, candidate))
            decisions.append({'job_id': candidate['job_id'], **decision})
        assert row['source_evidence'] == expected_files
        assert row['candidate_decisions'] == sorted(decisions, key=lambda d: d['job_id'])
        assert row['eligible_candidates'] == len(eligible)
        assert row['search_count'] == len(group)
        assert row['proposals_attempted'] == sum(c.get('steps_attempted', 0) for c in group)
        assert row['candidate_worsenings'] == sum(d['candidate_vienna_delta_kcal_mol'] is not None
                                                and d['candidate_vienna_delta_kcal_mol'] > 1e-9 for d in decisions)
        if energies:
            assert max(energies)-min(energies) <= 1e-9
        before = min(energies) if energies else None
        assert row['input_vienna_energy_kcal_mol'] == before
        if eligible:
            energy, job_id, expected, winner = min(eligible, key=lambda v: (v[0], v[1]))
            assert row['selection_source'] == 'finalist'
            assert row['selection_reason'] == 'best_confirmed_improvement'
            assert row['selected_job_id'] == job_id
            assert row['selected_beam_size'] == winner['beam_size']
            assert row['selected_search_seed'] == winner['search_seed']
            assert energy < before-1e-9
        else:
            energy, expected = before, original
            assert row['selection_source'] == 'input'
            assert row['selection_reason'] == 'no_eligible_improvement'
            assert row['selected_job_id'] is row['selected_beam_size'] is row['selected_search_seed'] is None
        assert row['selected_vienna_energy_kcal_mol'] == energy
        assert row['selected_vienna_delta_kcal_mol'] == (energy-before if energy is not None else None)
        records = read_fasta(row['selected_fasta'])
        assert len(records) == 1 and records[0][1] == expected
        assert row['selected_sha256'] == sha256(expected)
        assert row['selected_mutations_from_input'] == hamming(expected, original)
        check_constraints(expected, original, source['config']['optimization'])
    assert summary['input_count'] == len(keys)
    assert summary['search_count'] == len(source['rows']) == sum(r['search_count'] for r in summary['rows'])
    assert summary['proposals_attempted'] == sum(r['proposals_attempted'] for r in summary['rows'])
    assert summary['selected_finalists'] == sum(r['selection_source'] == 'finalist' for r in summary['rows'])
    assert summary['returned_inputs'] == sum(r['selection_source'] == 'input' for r in summary['rows'])
    assert json.loads((Path(summary['run_dir'])/'summary.json').read_text()) == summary
    with (args.summary.parent/'portfolio.csv').open() as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        assert len(rows) == len(summary['rows'])
        for actual, expected in zip(rows, summary['rows']):
            assert actual == {k: '' if expected[k] is None else str(expected[k]) for k in reader.fieldnames}
    print(f'Portfolio audit passed: {summary["input_count"]} inputs, {summary["search_count"]} searches, '
          f'{summary["proposals_attempted"]} proposals; best energies, constraints, provenance and FASTAs verified.')


if __name__ == '__main__':
    main()
