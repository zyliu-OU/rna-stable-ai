import json
from pathlib import Path
import numpy as np
import pytest
from rnastable.pair_penalty import penalize_candidates,validate_pair_penalty
from rnastable.exact_sparse_pairs import decode_exact_sparse
from rnastable.context_inference import infer_fasta,audit_inference
from rnastable.cli import ROOT
from rnastable.reference import digest


def test_penalty_reduces_scores_filters_nonpositive_and_reports_both_array_scopes():
    candidates={'pairs':np.array([[0,7],[1,6]],dtype=np.int32),'scores':np.array([2.,.5]),'candidate_count':2,'candidate_array_bytes':32}
    assert penalize_candidates(candidates,0) is candidates
    adjusted=penalize_candidates(candidates,1)
    assert adjusted['pairs'].tolist()==[[0,7]] and adjusted['scores'].tolist()==[1.]
    assert adjusted['candidate_count']==2 and adjusted['candidate_array_bytes']==32
    assert adjusted['retained_after_penalty']==1 and adjusted['penalty_candidate_array_bytes']==16
    assert candidates['scores'].tolist()==[2.,.5]
    result=decode_exact_sparse('GGAAAACC',adjusted['pairs'],adjusted['scores']);assert result['structure']=='(......)' and result['objective']==1


@pytest.mark.parametrize('value',[-1,9,True,float('nan'),float('inf'),'1'])
def test_invalid_penalty_rejects(value):
    with pytest.raises(ValueError):validate_pair_penalty(value)


def test_penalized_inference_freezes_and_replays_parameter_with_exports(tmp_path):
    source=ROOT/'results/helix_comparative_development_summary.json'
    if not source.exists():pytest.skip('No local-helix checkpoint')
    path=tmp_path/'input.fasta';path.write_text('>fixture\nGGGAAACCC\n')
    summary=infer_fasta(tmp_path,source,path,pair_penalty=1);run=Path(summary['run_dir']);audit_inference(run/'summary.json')
    assert summary['candidate_pair_penalty']==1 and summary['accuracy_evaluated'] is False
    row=json.loads((run/'predictions.json').read_text())[0];assert row['candidate_pair_penalty']==1 and row['retained_after_penalty']<=row['candidate_count']
    manifest=json.loads((run/'manifest.json').read_text());manifest['candidate_pair_penalty']=2;(run/'manifest.json').write_text(json.dumps(manifest));summary['manifest_sha256']=digest((run/'manifest.json').read_bytes());(run/'summary.json').write_text(json.dumps(summary))
    with pytest.raises(ValueError,match='penalty identity'):audit_inference(run/'summary.json')


def test_penalty_context_checkpoint_or_invalid_number_rejects_before_output(tmp_path):
    source=ROOT/'results/context_development_summary.json';path=tmp_path/'input.fasta';path.write_text('>fixture\nGGGAAACCC\n')
    if source.exists():
        with pytest.raises(ValueError,match='global sparse'):infer_fasta(tmp_path,source,path,pair_penalty=1)
    with pytest.raises(ValueError):infer_fasta(tmp_path,tmp_path/'missing.json',path,pair_penalty=-1)
    assert not (tmp_path/'results').exists()
