import json
from pathlib import Path
import pytest
from rnastable.cli import ROOT
from rnastable.context_inference import infer_fasta,audit_inference
from rnastable.exposures import collect_known_exposures


@pytest.mark.parametrize('text',['>duplicate\nAAAA\n>duplicate\nCCCC\n','>too_long\n'+'A'*10001+'\n'])
def test_invalid_inputs_reject_before_run_or_exposure(tmp_path,text):
    path=tmp_path/'input.fasta';path.write_text(text)
    with pytest.raises(ValueError):infer_fasta(tmp_path,tmp_path/'missing_source.json',path)
    assert not (tmp_path/'results').exists()


def test_real_checkpoint_inference_freezes_input_and_detects_corruption(tmp_path):
    source=ROOT/'results/context_development_summary.json'
    if not source.exists():pytest.skip('No completed context development checkpoint')
    path=tmp_path/'input.fasta';path.write_text('>fixture\nGGGAAACCC\n')
    summary=infer_fasta(tmp_path,source,path);run=Path(summary['run_dir'])
    path.write_text('>fixture\nAAAAAAAAA\n')
    audit_inference(run/'summary.json')
    assert summary['accuracy_evaluated'] is False
    assert collect_known_exposures(tmp_path)[0]['sequence']=='GGGAAACCC'
    predictions=json.loads((run/'predictions.json').read_text());predictions[0]['structure']='.'*9
    (run/'predictions.json').write_text(json.dumps(predictions))
    with pytest.raises(ValueError,match='artifact changed'):audit_inference(run/'summary.json')


def test_prediction_export_matches_supplied_reference_protocol(tmp_path):
    from rnastable.reference import validate_inputs
    source=ROOT/'results/context_development_summary.json'
    if not source.exists():pytest.skip('No context checkpoint')
    path=tmp_path/'input.fasta';path.write_text('>fixture\nGAAAC\n')
    summary=infer_fasta(tmp_path,source,path);run=Path(summary['run_dir'])
    exported=json.loads((run/'reference_predictions.json').read_text())
    references={'schema_version':1,'dataset_id':'protocol_fixture','records':[{'id':'fixture','sequence':'GAAAC','structure':'(...)','reference_kind':'computational','source':'synthetic protocol fixture'}]}
    validate_inputs(references,exported)
    audit_inference(run/'summary.json')
    assert summary['accuracy_evaluated'] is False


@pytest.mark.parametrize('filename,method',[('global_sparse_development_summary.json','trained_global_sparse'),('long_comparative_development_summary.json','trained_expanded_sparse'),('structured_comparative_development_summary.json','trained_structured_sparse'),('stack_comparative_development_summary.json','trained_stack_sparse'),('helix_comparative_development_summary.json','trained_helix_sparse')])
def test_global_checkpoint_fasta_inference_is_not_span_limited(tmp_path,filename,method):
    source=ROOT/'results'/filename
    if not source.exists():pytest.skip('No completed sparse checkpoint')
    sequence='G'+'A'*298+'C';path=tmp_path/'input.fasta';path.write_text('>synthetic_global\n'+sequence+'\n')
    summary=infer_fasta(tmp_path,source,path);run=Path(summary['run_dir']);audit_inference(run/'summary.json')
    exported=json.loads((run/'reference_predictions.json').read_text());row=json.loads((run/'predictions.json').read_text())[0]
    assert exported['methods']==[method] and row['sequence']==sequence
    assert 'max_pair_span' not in row and row['peak_score_tile_elements']<=300*64
    assert summary['accuracy_evaluated'] is False


@pytest.mark.parametrize('filename,method',[('long_comparative_development_summary.json','trained_expanded_sparse_exact_sparse'),('sampled_comparative_development_summary.json','trained_sampled_sparse_exact_sparse')])
def test_exact_sparse_inference_freezes_decoder_and_replays_exports(tmp_path,filename,method):
    source=ROOT/'results'/filename
    if not source.exists():pytest.skip('No completed expanded sparse checkpoint')
    path=tmp_path/'input.fasta';path.write_text('>exact_fixture\nGGGAAACCC\n')
    summary=infer_fasta(tmp_path,source,path,'exact_sparse');run=Path(summary['run_dir']);audit_inference(run/'summary.json')
    assert summary['decoder_override']=='exact_sparse'
    assert json.loads((run/'reference_predictions.json').read_text())['methods']==[method]
    assert json.loads((run/'predictions.json').read_text())[0]['dp_array_bytes']==12*9**2
    from rnastable.reference import digest
    manifest=json.loads((run/'manifest.json').read_text());manifest['decoder_override']='source';(run/'manifest.json').write_text(json.dumps(manifest))
    summary['manifest_sha256']=digest((run/'manifest.json').read_bytes());(run/'summary.json').write_text(json.dumps(summary))
    with pytest.raises(ValueError,match='Decoder identity'):audit_inference(run/'summary.json')


@pytest.mark.parametrize('filename,sequence',[('context_development_summary.json','GGGAAACCC'),('long_comparative_development_summary.json','A'*1025)])
def test_exact_sparse_bound_and_checkpoint_type_reject_before_output(tmp_path,filename,sequence):
    source=ROOT/'results'/filename
    if not source.exists():pytest.skip('No completed source checkpoint')
    path=tmp_path/'input.fasta';path.write_text('>rejected\n'+sequence+'\n')
    with pytest.raises(ValueError):infer_fasta(tmp_path,source,path,'exact_sparse')
    assert not (tmp_path/'results').exists()


def test_frozen_exact_checkpoint_uses_selection_decoder_by_default(tmp_path):
    source=ROOT/'results/exact_comparative_development_summary.json'
    if not source.exists():pytest.skip('No completed exact-selection checkpoint')
    path=tmp_path/'input.fasta';path.write_text('>frozen_exact\nGGGAAACCC\n')
    summary=infer_fasta(tmp_path,source,path);run=Path(summary['run_dir']);audit_inference(run/'summary.json')
    assert json.loads((run/'reference_predictions.json').read_text())['methods']==['trained_exact_sparse']
    assert 'dp_array_bytes' in json.loads((run/'predictions.json').read_text())[0]
    path.write_text('>too_long\n'+'A'*1025+'\n');other=tmp_path/'rejected'
    with pytest.raises(ValueError,match='1024'):infer_fasta(other,source,path)
    assert not (other/'results').exists()


@pytest.mark.parametrize('decoder',['greedy','refined'])
def test_explicit_approximate_override_allows_long_global_input_and_freezes_method(tmp_path,decoder):
    source=ROOT/'results/stack_comparative_development_summary.json'
    if not source.exists():pytest.skip('No completed stack checkpoint')
    sequence=('GGGAAACCC'*123)[:1100];path=tmp_path/'input.fasta';path.write_text('>long_override\n'+sequence+'\n')
    summary=infer_fasta(tmp_path,source,path,decoder);run=Path(summary['run_dir']);audit_inference(run/'summary.json')
    assert summary['decoder_override']==decoder and summary['accuracy_evaluated'] is False
    exported=json.loads((run/'reference_predictions.json').read_text())
    assert exported['methods']==['trained_stack_sparse_'+decoder] and len(exported['records'][0]['structure'])==1100
    assert 'dp_array_bytes' not in json.loads((run/'predictions.json').read_text())[0]
    if decoder=='refined':
        assert summary['decoder_settings']['include_subsets'] is True
        from rnastable.reference import digest
        manifest=json.loads((run/'manifest.json').read_text());manifest['decoder_settings']['passes']=1;summary['decoder_settings']['passes']=1;(run/'manifest.json').write_text(json.dumps(manifest));summary['manifest_sha256']=digest((run/'manifest.json').read_bytes());(run/'summary.json').write_text(json.dumps(summary))
        with pytest.raises(ValueError,match='settings differ'):audit_inference(run/'summary.json')


@pytest.mark.parametrize('decoder',['greedy','refined'])
def test_approximate_override_rejects_context_checkpoint_before_output(tmp_path,decoder):
    source=ROOT/'results/context_development_summary.json'
    if not source.exists():pytest.skip('No completed context checkpoint')
    path=tmp_path/'input.fasta';path.write_text('>invalid_override\nGGGAAACCC\n')
    with pytest.raises(ValueError,match='global sparse'):infer_fasta(tmp_path,source,path,decoder)
    assert not (tmp_path/'results').exists()


def test_measured_long_override_replays_and_matches_resource_decoder():
    path=ROOT/'results/stack_long_inference_summary.json';resource=ROOT/'results/stack_scalability_summary.json'
    if not path.exists() or not resource.exists():pytest.skip('No measured long stack override')
    summary=audit_inference(path);row=json.loads((Path(summary['run_dir'])/'predictions.json').read_text())[0];benchmark=json.loads(resource.read_text());raw=json.loads((Path(benchmark['run_dir'])/'predictions.json').read_text())[-1]
    assert len(row['sequence'])==10000 and summary['decoder_override']=='refined'
    assert row['structure']==raw['refined']['structure'] and row['objective']==raw['refined']['objective']
    assert json.loads((Path(summary['run_dir'])/'reference_predictions.json').read_text())['methods']==['trained_stack_sparse_refined']
