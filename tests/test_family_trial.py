import json
from pathlib import Path
import pytest
from rnastable.exposures import record_exposure, read_exposure, collect_known_exposures
from rnastable.rfam_data import select_cohort, cohort_inputs
from rnastable.family_plan import plan_families
from rnastable.cli import ROOT


def test_incomplete_test_start_is_exposed_and_family_cannot_be_reused(tmp_path):
    run = tmp_path/'results/family_trial_runs/interrupted'
    record = {'id': 'test', 'sequence': 'ACGUACGU', 'structure': '........', 'reference_kind': 'computational', 'source': 'fixture', 'family_id': 'test-family', 'family_source': 'fixture'}
    event = record_exposure(run, 'test_started', [record])
    assert not (run/'summary.json').exists()
    exposed = collect_known_exposures(tmp_path)
    assert exposed[0]['sequence'] == record['sequence']
    assert read_exposure(event['path'])['stage'] == 'test_started'
    records = [dict(record), {**record, 'id': 'train', 'sequence': 'AAAAAAAA', 'family_id': 'train-family'}, {**record, 'id': 'val', 'sequence': 'CCCCCCCC', 'family_id': 'val-family'}]
    config = {'families': {'train': ['train-family'], 'validation': ['val-family'], 'test': ['test-family']}}
    refs, assignments, plan = cohort_inputs(records, config)
    with pytest.raises(ValueError, match='previously exposed'): plan_families(refs, assignments, plan, exposed)


def test_corrupted_exposure_fails_closed(tmp_path):
    run = tmp_path/'results/family_trial_runs/interrupted'
    event = record_exposure(run, 'training_started', [{'sequence': 'AAAA'}])
    path = Path(event['path']); data = json.loads(path.read_text()); data['records'][0]['sequence'] = 'CCCC'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='changed'): collect_known_exposures(tmp_path)


def test_historical_custom_development_snapshot_counts_as_exposure(tmp_path):
    path = tmp_path/'results/pair_development_runs/custom/train.json'; path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'records': [{'sequence': 'GCGCGCGC', 'family_id': 'new-family'}]}))
    assert collect_known_exposures(tmp_path)[0]['family_id'] == 'new-family'


def test_deterministic_cohort_rejects_prior_and_redundant_sequences():
    config = {'families': {'train': ['tr'], 'validation': ['va'], 'test': ['te']}, 'max_records_per_family': 1}
    records = [{'id': 'a', 'sequence': 'AAAAAA', 'family_id': 'te'}, {'id': 'b', 'sequence': 'CCCCCC', 'family_id': 'te'}, {'id': 'c', 'sequence': 'GGGGGG', 'family_id': 'va'}, {'id': 'd', 'sequence': 'UUUUUU', 'family_id': 'tr'}, {'id': 'e', 'sequence': 'UUUUUU', 'family_id': 'tr'}]
    selected, excluded = select_cohort(records[::-1], config, [{'sequence': 'AAAAAA'}])
    assert [r['id'] for r in selected] == ['b', 'c', 'd']
    assert excluded == [{'id': 'a', 'reason': 'prior_sequence_exposure'}, {'id': 'e', 'reason': 'sequence_redundancy'}]


def test_completed_family_trial_replays():
    import importlib.util
    path = ROOT/'results/family_trial_summary.json'
    if not path.exists(): pytest.skip('No completed family trial')
    spec = importlib.util.spec_from_file_location('verify_family_trial', ROOT/'scripts/verify_family_trial.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.audit_trial(path)


def test_rfam_metadata_requires_exact_sequence_binding(tmp_path):
    import zipfile
    from rnastable.rfam_data import load_rfam_candidates
    directories = [('train', 'train_datasets/S-Processed-TRA.fasta'), ('holdout', 'holdout_datasets/S-Processed-VAL.fasta'), ('test', 'test_datasets/S-Processed-TES.fasta')]
    header = '>SSTRAND_ID=RFA_00001; TYPE=Other RNA; EXT_SOURCE=Rfam Database; EXT_ID=RF00001 fixture; ORGANISM=fixture\n'
    for split, name in directories:
        path = tmp_path/'datasets_in_fasta_form'/name; path.parent.mkdir(parents=True)
        path.write_text(header+'AAAA\n' if split == 'train' else '')
    with zipfile.ZipFile(tmp_path/'input_data.zip', 'w') as archive:
        archive.writestr('input_data/StructureData/train/RFA_00001.bpseq', '1 A 0\n2 A 0\n3 A 0\n4 C 0\n')
    config = {'min_length': 1, 'max_length': 256, 'families': {'train': ['RF00001'], 'validation': ['RF00008'], 'test': ['RF00169']}}
    records, imported = load_rfam_candidates(tmp_path, config)
    assert records == [] and imported['exclusions'][0]['reason'] == 'No exact Rfam-source metadata match'
    path = tmp_path/'datasets_in_fasta_form/train_datasets/S-Processed-TRA.fasta'; path.write_text(header+'AAAC\n')
    records, _ = load_rfam_candidates(tmp_path, config)
    assert records[0]['family_id'] == 'RF00001' and records[0]['reference_kind'] == 'computational'


def test_real_test_family_is_registered_and_reuse_rejected():
    path = ROOT/'results/family_trial_summary.json'
    if not path.exists(): pytest.skip('No completed family trial')
    run = Path(json.loads(path.read_text())['run_dir'])/'family_plan'
    refs, assignments, plan = [json.loads((run/name).read_text()) for name in ('references.json', 'assignments.json', 'plan.json')]
    exposed = collect_known_exposures(ROOT)
    assert any(row.get('family_id') == 'RF00008' for row in exposed)
    with pytest.raises(ValueError, match='previously exposed'): plan_families(refs, assignments, plan, exposed)


def test_empty_family_filter_and_invalid_exposure_stage_fail(tmp_path):
    config = {'families': {'train': ['tr'], 'validation': ['va'], 'test': ['te']}, 'max_records_per_family': 1}
    with pytest.raises(ValueError, match='empty planned family'): select_cohort([], config, [])
    with pytest.raises(ValueError, match='stage'): record_exposure(tmp_path, 'completed', [])
    assert not (tmp_path/'exposures').exists()


def test_context_development_events_are_also_registered(tmp_path):
    run=tmp_path/'results/context_development_runs/interrupted'
    record_exposure(run,'validation_started',[{'sequence':'AGAGAG','family_id':'context-family'}])
    assert collect_known_exposures(tmp_path)[0]['family_id']=='context-family'


def test_context_family_test_start_is_registered_without_completion(tmp_path):
    run=tmp_path/'results/context_family_trial_runs/interrupted'
    record_exposure(run,'test_started',[{'sequence':'ACGUAC','family_id':'RF00017'}])
    assert collect_known_exposures(tmp_path)[0]['family_id']=='RF00017'
    assert not (run/'summary.json').exists()
