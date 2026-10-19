"""Freeze, fit and replay STRAND on released reference features only."""
import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from rnastable.component_integration import fold_fixed_input
from rnastable.strand_reference import (
    reference_record, feature_identity, linear_prediction, replay_reference,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT/"configs/strand_reference_reproduction_v1_2026-10-18.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    with Path(path).open("x") as f:
        f.write(json.dumps(obj,indent=2,allow_nan=False)+"\n")


def load_references(config):
    manifest = json.loads((ROOT/config["source_manifest"]).read_text())
    files = {}
    for entry in manifest["files"]:
        if sha(ROOT/entry["local_path"]) != entry["sha256"]:
            raise ValueError("Pinned source hash mismatch")
        if entry["component"] == "strand":
            if entry["commit"] != config["source_commit"]:
                raise ValueError("STRAND source commit mismatch")
            files[entry["upstream_path"]] = ROOT/entry["local_path"]
    raw_train = list(csv.DictReader(files["Data/nluc_cleaned_new_final.csv"].open(encoding="utf-8-sig")))
    raw_validation = list(csv.DictReader(files["Data/validate_cleaned_new_final.csv"].open(encoding="utf-8-sig")))
    records = [reference_record(r,"train") for r in raw_train]
    raw = {r["name"]:r for r in raw_train+raw_validation}
    for row in raw_validation:
        cohort = {"CDS (eGFP) variants":"egfp","CDS (MEV) variants":"mev_exploratory"}[row["group"]]
        records.append(reference_record(row,cohort))
    counts = {c:sum(r["cohort"]==c for r in records) for c in ["train","egfp","mev_exploratory"]}
    if counts != {"train":69,"egfp":13,"mev_exploratory":9} or len(raw) != len(records):
        raise ValueError("Unexpected cohort inventory or duplicate reference IDs")
    return records,raw,files


def cross_language_check(run,records,tolerance):
    models = json.loads((run/"r_models.json").read_text())
    reference_map = {(r["cohort"],r["name"]):r for r in records}
    feature_error = 0.0
    for cohort,label in [("train","train"),("egfp","egfp"),("mev_exploratory","mev")]:
        for row in csv.DictReader((run/f"r_{label}_features.csv").open()):
            original = reference_map[(cohort,row["name"])]["features"]
            feature_error = max(feature_error,max(abs(float(row[k])-v) for k,v in original.items()))
    prediction_error = 0.0
    for row in csv.DictReader((run/"r_predictions.csv").open()):
        if row["cohort"] == "train_loo":
            continue
        component = models["models"][row["arm"]]["components"][row["ncomp"]]
        features = reference_map[(row["cohort"],row["name"])]["features"]
        prediction = linear_prediction(component,{k:features[k] for k in component["feature_order"]})
        prediction_error = max(prediction_error,abs(prediction-float(row["prediction"])))
    if max(feature_error,prediction_error) > tolerance:
        raise ValueError(f"R/Python replay mismatch: {feature_error}, {prediction_error}")
    return {"feature_max_abs_difference":feature_error,"prediction_max_abs_difference":prediction_error}


def verify_run(run):
    manifest = json.loads((run/"manifest.json").read_text())
    for relative,expected in manifest["artifacts"].items():
        path = run/relative
        if not path.resolve().is_relative_to(run.resolve()) or sha(path)!=expected:
            raise ValueError(f"Artifact checksum mismatch: {relative}")
    config = json.loads((run/"protocol.json").read_text())
    records = json.loads((run/"reference_inventory.json").read_text())
    check = cross_language_check(run/"fit",records,config["numerical_replay_absolute_tolerance"])
    model = json.loads((run/"reference_model.json").read_text())
    for record in records:
        replay_reference(model,record)
    # Use the frozen replay script to avoid changing historical replay semantics.
    p = subprocess.run([str(ROOT/config["Rscript"]),"--vanilla",str(run/"source/scripts/replay_strand_reference.R"),
                        str(run/"fit")],env=dict(os.environ,TZ="UTC"),capture_output=True,text=True,check=True)
    result = {"artifacts_verified":len(manifest["artifacts"]),"reference_records":len(records),
              **check,"RDS_replay":json.loads(p.stdout),"refit":False}
    print(json.dumps(result,indent=2))
    return result


@dataclass(frozen=True)
class FixedSequence:
    """Unannotated released input for a structure-feature diagnostic, not RiboNN."""
    tx_id: str
    sequence: str

    @property
    def sha256(self):
        return hashlib.sha256(self.sequence.encode()).hexdigest()

    @property
    def identity_sha256(self):
        return hashlib.sha256((self.tx_id+":"+self.sha256+":reference_diagnostic").encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",type=Path,default=DEFAULT)
    parser.add_argument("--verify-run",type=Path)
    args = parser.parse_args()
    if args.verify_run:
        verify_run(args.verify_run.resolve()); return
    config = json.loads(args.config.read_text())
    if config["new_sequence_scoring_enabled"] or config["expression_candidate_design_enabled"]:
        raise ValueError("Reference reproduction cannot enable candidate screening")
    records,raw,files = load_references(config)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out = ROOT/"results/strand_reference_reproduction_runs"/stamp
    out.mkdir(parents=True,exist_ok=False)
    print(out,flush=True)
    write(out/"protocol.json",config)
    write(out/"reference_inventory.json",records)
    sources = [Path(__file__),ROOT/"scripts/reproduce_strand_reference.R",
        ROOT/"scripts/replay_strand_reference.R",ROOT/"src/rnastable/strand_reference.py",
        ROOT/"src/rnastable/component_integration.py",ROOT/"src/rnastable/ensemble_worker.py"]
    implementation = {}
    for path in sources:
        target = out/"source"/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target); implementation[str(path.relative_to(ROOT))] = sha(path)
    for key in ["source_manifest","methods_manifest"]:
        shutil.copyfile(ROOT/config[key],out/(key+".json"))
    methods = json.loads((ROOT/config["methods_manifest"]).read_text())
    article = (ROOT/config["methods_manifest"]).parent/"article.xml"
    if sha(article)!=methods["sha256"]:
        raise ValueError("Article XML hash mismatch")
    shutil.copyfile(article,out/"article.xml")
    write(out/"identity.json",{"implementation":implementation,"config_sha256":sha(args.config),
        "source_manifest_sha256":sha(ROOT/config["source_manifest"]),"methods_manifest_sha256":sha(ROOT/config["methods_manifest"])})
    # Full conda URL/build lock, plus metadata carrying original archive hashes.
    envdir = (ROOT/config["Rscript"]).parent.parent
    lock = subprocess.run(["/home/zyliu/anaconda3/bin/conda","list","--prefix",str(envdir),"--explicit"],
                          capture_output=True,text=True,check=True)
    (out/"conda_explicit.txt").write_text(lock.stdout)
    package_meta = [json.loads(p.read_text()) for p in sorted((envdir/"conda-meta").glob("*.json"))]
    write(out/"conda_package_metadata.json",package_meta)
    fits = []
    for index in range(config["fit_repetitions"]):
        dest = out/("fit" if index==0 else f"fit_repeat{index}"); dest.mkdir()
        start = time.perf_counter()
        cmd = [str(ROOT/config["Rscript"]),"--vanilla",str(out/"source/scripts/reproduce_strand_reference.R"),
               str(files["Data/nluc_cleaned_new_final.csv"].parent),str(dest)]
        p = subprocess.run(cmd,env=dict(os.environ,TZ="UTC",OPENBLAS_NUM_THREADS="1"),
                           capture_output=True,text=True)
        (dest/"command.log").write_text(" ".join(cmd)+"\n"+p.stdout+p.stderr)
        if p.returncode:
            raise RuntimeError(p.stderr)
        fits.append({"repeat":index,"runtime_seconds":time.perf_counter()-start,
                     **cross_language_check(dest,records,config["numerical_replay_absolute_tolerance"])})
    rmodels = json.loads((out/"fit/r_models.json").read_text())
    runtime = {"R":rmodels["R_version"].split()[2],"pls":rmodels["pls_version"],"jsonlite":rmodels["jsonlite_version"]}
    if runtime != config["required_runtime"]:
        raise ValueError(f"Runtime mismatch: {runtime}")
    for arm,checks in rmodels["exact_upstream_block_checks"].items():
        if checks["coefficient_max_abs_difference"]!=0 or checks["selected_egfp_prediction_max_abs_difference"]!=0:
            raise ValueError("Exact upstream block replay differs")
    repeated = json.loads((out/"fit_repeat1/r_models.json").read_text())
    deterministic = repeated["models"]==rmodels["models"]
    if not deterministic:
        raise ValueError("Repeated R fits differ")
    selected = rmodels["models"]["with_alo"]["selected_ncomp"]
    model = {"schema_version":1,"name":"STRAND_nluc_training_LOO_selected_reference_reproduction",
        "source_commit":config["source_commit"],"source_manifest_sha256":sha(ROOT/config["source_manifest"]),
        "component":rmodels["models"]["with_alo"]["components"][str(selected)],
        "allowed_reference_feature_identities":[feature_identity(r) for r in records],
        "selection":config["selection"],"units":config["units"],
        "new_sequence_scoring_enabled":False,"stage3_ready":False}
    write(out/"reference_model.json",model)
    write(out/"python_reference_predictions.json",[replay_reference(model,r) for r in records])
    panel = []
    record_by_id = {r["name"]:r for r in records}
    for name in config["rnafold_panel_names"]:
        r = record_by_id[name]; seq = FixedSequence(name,raw[name]["sequence"])
        folding = fold_fixed_input(seq,config["rnafold"]["timeout_seconds"],config["rnafold"]["temperature_c"])
        write(out/f"rnafold_{name}.json",folding)
        item = {"name":name,"cohort":r["cohort"],"input_sha256":seq.sha256,"status":folding["status"],
                "reference_features":r["features"],"reference_replay_hours":replay_reference(model,r)["predicted_half_life"]}
        if folding["status"]=="ok":
            f = folding["feature_candidates"]
            item["hypotheses"] = {}
            for energy in config["rnafold"]["energy_hypotheses"]:
                features = {"energy_per_length":f[energy],"GC":f["gc_fraction"]*100,"aup":f["aup"],"alo":f["alo"]}
                # Diagnostic arithmetic only, deliberately bypassing the reference scorer.
                y = linear_prediction(model["component"],features)
                item["hypotheses"][energy] = {"features":features,
                    "feature_differences":{k:features[k]-r["features"][k] for k in features},
                    "uncalibrated_substitution_output":y,
                    "output_difference_from_reference":y-item["reference_replay_hours"],
                    "status":"incompatible_input_diagnostic_only_not_validated_stability_prediction"}
        panel.append(item)
        print("RNAfold compatibility",name,folding["status"],flush=True)
    write(out/"rnafold_compatibility.json",{"original_engine":"LinearPartition","panel":panel,
        "compatible_for_unchanged_model":False,"reason":"Engine and probability/energy provenance differ; calibration review required"})
    write(out/"summary.json",{"reference_fit_reproduced":True,"deterministic_fit_models_equal":deterministic,
        "fit_checks":fits,"selected_components":{k:m["selected_ncomp"] for k,m in rmodels["models"].items()},
        "metrics":rmodels["metrics"],"runtime":runtime,"reference_model_sha256":sha(out/"reference_model.json"),
        "rnafold_panel_complete":all(x["status"]=="ok" for x in panel),
        "new_sequence_scoring_enabled":False,"stage3_ready":False})
    artifacts = {str(p.relative_to(out)):sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
    write(out/"manifest.json",{"artifacts":artifacts})
    verify_run(out)
    print(out/"summary.json",flush=True)


if __name__ == "__main__":
    main()
