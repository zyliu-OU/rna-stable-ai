import json
from pathlib import Path
import pytest
from rnastable.native_journal import atomic_json
from rnastable.pooled_native import PooledNativeRunner,native_runtime
from rnastable.pooled_proposals import pooled_search
from rnastable.reference import digest
from test_pooled_proposals import config


def plan(tmp_path):
    run=tmp_path/'run';run.mkdir();checkpoint=tmp_path/'checkpoint';checkpoint.write_bytes(b'model')
    source=run/'source.json';source.write_bytes(b'source')
    code=tmp_path/'runner.py';code.write_bytes(b'code')
    cfg=config()
    manifest={'policy':'Synthetic test plan','run_dir':str(run),'config':cfg,'checkpoint':str(checkpoint),'checkpoint_sha256':digest(checkpoint.read_bytes()),'snapshot_sha256':{'source.json':digest(source.read_bytes())},'code_sha256':{str(code):digest(code.read_bytes())},'native_runtime':native_runtime(tmp_path,cfg)}
    atomic_json(run/'manifest.json',manifest)
    return run,cfg,manifest


def fold(root,seq,cfg,tool,path):
    path.parent.mkdir(exist_ok=True);path.write_text(seq)
    return {'status':'ok','tool':tool,'structure':'((....))','mfe_kcal_mol':-10.,'wall_seconds':0.25,'raw_output':str(path)}


def stable(result):
    return {**result,'history':[{k:v for k,v in row.items() if k!='proxy_wall_seconds'} for row in result['history']]}


def test_pooled_trajectory_resume_reuses_native_requests_and_cost(tmp_path):
    run,cfg,manifest=plan(tmp_path);calls=[]
    def native(*args):calls.append(args[1]);return fold(*args)
    first=PooledNativeRunner(tmp_path,run,cfg,manifest,native)
    search=pooled_search('GGAAAACC',cfg,'random_pool',lambda seq,step:first.run_request('random_pool',seq,'proposal' if step else 'baseline',step))
    reopened=PooledNativeRunner(tmp_path,run,cfg,manifest,lambda *args:pytest.fail('Native replay'))
    replay=pooled_search('GGAAAACC',cfg,'random_pool',lambda seq,step:reopened.run_request('random_pool',seq,'proposal' if step else 'baseline',step))
    assert stable(search)==stable(replay) and len(calls)==3
    assert reopened.accounting()=={'unique_requests':3,'completed_requests':3,'unknown_requests':0,'known_native_wall_seconds':0.75,'current_invocation_callbacks':0,'current_invocation_cache_hits':3,'total_cost_known':True}


def test_interrupted_proposal_is_unknown_without_retry_and_search_continues(tmp_path):
    run,cfg,manifest=plan(tmp_path);calls=[]
    def native(*args):
        calls.append(args[1])
        if len(calls)==2:raise KeyboardInterrupt
        return fold(*args)
    runner=PooledNativeRunner(tmp_path,run,cfg,manifest,native)
    with pytest.raises(KeyboardInterrupt):pooled_search('GGAAAACC',cfg,'random_pool',lambda seq,step:runner.run_request('random_pool',seq,'proposal' if step else 'baseline',step))
    reopened=PooledNativeRunner(tmp_path,run,cfg,manifest,native)
    result=pooled_search('GGAAAACC',cfg,'random_pool',lambda seq,step:reopened.run_request('random_pool',seq,'proposal' if step else 'baseline',step))
    assert result['history'][0]['fold']['interrupted'] and not result['history'][0]['accepted']
    assert len(calls)==3 and reopened.accounting()['unknown_requests']==1
    assert reopened.accounting()['known_native_wall_seconds']==0.5 and reopened.accounting()['total_cost_known'] is False


@pytest.mark.parametrize('asset',['source','checkpoint','code','config','runtime'])
def test_source_checkpoint_code_config_runtime_bindings_fail_before_native(tmp_path,asset):
    run,cfg,manifest=plan(tmp_path)
    if asset=='source':(run/'source.json').write_bytes(b'changed')
    if asset=='checkpoint':Path(manifest['checkpoint']).write_bytes(b'changed')
    if asset=='code':Path(next(iter(manifest['code_sha256']))).write_bytes(b'changed')
    if asset=='config':cfg={**cfg,'seed':cfg['seed']+1}
    if asset=='runtime':manifest['native_runtime']={}
    with pytest.raises(ValueError,match='binding'):PooledNativeRunner(tmp_path,run,cfg,manifest,lambda *args:pytest.fail('Native invoked'))


def test_manifest_rebinding_and_changed_raw_output_cannot_reuse_request(tmp_path):
    run,cfg,manifest=plan(tmp_path);runner=PooledNativeRunner(tmp_path,run,cfg,manifest,fold)
    result=runner.run_request('random_pool','GGAAAACC','baseline',0)
    rebound={**manifest,'purpose':'changed'}
    with pytest.raises(ValueError,match='binding'):PooledNativeRunner(tmp_path,run,cfg,rebound,fold).run_request('random_pool','GGAAAACC','baseline',0)
    Path(result['raw_output']).write_text('changed')
    with pytest.raises(ValueError,match='raw output'):runner.run_request('random_pool','GGAAAACC','baseline',0)


def test_pilot_driver_resume_preserves_exposures_and_counts_proxy_replay(tmp_path,monkeypatch):
    import importlib.util
    from rnastable.checkpoint_prior import compatibility
    root=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('pilot_driver',root/'scripts/run_checkpoint_prior_pilot.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,'ROOT',tmp_path)
    run,cfg,manifest=plan(tmp_path);calls=[]
    class Scorer:
        binding={'test':'bound'}
        def __init__(self,*args):pass
        def score(self,seq):
            contacts=len(compatibility(seq,[(0,7),(1,6)]))
            return {'sequence_sha256':digest(seq.encode()),'target_pairs':2,'compatible_target_pairs':contacts,'mean_compatible_logit':1. if contacts else None}
    monkeypatch.setattr(module,'TargetScorer',Scorer)
    def native(*args):
        calls.append(str(args[-1]))
        if args[-1].parent.name=='checkpoint_prior' and args[-1].name.startswith('proposal_0001'):
            raise KeyboardInterrupt
        return fold(*args)
    original='GGAAAACC';record={'id':'synthetic_test','sequence':original}
    runner=PooledNativeRunner(tmp_path,run,cfg,manifest,native)
    with pytest.raises(KeyboardInterrupt):module.execute(run,cfg,manifest,record,original,runner,'test_prior')
    exposures={p.name:p.read_bytes() for p in (run/'exposures').glob('*.json')}
    runner=PooledNativeRunner(tmp_path,run,cfg,manifest,fold)
    summary=module.execute(run,cfg,manifest,record,original,runner,'test_prior')
    assert all((run/'exposures'/name).read_bytes()==data for name,data in exposures.items())
    assert set(p.resolve() for p in (run/'exposures').glob('*.json'))=={Path(e['event']['path']).resolve() for e in summary['exposure_events']}
    assert summary['cost_accounting']['native']['unique_requests']==15
    assert summary['cost_accounting']['native']['unknown_requests']==1
    assert summary['cost_accounting']['completed_proxy_calls_across_attempts']==12
    assert summary['cost_accounting']['incomplete_attempts']==1
    assert summary['equal_native_proposal_budget_measured']
    assert len(calls)==12 and runner.journal.callbacks_invoked==3
    assert summary['rows'][2]['successful_proposal_folds']==1
