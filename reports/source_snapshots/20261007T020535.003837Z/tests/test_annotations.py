import json
import random
import subprocess
from rnastable.artifacts import sha256
from rnastable.cli import ROOT
from rnastable.annotations import apply_constraints
from rnastable.optimization import load_optimization_config, propose_mutation, check_constraints
from rnastable.sequences import generate_sequence, write_fasta
import pytest


def annotation(tmp_path,sequence,**changes):
    spec={'schema_version':1,'input_sha256':sha256(sequence),
          'protected_positions':[25],'protected_regions':[{'start':1,'end':24,'label':'test-only region'}]}
    spec.update(changes)
    path=tmp_path/'constraints.json';path.write_text(json.dumps(spec));return path


def test_overlaps_merge_and_original_config_is_preserved(tmp_path):
    sequence=generate_sequence(1000,'mixed',1729)
    base=load_optimization_config(ROOT/'configs/optimization.json');base['protected_positions']=[26]
    path=annotation(tmp_path,sequence,protected_regions=[{'start':1,'end':24},{'start':20,'end':30}])
    config=apply_constraints(base,sequence,path)
    assert base['protected_positions']==[26] and config['protected_positions']==list(range(1,31))
    assert config['constraint_annotation']['protected_position_count']==30
    rng=random.Random(2718);current=sequence
    for _ in range(20):
        current=propose_mutation(current,sequence,config,rng)
        assert current[:30]==sequence[:30]
        assert check_constraints(current,sequence,config)


@pytest.mark.parametrize('change',[{'input_sha256':'wrong'},{'schema_version':True},{'unknown':1},
    {'protected_positions':[0]},{'protected_positions':[1001]},{'protected_positions':[True]},
    {'protected_regions':[{'start':10,'end':9}]},{'protected_regions':[{'start':0,'end':10}]},
    {'protected_regions':[{'start':1,'end':1001}]},{'protected_regions':[{'start':1,'end':10,'label':1}]},
    {'protected_regions':[{'start':1,'end':10,'strand':'plus'}]}])
def test_bad_coordinates_and_sequence_identity_rejected(tmp_path,change):
    sequence=generate_sequence(1000,'mixed',1729)
    with pytest.raises(ValueError):
        apply_constraints(load_optimization_config(ROOT/'configs/optimization.json'),sequence,
                          annotation(tmp_path,sequence,**change))


def test_dry_run_cli_and_mismatched_annotation(tmp_path):
    sequence=generate_sequence(1000,'mixed',1729)
    path=annotation(tmp_path,sequence)
    fasta=write_fasta(tmp_path/'input.fasta','test_only',sequence)
    args=[str(ROOT/'scripts/rnastable'),'optimize','--input',str(fasta),'--constraints',str(path),
          '--dry-run','--output-root',str(tmp_path)]
    result=subprocess.run(args,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    report=json.loads(result.stdout)
    assert report['mode']=='input_validation_no_folding'
    assert report['config']['protected_positions']==list(range(1,26))
    assert not (tmp_path/'results').exists()
    annotation(tmp_path,sequence,input_sha256='wrong')
    result=subprocess.run(args,capture_output=True,text=True)
    assert result.returncode!=0 and 'SHA256' in result.stderr
