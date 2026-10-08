import copy
import importlib.util
import json

import numpy as np
import pytest

from rnastable.cli import ROOT
from rnastable.family_plan import audit_family_plan, plan_families, save_family_plan
from rnastable.pair_model import decode_pairs, legal_pairs, make_pair_model, supervision
from rnastable.reference import digest
from rnastable.scoring import base_pairs


def test_global_decoder_beats_a_largest_pair_greedy_choice():
    sequence = 'GGAAAACC'; scores = np.zeros((8, 8))
    for i, j, value in [(0, 6, 5), (1, 7, 5), (0, 7, 4), (1, 6, 4)]:
        scores[i, j] = scores[j, i] = value
    assert decode_pairs(sequence, scores) == '((....))'  # Total eight beats either crossing five.


def test_decoder_matches_exhaustive_non_crossing_optimum():
    sequence = 'GCGAAACGC'; pairs = legal_pairs(sequence)
    rng = np.random.default_rng(73)
    scores = rng.normal(size=(9, 9)); scores = (scores+scores.T)/2
    best = 0
    for bits in range(1 << len(pairs)):
        chosen = [p for k, p in enumerate(pairs) if bits & (1 << k)]
        endpoints = [x for p in chosen for x in p]
        if len(set(endpoints)) != len(endpoints): continue
        if any(i < k < j < l or k < i < l < j for i, j in chosen for k, l in chosen): continue
        best = max(best, sum(scores[i, j] for i, j in chosen))
    structure = decode_pairs(sequence, scores)
    assert sum(scores[i, j] for i, j in base_pairs(structure)) == pytest.approx(best)


def test_empty_score_and_unsupported_contacts():
    assert decode_pairs('GCAAAAGC', np.zeros((8, 8))) == '........'
    assert decode_pairs('AAAAAAAA', np.ones((8, 8))) == '........'
    for score in (np.ones((2, 2)), np.full((8, 8), float('nan')), np.triu(np.ones((8, 8)))):
        with pytest.raises(ValueError): decode_pairs('GCAAAAGC', score)
    with pytest.raises(ValueError): legal_pairs('A'*257)


def test_pair_scores_are_symmetric_and_differentiable():
    import torch
    from rnastable.structure_model import tokens
    config = json.loads((ROOT/'configs/pair_development.json').read_text())
    model = make_pair_model(config)
    scores = model(tokens('GCAAAAGC'))
    assert scores.shape == (1, 8, 8) and torch.equal(scores, scores.transpose(1, 2))
    scores.sum().backward()
    assert any(p.grad is not None and p.grad.abs().sum() > 0 for p in model.parameters())
    with pytest.raises(ValueError): model(torch.zeros((1, 257), dtype=torch.long))


def test_supervision_counts_unrepresentable_reference_contacts():
    indices, labels, excluded = supervision(dict(sequence='GCAAAAGC', structure='((....))'))
    assert labels.sum() == 2 and excluded == 0
    assert all(i < j-3 for i, j in indices.tolist())
    _, labels, excluded = supervision(dict(sequence='AAAAAAAA', structure='((....))'))
    assert labels.sum() == 0 and excluded == 2


@pytest.fixture
def family_inputs():
    records = [dict(id='a', sequence='GCAAAAGC', structure='((....))', reference_kind='synthetic_control', source='test-only'),
               dict(id='b', sequence='AAAAACCC', structure='........', reference_kind='synthetic_control', source='test-only'),
               dict(id='c', sequence='UUUUGGGG', structure='........', reference_kind='synthetic_control', source='test-only')]
    refs = dict(schema_version=1, dataset_id='test-only', records=records)
    assignments = dict(schema_version=1, records=[dict(id=r['id'], sequence_sha256=digest(r['sequence'].encode()),
        family_id=r['id'], source='test-only artificial family label') for r in records])
    return refs, assignments, {'train': ['a'], 'validation': ['b'], 'test': ['c']}, []


def test_family_plan_requires_disjoint_bound_evidence(family_inputs):
    result = plan_families(*family_inputs)
    assert result['counts'] == {'train': 1, 'validation': 1, 'test': 1}
    assert result['splits']['test'][0]['family_id'] == 'c'


@pytest.mark.parametrize('broken', ['family_overlap', 'missing_assignment', 'wrong_hash', 'missing_source',
    'duplicate', 'unknown_family', 'test_exposed', 'similar_test_exposed', 'accession_overlap', 'sequence_overlap', 'bool_schema', 'accession_case', 'exposed_family'])
def test_family_planner_rejects_leakage_and_missing_provenance(family_inputs, broken):
    refs, assignments, plan, exposed = family_inputs
    if broken == 'family_overlap': plan['test'] = ['a']
    elif broken == 'missing_assignment': assignments['records'].pop()
    elif broken == 'wrong_hash': assignments['records'][0]['sequence_sha256'] = '0'*64
    elif broken == 'missing_source': assignments['records'][0].pop('source')
    elif broken == 'duplicate': assignments['records'].append(copy.deepcopy(assignments['records'][0]))
    elif broken == 'unknown_family': assignments['records'][0]['family_id'] = 'unknown'
    elif broken == 'test_exposed': exposed.append(dict(sequence='UUUUGGGG', source='prior experiment'))
    elif broken == 'similar_test_exposed': exposed.append(dict(sequence='UUUUGGGA', source='prior experiment'))
    elif broken == 'accession_overlap':
        refs['records'][0]['pdb_accession'] = refs['records'][2]['pdb_accession'] = '1abc'
    elif broken == 'sequence_overlap':
        refs['records'][2]['sequence'] = refs['records'][0]['sequence']
        assignments['records'][2]['sequence_sha256'] = assignments['records'][0]['sequence_sha256']
    elif broken == 'bool_schema': assignments['schema_version'] = True
    elif broken == 'accession_case':
        refs['records'][0]['pdb_accession'] = '1AbC'; refs['records'][2]['pdb_accession'] = '1abc'
    elif broken == 'exposed_family': exposed.append(dict(sequence='CCCCAAAA', family_id='c', source='prior family'))
    with pytest.raises(ValueError): plan_families(refs, assignments, plan, exposed)


def test_failed_family_plan_writes_no_run(tmp_path, family_inputs):
    family_inputs[1]['records'].pop()
    paths = []
    for index, data in enumerate(family_inputs):
        path = tmp_path/f'{index}.json'; path.write_text(json.dumps(data)); paths.append(path)
    with pytest.raises(ValueError): save_family_plan(tmp_path/'run', *paths)
    assert not (tmp_path/'run').exists()


def test_known_exposure_cannot_be_bypassed_with_empty_ledger(tmp_path, family_inputs):
    paths = []
    for index, data in enumerate(family_inputs):
        path = tmp_path/f'{index}.json'; path.write_text(json.dumps(data)); paths.append(path)
    known = [dict(sequence='UUUUGGGG', source='known project test')]
    with pytest.raises(ValueError, match='previously exposed'):
        save_family_plan(tmp_path/'run', *paths, known_exposure=known)
    assert not (tmp_path/'run').exists()


def test_frozen_family_plan_audit_rejects_changed_ledger(tmp_path, family_inputs):
    paths = []
    for index, data in enumerate(family_inputs):
        path = tmp_path/f'{index}.json'; path.write_text(json.dumps(data)); paths.append(path)
    run = tmp_path/'run'; save_family_plan(run, *paths)
    assert audit_family_plan(run)['counts']['test'] == 1
    for path in paths: path.unlink()
    assert audit_family_plan(run)['complete']
    (run/'effective_exposure.json').write_text('[{}]')
    with pytest.raises(ValueError, match='exposure ledger changed'): audit_family_plan(run)


def test_pair_training_changes_weights_without_test_data(tmp_path):
    import torch
    spec = importlib.util.spec_from_file_location('pair_train', ROOT/'scripts/train_pair_development.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    config = json.loads((ROOT/'configs/pair_development.json').read_text()); config.update(epochs=2, channels=4, embedding_dim=4, pair_dim=4, cpu_threads=1)
    records = [dict(id='toy', sequence='GGAAAACC', structure='((....))')]
    initial, trained, result = module.train_pair(records, copy.deepcopy(records), config, tmp_path)
    assert any(not torch.equal(p, q) for p, q in zip(initial.parameters(), trained.parameters()))
    assert result['train_positive_pairs'] == 2
    selected = max(result['history'], key=lambda r: (r['validation_mean_pair_f1'], -r['mean_validation_loss']))
    assert result['selected_epoch'] == selected['epoch']


def test_saved_development_checkpoint_inference_and_hash_guard(monkeypatch):
    from pathlib import Path
    path = ROOT/'results/pair_development_summary.json'
    if not path.exists(): pytest.skip('Saved development run unavailable')
    spec = importlib.util.spec_from_file_location('pair_audit', ROOT/'scripts/verify_pair_development.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    assert module.audit_pair(path)['test_evaluated'] is False
    summary = json.loads(path.read_text()); checkpoint = Path(summary['run_dir'])/'best_pair_model.pt'
    original = Path.read_bytes
    def changed(self):
        content = original(self)
        return content+b'changed test view' if self == checkpoint else content
    monkeypatch.setattr(Path, 'read_bytes', changed)
    with pytest.raises(ValueError, match='pair checkpoint changed'): module.audit_pair(path)
