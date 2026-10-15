"""Separate proposal-pool search core; native folding energy alone accepts mutations."""
import random
import time
from .artifacts import sha256
from .checkpoint_prior import template_pairs,choose_pool
from .optimization import check_constraints,propose_mutation,validate_optimization_config
from .scoring import mfe_per_nt


def proposal_pool(current,original,config,rng,seen):
    pool=[];unique=set()
    for _ in range(256):
        proposal=propose_mutation(current,original,config,rng)
        if proposal is None:break
        identity=sha256(proposal)
        if identity in seen or identity in unique:continue
        check_constraints(proposal,original,config);pool.append(proposal);unique.add(identity)
        if len(pool)==config['pool_size']:break
    return pool


def pooled_search(original,config,policy,evaluator,scorer_factory=None,on_pool=None):
    validate_optimization_config(config);check_constraints(original,original,config)
    if type(config.get('pool_size')) is not int or not 1<=config['pool_size']<=64 or config['steps']>32:raise ValueError('Invalid bounded pool search settings')
    if policy not in ('random_pool','compatibility_only','checkpoint_prior'):raise ValueError('Unknown pool search policy')
    rng=random.Random(config['seed']);selector=random.Random(config['seed']+1000003)
    baseline=evaluator(original,0)
    if baseline['status']!='ok':return {'status':'baseline_failed','baseline':baseline,'best':baseline,'sequence':original,'history':[],'accepted_steps':0,'proxy_evaluations':0}
    mfe_per_nt(baseline['mfe_kcal_mol'],original);pairs=template_pairs(original,baseline['structure'])
    if policy=='checkpoint_prior' and scorer_factory is None:raise ValueError('Checkpoint policy requires a scorer factory')
    scorer=scorer_factory(original,baseline['structure']) if policy=='checkpoint_prior' else None
    current=original;best=baseline;seen={sha256(original)};history=[];proxy_count=0
    for step in range(1,config['steps']+1):
        pool=proposal_pool(current,original,config,rng,seen)
        if not pool:
            history.append({'step':step,'status':'no_legal_proposal','accepted':False,'pool':[]});break
        if on_pool is not None:on_pool(step,pool)
        begin=time.monotonic();selected,rows=choose_pool(pool,policy,pairs,selector,scorer);proxy_wall=time.monotonic()-begin
        proxy_count+=len(pool) if policy=='checkpoint_prior' else 0
        proposal=pool[selected];result=evaluator(proposal,step);seen.add(sha256(proposal));accepted=False
        if result['status']=='ok':
            mfe_per_nt(result['mfe_kcal_mol'],proposal)
            if result['mfe_kcal_mol']<=best['mfe_kcal_mol']-config['min_improvement_kcal_mol']+1e-9:current,best,accepted=proposal,result,True
        history.append({'step':step,'pool':pool,'pool_scores':rows,'selected_index':selected,'proposal_sha256':sha256(proposal),'fold':result,'status':result['status'],'accepted':accepted,'best_energy_kcal_mol':best['mfe_kcal_mol'],'proxy_wall_seconds':proxy_wall})
    check_constraints(current,original,config)
    return {'status':'completed','baseline':baseline,'best':best,'sequence':current,'history':history,'accepted_steps':sum(r['accepted'] for r in history),'proxy_evaluations':proxy_count,'target_structure':baseline['structure'],'target_pairs':len(pairs),**({'scorer_binding':scorer.binding} if scorer is not None and hasattr(scorer,'binding') else {})}
