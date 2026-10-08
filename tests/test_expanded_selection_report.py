import importlib.util
import json
import pytest
from rnastable.cli import ROOT
from rnastable.reference import digest


def report_module(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('report_expanded_checkpoint_selection',ROOT/'scripts/report_expanded_checkpoint_selection.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_report_rejects_changed_validation_before_composition(tmp_path,monkeypatch):
    base=tmp_path/'base';selected=tmp_path/'selected';base.mkdir();selected.mkdir();data=b'{"records": []}'
    (base/'validation.json').write_bytes(data);(base/'manifest.json').write_text(json.dumps({'validation_sha256':digest(data)}));pred=b'{"methods": [], "records": []}';(base/'predictions.json').write_bytes(pred)
    (selected/'validation.json').write_bytes(b'{"records": [{}]}');(selected/'manifest.json').write_text(json.dumps({'snapshot_sha256':{'validation.json':digest((selected/'validation.json').read_bytes())}}))
    sources={'expanded_development_comparison':{'run_dir':str(base),'artifacts_sha256':{'predictions.json':digest(pred)}},'exact_comparative_development':{'run_dir':str(selected)}}
    with pytest.raises(ValueError,match='validation differs'):report_module(monkeypatch).compose(sources)


def test_measured_selection_report_replays(monkeypatch):
    path=ROOT/'results/expanded_checkpoint_selection_summary.json'
    if not path.exists():pytest.skip('No completed selection report')
    report_module(monkeypatch).audit_report(path)
