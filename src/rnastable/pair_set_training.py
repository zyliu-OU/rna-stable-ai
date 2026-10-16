"""Train sparse pair heads from complete explicit pair references."""

import copy
import json
import math
from pathlib import Path
import random

from .pair_head_study import FACTORIES, head_config, predictions
from .pair_model import CANONICAL
from .pair_reference import pair_agreement, validate_pairs
from .reference import digest
from .scoring import base_pairs
from .sequences import validate_sequence
from .structure_model import tokens


def pair_set_supervision(record, max_length=1024):
    import torch

    sequence = validate_sequence(record["sequence"])
    if type(max_length) is not int or not 1 <= max_length <= 1024 or len(sequence) > max_length:
        raise ValueError("Pair-set supervision exceeds the length bound")
    reference = validate_pairs(record["pairs"], len(sequence))
    legal = [(i, j) for j in range(len(sequence)) for i in range(j - 3)
             if sequence[i] + sequence[j] in CANONICAL]
    indices = torch.tensor(legal, dtype=torch.long).reshape(-1, 2)
    labels = torch.tensor([float(pair in reference) for pair in legal])
    return indices, labels, len(reference - set(legal))


def score_predictions(rows, records):
    if len(rows) != len(records):
        raise ValueError("Validation prediction inventory differs")
    scored = []
    for row, record in zip(rows, records, strict=True):
        if (row.get("id") != record["id"] or row.get("sequence") != record["sequence"]
                or row.get("status") != "ok"):
            raise ValueError("Validation prediction identity/status differs")
        predicted = base_pairs(row["structure"])
        reference = validate_pairs(record["pairs"], len(record["sequence"]))
        scored.append(pair_agreement(predicted, reference))
    return sum(row["pair_f1"] for row in scored) / len(scored), scored


def train_component(train, validation, base_config, head, seed, run):
    import torch

    if not train or not validation:
        raise ValueError("Both development splits must be nonempty")
    config = head_config(base_config, head, seed)
    if (config["mode"] != "family_coverage_development_only"
            or config["epochs"] != 10 or config["learning_rate"] != 0.001
            or config["cpu_threads"] != 2 or config["top_k"] != 16
            or config["inference_decoder"] != "exact_sparse"):
        raise ValueError("Training settings differ from frozen study")
    run = Path(run)
    torch.set_num_threads(config["cpu_threads"])
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    rng = random.Random(seed)
    model = FACTORIES[head](copy.deepcopy(config))
    initial = copy.deepcopy(model.state_dict())
    torch.save(initial, run / "initial_model.pt")
    samples = [pair_set_supervision(r, config["training_max_length"]) for r in train]
    validation_samples = [pair_set_supervision(r, config["training_max_length"])
                          for r in validation]
    positive = sum(int(y.sum()) for _, y, _ in samples)
    negative = sum(len(y) - int(y.sum()) for _, y, _ in samples)
    if positive == 0 or negative == 0 or not any(len(y) for _, y, _ in validation_samples):
        raise ValueError("Need positive/negative train and legal validation pairs")
    weight = (negative / positive) ** config["positive_weight_exponent"]
    loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(weight))
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
    history, best_key, chosen = [], None, None
    for epoch in range(1, config["epochs"] + 1):
        order = list(range(len(train)))
        rng.shuffle(order)
        model.train()
        losses = []
        for index in order:
            edges, target, _ = samples[index]
            if len(target) == 0:
                continue
            optimizer.zero_grad(set_to_none=True)
            logits = model(tokens(train[index]["sequence"]), edges)
            loss = loss_fn(logits, target)
            if not bool(torch.isfinite(loss)):
                raise ValueError("Nonfinite training loss")
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        if not losses:
            raise ValueError("No trainable sequence in epoch")
        model.eval()
        with torch.inference_mode():
            rows = predictions(model, validation, "validation", config)
            f1, _ = score_predictions(rows, validation)
            val_losses = [loss_fn(model(tokens(r["sequence"]), edges), target).item()
                          for r, (edges, target, _) in zip(validation, validation_samples, strict=True)
                          if len(target)]
        row = {"epoch": epoch, "mean_train_loss": sum(losses) / len(losses),
               "validation_mean_full_pair_f1": f1,
               "mean_validation_loss": sum(val_losses) / len(val_losses)}
        history.append(row)
        key = (f1, -row["mean_validation_loss"])
        if best_key is None or key > best_key:
            best_key, chosen = key, epoch
            torch.save(model.state_dict(), run / "best_model.pt")
        with (run / "epochs.jsonl").open("a") as stream:
            stream.write(json.dumps(row, allow_nan=False) + "\n")
        print(f"{head} seed {seed} epoch {epoch}/10: validation full-pair F1 {f1:.4f}",
              flush=True)
    model.load_state_dict(torch.load(run / "best_model.pt", map_location="cpu", weights_only=True))
    model.eval()
    initial_model = FACTORIES[head](copy.deepcopy(config))
    initial_model.load_state_dict(initial)
    initial_model.eval()
    with torch.inference_mode():
        baseline = predictions(initial_model, validation, "untrained", config)
        chosen_rows = predictions(model, validation, "trained", config)
    initial_f1, _ = score_predictions(baseline, validation)
    trained_f1, per_record = score_predictions(chosen_rows, validation)
    if trained_f1 != best_key[0]:
        raise ValueError("Selected checkpoint score differs")
    result = {"history": history, "selected_epoch": chosen,
              "initial_validation_full_pair_f1": initial_f1,
              "selected_validation_full_pair_f1": trained_f1,
              "train_positive_pairs": positive, "train_negative_pairs": negative,
              "train_only_positive_weight": weight,
              "unlearnable_train_gold_pairs": sum(s[2] for s in samples),
              "unlearnable_validation_gold_pairs": sum(s[2] for s in validation_samples),
              "full_train_gold_pairs": sum(len(r["pairs"]) for r in train),
              "full_validation_gold_pairs": sum(len(r["pairs"]) for r in validation),
              "parameters": sum(p.numel() for p in model.parameters()),
              "checkpoint_sha256": {
                  "initial_model.pt": digest((run / "initial_model.pt").read_bytes()),
                  "best_model.pt": digest((run / "best_model.pt").read_bytes())},
              "selection_policy": "highest_full_gold_validation_pair_f1_then_lowest_validation_bce_then_earliest_epoch",
              "validation_record_scores": [
                  {"id": record["id"], **score}
                  for record, score in zip(validation, per_record, strict=True)]}
    return result, {"untrained": baseline, "trained": chosen_rows}
