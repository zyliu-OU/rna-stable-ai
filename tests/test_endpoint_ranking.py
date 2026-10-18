"""Ranking loss must penalize actual endpoint competitors and preserve gradients."""

import pytest
import torch

from rnastable.endpoint_ranking import endpoint_ranking_loss


def test_hardest_shared_endpoint_competitor_receives_gradient():
    logits = torch.tensor([0.0, 2.0, -1.0, 100.0], requires_grad=True)
    edges = torch.tensor([[0, 7], [0, 6], [1, 7], [2, 8]])
    labels = torch.tensor([1.0, 0.0, 0.0, 0.0])
    loss, info = endpoint_ranking_loss(logits, edges, labels, 9)
    assert loss.item() == pytest.approx(torch.nn.functional.softplus(torch.tensor(3.0)).item())
    assert info == {"positive_pairs": 1, "ranked_pairs": 1}
    loss.backward()
    assert logits.grad[0] < 0 and logits.grad[1] > 0
    assert logits.grad[2] == logits.grad[3] == 0


def test_negative_using_gold_right_endpoint_as_its_left_is_a_competitor():
    logits = torch.tensor([0.0, 2.0], requires_grad=True)
    loss, info = endpoint_ranking_loss(logits, torch.tensor([[0, 4], [4, 8]]), torch.tensor([1.0, 0.0]), 9)
    assert info["ranked_pairs"] == 1
    loss.backward()
    assert logits.grad[1] > 0


@pytest.mark.parametrize("labels", [[1.0, 1.0], [0.0, 0.0]])
def test_single_class_has_differentiable_zero_loss(labels):
    logits = torch.tensor([0.0, 1.0], requires_grad=True)
    loss, info = endpoint_ranking_loss(logits, torch.tensor([[0, 7], [1, 6]]), torch.tensor(labels), 8)
    assert loss.item() == 0 and info["ranked_pairs"] == 0
    loss.backward()
    assert torch.equal(logits.grad, torch.zeros(2))


def test_unrelated_negative_does_not_create_a_comparison():
    logits = torch.tensor([0.0, 99.0], requires_grad=True)
    loss, info = endpoint_ranking_loss(logits, torch.tensor([[0, 4], [1, 5]]), torch.tensor([1.0, 0.0]), 6)
    assert loss.item() == 0 and info["ranked_pairs"] == 0


def test_rejects_deferred_length_nonfinite_scores_and_bad_labels():
    args = (torch.tensor([0.0]), torch.tensor([[0, 4]]), torch.tensor([1.0]))
    with pytest.raises(ValueError, match="1-2999"):
        endpoint_ranking_loss(*args, 3000)
    with pytest.raises(ValueError, match="Invalid"):
        endpoint_ranking_loss(torch.tensor([float('nan')]), args[1], args[2], 5)
    with pytest.raises(ValueError, match="Invalid"):
        endpoint_ranking_loss(args[0], args[1], torch.tensor([0.5]), 5)
