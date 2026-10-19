"""Finite-pool deterministic BoTorch mechanics, initially for toy objectives only."""
import math
import random


def select_next(features, observed, feasible, seed):
    import torch
    from botorch.models import SingleTaskGP
    from botorch.models.transforms.outcome import Standardize
    from botorch.fit import fit_gpytorch_mll
    from botorch.acquisition.analytic import LogExpectedImprovement
    from botorch.optim import optimize_acqf_discrete
    from gpytorch.mlls import ExactMarginalLogLikelihood

    if len(features) != len(feasible) or len(observed) < 2:
        raise ValueError("Pool/feasibility mismatch or insufficient initial observations")
    x = torch.tensor(features, dtype=torch.double)
    if x.ndim != 2 or x.shape[1] < 1 or not torch.isfinite(x).all() or (x < 0).any() or (x > 1).any():
        raise ValueError("Finite features scaled to [0,1] required")
    if len({tuple(row) for row in features}) != len(features):
        raise ValueError("Unique pool representations required")
    if any(type(i) is not int or not 0 <= i < len(features) or not feasible[i]
           or not math.isfinite(y) for i,y in observed.items()):
        raise ValueError("Invalid or infeasible observation")
    available = [i for i, ok in enumerate(feasible) if ok and i not in observed]
    if not available:
        raise ValueError("No unevaluated feasible candidates")
    # Preserve the caller's RNG state; deterministic CPU fitting.
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        train_ids = sorted(observed)
        y = torch.tensor([[observed[i]] for i in train_ids], dtype=torch.double)
        gp = SingleTaskGP(x[train_ids], y, train_Yvar=torch.full_like(y, 1e-6),
                          outcome_transform=Standardize(m=1))
        mll = ExactMarginalLogLikelihood(gp.likelihood, gp)
        fit_gpytorch_mll(mll, optimizer_kwargs={"options": {"maxiter": 50}})
        acquisition = LogExpectedImprovement(gp, best_f=y.max())
        candidate, value = optimize_acqf_discrete(acquisition, q=1, choices=x[available], unique=True)
        matches = torch.all(x[available] == candidate[0], dim=1).nonzero().flatten()
        if len(matches) != 1:
            raise RuntimeError("Acquisition returned an unknown/ambiguous pool member")
        index = available[matches.item()]
    return index, float(value.item())


def toy_objective(x):
    return 1-(x-0.73)**2+0.04*math.sin(19*x)


def run_toy(seed=7, budget=8, state=None, checkpoint=None):
    """Resume cached evaluations; use a finite mathematical pool, never RNA."""
    features = [[i/30] for i in range(31)]
    feasible = [not 0.40 <= row[0] <= 0.60 for row in features]
    protocol = {"seed": seed, "budget": budget, "features": features, "feasible": feasible,
                "initial_indices": [0, 10, 30], "objective": "toy_parabola_plus_sine_v1",
                "acquisition": "LogExpectedImprovement", "gp": "SingleTaskGP",
                "noise_variance": 1e-6, "fit_maxiter": 50,
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
        if row["value"] != toy_objective(features[i][0]):
            raise ValueError("Cached objective mismatch")
        if step < 3 and i != protocol["initial_indices"][step]:
            raise ValueError("Cached initial design mismatch")
        observed[i] = row["value"]
    if len(history) > budget:
        raise ValueError("Cached history exceeds budget")
    for step in range(len(history), budget):
        if step < 3:
            i, acquisition = protocol["initial_indices"][step], None
        else:
            i, acquisition = select_next(features, observed, feasible, seed)
        observed[i] = toy_objective(features[i][0])
        history.append({"index": i, "value": observed[i], "log_acquisition": acquisition})
        if checkpoint is not None:
            checkpoint({"protocol": protocol, "history": list(history)})
    rng = random.Random(seed)
    pool = [i for i,ok in enumerate(feasible) if ok and i not in protocol["initial_indices"]]
    random_ids = protocol["initial_indices"] + rng.sample(pool, budget-3)
    return {"protocol": protocol, "history": history, "unique_evaluations": len(observed),
            "best_value": max(observed.values()), "random_indices": random_ids,
            "random_best_value": max(toy_objective(features[i][0]) for i in random_ids)}
