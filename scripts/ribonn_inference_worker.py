"""Run the pinned upstream RiboNN implementation in its isolated CPU runtime.

This file intentionally avoids importing the main project's scientific stack.
The sole upstream runtime adjustment maps verified tensor-only weights to CPU.
"""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import math
import os
from pathlib import Path
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job",type=Path)
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    out = Path(job["output"]).resolve(); out.mkdir(exist_ok=False,parents=True)
    work = Path(job["work_directory"]).resolve()
    sys.path.insert(0,str(work)); os.chdir(work)
    import numpy as np
    import pandas as pd
    import torch
    from src.data import RiboNNDataModule
    from src.utils.helpers import extract_config
    from src.predict import predict_using_nested_cross_validation_models

    torch.set_num_threads(job["cpu_threads"])
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    if torch.cuda.is_available():
        raise ValueError("This protocol requires a CPU-only torch build")
    versions = {p:metadata.version(p) for p in ["torch","numpy","pandas","pytorch-lightning",
                 "torchmetrics","lightning-utilities","scikit-learn","scipy","setuptools"]}
    run_df = pd.read_csv(job["runs_csv"])
    selected = []
    for fold in np.sort(run_df["params.test_fold"].unique()):
        candidates = run_df[run_df["params.test_fold"]==fold].sort_values("metrics.val_r2",ascending=False).head(job["top_k"])
        selected.extend({"fold":int(fold),"run_id":str(row.run_id)} for row in candidates.itertuples())
    if selected != [{"fold":r["fold"],"run_id":r["run_id"]} for r in job["selected_checkpoints"]]:
        raise ValueError("Pinned checkpoint selection differs from upstream pandas ranking")
    config = extract_config(run_df,run_df.run_id[0])
    architecture_keys = ["activation","num_conv_layers","kernel_size","conv_stride","conv_padding",
        "conv_dilation","dropout","ln_epsilon","num_targets","filters","len_after_conv","residual",
        "split_utr5_cds_utr3_channels","label_codons","label_utr5","label_utr3","label_splice_sites",
        "label_up_probs","with_NAs","max_shift","pad_5_prime","label_3rd_nt_of_codons"]
    architecture = {k:config[k] for k in architecture_keys}
    for row in selected:
        other = extract_config(run_df,row["run_id"])
        if any(other[k]!=architecture[k] for k in architecture_keys):
            raise ValueError("Selected checkpoint architecture/configuration mismatch")
    if config["max_shift"]!=0:
        raise ValueError("Stochastic forward augmentation needs a separate protocol")
    config.update(species=job["species"],max_utr5_len=1381,max_cds_utr3_len=11937,
                  tx_info_path=job["input_tsv"],num_workers=0,test_batch_size=job["batch_size"],
                  remove_extreme_txs=False,target_column_pattern=None)
    dm = RiboNNDataModule(config)
    loader = dm.predict_dataloader(); dataset = loader.dataset
    encoding = []
    for i,row in dm.df.iterrows():
        encoded = dataset[i]
        # Independent explicit encoding check for the released 5-channel mode.
        if encoded.shape[0]!=5 or not config["pad_5_prime"] or config["split_utr5_cds_utr3_channels"]:
            raise ValueError("Expected released 5-channel start-codon-aligned input")
        reference = torch.zeros_like(encoded)
        offset = config["max_utr5_len"]-int(row.utr5_size)
        # Released DataFrameDataset uses A,T,C,G channel order.
        mapping = {"A":0,"T":1,"C":2,"G":3}
        for j,nt in enumerate(row.tx_sequence): reference[mapping[nt],offset+j]=1
        for j in range(0,int(row.cds_size),3): reference[4,1381+j]=1
        if not torch.equal(reference,encoded):
            raise ValueError("Independent nucleotide/CDS channel encoding mismatch")
        encoding.append({"tx_id":str(row.tx_id),"shape":list(encoded.shape),
                         "sha256":hashlib.sha256(encoded.numpy().tobytes()).hexdigest(),
                         "cds_codon_markers":int(encoded[4].sum().item())})
    (out/"encoding_audit.json").write_text(json.dumps(encoding,indent=2)+"\n")
    audited_config = {k:({"unused_nonfinite_metadata":str(v)} if isinstance(v,float) and not math.isfinite(v) else v)
                      for k,v in config.items()}
    (out/"effective_config.json").write_text(json.dumps(audited_config,indent=2,default=str,allow_nan=False)+"\n")
    allowed = {Path(r["path"]).resolve():r for r in job["selected_checkpoints"]}
    original_load = torch.load
    loaded = []
    def audited_load(path,*args,**kwargs):
        actual = Path(path).resolve()
        if actual not in allowed:
            raise ValueError("Upstream requested an unpinned checkpoint")
        item = allowed[actual]
        if hashlib.sha256(actual.read_bytes()).hexdigest()!=item["sha256"]:
            raise ValueError("Checkpoint changed before deserialization")
        kwargs.update(map_location="cpu",weights_only=True)
        state = original_load(path,*args,**kwargs)
        if not isinstance(state,dict) or not all(isinstance(k,str) and torch.is_tensor(v) for k,v in state.items()):
            raise ValueError("Tensor-only state dictionary required")
        loaded.append({"run_id":item["run_id"],"fold":item["fold"],"sha256":item["sha256"],
                       "tensors":len(state),"parameters_and_buffers":sum(x.numel() for x in state.values())})
        return state
    torch.load = audited_load
    started = time.perf_counter()
    try:
        result = predict_using_nested_cross_validation_models(job["input_tsv"],job["species"],run_df,
                       top_k_models_to_use=job["top_k"],batch_size=job["batch_size"],num_workers=0)
    finally:
        torch.load = original_load
    elapsed = time.perf_counter()-started
    if [r["run_id"] for r in loaded]!=[r["run_id"] for r in selected]:
        raise ValueError("Actual checkpoint load order/count differs from frozen inventory")
    if job["score_column"] not in result or not np.isfinite(result.filter(regex="^predicted_TE_").to_numpy()).all():
        raise ValueError("Missing task or nonfinite pretrained output")
    result.to_csv(out/"raw_fold_predictions.tsv",sep="\t",index=False,float_format="%.17g")
    memory = next(int(line.split()[1]) for line in Path("/proc/self/status").read_text().splitlines() if line.startswith("VmHWM:"))
    summary = {"python":sys.version,"versions":versions,"device":"cpu","cpu_threads":job["cpu_threads"],
               "dataloader_workers":0,"batch_size":job["batch_size"],"architecture":architecture,
               "selected_checkpoints":loaded,"rows":len(result),
               "task_columns":[x for x in result if x.startswith("predicted_TE_")],
               "runtime_seconds":elapsed,"peak_worker_rss_kib":memory,
               "checkpoint_load_adjustment":"torch.load(map_location=cpu, weights_only=True); original inference unchanged",
               "biological_interpretation":"released target scale only; no cell-free calibration or measurements"}
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps({"rows":len(result),"models":len(loaded),"runtime_seconds":elapsed,
                      "peak_worker_rss_kib":memory}),flush=True)


if __name__ == "__main__":main()
