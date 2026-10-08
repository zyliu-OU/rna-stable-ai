import zipfile
import pytest
from rnastable.long_training_data import import_long_training


def test_empty_fixed_long_range_is_preserved_as_availability_evidence(tmp_path):
    fasta=tmp_path/'datasets_in_fasta_form/train_datasets/S-Processed-TRA.fasta';fasta.parent.mkdir(parents=True);fasta.write_text('> SSTRAND_ID=CRW_00001; EXT_SOURCE=Gutell Lab CRW; EXT_ID=ABC; TYPE=rRNA; ORGANISM=fixture;\nGGAAAACC\n')
    with zipfile.ZipFile(tmp_path/'input_data.zip','w') as archive:
        archive.writestr('input_data/StructureData/train/CRW_00001.bpseq','1 G 8\n2 G 7\n3 A 0\n4 A 0\n5 A 0\n6 A 0\n7 C 2\n8 C 1\n')
        archive.writestr('input_data/StructureData/test/CRW_99999.bpseq','INVALID TEST LABELS MUST NEVER BE PARSED')
        archive.writestr('input_data/StructureData/holdout/CRW_99998.bpseq','INVALID HOLDOUT LABELS MUST NEVER BE PARSED')
    records,metadata=import_long_training(tmp_path,{'train':[],'validation':[]})
    assert records==[] and metadata['availability']=='no_records_in_fixed_plan'
    assert metadata['training_member_count']==1 and metadata['maximum_raw_training_length']==8
    assert metadata['minimum']==1025 and metadata['maximum']==4096
    assert metadata['test_sources_read'] is False and metadata['holdout_sources_read'] is False
    assert metadata['exclusions']==[{'id':'input_data_StructureData_train_CRW_00001','reason':'outside_long_training_range'}]


def test_long_training_plan_does_not_silently_lower_length_range(tmp_path):
    with pytest.raises(ValueError,match='range'):import_long_training(tmp_path,{},minimum=256)
