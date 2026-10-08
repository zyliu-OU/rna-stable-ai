import pytest
from pathlib import Path
import zipfile
from rnastable.crw_development_data import load_crw_development,select_crw,overlaps
from rnastable.experimental_data import sequence_similarity


def fixture_archive(root):
    rows=[('train','train_datasets/S-Processed-TRA.fasta','CRW_00001','GGAAAACC','AJ0001'),('holdout','holdout_datasets/S-Processed-VAL.fasta','CRW_00002','CCCCGGGG','AJ0002')]
    with zipfile.ZipFile(root/'input_data.zip','w') as archive:
        for split,name,identity,seq,accession in rows:
            path=root/'datasets_in_fasta_form'/name;path.parent.mkdir(parents=True)
            path.write_text(f'>SSTRAND_ID={identity}; TYPE=Group I Intron; EXT_SOURCE=Gutell Lab CRW; EXT_ID={accession}; ORGANISM=fixture\n{seq}\n')
            archive.writestr(f'input_data/StructureData/{split}/{identity}.bpseq',''.join(f'{i+1} {c} 0\n' for i,c in enumerate(seq)))
        archive.writestr('input_data/StructureData/test/CRW_99999.bpseq','This must never be imported')


def test_source_binding_and_development_only_import(tmp_path):
    fixture_archive(tmp_path);config={'min_length':1,'max_length':1024,'train_cap':1,'validation_cap':1}
    candidates,source=load_crw_development(tmp_path,config)
    assert source['candidate_counts']=={'train':1,'validation':1} and source['test_sources_read'] is False
    assert not (tmp_path/'datasets_in_fasta_form/test_datasets').exists()
    record=candidates['train'][0]
    assert record['reference_kind']=='computational' and 'family_id' not in record
    selected,_=select_crw(candidates,config,[])
    assert len(selected['train'])==len(selected['validation'])==1
    path=tmp_path/'datasets_in_fasta_form/train_datasets/S-Processed-TRA.fasta';path.write_text(path.read_text().replace('GGAAAACC','GGAAAACU'))
    candidates,source=load_crw_development(tmp_path,config)
    assert not candidates['train'] and any('No exact' in r['reason'] for r in source['import_exclusions'])


def test_accession_collision_and_prior_exposure_fail_closed(tmp_path):
    fixture_archive(tmp_path);config={'min_length':1,'max_length':1024,'train_cap':1,'validation_cap':1}
    candidates,_=load_crw_development(tmp_path,config)
    with pytest.raises(ValueError,match='validation'):select_crw(candidates,config,[{'sequence':'CCCCGGGG'}])
    candidates['train'][0]['external_accessions']=['aj0002']
    with pytest.raises(ValueError,match='train'):select_crw(candidates,config,[])


@pytest.mark.parametrize('first,second',[('A'*10,'A'*100),('ACGUACGU','ACGUACGA'),('GAAAAC','CCCCGGGG'),('GCGCGC','GCGCGC')])
def test_length_upper_bound_preserves_fixed_overlap_decision(first,second):
    assert overlaps(first,second)==(sequence_similarity(first,second)>=.8)


def test_full_supervision_includes_distant_contacts_without_projection():
    from rnastable.full_pair_supervision import full_supervision
    seq='G'+'A'*298+'C';record={'sequence':seq,'structure':'('+'.'*298+')'}
    indices,labels,excluded=full_supervision(record)
    assert excluded==0 and labels.sum()==1 and indices[labels.bool()].tolist()==[[0,299]]
    with pytest.raises(ValueError,match='bounded'):full_supervision(record,256)


def test_measured_expanded_training_replays(monkeypatch):
    import importlib.util
    from rnastable.cli import ROOT
    path=ROOT/'results/long_comparative_development_summary.json'
    if not path.exists():pytest.skip('No completed expanded comparative development')
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('verify_long_comparative_development',ROOT/'scripts/verify_long_comparative_development.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.audit_expanded(path)
