"""Isolated ViennaRNA MFE+partition-function worker for integration v1."""
import hashlib
import json
import math
from pathlib import Path
import resource
import sys
import tempfile
import time

from .component_integration import strand_alo


def main():
    import RNA
    payload = json.load(sys.stdin)
    sequence = payload["sequence"]
    if not 1 <= len(sequence) < 3000 or set(sequence) - set("ACGU"):
        raise ValueError("Canonical in-scope RNA required")
    temperature = float(payload["temperature"])
    if not math.isfinite(temperature) or not 0 <= temperature <= 100:
        raise ValueError("Invalid temperature")
    start = time.perf_counter()
    RNA.params_load_RNA_Turner2004()
    md = RNA.md()
    md.temperature = temperature
    md.dangles = 2
    md.compute_bpp = 1
    md.noLP = 0
    md.max_bp_span = -1
    md.min_loop_size = 3
    with tempfile.TemporaryDirectory() as tmp:
        param_path = Path(tmp)/"turner2004.par"
        RNA.params_save(str(param_path))
        parameter_hash = hashlib.sha256(param_path.read_bytes()).hexdigest()
    fc = RNA.fold_compound(sequence, md)
    structure, mfe = fc.mfe()
    fc.exp_params_rescale(mfe)
    ensemble_structure, ensemble_energy = fc.pf()
    # bpp() contains 1-based upper-triangular p_ij, not symmetric rows.
    bpp = fc.bpp()
    paired = [0.0]*len(sequence)
    for i in range(1, len(sequence)+1):
        for j in range(i+1, len(sequence)+1):
            p = bpp[i][j]
            if not math.isfinite(p) or not 0 <= p <= 1:
                raise ValueError("Invalid pair probability")
            paired[i-1] += p
            paired[j-1] += p
    if any(not math.isfinite(x) or x < -1e-8 or x > 1+1e-8 for x in paired):
        raise ValueError("Invalid positional paired probability sum")
    paired = [min(1.0, max(0.0, x)) for x in paired]
    unpaired = [1-x for x in paired]
    if not all(math.isfinite(x) for x in (mfe, ensemble_energy)):
        raise ValueError("Nonfinite folding energy")
    # Linux ru_maxrss can retain the parent's pre-exec high-water mark. VmHWM
    # describes this post-exec address space, avoiding imported torch inflation.
    memory = {}
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmHWM:"):
            memory["peak_worker_rss_kib"] = int(line.split()[1])
    memory["resource_highwater_including_preexec_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    output = {"status": "ok", "tool": "ViennaRNA", "version": RNA.__version__,
        "settings": {"temperature_c": temperature, "parameter_set": "RNA_Turner2004",
            "parameter_file_sha256": parameter_hash, "dangles": 2,
            "constraints": None, "full_model_details": str(md), "precision": "binding_default"},
        "mfe_structure": structure, "mfe_kcal_mol": mfe,
        "ensemble_structure_annotation": ensemble_structure,
        "ensemble_free_energy_kcal_mol": ensemble_energy,
        "paired_probability_per_position": paired, "unpaired_probability_per_position": unpaired,
        "feature_candidates": {"mfe_energy_per_nt": mfe/len(sequence),
            "ensemble_energy_per_nt": ensemble_energy/len(sequence),
            "gc_fraction": sum(sequence.count(x) for x in "GC")/len(sequence),
            "aup": sum(unpaired)/len(sequence), "alo": strand_alo(paired)},
        "strand_compatibility": "pending_original_extraction_audit_no_stability_prediction",
        "runtime_seconds": time.perf_counter()-start,
        **memory}
    print(json.dumps(output, allow_nan=False))


if __name__ == "__main__":
    main()
