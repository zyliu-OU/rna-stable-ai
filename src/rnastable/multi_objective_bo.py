"""Finite-pool deterministic multi-objective BoTorch mechanics, toy only.

The single-objective counterpart is `discrete_bo.py`. This exists because the
project's two score sides are incommensurable and no composite is permitted, so
the optimizer is asked for a **Pareto front** rather than a maximum. Dominance
compares objectives coordinate-wise, which needs neither a shared unit nor a
weight, so the formulation respects `score_record_schema_v1`'s prohibition
instead of working around it.

Scope, deliberately narrow and matching `discrete_bo.py`:

- Objectives are toy mathematical functions over a finite pool. **No RNA
  sequence is designed, scored or proposed here.** Expression candidate design
  is disabled by the Stage 2 gate and nothing in this module opens it.
- Both objective models are independent single-output GPs over the same pool. No
  correlation between the two sides is assumed, because none is established.
- The reference point is **required** rather than inferred. Hypervolume is only
  comparable across runs that share a reference, and an inferred one changes
  with the observations, which would make the diagnostic drift silently.
"""
import math
import random

from .pareto import hypervolume_2d, non_dominated_indices


def select_next_pareto(features, observed, feasible, seed, reference_point):
    """One qLogNEHVI step over a finite pool, maximizing both objectives.

    `observed` maps a pool index to a sequence of objective values, all already
    oriented so that larger is better. Validation mirrors `discrete_bo.select_next`
    so the two paths fail the same way on the same bad input.
    """
    import torch
    from botorch.acquisition.multi_objective import qLogNoisyExpectedHypervolumeImprovement
    from botorch.fit import fit_gpytorch_mll
    from botorch.models import SingleTaskGP
    from botorch.models.model_list_gp_regression import ModelListGP
    from botorch.models.transforms.outcome import Standardize
    from botorch.optim import optimize_acqf_discrete
    from gpytorch.mlls import SumMarginalLogLikelihood

    if len(features) != len(feasible) or len(observed) < 2:
        raise ValueError("Pool/feasibility mismatch or insufficient initial observations")
    x = torch.tensor(features, dtype=torch.double)
    if x.ndim != 2 or x.shape[1] < 1 or not torch.isfinite(x).all() or (x < 0).any() or (x > 1).any():
        raise ValueError("Finite features scaled to [0,1] required")
    if len({tuple(row) for row in features}) != len(features):
        raise ValueError("Unique pool representations required")
    objectives = len(reference_point)
    if objectives != 2:
        raise ValueError("Exactly two objectives are supported")
    if any(type(i) is not int or not 0 <= i < len(features) or not feasible[i]
           or len(values) != objectives or not all(math.isfinite(v) for v in values)
           for i, values in observed.items()):
        raise ValueError("Invalid or infeasible observation")
    available = [i for i, ok in enumerate(feasible) if ok and i not in observed]
    if not available:
        raise ValueError("No unevaluated feasible candidates")
    # Preserve the caller's RNG state; deterministic CPU fitting.
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        train_ids = sorted(observed)
        train_x = x[train_ids]
        y = torch.tensor([list(observed[i]) for i in train_ids], dtype=torch.double)
        # One independent GP per objective. A multi-output model would impose a
        # correlation between the stability and translation sides that nothing
        # in this project establishes.
        models = [
            SingleTaskGP(train_x, y[:, k: k + 1],
                         train_Yvar=torch.full((len(train_ids), 1), 1e-6, dtype=torch.double),
                         outcome_transform=Standardize(m=1))
            for k in range(objectives)
        ]
        model = ModelListGP(*models)
        mll = SumMarginalLogLikelihood(model.likelihood, model)
        fit_gpytorch_mll(mll, optimizer_kwargs={"options": {"maxiter": 50}})
        acquisition = qLogNoisyExpectedHypervolumeImprovement(
            model=model, ref_point=list(reference_point), X_baseline=train_x, prune_baseline=True)
        candidate, value = optimize_acqf_discrete(
            acquisition, q=1, choices=x[available], unique=True)
        matches = torch.all(x[available] == candidate[0], dim=1).nonzero().flatten()
        if len(matches) != 1:
            raise RuntimeError("Acquisition returned an unknown/ambiguous pool member")
        index = available[matches.item()]
    return index, float(value.item())


def toy_objectives(value):
    """Two conflicting toy objectives over one variable, both maximized.

    They conflict on purpose: the first peaks near 0.73 and the second falls
    monotonically, so no single point maximizes both and the front has more than
    one member. A pair of objectives that agreed would make the mechanics pass
    without ever exercising a trade-off.
    """
    first = 1 - (value - 0.73) ** 2 + 0.04 * math.sin(19 * value)
    second = 1 - value ** 1.5
    return (first, second)


def run_toy_pareto(seed=7, budget=8, state=None, checkpoint=None, reference_point=(0.0, 0.0)):
    """Resume cached evaluations; finite mathematical pool, never RNA."""
    features = [[i / 30] for i in range(31)]
    feasible = [not 0.40 <= row[0] <= 0.60 for row in features]
    protocol = {"seed": seed, "budget": budget, "features": features, "feasible": feasible,
                "initial_indices": [0, 10, 30], "objectives": "toy_conflicting_pair_v1",
                "objective_directions": ["maximize", "maximize"],
                "acquisition": "qLogNoisyExpectedHypervolumeImprovement",
                "gp": "ModelListGP_of_independent_SingleTaskGP",
                "reference_point": list(reference_point),
                "noise_variance": 1e-6, "fit_maxiter": 50,
                "composite_score_emitted": False,
                "meaning": "optimizer_mechanics_only_no_RNA_or_biological_validation"}
    if type(budget) is not int or not 3 <= budget <= sum(feasible):
        raise ValueError("Invalid unique evaluation budget")
    if state is not None and state["protocol"] != protocol:
        raise ValueError("Resume protocol mismatch")
    history = list(state["history"]) if state is not None else []
    observed = {}
    for step, row in enumerate(history):
        i = row["index"]
        if type(i) is not int or not 0 <= i < len(features) or i in observed or not feasible[i]:
            raise ValueError("Corrupt or duplicate cached evaluation")
        if tuple(row["values"]) != toy_objectives(features[i][0]):
            raise ValueError("Cached objective mismatch")
        if step < 3 and i != protocol["initial_indices"][step]:
            raise ValueError("Cached initial design mismatch")
        observed[i] = tuple(row["values"])
    if len(history) > budget:
        raise ValueError("Cached history exceeds budget")
    for step in range(len(history), budget):
        if step < 3:
            i, acquisition = protocol["initial_indices"][step], None
        else:
            i, acquisition = select_next_pareto(features, observed, feasible, seed, reference_point)
        observed[i] = toy_objectives(features[i][0])
        history.append({"index": i, "values": list(observed[i]), "log_acquisition": acquisition})
        if checkpoint is not None:
            checkpoint({"protocol": protocol, "history": list(history)})

    evaluated = sorted(observed)
    rows = [observed[i] for i in evaluated]
    front = [evaluated[k] for k in non_dominated_indices(rows)]
    rng = random.Random(seed)
    pool = [i for i, ok in enumerate(feasible) if ok and i not in protocol["initial_indices"]]
    random_ids = protocol["initial_indices"] + rng.sample(pool, budget - 3)
    random_rows = [toy_objectives(features[i][0]) for i in random_ids]
    return {
        "protocol": protocol,
        "history": history,
        "unique_evaluations": len(observed),
        "pareto_indices": front,
        "pareto_front": [list(observed[i]) for i in front],
        "hypervolume": hypervolume_2d(rows, reference_point),
        "random_indices": random_ids,
        "random_pareto_indices": [random_ids[k] for k in non_dominated_indices(random_rows)],
        "random_hypervolume": hypervolume_2d(random_rows, reference_point),
        # No best_value is reported. With two incommensurable objectives there
        # is no single best point, and inventing one would be the composite the
        # score-record schema forbids.
    }
