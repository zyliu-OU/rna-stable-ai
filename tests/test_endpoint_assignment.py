"""Categorical endpoint targets must preserve null and unsupported-node semantics."""

import math
import pytest
import torch

from rnastable.endpoint_assignment import assignment_targets, endpoint_assignment_loss


def test_partner_competition_and_null_option_match_explicit_softmax():
    record = {"sequence": "GAAACC", "pairs": [[0, 4]]}
    edges = torch.tensor([[0, 4], [0, 5]])
    targets, known = assignment_targets(record, edges)
    logits = torch.tensor([0.0, 0.0], requires_grad=True)
    loss, counts = endpoint_assignment_loss(logits, edges, targets, known)
    assert loss.item() == pytest.approx((math.log(3) + 2 * math.log(2)) / 6)
    assert counts == {"known_nodes": 6, "paired_nodes": 2, "null_nodes": 4, "unknown_nodes": 0}
    loss.backward()
    assert logits.grad[0] < 0 and logits.grad[1] > 0


def test_unsupported_gold_endpoints_are_unknown_not_unpaired_targets():
    record = {"sequence": "GAAACC", "pairs": [[0, 4], [1, 2]]}
    edges = torch.tensor([[0, 4], [0, 5]])
    targets, known = assignment_targets(record, edges)
    assert known.tolist() == [True, False, False, True, True, True]
    loss, counts = endpoint_assignment_loss(torch.zeros(2), edges, targets, known)
    assert counts["unknown_nodes"] == 2 and counts["null_nodes"] == 2
    assert loss.item() == pytest.approx((math.log(3) + 2 * math.log(2)) / 4)


def test_stable_extreme_logits_match_explicit_endpoint_losses():
    record = {"sequence": "GAAACC", "pairs": [[0, 4]]}
    edges = torch.tensor([[0, 4], [0, 5]])
    targets, known = assignment_targets(record, edges)
    logits = torch.tensor([1000.0, -1000.0], requires_grad=True)
    loss, _ = endpoint_assignment_loss(logits, edges, targets, known)
    assert torch.isfinite(loss) and loss.item() == pytest.approx(0)
    loss.backward()
    assert torch.isfinite(logits.grad).all()


def test_no_candidates_and_no_known_nodes_have_explicit_zero_loss():
    edges = torch.empty((0, 2), dtype=torch.long)
    logits = torch.empty(0, requires_grad=True)
    target, known = assignment_targets({"sequence": "AAAA", "pairs": []}, edges)
    loss, counts = endpoint_assignment_loss(logits, edges, target, known)
    assert loss.item() == 0 and counts["null_nodes"] == 4
    loss.backward()
    loss, counts = endpoint_assignment_loss(torch.empty(0, requires_grad=True), edges, target, torch.zeros(4, dtype=torch.bool))
    assert loss.item() == 0 and counts["known_nodes"] == 0


def test_missing_legal_target_scope_and_mismatched_endpoint_rejected():
    with pytest.raises(ValueError, match="missing"):
        assignment_targets({"sequence": "GAAACC", "pairs": [[0, 4]]}, torch.tensor([[0, 5]]))
    with pytest.raises(ValueError, match="1-2999"):
        assignment_targets({"sequence": "A" * 3000, "pairs": []}, torch.empty((0, 2), dtype=torch.long))
    with pytest.raises(ValueError, match="does not contain"):
        endpoint_assignment_loss(torch.zeros(1), torch.tensor([[0, 4]]), torch.tensor([-1, 0, -1, -1, -1]), torch.ones(5, dtype=torch.bool))
