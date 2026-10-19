"""Build and verify a fixed-input integration milestone; never design candidates."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import csv
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import random
import shutil
import sys
import time

from rnastable.component_integration import Transcript, export_ribonn, fold_fixed_input, strand_alo
from rnastable.discrete_bo import run_toy

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT/"configs/four_component_build_v1_2026-10-18.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    temp = path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(obj, indent=2, allow_nan=False)+"\n")
    temp.replace(path)


def source_audit(manifest_path):
    manifest = json.loads(manifest_path.read_text())
    for entry in manifest["files"]:
        if sha(ROOT/entry["local_path"]) != entry["sha256"]:
            raise ValueError(f"Upstream snapshot hash mismatch: {entry['local_path']}")
    data_path = next(ROOT/x["local_path"] for x in manifest["files"]
                     if x["upstream_path"] == "Data/nluc_cleaned_new_final.csv")
    rows = list(csv.DictReader(data_path.open(encoding="utf-8-sig")))
    feature_rows = []
    for row in rows:
        sequence = row["sequence"]
        probability = json.loads(row["bpp_per_pos"])
        if len(sequence) != int(row["seq_len"]) or len(probability) != len(sequence):
            raise ValueError("STRAND reference positional length mismatch")
        alo = strand_alo(probability)
        aup = 1-sum(probability)/len(probability)
        gc = 100*(sequence.count("G")+sequence.count("C"))/len(sequence)
        feature_rows.append({"name": row["name"], "input_sha256": hashlib.sha256(sequence.encode()).hexdigest(),
            "length_nt": len(sequence), "alo_from_released_probabilities": alo,
            "released_out_of_range_positions": sum(not 0 <= p <= 1 for p in probability),
            "released_max_positional_value": max(probability),
            "aup_residual": aup-float(row["aup"]), "gc_percent_residual": gc-float(row["GC"]),
            "released_energy_per_nt": float(row["energy"])/len(sequence)})
    return {"source_manifest_sha256": sha(manifest_path), "files_verified": len(manifest["files"]),
        "nluc_rows": len(rows), "feature_rows": feature_rows,
        "released_out_of_range_positions": sum(x["released_out_of_range_positions"] for x in feature_rows),
        "released_rows_with_out_of_range_positions": sum(x["released_out_of_range_positions"] > 0 for x in feature_rows),
        "max_abs_aup_residual": max(abs(x["aup_residual"]) for x in feature_rows),
        "max_abs_gc_percent_residual": max(abs(x["gc_percent_residual"]) for x in feature_rows),
        "gc_unit": "percent_0_to_100_in_released_data",
        "alo_rule": "mean natural log odds; replace all values <=0 with 1e-10 and >=1 with 1-1e-10",
        "regression": "R pls::plsr(scale=TRUE, validation=LOO); component selection varies by figure",
        "pending": ["original sequence-to-probability extraction settings", "meaning of released energy column",
                    "R reference fit and component-count selection", "saved coefficient/calibration artifact"],
        "stability_prediction_enabled": False}


def fixed_inputs(config):
    rng = random.Random(config["fixed_input_seed"])
    codons = [a+b+c for a in "ACGU" for b in "ACGU" for c in "ACGU"
              if a+b+c not in ("UAA", "UAG", "UGA")]
    output = []
    for length in config["fixed_synthetic_lengths_nt"]:
        utr5_size = 12
        n_codons = (length-utr5_size-12)//3
        cds = "AUG"+"".join(rng.choice(codons) for _ in range(n_codons))+"UAA"
        utr5 = "".join(rng.choice("ACGU") for _ in range(utr5_size))
        utr3 = "".join(rng.choice("ACGU") for _ in range(length-len(cds)-len(utr5)))
        output.append(Transcript(f"fixed_synthetic_{length}", utr5+cds+utr3,
                                 utr5_size, utr5_size+len(cds),
                                 "Synthetic fixed random input; no assay measurement or optimization",
                                 "software mechanics only"))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--resume", type=Path, help="An existing run directory with an identical protocol/code")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if config["stability_score_enabled"] or config["expression_candidate_design_enabled"]:
        raise ValueError("This driver permits fixed-input integration checks only")
    versions = {p: metadata.version(p) for p in
                ["torch", "ViennaRNA", "numpy", "scipy", "botorch", "gpytorch", "linear_operator"]}
    for name, version in config["required_optimizer_versions"].items():
        if versions[name] != version:
            raise ValueError(f"Pinned optimizer version mismatch: {name}")
    source_files = [Path(__file__), ROOT/"src/rnastable/component_integration.py",
                    ROOT/"src/rnastable/ensemble_worker.py", ROOT/"src/rnastable/discrete_bo.py"]
    implementation = {str(p.relative_to(ROOT)): sha(p) for p in source_files}
    identity = {"config_sha256": sha(args.config), "implementation": implementation, "versions": versions,
                "source_manifest_sha256": sha(ROOT/config["source_manifest"])}
    if args.resume:
        output = args.resume.resolve()
        if json.loads((output/"identity.json").read_text()) != identity:
            raise ValueError("Resume identity differs; use a fresh run")
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        output = ROOT/"results/four_component_build_runs"/stamp
        output.mkdir(parents=True, exist_ok=False)
        write(output/"identity.json", identity)
        write(output/"protocol.json", config)
        for path in source_files:
            target = output/"source"/path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        write(output/"runtime.json", {"python": sys.version, "platform": platform.platform(),
                                    "versions": versions, "Rscript": shutil.which("Rscript"),
                                    "device": "cpu", "optimizer_torch_threads": 1})
    print(output, flush=True)
    audit = source_audit(ROOT/config["source_manifest"])
    write(output/"source_audit.json", audit)
    records = fixed_inputs(config)
    write(output/"fixed_inputs.json", [dict(asdict(r), input_sha256=r.sha256,
                                           identity_sha256=r.identity_sha256) for r in records])
    input_path = output/"ribonn_prediction_input.tsv"
    if not input_path.exists():
        exclusions = export_ribonn(records, input_path)
        write(output/"ribonn_preflight.json", {"exclusions": exclusions, "status": "input_contract_verified",
            "inference_status": "pending_isolated_environment_and_weight_inventory",
            "weight_license": "academic research and noncommercial restrictions; see pinned source license"})
    folding = []
    for record in records:
        path = output/f"rnafold_{record.tx_id}.json"
        if path.exists():
            result = json.loads(path.read_text())
            if result["identity_sha256"] != record.identity_sha256:
                raise ValueError("Cached folding identity mismatch")
        else:
            result = fold_fixed_input(record, config["rnafold"]["timeout_seconds"],
                                      config["rnafold"]["temperature_c"])
            write(path, result)
        folding.append({"tx_id": record.tx_id, "status": result["status"], "path": str(path.relative_to(ROOT)),
                        "sha256": sha(path), "runtime_seconds": result.get("runtime_seconds"),
                        "peak_worker_rss_kib": result.get("peak_worker_rss_kib")})
        print("fold", record.tx_id, result["status"], result.get("runtime_seconds"), flush=True)
    import torch
    torch.set_num_threads(1)
    optimizer = []
    for seed in config["toy_optimizer"]["seeds"]:
        path = output/f"toy_seed{seed}.json"
        cached = json.loads(path.read_text()) if path.exists() else None
        start = time.perf_counter()
        result = run_toy(seed, config["toy_optimizer"]["unique_evaluation_budget"], cached,
                         checkpoint=lambda obj: write(path, obj))
        write(path, result)
        optimizer.append({"seed": seed, "path": str(path.relative_to(ROOT)), "sha256": sha(path),
                          "best_value": result["best_value"], "random_best_value": result["random_best_value"],
                          "unique_evaluations": result["unique_evaluations"],
                          "invocation_runtime_seconds": time.perf_counter()-start})
        print("toy", seed, result["best_value"], flush=True)
    artifacts = [p for p in output.rglob("*") if p.is_file() and p.name not in ("summary.json", "artifacts.json")]
    write(output/"artifacts.json", {str(p.relative_to(output)): sha(p) for p in sorted(artifacts)})
    write(output/"summary.json", {"integration_mechanics_complete": all(x["status"] == "ok" for x in folding),
        "folding": folding, "optimizer": optimizer, "source_files_verified": audit["files_verified"],
        "combined_pipeline_complete": False, "stage3_ready": False,
        "pending": ["STRAND original feature-generation and R-fit reproduction",
                    "RiboNN isolated environment, weight inventory, fixed-input checkpoint inference",
                    "independent Stage 2 validation and gate review"]})
    print(output/"summary.json", flush=True)


if __name__ == "__main__":
    main()
