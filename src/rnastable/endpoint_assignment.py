"""Sampled endpoint partner classification with an explicit zero-score null option."""

from .pair_model import CANONICAL
from .pair_reference import validate_pairs
from .sequences import validate_sequence


def assignment_targets(record, indices):
    import torch

    sequence = validate_sequence(record["sequence"])
    n = len(sequence)
    if not 1 <= n < 3000:
        raise ValueError("Endpoint assignment requires length 1-2999 nt")
    if indices.ndim != 2 or indices.shape[1] != 2 or indices.dtype != torch.long:
        raise ValueError("Expected integer pair indices")
    lookup = {}
    for offset, (left, right) in enumerate(indices.tolist()):
        if (not 0 <= left < right < n or right - left < 4
                or sequence[left] + sequence[right] not in CANONICAL or (left, right) in lookup):
            raise ValueError("Invalid or duplicated assignment candidate")
        lookup[left, right] = offset
    gold = validate_pairs(record["pairs"], n)
    target = torch.full((n,), -1, dtype=torch.long, device=indices.device)
    known = torch.ones(n, dtype=torch.bool, device=indices.device)
    for left, right in gold:
        if right - left < 4 or sequence[left] + sequence[right] not in CANONICAL:
            known[left] = known[right] = False
        else:
            if (left, right) not in lookup:
                raise ValueError("Legal gold target is missing from sampled candidates")
            target[left] = target[right] = lookup[left, right]
    return target, known


def endpoint_assignment_loss(logits, indices, targets, known):
    import torch

    n = len(targets)
    if (not 1 <= n < 3000 or logits.ndim != 1 or indices.shape != (len(logits), 2)
            or targets.shape != (n,) or known.shape != (n,) or indices.dtype != torch.long
            or targets.dtype != torch.long or known.dtype != torch.bool
            or any(t.device != logits.device for t in (indices, targets, known))):
        raise ValueError("Expected aligned bounded endpoint-assignment tensors")
    if (not bool(torch.isfinite(logits).all()) or bool((targets < -1).any())
            or bool((targets >= len(logits)).any())
            or (len(indices) and (int(indices.min()) < 0 or int(indices.max()) >= n
                                 or bool((indices[:, 1] - indices[:, 0] < 4).any())))):
        raise ValueError("Invalid assignment scores or coordinates")
    paired = targets >= 0
    nodes = torch.arange(n, device=logits.device)[paired]
    if len(nodes) and not bool((indices[targets[paired]] == nodes[:, None]).any(dim=1).all()):
        raise ValueError("Assignment target does not contain its endpoint")
    counts = {"known_nodes": int(known.sum()), "paired_nodes": int((known & paired).sum()),
              "null_nodes": int((known & ~paired).sum()), "unknown_nodes": int((~known).sum())}
    if not counts["known_nodes"]:
        return logits.sum() * 0, counts
    endpoints = indices.reshape(-1)
    repeated = logits.repeat_interleave(2)
    # Detached maxima stabilize log-sum-exp; the null class always has score zero.
    maximum = torch.zeros(n, dtype=logits.dtype, device=logits.device)
    maximum = maximum.scatter_reduce(0, endpoints, repeated, reduce="amax", include_self=True).detach()
    sums = torch.exp(-maximum).scatter_add(0, endpoints, torch.exp(repeated - maximum[endpoints]))
    log_partition = maximum + torch.log(sums)
    target_scores = torch.zeros(n, dtype=logits.dtype, device=logits.device)
    target_scores = target_scores.scatter(0, nodes, logits[targets[paired]])
    return (log_partition - target_scores)[known].mean(), counts
