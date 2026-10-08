import pytest
from rnastable.candidate_diagnostics import candidate_coverage


def test_oracle_is_bound_and_loss_components_partition_reference():
    r={'sequence':'GGGAAACCC','structure':'(((...)))'}
    result=candidate_coverage(r,[(0,8),(1,7)],[(0,8),(1,7)],'('+'.'*7+')')
    assert result['reference_pairs']==3 and result['nonpositive_reference_pairs']==1
    assert result['decoder_omitted_reference_pairs']==1 and result['top_k_removed_reference_pairs']==0
    assert result['oracle_candidate_f1_upper_bound']==.8 and result['decoded_pair_f1']==.5
    result=candidate_coverage(r,[(0,8)],[(0,8),(1,7)],'('+'.'*7+')')
    assert result['top_k_removed_reference_pairs']==1


def test_unsupported_contacts_and_empty_reference():
    r={'sequence':'AAAAAAAA','structure':'((....))'}
    result=candidate_coverage(r,[],[],'.'*8)
    assert result['unsupported_reference_pairs']==2 and result['oracle_candidate_f1_upper_bound']==0
    r['structure']='.'*8
    assert candidate_coverage(r,[],[],'.'*8)['oracle_candidate_f1_upper_bound']==1


def test_rejects_impossible_candidate_inventory():
    r={'sequence':'GGAAAACC','structure':'((....))'}
    with pytest.raises(ValueError,match='positive'):candidate_coverage(r,[(0,7)],[],'.'*8)
    with pytest.raises(ValueError,match='outside'):candidate_coverage(r,[],[],r['structure'])


def test_measured_candidate_diagnostics_replay(monkeypatch):
    import importlib.util
    from rnastable.cli import ROOT
    path=ROOT/'results/expanded_candidate_diagnostics_summary.json'
    if not path.exists():pytest.skip('No completed expanded candidate diagnostics')
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('verify_expanded_candidate_diagnostics',ROOT/'scripts/verify_expanded_candidate_diagnostics.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.audit_diagnostics(path)
