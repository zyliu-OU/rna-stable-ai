import pytest
from rnastable.negative_sampling import sampled_supervision
from rnastable.full_pair_supervision import full_supervision


def test_sampling_is_reproducible_and_preserves_positives():
    import torch
    record={'id':'fixture','sequence':'G'*10+'A'*60+'C'*10,'structure':'('*10+'.'*60+')'*10}
    full,y,excluded=full_supervision(record);first,labels,skipped=sampled_supervision(record,negatives_per_positive=2,minimum_negatives=1);second,y2,_=sampled_supervision(record,negatives_per_positive=2,minimum_negatives=1)
    assert torch.equal(first,second) and torch.equal(labels,y2)
    assert labels.sum()==y.sum()==10 and len(labels)-labels.sum()==20 and skipped==excluded==0
    assert set(map(tuple,first[labels.bool()].tolist()))==set(map(tuple,full[y.bool()].tolist()))
    changed,_,_=sampled_supervision(record,seed=42,negatives_per_positive=2,minimum_negatives=1)
    assert not torch.equal(changed,first)


def test_negative_only_record_keeps_bounded_training_signal():
    record={'id':'unpaired','sequence':'GC'*40,'structure':'.'*80}
    pairs,labels,excluded=sampled_supervision(record)
    assert len(labels)==64 and not labels.any() and excluded==0


@pytest.mark.parametrize('settings',[{'seed':True},{'negatives_per_positive':0},{'minimum_negatives':0}])
def test_invalid_sampling_settings_rejected(settings):
    with pytest.raises(ValueError):sampled_supervision({'id':'x','sequence':'GAAAC','structure':'(...)'},**settings)


def test_measured_sampling_checkpoint_replays(monkeypatch):
    import importlib.util
    from rnastable.cli import ROOT
    path=ROOT/'results/sampled_comparative_development_summary.json'
    if not path.exists():pytest.skip('No completed sampled comparative development')
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('verify_sampled_comparative_development',ROOT/'scripts/verify_sampled_comparative_development.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.audit_sampled(path)
