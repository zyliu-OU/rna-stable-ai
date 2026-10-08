import random
import pytest
from rnastable.checkpoint_prior import template_pairs,compatibility,choose_pool,TargetScorer
from rnastable.reference import digest
from rnastable.cli import ROOT


def test_native_template_coordinates_and_compatibility_are_explicit():
    pairs=template_pairs('GGAAAACC','((....))');assert pairs==[(1,6),(0,7)]
    assert compatibility('GAAAAACC',pairs)==[(0,7)]
    with pytest.raises(ValueError,match='canonical'):template_pairs('AAAAAAAA','((....))')
    with pytest.raises(ValueError,match='length'):template_pairs('GGAAAACC','.')


def test_checkpoint_ranking_keeps_compatibility_primary_and_stable_ties():
    pairs=template_pairs('GGAAAACC','((....))');pool=['GGAAAACC','GGAACCAA','GAAAAACC']
    class Scorer:
        def score(self,seq):
            return {'sequence_sha256':digest(seq.encode()),'compatible_target_pairs':len(compatibility(seq,pairs)),'target_pairs':len(pairs),'mean_compatible_logit':{'GGAAAACC':0.,'GGAACCAA':None,'GAAAAACC':100.}[seq]}
    assert choose_pool(pool,'checkpoint_prior',pairs,random.Random(1),Scorer())[0]==0
    assert choose_pool(pool,'compatibility_only',pairs,random.Random(1))[0]==0
    with pytest.raises(ValueError,match='unique'):choose_pool(pool+[pool[0]],'random_pool',pairs,random.Random(1))


def test_logits_break_contact_ties_without_native_acceptance():
    pairs=template_pairs('GGAAAACC','((....))');pool=['GGAAAACC','CCAAAAGG']
    class Scorer:
        def score(self,seq):return {'sequence_sha256':digest(seq.encode()),'compatible_target_pairs':2,'target_pairs':2,'mean_compatible_logit':float(seq[0]=='C')}
    assert choose_pool(pool,'checkpoint_prior',pairs,random.Random(1),Scorer())[0]==1
    assert choose_pool(pool,'compatibility_only',pairs,random.Random(1))[0]==0


def test_real_checkpoint_scores_template_without_inference_decoder_length_limit():
    source=ROOT/'results/stack_comparative_development_summary.json'
    if not source.exists():pytest.skip('No completed stack checkpoint')
    sequence='G'+'A'*1098+'C';structure='('+'.'*1098+')';scorer=TargetScorer(source,sequence,structure)
    row=scorer.score(sequence);assert row['compatible_target_pairs']==1 and row['mean_compatible_logit'] is not None
    assert scorer.score('A'*1100)['mean_compatible_logit'] is None
    assert scorer.binding['target_pairs']==1
    with pytest.raises(ValueError):scorer.score('GAAAC')
