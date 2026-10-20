"""Freeze and verify upstream RiboNN inference on fixed annotated inputs."""
import argparse
import csv
from dataclasses import fields,asdict
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from rnastable.component_integration import Transcript,export_ribonn,join_ribonn_predictions
from rnastable.ribonn_integration import selected_checkpoints,verify_weight_files,exact_prediction_replay

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT/"configs/ribonn_fixed_inference_v1_2026-10-18.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path,obj):
    with Path(path).open("x") as f:f.write(json.dumps(obj,indent=2,allow_nan=False)+"\n")


def records_from_inventory(path):
    keys = {field.name for field in fields(Transcript)}
    records=[]
    for row in json.loads(path.read_text()):
        record=Transcript(**{k:v for k,v in row.items() if k in keys})
        if record.sha256!=row["input_sha256"] or record.identity_sha256!=row["identity_sha256"]:
            raise ValueError("Fixed transcript identity mismatch")
        records.append(record)
    return records


def reference_records(config):
    """Build records from the recorded construct inputs instead of the synthetic set.

    Used when a config names a reference_transcript block. The CDS is re-verified
    against its recorded hash by assemble(), so a reference run cannot silently
    score a different sequence than the one the project recorded.
    """
    from rnastable.transcript_assembly import assemble
    spec = config["reference_transcript"]
    records = []
    for variant in spec["variants"]:
        component = variant.get("cds_component", "cds")
        cds_file = spec["cds_files"][component] if "cds_files" in spec else spec["cds_file"]
        record, _ = assemble(
            (ROOT/cds_file).read_text(), ROOT/spec["inputs_config"],
            variant["tx_id"], spec["provenance"], spec["assay_context"],
            include_poly_a=variant["include_poly_a"], cds_component=component)
        records.append(record)
    return records


def verify(run):
    manifest=json.loads((run/"manifest.json").read_text())
    for relative,expected in manifest["artifacts"].items():
        path=run/relative
        if not path.resolve().is_relative_to(run.resolve()) or sha(path)!=expected:
            raise ValueError(f"Artifact checksum mismatch: {relative}")
    config=json.loads((run/"protocol.json").read_text())
    records=records_from_inventory(run/"input_inventory.json")
    raw=[list(csv.DictReader((run/f"inference_{i}/raw_fold_predictions.tsv").open(),delimiter="\t"))
         for i in range(config["replay_processes"])]
    replay=exact_prediction_replay(raw[0],raw[1],config["score_column"])
    joined=join_ribonn_predictions(records,raw[0],config["score_column"],config["expected_folds"])
    expected=json.loads((run/"joined_predictions.json").read_text())
    # JSON dictionary fold keys are strings on disk.
    if json.loads(json.dumps(joined))!=expected:
        raise ValueError("Joined prediction replay mismatch")
    result={"artifacts_verified":len(manifest["artifacts"]),"inputs":len(records),
            "joined_ok":sum(x["status"]=="ok" for x in joined),
            "explicit_exclusions":sum(x["status"]=="excluded" for x in joined),"cached_task_replay":replay,
            "mode":"artifact and cached output audit; no new checkpoint inference"}
    print(json.dumps(result,indent=2)); return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",type=Path,default=DEFAULT)
    parser.add_argument("--verify-run",type=Path)
    args=parser.parse_args()
    if args.verify_run:verify(args.verify_run.resolve());return
    config=json.loads(args.config.read_text())
    if config["candidate_design_enabled"] or config["stage3_ready"]:
        raise ValueError("Fixed input mechanics protocol only")
    sources=json.loads((ROOT/config["source_manifest"]).read_text())
    for row in sources["files"]:
        if sha(ROOT/row["local_path"])!=row["sha256"]:raise ValueError("Upstream source hash mismatch")
    weights=json.loads((ROOT/config["weight_manifest"]).read_text())
    verified_weights=verify_weight_files(weights,ROOT)
    archive=ROOT/weights["archive_path"]
    if sha(archive)!=weights["sha256"]:raise ValueError("Weight archive checksum mismatch")
    modelroot=archive.parent/"extracted"
    runs=modelroot/config["species"]/"runs.csv"
    rows=list(csv.DictReader(runs.open()))
    selected=selected_checkpoints(rows,config["top_k_per_fold"])
    if sorted({x["fold"] for x in selected})!=config["expected_folds"]:
        raise ValueError("Checkpoint fold inventory mismatch")
    listed={str((ROOT/x["path"]).resolve()):x for x in weights["files"]}
    for item in selected:
        target=(modelroot/config["species"]/item["run_id"]/"state_dict.pth").resolve()
        item.update(path=str(target),sha256=listed[str(target)]["sha256"],bytes=listed[str(target)]["bytes"])
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out=ROOT/"results/ribonn_fixed_inference_runs"/stamp;out.mkdir(parents=True,exist_ok=False)
    print(out,flush=True)
    write(out/"protocol.json",config);write(out/"checkpoint_inventory.json",selected)
    if "reference_transcript" in config:
        # Scoring the supplied reference construct, not a designed candidate.
        # The synthetic input inventory is deliberately not mixed in, so the run
        # contains exactly the sequences the project recorded.
        records=reference_records(config)
        prior_identity=None
    else:
        prior=ROOT/config["synthetic_input_run"]
        prior_manifest=json.loads((prior/"artifacts.json").read_text())
        if sha(prior/"fixed_inputs.json")!=prior_manifest["fixed_inputs.json"]:
            raise ValueError("Original fixed input inventory changed")
        records=records_from_inventory(prior/"fixed_inputs.json")
        records += [Transcript("ribonn_empty_UTRs","AUGGCUUAA",0,9,"synthetic empty-UTR control","software mechanics only"),
            Transcript("ribonn_utr5_1381","A"*1381+"AUGGCUUAA",1381,1390,"synthetic input-boundary control","software mechanics only"),
            Transcript("ribonn_utr5_1382","A"*1382+"AUGGCUUAA",1382,1391,"synthetic exclusion control","software mechanics only")]
        prior_identity=sha(prior/"fixed_inputs.json")
    write(out/"input_inventory.json",[dict(asdict(r),input_sha256=r.sha256,identity_sha256=r.identity_sha256) for r in records])
    exclusions=export_ribonn(records,out/"validated_input.tsv");write(out/"expected_exclusions.json",exclusions)
    # Also send the excluded in-scope boundary control to upstream so that its
    # actual length filter, rather than only our preflight, is exercised.
    with (out/"upstream_input.tsv").open("x",newline="") as f:
        writer=csv.writer(f,delimiter="\t");writer.writerow(["tx_id","tx_sequence","utr5_size","cds_size"])
        writer.writerows([r.tx_id,r.sequence,r.cds_start,r.cds_end-r.cds_start] for r in records)
    work=out/"upstream_workspace";work.mkdir()
    for row in sources["files"]:
        if row["component"]!="ribonn":continue
        target=work/row["upstream_path"];target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/row["local_path"],target)
    for name in ["src/__init__.py","src/utils/__init__.py"]:(work/name).write_text("")
    (work/"models").symlink_to(modelroot,target_is_directory=True)
    implementations=[Path(__file__),ROOT/"scripts/ribonn_inference_worker.py",ROOT/"scripts/acquire_ribonn_weights.py",
        ROOT/"src/rnastable/ribonn_integration.py",ROOT/"src/rnastable/component_integration.py"]
    identities={}
    for path in implementations:
        target=out/"source"/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target);identities[str(path.relative_to(ROOT))]=sha(path)
    write(out/"identity.json",{"implementation":identities,"config_sha256":sha(args.config),
        "source_manifest_sha256":sha(ROOT/config["source_manifest"]),"weight_manifest_sha256":sha(ROOT/config["weight_manifest"]),
        "fixed_input_inventory_sha256":prior_identity})
    shutil.copyfile(ROOT/config["weight_manifest"],out/"weight_manifest.json")
    shutil.copyfile(ROOT/config["source_manifest"],out/"source_manifest.json")
    envpath=(ROOT/config["python"]).parent.parent
    lock=subprocess.run(["/home/zyliu/anaconda3/bin/conda","list","--prefix",str(envpath),"--explicit"],capture_output=True,text=True,check=True)
    (out/"conda_explicit.txt").write_text(lock.stdout)
    write(out/"conda_package_metadata.json",[json.loads(p.read_text()) for p in sorted((envpath/"conda-meta").glob("*.json"))])
    raw=[];worker_summaries=[]
    for index in range(config["replay_processes"]):
        job={"output":str(out/f"inference_{index}"),"work_directory":str(work),"runs_csv":str(runs),
             "input_tsv":str(out/"upstream_input.tsv"),"selected_checkpoints":selected,
             "species":config["species"],"top_k":config["top_k_per_fold"],"score_column":config["score_column"],
             "cpu_threads":config["cpu_threads"],"batch_size":config["batch_size"]}
        jobfile=out/f"job_{index}.json";write(jobfile,job)
        start=time.perf_counter()
        cmd=[str(ROOT/config["python"]),str(out/"source/scripts/ribonn_inference_worker.py"),str(jobfile)]
        p=subprocess.run(cmd,env=dict(os.environ,PYTHONPATH="",CUDA_VISIBLE_DEVICES="",OMP_NUM_THREADS=str(config["cpu_threads"]),
                             MKL_NUM_THREADS=str(config["cpu_threads"]),TZ="UTC"),capture_output=True,text=True,
                             timeout=config["worker_timeout_seconds"])
        (out/f"worker_{index}.log").write_text(" ".join(cmd)+"\n"+p.stdout+p.stderr+f"\nExit code: {p.returncode}\n")
        if p.returncode:raise RuntimeError(p.stderr)
        summary=json.loads((out/f"inference_{index}/summary.json").read_text())
        for key,version in config["required_versions"].items():
            if summary["versions"][key]!=version:raise ValueError("Pinned runtime mismatch")
        summary["subprocess_wall_seconds"]=time.perf_counter()-start
        worker_summaries.append(summary)
        raw.append(list(csv.DictReader((out/f"inference_{index}/raw_fold_predictions.tsv").open(),delimiter="\t")))
        print("Inference process",index,"completed",summary["rows"],"rows",summary["runtime_seconds"],flush=True)
    replay=exact_prediction_replay(raw[0],raw[1],config["score_column"])
    # Verify every released task, not only the single designated task.
    for task in worker_summaries[0]["task_columns"]:exact_prediction_replay(raw[0],raw[1],task)
    joined=join_ribonn_predictions(records,raw[0],config["score_column"],config["expected_folds"])
    shuffled=join_ribonn_predictions(records,list(reversed(raw[0])),config["score_column"],config["expected_folds"])
    for a,b in zip(joined,shuffled):
        if a.get("fold_scores")!=b.get("fold_scores") or abs(a.get("mean_score",0)-b.get("mean_score",0))>1e-14:
            raise ValueError("Prediction join depends on row order")
    write(out/"joined_predictions.json",joined)
    write(out/"summary.json",{"fixed_inference_complete":True,"weights_files_verified":verified_weights,
        "archive_sha256":weights["sha256"],"selected_models":len(selected),"folds":config["expected_folds"],
        "score_column":config["score_column"],"inputs":len(records),"raw_rows_per_process":len(raw[0]),
        "explicit_exclusions":exclusions,"replay":replay,"all_task_replays_equal":True,
        "workers":worker_summaries,"cell_free_calibrated":False,"candidate_design_enabled":False,"stage3_ready":False})
    artifacts={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
    write(out/"manifest.json",{"artifacts":artifacts})
    verify(out);print(out/"summary.json",flush=True)


if __name__=="__main__":main()
