"""Label-informed development diagnostics; oracle scores are not model predictions."""
from .pair_model import CANONICAL
from .scoring import base_pairs,structure_agreement


def candidate_coverage(record,candidates,positive_reference_pairs,predicted_structure):
    truth=base_pairs(record['structure']);sequence=record['sequence']
    legal={p for p in truth if p[1]-p[0]>=4 and sequence[p[0]]+sequence[p[1]] in CANONICAL}
    positive=set(positive_reference_pairs);retained={tuple(map(int,p)) for p in candidates}
    if not positive<=legal or not (truth&retained)<=positive:raise ValueError('Invalid positive reference candidate inventory')
    predicted=base_pairs(predicted_structure)
    if not predicted<=retained:raise ValueError('Prediction includes a pair outside candidates')
    covered=truth&retained;oracle=['.']*len(sequence)
    for i,j in covered:oracle[i],oracle[j]='(',')'
    return {'reference_pairs':len(truth),'supported_reference_pairs':len(legal),'positive_reference_pairs':len(positive),'retained_reference_pairs':len(covered),'decoded_reference_pairs':len(truth&predicted),'unsupported_reference_pairs':len(truth-legal),'nonpositive_reference_pairs':len(legal-positive),'top_k_removed_reference_pairs':len(positive-covered),'decoder_omitted_reference_pairs':len(covered-predicted),'retained_reference_recall':len(covered)/len(truth) if truth else 1.0,'oracle_candidate_f1_upper_bound':structure_agreement(''.join(oracle),record['structure'])['pair_f1'],'decoded_pair_f1':structure_agreement(predicted_structure,record['structure'])['pair_f1']}
