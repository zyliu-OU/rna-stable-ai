#!/usr/bin/env python3
"""Measure synthetic helix-head scoring with explicitly substituted approximate decoders."""
import argparse
import json
from pathlib import Path
import resource
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp
from rnastable.context_inference import load_checkpoint
from rnastable.exposures import record_exposure,read_exposure,exposure_records
from rnastable.global_sparse_pairs import sparse_candidates,decode_sparse
from rnastable.sparse_refinement import refine_sparse
from rnastable.reference import digest
from rnastable.reference_audit import require

REFINEMENT={'passes':2,'max_remove':2,'group_cap':8,'include_subsets':True}


def planned_inputs():
    rng=np.random.default_rng(20261006)
    return [{'id':'synthetic_'+str(n),'sequence':''.join(rng.choice(list('ACGU'),n))} for n in (1000,5000,10000)]


def audit_scalability(path):
    summary=json.loads(Path(path).read_text());run=Path(summary['run_dir']);require(summary['complete'] is True and summary['accuracy_evaluated'] is False and summary['test_evaluated'] is False and summary==json.loads((run/'summary.json').read_text()),'Resource study identity differs')
    for name,key in [('manifest.json','manifest_sha256'),('predictions.json','predictions_sha256')]:require(digest((run/name).read_bytes())==summary[key],'Resource artifact changed')
    manifest=json.loads((run/'manifest.json').read_text());require(manifest['run_dir']==str(run) and manifest['refinement']==REFINEMENT,'Resource manifest identity differs')
    source_bytes,config,checkpoint,model=load_checkpoint(run/'source_summary.json');require(digest(source_bytes)==manifest['source_summary_sha256'] and config==manifest['config'] and str(checkpoint)==manifest['checkpoint'] and digest(checkpoint.read_bytes())==manifest['checkpoint_sha256'],'Resource checkpoint differs')
    require(digest((run/'inputs.json').read_bytes())==manifest['inputs_sha256'],'Synthetic inputs changed');records=planned_inputs();require(records==json.loads((run/'inputs.json').read_text()),'Synthetic plan differs')
    rows=json.loads((run/'predictions.json').read_text());require(len(rows)==len(records),'Resource row inventory differs')
    for record,row in zip(records,rows):
        require(row['id']==record['id'] and row['length']==len(record['sequence']),'Resource sequence binding differs');p=Path(row['candidate_path']);require(p.resolve().parent==run.resolve() and digest(p.read_bytes())==row['candidate_sha256'],'Candidate file changed')
        candidates=sparse_candidates(model,record['sequence'],config['top_k'],config['block_size'])
        with np.load(p,allow_pickle=False) as saved:require(set(saved.files)=={'pairs','scores'} and np.array_equal(saved['pairs'],candidates['pairs']) and np.array_equal(saved['scores'],candidates['scores']),'Checkpoint candidate replay differs')
        for key,value in candidates.items():
            if key not in ('pairs','scores','interpretation'):require(row[key]==value,'Resource candidate statistics differ')
        require(candidates['candidate_count']<=len(record['sequence'])*config['top_k'] and candidates['peak_score_tile_elements']<=len(record['sequence'])*config['block_size'] and candidates['pair_context_feature_tile_elements']==8*candidates['peak_score_tile_elements'],'Tile/candidate bounds differ')
        for name,result in [('greedy',decode_sparse(record['sequence'],candidates['pairs'],candidates['scores'])),('refined',refine_sparse(record['sequence'],candidates['pairs'],candidates['scores'],**REFINEMENT))]:require(row[name]==result,'Approximate resource decoder replay differs')
        require(row['refined']['objective']+1e-8>=row['greedy']['objective'],'Refinement decreases objective')
        for key in ('scoring_wall_seconds','greedy_wall_seconds','refinement_wall_seconds'):require(type(row[key]) in (int,float) and np.isfinite(row[key]) and row[key]>=0,'Invalid resource timing')
    require([{k:v for k,v in row.items() if k not in ('greedy','refined')} for row in rows]==summary['rows'],'Resource summary differs')
    event=summary['exposure_event'];p=Path(event['path']);require(p.resolve().parent==(run/'exposures').resolve() and list((run/'exposures').glob('*.json'))==[p] and digest(p.read_bytes())==event['sha256'],'Resource exposure changed');data=read_exposure(p);require(data['stage']==event['stage']=='validation_started' and data['records']==exposure_records(records,str(run)+' validation_started'),'Resource exposure binding differs')
    print('Helix resource audit passed:3 exact synthetic candidate inventories and substituted greedy/refinement structures; no labels or accuracy evaluation.')
    return summary


def main():
    source_bytes,config,checkpoint,model=load_checkpoint(ROOT/'results/helix_comparative_development_summary.json');require(config.get('pair_features')=='local_helix_context_v1','Expected measured local-helix checkpoint')
    records=planned_inputs();run=ROOT/'results/helix_scalability_runs'/timestamp();run.mkdir(parents=True,exist_ok=False);(run/'source_summary.json').write_bytes(source_bytes);(run/'inputs.json').write_text(json.dumps(records,indent=2)+'\n')
    manifest={'run_dir':str(run),'config':config,'refinement':REFINEMENT,'source_summary_sha256':digest(source_bytes),'checkpoint':str(checkpoint),'checkpoint_sha256':digest(checkpoint.read_bytes()),'inputs_sha256':digest((run/'inputs.json').read_bytes()),'code_sha256':{str(p):digest(p.read_bytes()) for p in (Path(__file__),*[ROOT/'src/rnastable'/n for n in ('helix_pairs.py','global_sparse_pairs.py','sparse_refinement.py','context_inference.py')])},'policy':'Unlabelled synthetic resource benchmark, not checkpoint accuracy. Explicitly substitute approximate greedy/refinement decoding for the source exact decoder; never silently change FASTA behavior.'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');event=record_exposure(run,'validation_started',records);rows=[]
    for record in records:
        print('Helix resource scoring: '+record['id'],flush=True);begin=time.monotonic();c=sparse_candidates(model,record['sequence'],config['top_k'],config['block_size']);scoring=time.monotonic()-begin
        begin=time.monotonic();greedy=decode_sparse(record['sequence'],c['pairs'],c['scores']);greedy_time=time.monotonic()-begin
        begin=time.monotonic();refined=refine_sparse(record['sequence'],c['pairs'],c['scores'],**REFINEMENT);refinement_time=time.monotonic()-begin
        p=run/(record['id']+'_candidates.npz');np.savez_compressed(p,pairs=c['pairs'],scores=c['scores']);row={'id':record['id'],'length':len(record['sequence']),'greedy':greedy,'refined':refined,**{k:v for k,v in c.items() if k not in ('pairs','scores','interpretation')},'scoring_wall_seconds':scoring,'greedy_wall_seconds':greedy_time,'refinement_wall_seconds':refinement_time,'candidate_path':str(p),'candidate_sha256':digest(p.read_bytes())};rows.append(row);print(json.dumps({k:v for k,v in row.items() if k not in ('greedy','refined')}),flush=True)
    (run/'predictions.json').write_text(json.dumps(rows,indent=2)+'\n');summary={'complete':True,'run_dir':str(run),'test_evaluated':False,'accuracy_evaluated':False,'purpose':'synthetic_helix_head_resource_benchmark_with_substituted_approximate_decoders','manifest_sha256':digest((run/'manifest.json').read_bytes()),'predictions_sha256':digest((run/'predictions.json').read_bytes()),'exposure_event':event,'rows':[{k:v for k,v in r.items() if k not in ('greedy','refined')} for r in rows],'process_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limitations':['Quadratic all-distance scoring; sorting adds work, bounded tile/candidate storage.','Feature tile elements/retained arrays exclude other transient tensors; cumulative process RSS includesTorch.','One observation per length; decoder substitution for synthetic resource use only.','No speedup, long labelled accuracy, independent generalization or stability claim.']};(run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(ROOT/'results/helix_scalability_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    if args.verify:audit_scalability(ROOT/'results/helix_scalability_summary.json')
    else:main()
