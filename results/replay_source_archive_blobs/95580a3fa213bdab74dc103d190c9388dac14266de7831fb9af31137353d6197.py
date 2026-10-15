"""Exact noncrossing decoding with a fixed maximum pair span and O(n*span) storage."""
import math
import numpy as np
from .pair_model import CANONICAL
from .sequences import validate_sequence


def validate_band(sequence, max_span):
    validate_sequence(sequence)
    if type(max_span) is not int or not 4 <= max_span <= 255:
        raise ValueError('Maximum pair span must be an integer in 4..255')
    return min(max_span, len(sequence)-1)


def band_scores(model, sequence, max_span=64):
    """Use the existing pair head without allocating a full sequence-square tensor.

    Distance embeddings restrict span to 255. Encoder sees the entire sequence;
    candidate pairs outside the band are omitted, not estimated or window-stitched.
    """
    import torch
    from .structure_model import tokens
    width = validate_band(sequence, max_span)
    model.eval()
    with torch.inference_mode():
        h = model.encoder(model.embedding(tokens(sequence)).transpose(1, 2)).transpose(1, 2)[0]
        projected = model.projection(h); endpoints = model.endpoint(h).squeeze(-1)
        output = np.zeros((len(sequence), width+1), dtype=np.float64)
        for distance in range(4, width+1):
            logits = (projected[:-distance]*projected[distance:]).sum(-1)/math.sqrt(projected.shape[-1])
            logits = logits+endpoints[:-distance]+endpoints[distance:]+model.distance.weight[distance, 0]
            values = logits.cpu().numpy()
            eligible = np.fromiter((sequence[i]+sequence[i+distance] in CANONICAL for i in range(len(sequence)-distance)), dtype=bool)
            output[distance:, distance] = np.where(eligible, values, 0.)
    return output


def decode_band(sequence, scores, max_span=64):
    """Exact maximum positive score for noncrossing pairs with j-i <= max_span.

    Banded interval tables solve interiors of possible outer pairs. A separate
    prefix table combines complete structures of any length. This is O(n*w^2)
    work and O(n*w) storage for fixed span w, not unrestricted global decoding.
    Ties leave sites unpaired, then choose the smallest partner.
    """
    width = validate_band(sequence, max_span); n = len(sequence)
    scores = np.asarray(scores, dtype=float)
    if scores.shape != (n, width+1) or not np.isfinite(scores).all():
        raise ValueError('Expected finite right-endpoint by pair-span scores')
    for j in range(n):
        for distance in range(width+1):
            if (distance < 4 or distance > j or sequence[j-distance]+sequence[j] not in CANONICAL) and scores[j, distance] != 0:
                raise ValueError('Illegal or padded band score must be zero')
    table = np.zeros((n, width+1), dtype=float)
    choice = np.full((n, width+1), -1, dtype=np.int32)
    prefix = np.zeros(n, dtype=float); prefix_choice = np.full(n, -1, dtype=np.int32)
    for j in range(n):
        for span in range(1, min(width, j)+1):
            i = j-span
            best = table[j-1, span-1]
            partners = np.arange(i, j-3)
            if len(partners):
                values = scores[j, j-partners]+table[j-1, j-partners-2]
                left = partners > i
                values[left] += table[partners[left]-1, partners[left]-i-1]
                values[scores[j, j-partners] <= 0] = -np.inf
                winner = int(np.argmax(values))
                if values[winner] > best:
                    best = values[winner]; choice[j, span] = partners[winner]
            table[j, span] = best
        best = prefix[j-1] if j else 0.
        partners = np.arange(max(0, j-width), j-3)
        if len(partners):
            values = scores[j, j-partners]+table[j-1, j-partners-2]
            left = partners > 0
            values[left] += prefix[partners[left]-1]
            values[scores[j, j-partners] <= 0] = -np.inf
            winner = int(np.argmax(values))
            if values[winner] > best:
                best = values[winner]; prefix_choice[j] = partners[winner]
        prefix[j] = best
    structure = ['.']*n; interiors = []; j = n-1
    while j >= 0:
        k = int(prefix_choice[j])
        if k >= 0:
            structure[k], structure[j] = '(', ')'; interiors.append((k+1, j-1)); j = k-1
        else: j -= 1
    while interiors:
        i, j = interiors.pop()
        if i >= j: continue
        k = int(choice[j, j-i])
        if k >= 0:
            structure[k], structure[j] = '(', ')'; interiors.extend([(i, k-1), (k+1, j-1)])
        else: interiors.append((i, j-1))
    return {'structure': ''.join(structure), 'objective': float(prefix[-1]),
            'max_pair_span': max_span, 'effective_band_width': width,
            'dp_array_bytes': table.nbytes+choice.nbytes+prefix.nbytes+prefix_choice.nbytes,
            'score_array_bytes': scores.nbytes,
            'interpretation': 'Exact within fixed maximum pair span; contacts outside band excluded. Scores are logits, not energy.'}
