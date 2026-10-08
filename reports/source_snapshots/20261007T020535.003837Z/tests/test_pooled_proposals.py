import pytest
from rnastable.pooled_proposals import pooled_search
from rnastable.checkpoint_prior import compatibility
from rnastable.reference import digest
from rnastable.optimization import check_constraints


def config():return {'seed':42,'steps':2,'pool_size':4,'max_mutations':4,'beam_size':100,'timeout_seconds':30,'finalist_timeout_seconds':30,'memory_limit_gib':4,'min_improvement_kcal_mol':.1,'temperature_c':37,'preserve_protein':False,'protected_positions':[]}


def test_prior_ranking_never_overrides_native_energy_and_exposure_precedes_scores():
    original='GGAAAACC';events=[]
    class Scorer:
        def __init__(self,sequence,structure):self.pairs=[(0,7),(1,6)]
        def score(self,seq):
            assert events[-1][0]=='pool'
            return {'sequence_sha256':digest(seq.encode()),'target_pairs':2,'compatible_target_pairs':len(compatibility(seq,self.pairs)),'mean_compatible_logit':100. if compatibility(seq,self.pairs) else None}
    def fold(seq,step):events.append(('fold',step));return {'status':'ok','structure':'((....))' if step==0 else '.'*8,'mfe_kcal_mol':[-10.,-9.,-11.][step]}
    def exposed(step,pool):events.append(('pool',step))
    result=pooled_search(original,config(),'checkpoint_prior',fold,Scorer,exposed)
    assert [r['accepted'] for r in result['history']]==[False,True]
    assert result['best']['mfe_kcal_mol']==-11 and result['proxy_evaluations']==8
    check_constraints(result['sequence'],original,config())
    assert [event for event in events if event[0]=='fold']==[('fold',0),('fold',1),('fold',2)]


def test_failed_folds_keep_previous_best_and_failed_baseline_stops():
    cfg=config();original='GGAAAACC'
    result=pooled_search(original,cfg,'random_pool',lambda seq,step:{'status':'ok','structure':'((....))','mfe_kcal_mol':-10.} if step==0 else {'status':'timeout'})
    assert result['sequence']==original and result['accepted_steps']==0
    result=pooled_search(original,cfg,'random_pool',lambda seq,step:{'status':'error'})
    assert result['status']=='baseline_failed' and result['history']==[]


def test_fully_protected_pool_is_empty_without_proxy_or_proposal_folds():
    cfg=config();cfg['protected_positions']=list(range(1,9));calls=[]
    def fold(seq,step):calls.append(step);return {'status':'ok','structure':'((....))','mfe_kcal_mol':-10.}
    result=pooled_search('GGAAAACC',cfg,'compatibility_only',fold)
    assert calls==[0] and result['history'][0]['status']=='no_legal_proposal'


def test_nonfinite_fold_energy_rejects():
    with pytest.raises(ValueError,match='finite'):pooled_search('GGAAAACC',config(),'random_pool',lambda seq,step:{'status':'ok','structure':'((....))','mfe_kcal_mol':float('nan')})


def test_measured_checkpoint_prior_pilot_replays(monkeypatch):
    import importlib.util
    from rnastable.cli import ROOT
    path=ROOT/'results/checkpoint_prior_pilot_summary.json'
    if not path.exists():pytest.skip('No completed checkpoint-prior pilot')
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('verify_checkpoint_prior_pilot',ROOT/'scripts/verify_checkpoint_prior_pilot.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.audit_prior(path)
