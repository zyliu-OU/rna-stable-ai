"""Test-only fold responses exercise selection; they are not benchmark data."""
import json
from pathlib import Path
import pytest
from rnastable.cli import ROOT
from rnastable.optimization import load_optimization_config, run_optimization
from rnastable.selection import select_finalist
from rnastable.sequences import generate_sequence, read_fasta, write_fasta


def record(energy=-100, status='ok'):
    return {'status': status, 'mfe_kcal_mol': energy, 'structure': '.'*1000,
            'error': '' if status == 'ok' else 'Test-only simulated failure'}


@pytest.mark.parametrize('energy,source,reason', [(-101,'finalist','confirmed_improvement'),
    (-100,'input','no_reference_improvement'),(-99,'input','no_reference_improvement'),
    (-100-1e-10,'input','no_reference_improvement')])
def test_reference_selection_direction(energy,source,reason):
    result=select_finalist('ACGU','CAGU','completed',record(),record(energy))
    assert result['source']==source and result['reason']==reason
    assert result['selected_vienna_delta_kcal_mol'] == (energy+100 if source=='finalist' else 0)


@pytest.mark.parametrize('bad', [None, record(status='timeout'), record(float('nan')),
    record(float('inf')), record(True), {'status':'ok'}, record('-200')])
def test_failed_or_invalid_validation_returns_input(bad):
    for before,after in [(record(),bad),(bad,record(-101))]:
        result=select_finalist('ACGU','CAGU','completed',before,after)
        assert result['source']=='input' and result['reason']=='validation_failed'
        assert result['candidate_vienna_delta_kcal_mol'] is None
        assert result['vienna_improvement_confirmed'] is None


@pytest.mark.parametrize('case', ['improved','equal','worsened','input_timeout',
                                  'finalist_timeout','unchanged_sequence','search_failed'])
def test_optimization_publishes_selected_and_retains_finalist(tmp_path,monkeypatch,case):
    config=load_optimization_config(ROOT/'configs/optimization.json')
    config['steps']=2
    original=generate_sequence(1000,'mixed',1729)
    if case=='unchanged_sequence':
        config['protected_positions']=list(range(1,1001))
    input_path=write_fasta(tmp_path/'input.fasta','test_only',original)
    lf_calls=0
    def fake_fold(root,sequence,config,tool,raw_path):
        nonlocal lf_calls
        if tool=='LinearFold':
            lf_calls+=1
            return record(-10-lf_calls, 'unavailable' if case=='search_failed' else 'ok')
        if sequence==original:
            return record(-100,'timeout' if case=='input_timeout' else 'ok')
        energy={'improved':-101,'equal':-100,'worsened':-99}.get(case,-101)
        return record(energy,'timeout' if case=='finalist_timeout' else 'ok')
    monkeypatch.setattr('rnastable.optimization.fold_sequence',fake_fold)
    monkeypatch.setattr('rnastable.cli.versions',lambda: {'test_only':True})
    summary=run_optimization(tmp_path,input_path,config)
    candidate=read_fasta(summary['finalist_fasta'])[0][1]
    selected=read_fasta(summary['selected_fasta'])[0][1]
    assert selected==(candidate if case=='improved' else original)
    assert summary['selection']['source']==('finalist' if case=='improved' else 'input')
    assert summary['selected_mutations_from_input']==(summary['mutations_from_input'] if case=='improved' else 0)
    assert json.loads((Path(summary['run_dir'])/'summary.json').read_text())==summary
    assert 'validation' in summary
    if case not in ('search_failed','unchanged_sequence'):
        assert candidate!=original  # rejected proposals remain available for audit


def test_unchanged_or_failed_search_never_selects_finalist():
    assert select_finalist('ACGU','ACGU','completed',record(),record())['reason']=='unchanged_sequence'
    assert select_finalist('ACGU','CAGU','baseline_failed',None,None)['reason']=='search_failed'


def test_sweep_fallback_preserves_candidate_and_resume_checks_selected(tmp_path,monkeypatch):
    from rnastable.sweep import run_sweep
    base=load_optimization_config(ROOT/'configs/optimization.json')
    (tmp_path/'optimization.json').write_text(json.dumps(base))
    spec=json.loads((ROOT/'configs/evaluation_selection_smoke.json').read_text())
    spec['optimization_overrides']['steps']=2
    path=tmp_path/'sweep.json';path.write_text(json.dumps(spec))
    original=generate_sequence(1000,'mixed',1729)
    calls={200:0,400:0}
    def fake_fold(root,seq,config,tool,raw_path):
        if tool=='LinearFold':
            beam=config['beam_size'];calls[beam]+=1
            return record(-10-calls[beam])
        return record(-100 if seq==original else -99)
    monkeypatch.setattr('rnastable.sweep.fold_sequence',fake_fold)
    monkeypatch.setattr('rnastable.sweep.plot_tradeoffs',lambda *_:'test-only-no-plot')
    result=run_sweep(tmp_path,path)
    for row in result['rows']:
        assert row['status']=='validated' and row['vienna_delta_kcal_mol']==1
        assert row['selection_source']=='input' and row['selected_mutations_from_input']==0
        assert read_fasta(row['finalist_fasta'])[0][1]!=original
        assert read_fasta(row['selected_fasta'])[0][1]==original
    assert sum(a['worsened'] for a in result['aggregates'])==2
    resumed=run_sweep(tmp_path,path,result['run_dir'])
    assert resumed['rows']==result['rows']
    selected=Path(result['rows'][0]['selected_fasta'])
    # Modify only test-local output to verify a corrupt selected file is rejected.
    selected.write_text('>tampered\n'+'A'*1000+'\n')
    with pytest.raises(ValueError,match='selected output'):
        run_sweep(tmp_path,path,result['run_dir'])
