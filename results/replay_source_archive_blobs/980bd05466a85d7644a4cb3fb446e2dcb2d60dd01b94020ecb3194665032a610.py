"""Sequence-only contiguous local helix compatibility features for global pair logits."""

from .global_sparse_pairs import make_global_model

FEATURE_NAMES = (
    "outer_1",
    "inner_1",
    "outer_2",
    "inner_2",
    "outer_3",
    "inner_3",
    "gc_pair",
    "gu_pair",
)


def helix_features(codes, left, right):
    import torch

    if (
        codes.ndim != 1
        or codes.dtype != torch.long
        or not 1 <= len(codes) <= 10000
        or left.dtype != torch.long
        or right.dtype != torch.long
    ):
        raise ValueError("Expected bounded sequence codes and integer pair indices")
    if bool((codes < 0).any()) or bool((codes > 3).any()):
        raise ValueError("Invalid nucleotide codes")
    n = len(codes)
    if (left.numel() and (bool((left < 0).any()) or bool((left >= n).any()))) or (
        right.numel() and (bool((right < 0).any()) or bool((right >= n).any()))
    ):
        raise ValueError("Pair indices outside sequence")
    left, right = torch.broadcast_tensors(left, right)
    canonical = torch.tensor(
        [
            [False, False, False, True],
            [False, False, True, False],
            [False, True, False, True],
            [True, False, True, False],
        ],
        device=codes.device,
    )
    outer = torch.ones_like(left, dtype=torch.bool)
    inner = torch.ones_like(left, dtype=torch.bool)
    features = []
    for offset in (1, 2, 3):
        outer = (
            outer
            & (left >= offset)
            & (right + offset < n)
            & (right - left + 2 * offset >= 4)
            & canonical[
                codes[(left - offset).clamp(0, n - 1)],
                codes[(right + offset).clamp(0, n - 1)],
            ]
        )
        inner = (
            inner
            & (left + offset < n)
            & (right >= offset)
            & (right - left - 2 * offset >= 4)
            & canonical[
                codes[(left + offset).clamp(0, n - 1)],
                codes[(right - offset).clamp(0, n - 1)],
            ]
        )
        features.extend((outer, inner))
    a, b = codes[left], codes[right]
    features.extend(
        (
            ((a == 1) & (b == 2)) | ((a == 2) & (b == 1)),
            ((a == 2) & (b == 3)) | ((a == 3) & (b == 2)),
        )
    )
    return torch.stack(features, dim=-1).to(torch.float32)


def make_helix_model(config):
    import torch

    if config.get("pair_features") != "local_helix_context_v1":
        raise ValueError("Expected fixed local-helix configuration")

    class HelixModel(torch.nn.Module):
        pair_context_feature_count = len(FEATURE_NAMES)

        def __init__(self):
            super().__init__()
            self.base = make_global_model(config)
            self.helix_weights = torch.nn.Linear(len(FEATURE_NAMES), 1, bias=False)
            torch.nn.init.zeros_(self.helix_weights.weight)

        def encode(self, tokens):
            return self.base.encode(tokens)

        def distance_logits(self, distance):
            return self.base.distance_logits(distance)

        def pair_context_logits(self, codes, left, right):
            return self.helix_weights(helix_features(codes, left, right)).squeeze(-1)

        def forward(self, tokens, indices):
            return self.base(tokens, indices) + self.pair_context_logits(
                tokens[0], indices[:, 0], indices[:, 1]
            )

    return HelixModel()
