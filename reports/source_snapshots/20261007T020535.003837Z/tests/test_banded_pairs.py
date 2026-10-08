import numpy as np
import pytest
from rnastable.banded_pairs import band_scores, decode_band
from rnastable.pair_model import decode_pairs, make_pair_model, CANONICAL
from rnastable.scoring import base_pairs
from rnastable.structure_model import tokens


def convert(sequence, dense, width):
    width = min(width, len(sequence)-1)
    band = np.zeros((len(sequence), width+1))
    for j in range(len(sequence)):
        for d in range(4, min(width, j)+1):
            if sequence[j-d]+sequence[j] in CANONICAL: band[j, d] = dense[j-d, j]
    return band


@pytest.mark.parametrize('span', [4, 5, 8, 255])
def test_exact_banded_optimum_matches_full_dynamic_program(span):
    rng = np.random.default_rng(13)
    for _ in range(10):
        seq = ''.join(rng.choice(list('ACGU'), 20)); dense = rng.normal(size=(20, 20)); dense = (dense+dense.T)/2
        masked = dense.copy()
        for i in range(20):
            for j in range(20):
                if abs(i-j) > span: masked[i, j] = 0
        band = convert(seq, dense, span); result = decode_band(seq, band, span)
        assert result['structure'] == decode_pairs(seq, masked)
        assert result['objective'] == pytest.approx(sum(dense[i, j] for i, j in base_pairs(result['structure'])))


def test_long_sequence_stays_in_band_and_storage_is_linear():
    n = 1000; span = 4; seq = 'GAAAC'*200; band = np.zeros((n, span+1))
    for j in range(4, n, 5): band[j, 4] = 1
    result = decode_band(seq, band, span)
    assert result['structure'] == '(...)'*200
    assert result['objective'] == 200
    assert result['dp_array_bytes'] == n*((span+1)*12+12)
    assert result['score_array_bytes'] == n*(span+1)*8


def test_chunked_head_matches_dense_model_scores():
    import torch
    torch.manual_seed(77); torch.set_num_threads(2)
    model = make_pair_model({'embedding_dim': 8, 'channels': 8, 'pair_dim': 8}).eval()
    seq = 'ACGU'*12
    with torch.inference_mode(): dense = model(tokens(seq))[0].numpy()
    assert np.allclose(band_scores(model, seq, 20), convert(seq, dense, 20), atol=1e-6, rtol=1e-6)
    assert band_scores(model, 'ACGU'*100, 20).shape == (400, 21)


@pytest.mark.parametrize('span', [0, 3, 256, True, 4.5])
def test_invalid_span_rejected(span):
    with pytest.raises(ValueError): decode_band('GAAAC', np.zeros((5, 5)), span)


def test_invalid_and_illegal_scores_rejected():
    for band in (np.ones((5, 5)), np.zeros((4, 5)), np.full((5, 5), np.nan)):
        with pytest.raises(ValueError): decode_band('GAAAC', band, 4)
    assert decode_band('A', np.zeros((1, 1)), 4)['structure'] == '.'


def test_sparse_context_logits_match_banded_scoring_and_backpropagate():
    import torch
    from rnastable.context_pairs import make_context_model,band_supervision
    torch.manual_seed(3)
    model=make_context_model({'embedding_dim':8,'channels':8,'pair_dim':8,'dilations':[1,2,4,8],'max_pair_span':16})
    seq='ACGU'*15;indices,labels,excluded=band_supervision({'sequence':seq,'structure':'.'*len(seq)},16)
    logits=model(tokens(seq),indices)
    band=band_scores(model,seq,16)
    assert np.allclose(logits.detach().numpy(),band[indices[:,1],indices[:,1]-indices[:,0]],atol=1e-6,rtol=1e-6)
    logits.square().mean().backward()
    assert model.encoder[0].weight.grad.abs().sum()>0
    assert not labels.any() and excluded==0


def test_sparse_supervision_counts_contacts_outside_span():
    from rnastable.context_pairs import band_supervision
    indices,labels,excluded=band_supervision({'sequence':'GAAAAC','structure':'(....)'},4)
    assert len(labels)==0 and excluded==1


def test_context_rejects_invalid_sparse_pair_indices():
    import torch
    from rnastable.context_pairs import make_context_model
    model=make_context_model({'embedding_dim':8,'channels':8,'pair_dim':8,'dilations':[1,2],'max_pair_span':4})
    for edges in (torch.tensor([[0,3]]),torch.tensor([[0,5]]),torch.tensor([[-1,4]]),torch.tensor([[0,6]])):
        with pytest.raises(ValueError):model(tokens('GAAAAC'),edges)


def test_context_sparse_supervision_recovers_wide_development_contact():
    from rnastable.context_pairs import band_supervision
    record={'sequence':'G'+'A'*98+'C','structure':'('+'.'*98+')'}
    assert band_supervision(record,64)[2]==1
    edges,labels,excluded=band_supervision(record,128)
    assert excluded==0 and labels.sum()==1 and edges[labels.bool()].tolist()==[[0,99]]


def test_measured_context_comparison_replays(monkeypatch):
    import importlib.util
    from rnastable.cli import ROOT
    path=ROOT/'results/context_development_comparison_summary.json'
    if not path.exists():pytest.skip('No measured context comparison')
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('verify_context_comparison',ROOT/'scripts/verify_context_comparison.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.audit_comparison(path)


def test_reusable_context_trainer_fits_development_only(tmp_path):
    from rnastable.context_training import train_context,predictions
    config={'embedding_dim':8,'channels':8,'pair_dim':8,'dilations':[1,2,4,8],'max_pair_span':8,'positive_weight_exponent':1.,'epochs':1,'cpu_threads':2,'seed':11,'learning_rate':.001}
    train=[{'id':'train','sequence':'GGAAAACC','structure':'((....))'}]
    val=[{'id':'val','sequence':'GGGAAACC','structure':'((....))'}]
    initial,model,training=train_context(train,val,config,tmp_path)
    assert training['selected_epoch']==1 and len(training['history'])==1
    assert training['train_positive_pairs']>0 and training['train_negative_pairs']>0
    assert training['train_only_positive_weight']==training['train_negative_pairs']/training['train_positive_pairs']
    assert len(predictions(model,val,'context',8))==1
    assert not list(tmp_path.glob('*test*'))
    with pytest.raises(ValueError):train_context([],val,config,tmp_path)


def test_measured_context_family_trial_replays():
    import importlib.util
    from rnastable.cli import ROOT
    path=ROOT/'results/context_family_trial_summary.json'
    if not path.exists():pytest.skip('No completed context family trial')
    spec=importlib.util.spec_from_file_location('verify_context_family_trial',ROOT/'scripts/verify_context_family_trial.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.audit_context_trial(path)
