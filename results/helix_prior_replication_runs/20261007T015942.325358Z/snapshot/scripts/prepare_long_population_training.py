#!/usr/bin/env python3
"""Freeze a bounded longer training-only annotation cohort for sampled supervision."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.artifacts import timestamp,publish
from rnastable.exposures import record_exposure
from rnastable.long_training_data import import_long_training
from rnastable.native_journal import atomic_json
from rnastable.population_sampling import PairPopulation
from rnastable.reference import digest
from train_sampled_comparative_development import frozen_inputs


def main():
    source_bytes,source,snapshots,splits=frozen_inputs(ROOT/'results/exact_comparative_development_summary.json')
    records,imported=import_long_training(ROOT/'external/EternaFold',splits)
    run=ROOT/'results/long_population_training_data_runs'/timestamp();run.mkdir(parents=True)
    atomic_json(run/'extra_training.json',{'schema_version':1,'dataset_id':'longer_crw_training_only','records':records});atomic_json(run/'import.json',imported);(run/'source_summary.json').write_bytes(source_bytes)
    event=record_exposure(run,'training_started',records) if records else None;rows=[]
    for record in records:
        population=PairPopulation(record)
        rows.append({'id':record['id'],'length':len(record['sequence']),'rna_type':record['rna_type'],'population_positive':population.positive_count,'population_negative':population.negative_count,'excluded_contacts':population.excluded})
    manifest={'run_dir':str(run),'source_summary_sha256':digest(source_bytes),'import_sha256':digest((run/'import.json').read_bytes()),'extra_training_sha256':digest((run/'extra_training.json').read_bytes()),'exposure_event':event,'policy':imported['policy']};atomic_json(run/'manifest.json',manifest)
    summary={'complete':True,'run_dir':str(run),'manifest_sha256':digest((run/'manifest.json').read_bytes()),'holdout_sources_read':False,'test_sources_read':False,'model_fitted':False,'availability':imported['availability'],'maximum_raw_crw_training_length':imported['maximum_raw_training_length'],'training_crw_member_count':imported['training_member_count'],'rows':rows,'extra_training':str(run/'extra_training.json'),
             'limitations':['Additional upstream training annotations only; the existing validation cohort remains unchanged.','Processed comparative annotations are not new experimental measurements.','Sequence/accession separation does not establish family/clan independence or generalization.']};atomic_json(run/'summary.json',summary)
    report=['# Longer training-only comparative annotation cohort','',imported['policy'],'','| ID | Length | RNA type | Positive legal pairs | Full negative population |','|---|---:|---|---:|---:|']
    for row in rows:report.append(f"| {row['id']} | {row['length']} | {row['rna_type']} | {row['population_positive']} | {row['population_negative']} |")
    report+=['',f"Availability: {imported['availability']}. Inspected {imported['training_member_count']} CRW training members; maximum raw annotation length {imported['maximum_raw_training_length']}nt. Fixed requested range {imported['minimum']}–{imported['maximum']}nt. No fit or new validation labels.",'',*summary['limitations']];publish(ROOT,'long_population_training_data',summary,rows,['id','length','rna_type','population_positive','population_negative','excluded_contacts'],'\n'.join(report)+'\n');print(json.dumps(summary,indent=2));return summary

if __name__=='__main__':main()
