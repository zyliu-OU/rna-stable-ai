import copy
import json

import pytest

from rnastable.budget_study import arm_specs, compare_arms, measured_sum, run_budget_study
from rnastable.cli import ROOT


def spec():
    return json.loads((ROOT/'configs/evaluation_equal_budget.json').read_text())


def test_prespecified_equal_caps_fixed_beam_and_paired_initial_seed():
    study = spec()
    arms = arm_specs(study, ROOT/'configs/optimization.json')
    assert arms['long']['search_seeds'] == [2740]
    assert arms['restarts']['search_seeds'] == [2740,2741,2742,2743]
    assert arms['long']['optimization_overrides']['steps'] == 32
    assert arms['restarts']['optimization_overrides']['steps'] == 8
    assert arms['long']['beam_sizes'] == arms['restarts']['beam_sizes'] == [200]
    assert arms['long']['sequence_seeds'] == [1732,1733,1734]


@pytest.mark.parametrize('change', [{'long_steps':31}, {'long_steps':True},
    {'steps_per_restart':0}, {'restart_search_seeds':[1,1]}, {'restart_search_seeds':[1]},
    {'restart_search_seeds':[1,True]}, {'beam_size':True}, {'schema_version':2},
    {'optimization_overrides':{'steps':48}}])
def test_invalid_study_rejected(change):
    with pytest.raises(ValueError):
        arm_specs({**spec(), **change}, ROOT/'configs/optimization.json')


def observations():
    study = spec(); study.update(lengths=[1000], sequence_seeds=[1732])
    sweeps, portfolios = {}, {}
    for name, seeds in [('long',[2740]), ('restarts',[2740,2741,2742,2743])]:
        sweeps[name] = {'rows': [dict(kind='mixed', length=1000, sequence_seed=1732,
            search_seed=s, beam_size=200, input_sha256='test_only_hash', status='validated',
            steps_attempted=32 if name=='long' else 8, search_wall_seconds=1.,
            finalist_validation_wall_seconds=2., reference_wall_seconds=3., reference_reused=i>0)
            for i,s in enumerate(seeds)]}
        portfolios[name] = {'rows': [dict(kind='mixed',length=1000,sequence_seed=1732,
            input_sha256='test_only_hash', input_vienna_energy_kcal_mol=-100.,
            selected_vienna_delta_kcal_mol=-5. if name=='long' else -6.,
            selected_fasta='test_only.fasta', selected_job_id='test_only')]}
    return study,sweeps,portfolios


def test_pairing_reports_extra_cost_and_full_denominators():
    study,sweeps,portfolios=observations()
    rows, groups = compare_arms(study,sweeps,portfolios)
    row=rows[0]
    assert row['winner']=='restarts' and row['restart_minus_long_kcal_mol']==-1.
    assert row['long_attempted_proposals']==row['restarts_attempted_proposals']==32
    assert row['long_search_wall_seconds']==1. and row['restarts_search_wall_seconds']==4.
    assert row['restarts_reference_wall_seconds']==3.  # reused reference never counted twice
    assert row['restarts_validation_wall_seconds']==8.
    assert groups[0]['measured_pairs']==1 and groups[0]['unknown_pairs']==0


def test_failed_restart_is_unknown_even_if_portfolio_has_an_output():
    study,sweeps,portfolios=observations()
    sweeps['restarts']['rows'][0]['status']='validation_failed'
    rows,groups=compare_arms(study,sweeps,portfolios)
    assert rows[0]['winner']=='unknown' and rows[0]['restart_minus_long_kcal_mol'] is None
    assert groups[0]['measured_pairs']==0 and groups[0]['unknown_pairs']==1


@pytest.mark.parametrize('change', ['input', 'reference', 'beam', 'duplicate_seed', 'over_budget'])
def test_incompatible_or_over_budget_comparison_fails(change):
    study,sweeps,portfolios=observations()
    if change=='input': portfolios['restarts']['rows'][0]['input_sha256']='different'
    elif change=='reference': portfolios['restarts']['rows'][0]['input_vienna_energy_kcal_mol']=-101.
    elif change=='beam': sweeps['restarts']['rows'][0]['beam_size']=400
    elif change=='duplicate_seed': sweeps['restarts']['rows'][0]['search_seed']=2741
    else: sweeps['restarts']['rows'][0]['steps_attempted']=9
    with pytest.raises(ValueError): compare_arms(study,sweeps,portfolios)


@pytest.mark.parametrize('value', [None, float('nan'), float('inf'), -1, True])
def test_missing_or_invalid_cost_is_unknown(value):
    assert measured_sum([{'time':value}], 'time') is None


def test_invalid_budget_creates_no_measurement_artifacts(tmp_path):
    invalid={**spec(), 'long_steps':31}
    path=tmp_path/'config.json';path.write_text(json.dumps(invalid))
    with pytest.raises(ValueError): run_budget_study(tmp_path/'output',path)
    assert not (tmp_path/'output').exists()


def test_input_records_are_not_mutated():
    study,sweeps,portfolios=observations()
    saved=copy.deepcopy((study,sweeps,portfolios))
    compare_arms(study,sweeps,portfolios)
    assert (study,sweeps,portfolios)==saved


def test_fold_request_counts_exclude_duplicates_and_reference_reuse(tmp_path):
    from rnastable.budget_study import fold_requests
    rows=[]
    for index in range(2):
        path=tmp_path/f'job{index}.json'
        evidence={'search':{'status':'completed','history':[
            {'status':'ok'}, {'status':'duplicate'}, {'status':'timeout'}, {'status':'no_legal_proposal'}]}}
        path.write_text(json.dumps(evidence))
        rows.append({'summary_path':str(path),'input_sha256':'original',
                     'finalist_sha256':'changed' if index==0 else 'original',
                     'reference_reused':index>0})
    assert fold_requests(rows)=={'baseline':2,'proposals':4,'reference':1,'validation':1}


def test_one_failed_arm_does_not_stop_the_other_or_publish_success(tmp_path,monkeypatch):
    calls=[]
    def failed_arm(root,path,resume):
        calls.append(root.name)
        raise ValueError('test-only folding failure')
    monkeypatch.setattr('rnastable.budget_study.run_sweep',failed_arm)
    with pytest.raises(ValueError,match='failed arms'):
        run_budget_study(tmp_path,ROOT/'configs/evaluation_equal_budget.json')
    assert calls==['long','restarts']
    run=next((tmp_path/'results/equal_budget_runs').iterdir())
    status=json.loads((run/'status.json').read_text())
    assert not status['complete'] and set(status['errors'])=={'long','restarts'}
    assert not (tmp_path/'results/equal_budget_summary.json').exists()
    assert len(list((run/'attempts').rglob('*.json')))==2
    changed=json.loads((run/'long/config.json').read_text())
    changed['optimization_overrides']['steps']=33
    (run/'long/config.json').write_text(json.dumps(changed))
    with pytest.raises(ValueError,match='frozen arm configuration changed'):
        run_budget_study(tmp_path,ROOT/'configs/evaluation_equal_budget.json',run)
    assert calls==['long','restarts']


def test_interrupt_records_partial_state_and_stops_owned_study(tmp_path,monkeypatch):
    calls=[]
    def interrupt(root,path,resume):
        calls.append(root.name)
        raise KeyboardInterrupt
    monkeypatch.setattr('rnastable.budget_study.run_sweep',interrupt)
    with pytest.raises(KeyboardInterrupt):
        run_budget_study(tmp_path,ROOT/'configs/evaluation_equal_budget.json')
    assert calls==['long']
    run=next((tmp_path/'results/equal_budget_runs').iterdir())
    status=json.loads((run/'status.json').read_text())
    assert status=={'complete':False,'interrupted_arm':'long'}
    assert len(list((run/'attempts').rglob('*.json')))==1
    assert not (tmp_path/'results/equal_budget_summary.json').exists()
