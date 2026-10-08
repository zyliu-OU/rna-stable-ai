import importlib.util
import pytest
from rnastable.cli import ROOT


def module(name,monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/(name+'.py'));value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def test_grouped_metrics_keeps_failures_and_missing(monkeypatch):
    m=module('compare_expanded_development',monkeypatch)
    refs=[{'id':'one','sequence':'GGAAAACC','structure':'((....))','source':'Gutell Lab CRW','reference_kind':'computational'}, {'id':'two','sequence':'GGAAAACC','structure':'((....))','source':'Rfam','reference_kind':'computational'}]
    pred=[{'id':'one','sequence':'GGAAAACC','structure':'((....))','method':'model','status':'ok'},{'id':'two','sequence':'GGAAAACC','method':'model','status':'timeout'}]
    rows=m.grouped_metrics(refs,pred,['model','missing'])
    assert rows[0]=={'group':'all','method':'model','planned':2,'measured':1,'failed':1,'missing':0,'mean_pair_f1':1.0}
    assert rows[1]['missing']==2 and rows[1]['mean_pair_f1'] is None
    with pytest.raises(ValueError,match='Duplicate'):m.grouped_metrics(refs,pred+[pred[0]],['model'])


def test_grouped_metrics_rejects_sequence_mismatch(monkeypatch):
    m=module('compare_expanded_development',monkeypatch)
    refs=[{'id':'one','sequence':'GGAAAACC','structure':'((....))','source':'Gutell Lab CRW','reference_kind':'computational'}]
    with pytest.raises(ValueError,match='Sequence'):m.grouped_metrics(refs,[{'id':'one','sequence':'GGAAAACU','structure':'((....))','method':'m','status':'ok'}],['m'])


def test_measured_comparison_replays(monkeypatch):
    path=ROOT/'results/expanded_development_comparison_summary.json'
    if not path.exists():pytest.skip('No completed expanded comparison')
    module('verify_expanded_development_comparison',monkeypatch).audit_comparison(path)
