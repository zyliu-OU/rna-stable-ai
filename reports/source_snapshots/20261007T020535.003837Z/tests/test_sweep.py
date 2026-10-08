import copy
import json
from pathlib import Path
import pytest
from rnastable.cli import ROOT
from rnastable.sweep import aggregate_rows, load_sweep_config, plan_jobs, run_sweep


def write_config(tmp_path, **changes):
    spec=json.loads((ROOT/'configs/evaluation_sweep.json').read_text())
    spec.update(changes)
    (tmp_path/'optimization.json').write_text((ROOT/'configs/optimization.json').read_text())
    path=tmp_path/'sweep.json';path.write_text(json.dumps(spec))
    return path


def test_paired_job_plan_and_config(tmp_path):
    config=load_sweep_config(write_config(tmp_path))
    jobs=plan_jobs(config)
    assert len(jobs)==36
    assert len({j['job_id'] for j in jobs})==36
    assert config['optimization']['steps']==24
    first=[j for j in jobs if j['kind']=='mixed' and j['sequence_seed']==1729 and j['search_seed']==2718]
    assert [j['beam_size'] for j in first]==[50,100,200]


@pytest.mark.parametrize('change',[{'lengths':[999]},{'beam_sizes':[True]},{'sequence_seeds':[1,1]},
 {'search_seeds':[]},{'kinds':['unknown']},{'optimization_overrides':{'not_a_parameter':1}},
 {'optimization_overrides':{'preserve_protein':True}}])
def test_bad_grid_rejected(tmp_path,change):
    with pytest.raises(ValueError):
        load_sweep_config(write_config(tmp_path,**change))


def test_missing_validation_excluded_not_zero():
    jobs=[dict(kind='mixed',length=1000,beam_size=100) for _ in range(3)]
    common=dict(kind='mixed',length=1000,beam_size=100)
    rows=[dict(common,status='validated',vienna_delta_kcal_mol=-10,vienna_delta_kcal_mol_per_nt=-0.01,
               input_pair_f1=0.5,finalist_pair_f1=0.6),dict(common,status='validation_failed')]
    result=aggregate_rows(rows,jobs)[0]
    assert result['planned_runs']==3 and result['completed_runs']==2
    assert result['validated_runs']==1 and result['failed_runs']==1
    assert result['mean_vienna_delta_kcal_mol_per_nt']==-0.01
    assert result['sd_vienna_delta_kcal_mol_per_nt'] is None
    assert result['improvement_fraction_validated']==1
    empty=aggregate_rows([dict(common,status='validation_failed')],jobs)[0]
    assert empty['mean_vienna_delta_kcal_mol_per_nt'] is None
    assert empty['improvement_fraction_validated'] is None


def test_failed_cell_does_not_stop_remaining_and_resume(tmp_path,monkeypatch):
    path=write_config(tmp_path,kinds=['mixed'],sequence_seeds=[1729],search_seeds=[2718],beam_sizes=[50,100],
                      optimization_overrides={'steps':2})
    calls=[]
    def fake_fold(root,seq,config,tool='LinearFold',raw_path=None):
        calls.append((tool,config['beam_size']))
        if tool=='LinearFold' and config['beam_size']==50:
            return {'status':'timeout','error':'Test-only simulated timeout'}
        return {'status':'ok','structure':'.'*len(seq),'mfe_kcal_mol':-10,'wall_seconds':0.01}
    monkeypatch.setattr('rnastable.sweep.fold_sequence',fake_fold)
    monkeypatch.setattr('rnastable.sweep.plot_tradeoffs',lambda *_:'test-only-no-plot')
    summary=run_sweep(tmp_path,path)
    assert summary['status_counts']=={'search_failed':1,'validated':1}
    assert sum(tool=='ViennaRNA' for tool,beam in calls)==1
    old_calls=len(calls)
    resumed=run_sweep(tmp_path,path,Path(summary['run_dir']))
    assert len(calls)==old_calls
    assert resumed['rows']==summary['rows']
    assert (tmp_path/'results/evaluation_sweep.csv').exists()
    assert list((tmp_path/'results/archive').glob('*/evaluation_sweep.csv'))
    modified=json.loads(path.read_text());modified['search_seeds']=[999]
    path.write_text(json.dumps(modified))
    with pytest.raises(ValueError,match='Resume rejected'):
        run_sweep(tmp_path,path,Path(summary['run_dir']))


def test_reference_failure_remains_unknown(tmp_path,monkeypatch):
    path=write_config(tmp_path,kinds=['structured'],sequence_seeds=[1729],search_seeds=[2718],beam_sizes=[100],
                      optimization_overrides={'steps':1})
    def fake_fold(root,seq,config,tool='LinearFold',raw_path=None):
        if tool=='ViennaRNA':
            return {'status':'unavailable','error':'Test-only missing tool'}
        return {'status':'ok','structure':'.'*len(seq),'mfe_kcal_mol':-10,'wall_seconds':0.01}
    monkeypatch.setattr('rnastable.sweep.fold_sequence',fake_fold)
    summary=run_sweep(tmp_path,path)
    row=summary['rows'][0]
    assert row['status']=='validation_failed'
    assert 'vienna_delta_kcal_mol' not in row
    assert summary['aggregates'][0]['validated_runs']==0


def test_resume_rejects_modified_finalist(tmp_path,monkeypatch):
    path=write_config(tmp_path,kinds=['mixed'],sequence_seeds=[1729],search_seeds=[2718],beam_sizes=[100],
                      optimization_overrides={'steps':1})
    monkeypatch.setattr('rnastable.sweep.fold_sequence',lambda root,seq,config,tool='LinearFold',raw_path=None:
                        {'status':'ok','structure':'.'*len(seq),'mfe_kcal_mol':-10,'wall_seconds':0.01})
    monkeypatch.setattr('rnastable.sweep.plot_tradeoffs',lambda *_:'test-only-no-plot')
    summary=run_sweep(tmp_path,path)
    p=Path(summary['rows'][0]['finalist_fasta']);text=p.read_text()
    # Valid alphabet/length, different content: must be rejected before any new folds.
    lines=text.splitlines();lines[1]=('A' if lines[1][0]!='A' else 'C')+lines[1][1:]
    p.write_text('\n'.join(lines)+'\n')
    with pytest.raises(ValueError,match='FASTA changed'):
        run_sweep(tmp_path,path,Path(summary['run_dir']))


def test_interrupt_kills_owned_folding_process_group(monkeypatch):
    import signal
    from rnastable.folding import run_bounded
    killed=[]
    class InterruptedProcess:
        pid=12345
        returncode=-9
        calls=0
        def wait(self,timeout=None):
            self.calls+=1
            if self.calls==1:
                raise KeyboardInterrupt
            return self.returncode
    process=InterruptedProcess()
    monkeypatch.setattr('rnastable.folding.subprocess.Popen',lambda *a,**k:process)
    monkeypatch.setattr('rnastable.folding.os.killpg',lambda pid,sig:killed.append((pid,sig)))
    with pytest.raises(KeyboardInterrupt):
        run_bounded(['test-only-process'],'ACGU')
    assert killed==[(12345,signal.SIGKILL)]
    assert process.calls==2
