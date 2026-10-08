import json
from pathlib import Path

import pytest

from rnastable.budget_batches import aggregate_pairs, batch_provenance, run_budget_batches
from rnastable.cli import ROOT


def test_long_plan_preserves_protocol_and_uses_new_inputs():
    from rnastable.budget_study import arm_specs
    short=json.loads((ROOT/'configs/evaluation_equal_budget.json').read_text())
    long=json.loads((ROOT/'configs/evaluation_equal_budget_long.json').read_text())
    assert long['lengths']==[5000,10000]
    assert long['sequence_seeds']==[1735,1736]
    assert not set(long['sequence_seeds'])&set(short['sequence_seeds'])
    for key in ('long_steps','steps_per_restart','beam_size','restart_search_seeds'):
        assert long[key]==short[key]
    arms=arm_specs(long,ROOT/'configs/optimization.json')
    assert arms['long']['optimization_overrides']['steps']==32
    assert len(arms['restarts']['search_seeds'])*arms['restarts']['optimization_overrides']['steps']==32


def test_unknown_pairs_are_not_measured_zero():
    rows=[dict(length=5000,comparison_status='measured',restart_minus_long_kcal_mol=-2.,winner='restarts'),
          dict(length=5000,comparison_status='incomplete_validation',restart_minus_long_kcal_mol=None,winner='unknown')]
    group=aggregate_pairs(rows)[0]
    assert group['mean_restart_minus_long_kcal_mol']==-2.
    assert group['measured_pairs']==1 and group['unknown_pairs']==1


@pytest.mark.parametrize('workers',[0,3,True])
def test_invalid_worker_count_creates_no_outputs(tmp_path,workers):
    with pytest.raises(ValueError,match='one or two'):
        run_budget_batches(tmp_path,ROOT/'configs/evaluation_equal_budget_long.json',workers)
    assert not (tmp_path/'results').exists()


def test_failure_records_native_events_and_allows_resume_checks(tmp_path,monkeypatch):
    called=[]
    def fail(tasks,command,workers,progress):
        assert len(tasks)==4 and workers==2
        for i,task in enumerate(tasks):
            called.append(command(task))
            progress('started',i,100+i,i,4)
            progress('finished',i,1,i+1,4)
        return [1]*4
    monkeypatch.setattr('rnastable.budget_batches.run_batches',fail)
    with pytest.raises(ValueError,match='Budget batch failures'):
        run_budget_batches(tmp_path,ROOT/'configs/evaluation_equal_budget_long.json')
    assert len(called)==4
    assert all('--workers' not in command for command in called)  # each input folds serially
    run=next((tmp_path/'results/equal_budget_batch_runs').iterdir())
    status=json.loads((run/'driver_status.json').read_text())
    assert not status['complete'] and status['component_exit_codes']==[1]*4
    assert not (tmp_path/'results/equal_budget_long_summary.json').exists()
    events=[json.loads(line) for line in Path(status['event_log']).read_text().splitlines()]
    assert events[-1]['event']=='failed'
    with pytest.raises(ValueError,match='worker limit changed'):
        run_budget_batches(tmp_path,ROOT/'configs/evaluation_equal_budget_long.json',1,run)
    manifest=json.loads((run/'manifest.json').read_text())
    config=Path(manifest['components'][0]['config']);config.write_text('{}')
    with pytest.raises(ValueError,match='frozen component config changed'):
        run_budget_batches(tmp_path,ROOT/'configs/evaluation_equal_budget_long.json',2,run)


def test_interruption_is_saved(tmp_path,monkeypatch):
    def interrupt(*args):raise KeyboardInterrupt
    monkeypatch.setattr('rnastable.budget_batches.run_batches',interrupt)
    with pytest.raises(KeyboardInterrupt):
        run_budget_batches(tmp_path,ROOT/'configs/evaluation_equal_budget_long.json')
    run=next((tmp_path/'results/equal_budget_batch_runs').iterdir())
    status=json.loads((run/'driver_status.json').read_text())
    assert not status['complete'] and status['interrupted']
    assert not (tmp_path/'results/equal_budget_long_summary.json').exists()


def test_heartbeat_uses_only_live_searches(tmp_path,monkeypatch,capsys):
    from rnastable.budget_progress import count_saved_searches
    from test_budget_progress import checkpoint

    def fail(tasks,command,workers,progress):
        for task in tasks:
            for stamp in ('20260101','20260102'):
                child=Path(task['root'])/'results/equal_budget_runs'/stamp
                child.mkdir(parents=True)
                (child/'manifest.json').write_text('{}')
                for arm,count in (('long',1),('restarts',4)):
                    sweep=child/arm/'results/sweep_runs'
                    checkpoint(sweep/'20260103/checkpoint.json',count)
                    checkpoint(sweep/'20260103/archive/20260104/checkpoint.json',count)
                    checkpoint(sweep/'20260102/checkpoint.json',count)
        progress('heartbeat',-1,0,0,len(tasks))
        run=Path(tasks[0]['root']).parents[1]
        status=json.loads((run/'driver_status.json').read_text())
        assert status['saved_searches']==count_saved_searches(tasks)==20
        return [1]*len(tasks)

    monkeypatch.setattr('rnastable.budget_batches.run_batches',fail)
    with pytest.raises(ValueError,match='Budget batch failures'):
        run_budget_batches(tmp_path,ROOT/'configs/evaluation_equal_budget_long.json')
    assert '20/20 saved searches' in capsys.readouterr().out


@pytest.mark.parametrize('change',['historical_driver','missing_helper','changed_helper'])
def test_changed_driver_provenance_rejects_resume_without_writes(tmp_path,monkeypatch,change):
    monkeypatch.setattr('rnastable.budget_batches.run_batches',lambda *args: [1]*4)
    with pytest.raises(ValueError,match='Budget batch failures'):
        run_budget_batches(tmp_path,ROOT/'configs/evaluation_equal_budget_long.json')
    run=next((tmp_path/'results/equal_budget_batch_runs').iterdir())
    path=run/'manifest.json'
    manifest=json.loads(path.read_text())
    hashes=manifest['provenance']['batch_code_sha256']
    helper=str(ROOT/'src/rnastable/budget_progress.py')
    assert helper in batch_provenance()['batch_code_sha256']
    if change=='historical_driver':
        hashes.pop(helper)
        hashes[str(ROOT/'src/rnastable/budget_batches.py')]='8e3fdb03b3e4c71608719896a6d29e185facaa43e44ebad888bac2ae0ecde0f1'
    elif change=='missing_helper':
        hashes.pop(helper)
    else:
        hashes[helper]='0'*64
    path.write_text(json.dumps(manifest))
    before={p.relative_to(run):p.read_bytes() for p in run.rglob('*') if p.is_file()}
    def forbidden(*args):
        pytest.fail('Rejected resume must not start children')
    monkeypatch.setattr('rnastable.budget_batches.run_batches',forbidden)
    with pytest.raises(ValueError,match='Historical runs require.*no.*') as error:
        run_budget_batches(tmp_path,ROOT/'configs/evaluation_equal_budget_long.json',2,run)
    assert 'verify_equal_budget.py --summary' in str(error.value)
    assert before=={p.relative_to(run):p.read_bytes() for p in run.rglob('*') if p.is_file()}
