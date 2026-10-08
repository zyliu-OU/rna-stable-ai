import json

from rnastable.budget_progress import count_saved_searches


def checkpoint(path,count):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({'completed_jobs':count,'rows':[{}]*count}))


def test_archives_and_old_child_runs_do_not_inflate_progress(tmp_path):
    directory=tmp_path/'results/equal_budget_runs'
    for stamp in ['older','newer']:
        # Use sortable timestamps rather than lexical words.
        stamp='20260101' if stamp=='older' else '20260102'
        run=directory/stamp
        run.mkdir(parents=True)
        (run/'manifest.json').write_text('{}')
        checkpoint(run/'long/results/sweep_runs/20260103/checkpoint.json',1)
        checkpoint(run/'restarts/results/sweep_runs/20260103/checkpoint.json',4)
        checkpoint(run/'restarts/results/sweep_runs/20260103/archive/20260104/checkpoint.json',3)
        checkpoint(run/'restarts/results/sweep_runs/20260102/checkpoint.json',2)
    assert count_saved_searches([{'root':str(tmp_path)}])==5


def test_missing_partial_and_inconsistent_checkpoints_are_tolerated(tmp_path):
    tasks=[{'root':str(tmp_path)}]
    assert count_saved_searches(tasks)==0
    run=tmp_path/'results/equal_budget_runs/20260101'
    run.mkdir(parents=True);(run/'manifest.json').write_text('{}')
    path=run/'long/results/sweep_runs/20260102/checkpoint.json'
    path.parent.mkdir(parents=True);path.write_text('{')
    assert count_saved_searches(tasks)==0
    path.write_text(json.dumps({'completed_jobs':8,'rows':[]}))
    assert count_saved_searches(tasks)==0
