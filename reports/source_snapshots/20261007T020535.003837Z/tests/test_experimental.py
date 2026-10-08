import copy
import json
from pathlib import Path

import pytest

from rnastable.cli import ROOT
from rnastable.experimental_data import (conflicts, filter_splits, load_pdb_splits,
                                         load_pilot_config, parse_bpseq, sequence_similarity)
from rnastable.scoring import base_pairs, paired_fraction
from rnastable.structure_model import decode_states, predict, train_model


def test_bpseq_preserves_exact_pairs():
    seq, structure = parse_bpseq('1 G 6\n2 C 5\n3 A 0\n4 A 0\n5 G 2\n6 C 1\n')
    assert seq == 'GCAAGC' and structure == '((..))'
    assert base_pairs(structure) == {(0, 5), (1, 4)}


@pytest.mark.parametrize('content', [
    '1 G 3\n2 A 0\n3 C 0', '1 G 1', '2 A 0', '1 G -1', '1 T 0',
    '1 G 3\n2 C 4\n3 C 1\n4 G 2', '1 G e1 0.1', '',
])
def test_bpseq_rejects_corruption_and_crossing_pairs(content):
    with pytest.raises(ValueError): parse_bpseq(content)


def test_overlap_filter_retains_test_priority():
    def item(identity, accession, sequence):
        return dict(id=identity, pdb_accession=accession, sequence=sequence)
    test = item('test', '1abc', 'GCAAAAGC')
    val = item('val', '2abc', 'AAAAACCC')
    candidates = {'test': [test], 'validation': [val, item('overlap-val', '1abc', 'UUUUUUUU')],
                  'train': [item('similar', '3abc', 'GCAAAAGU'), item('duplicate', '4abc', 'AAAAACCC'),
                            item('unique', '5abc', 'UUUUGGGG')]}
    kept, excluded = filter_splits(candidates, .8)
    assert [r['id'] for r in kept['train']] == ['unique']
    assert len(excluded) == 3 and kept['test'] == [test]
    assert sequence_similarity('GCAAAAGC', 'GCAAAAGU') == .875


def test_real_import_binds_metadata_and_has_no_split_conflicts():
    config = load_pilot_config(ROOT/'configs/experimental_pilot.json')
    splits, record = load_pdb_splits(ROOT/'external/EternaFold', config)
    assert all(splits.values())
    for split, records in splits.items():
        assert record['retained_counts'][split] == len(records)
        for r in records:
            assert r['reference_kind'] == 'experimental' and r['source_url'].endswith(r['pdb_accession'])
            assert 20 <= len(r['sequence']) <= 256
            paired_fraction(r['structure'], len(r['sequence']))
    all_records = [r for records in splits.values() for r in records]
    for i, first in enumerate(all_records):
        assert not any(conflicts(first, second, config['similarity_threshold']) for second in all_records[i+1:])


@pytest.mark.parametrize('key,value', [('epochs', True), ('max_length', 1000), ('cpu_threads', 3),
    ('learning_rate', float('nan')), ('seed', -1), ('embedding_dim', 0), ('similarity_threshold', 0)])
def test_config_rejects_unbounded_or_invalid_settings(tmp_path, key, value):
    config = json.loads((ROOT/'configs/experimental_pilot.json').read_text()); config[key] = value
    path = tmp_path/'bad.json'; path.write_text(json.dumps(config))
    with pytest.raises(ValueError): load_pilot_config(path)


def test_decoder_handles_invalid_contacts_and_unmatched_states():
    assert decode_states('GCAAAAGC', [1, 1, 0, 0, 0, 0, 2, 2]) == '((....))'
    assert decode_states('AAAAAAAA', [1, 1, 0, 0, 0, 0, 2, 2]) == '........'
    assert decode_states('GCGC', [1, 1, 2, 2]) == '....'
    with pytest.raises(ValueError): decode_states('GC', [1])


def test_decoder_always_produces_nested_canonical_pairs():
    import random
    rng = random.Random(22)
    for _ in range(30):
        sequence = ''.join(rng.choices('ACGU', k=80))
        structure = decode_states(sequence, rng.choices([0, 1, 2], k=80))
        paired_fraction(structure, 80)
        for i, j in base_pairs(structure):
            assert j-i > 3 and sequence[i]+sequence[j] in ('AU', 'UA', 'CG', 'GC', 'GU', 'UG')


def test_training_updates_weights_and_selects_validation_only(tmp_path):
    import torch
    config = load_pilot_config(ROOT/'configs/experimental_pilot.json')
    config.update(epochs=2, cpu_threads=1, embedding_dim=4, channels=4)
    records = [dict(id='toy', sequence='GCAAAAGC', structure='((....))')]
    initial, model, summary = train_model(records, copy.deepcopy(records), config, tmp_path)
    assert summary['complete'] and summary['epochs_completed'] == 2
    assert summary['class_counts_train_only'] == [4, 2, 2]
    assert any(not torch.equal(p, q) for p, q in zip(initial.parameters(), model.parameters()))
    expected = max(summary['history'], key=lambda r: (r['validation_mean_pair_f1'], -r['validation_mean_loss']))
    assert summary['selected_epoch'] == expected['epoch']
    assert predict(model, records, 'trained')[0]['sequence'] == records[0]['sequence']
    assert (tmp_path/'best_model.pt').exists() and (tmp_path/'initial_model.pt').exists()


def pilot_auditor():
    import importlib.util
    spec = importlib.util.spec_from_file_location('pilot_audit', ROOT/'scripts/verify_experimental_pilot.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.audit_pilot


def test_saved_real_pilot_audit():
    path = ROOT/'results/experimental_pilot_summary.json'
    if not path.exists():
        pytest.skip('Measured pilot is not available in this checkout')
    assert pilot_auditor()(path)['complete']


def test_saved_pilot_rejects_checkpoint_corruption(monkeypatch):
    path = ROOT/'results/experimental_pilot_summary.json'
    if not path.exists():
        pytest.skip('Measured pilot is not available in this checkout')
    summary = json.loads(path.read_text())
    checkpoint = Path(summary['training']['best_checkpoint']).resolve()
    original = Path.read_bytes
    def corrupt(self):
        content = original(self)
        return content+b'corrupted test view' if self.resolve() == checkpoint else content
    monkeypatch.setattr(Path, 'read_bytes', corrupt)
    with pytest.raises(ValueError, match='model checkpoint changed'):
        pilot_auditor()(path)
