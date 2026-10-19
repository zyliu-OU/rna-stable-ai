import copy
import pytest

pytest.importorskip("botorch")
from rnastable.discrete_bo import run_toy, select_next


def test_budget_feasibility_resume_and_determinism():
    import torch
    torch.set_num_threads(1)
    checkpoints = []
    run = run_toy(seed=7, budget=5, checkpoint=lambda s: checkpoints.append(copy.deepcopy(s)))
    replay = run_toy(seed=7, budget=5, state=checkpoints[3])
    assert replay == run
    assert len(set(x["index"] for x in run["history"])) == 5
    assert all(run["protocol"]["feasible"][x["index"]] for x in run["history"])
    corrupt = copy.deepcopy(checkpoints[3])
    corrupt["history"][0]["value"] += 1
    with pytest.raises(ValueError, match="Cached objective"):
        run_toy(seed=7, budget=5, state=corrupt)
    with pytest.raises(ValueError, match="protocol"):
        run_toy(seed=1729, budget=5, state=checkpoints[3])


def test_representation_collision_and_nonfinite_observations_rejected():
    with pytest.raises(ValueError, match="Unique"):
        select_next([[0],[0],[1]], {0:1,2:2}, [True]*3, 7)
    with pytest.raises(ValueError, match="Invalid"):
        select_next([[0],[0.5],[1]], {0:1,2:float("nan")}, [True]*3, 7)
    with pytest.raises(ValueError, match="unevaluated"):
        select_next([[0],[1]], {0:1,1:2}, [True]*2, 7)
