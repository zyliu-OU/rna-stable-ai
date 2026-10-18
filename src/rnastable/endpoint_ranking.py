"""Bounded ranking loss against sampled competitors at a gold pair's endpoints."""


def endpoint_ranking_loss(logits, indices, labels, length, margin=1.0):
    import math
    import torch
    import torch.nn.functional as functional

    if type(length) is not int or not 1 <= length < 3000:
        raise ValueError("Ranking supervision requires length 1-2999 nt")
    if isinstance(margin, bool) or not isinstance(margin, (int, float)) or not math.isfinite(margin) or margin < 0:
        raise ValueError("Ranking margin must be finite and nonnegative")
    if (logits.ndim != 1 or indices.shape != (len(logits), 2)
            or labels.shape != logits.shape or indices.dtype != torch.long
            or indices.device != logits.device or labels.device != logits.device):
        raise ValueError("Expected aligned logits, integer pair indices and binary labels")
    if (not bool(torch.isfinite(logits).all()) or not bool(((labels == 0) | (labels == 1)).all())
            or (len(indices) and (int(indices.min()) < 0 or int(indices.max()) >= length
                                 or bool((indices[:, 1] - indices[:, 0] < 4).any())))):
        raise ValueError("Invalid scores, labels or legal pair coordinates")
    positive = labels == 1
    negative = labels == 0
    if not bool(positive.any()) or not bool(negative.any()):
        return logits.sum() * 0, {"positive_pairs": int(positive.sum()), "ranked_pairs": 0}
    worst = torch.full((length,), -torch.inf, dtype=logits.dtype, device=logits.device)
    worst = worst.scatter_reduce(0, indices[negative].reshape(-1),
                                 logits[negative].repeat_interleave(2), reduce="amax", include_self=True)
    partners = indices[positive]
    competitor = torch.maximum(worst[partners[:, 0]], worst[partners[:, 1]])
    covered = torch.isfinite(competitor)
    count = int(covered.sum())
    if not count:
        return logits.sum() * 0, {"positive_pairs": int(positive.sum()), "ranked_pairs": 0}
    loss = functional.softplus(margin + competitor[covered] - logits[positive][covered]).mean()
    return loss, {"positive_pairs": int(positive.sum()), "ranked_pairs": count}
