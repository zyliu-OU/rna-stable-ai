"""CPU-only folding in isolated, bounded subprocesses."""

import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from .scoring import paired_fraction

FIELDS = [
    "sequence_id",
    "kind",
    "length",
    "tool",
    "device",
    "status",
    "wall_seconds",
    "peak_rss_mib",
    "memory_method",
    "supervisor",
    "mfe_kcal_mol",
    "ensemble_free_energy_kcal_mol",
    "paired_fraction",
    "structure",
    "returncode",
    "command",
    "error",
    "raw_output",
]


def run_bounded(command, sequence, timeout=120, memory_limit_gib=8, cwd=None):
    """File-backed pipes avoid deadlocks; kill entire process group on timeout.

    GNU time reports process peak RSS on success. Includes interpreter startup.
    The address-space cap is inherited by tool children (per process).
    """
    start = time.perf_counter()

    def limits():
        cap = int(memory_limit_gib * 1024**3)
        resource.setrlimit(resource.RLIMIT_AS, (cap, cap))

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        rss_file = tmp / "rss"
        wrapper = (
            ["/usr/bin/time", "-f", "%M", "-o", str(rss_file)]
            if Path("/usr/bin/time").exists()
            else []
        )
        with (
            (tmp / "in").open("w+") as stdin,
            (tmp / "out").open("w+") as stdout,
            (tmp / "err").open("w+") as stderr,
        ):
            stdin.write(sequence + "\n")
            stdin.seek(0)
            try:
                execution = wrapper + command
                if sys.platform.startswith("linux"):
                    execution = [
                        sys.executable,
                        "-m",
                        "rnastable.process_guard",
                        str(os.getpid()),
                        "--",
                        *execution,
                    ]
                p = subprocess.Popen(
                    execution,
                    stdin=stdin,
                    stdout=stdout,
                    stderr=stderr,
                    cwd=cwd,
                    start_new_session=True,
                    preexec_fn=limits,
                )
            except OSError as exc:
                return {
                    "status": "error",
                    "wall_seconds": time.perf_counter() - start,
                    "error": str(exc),
                }
            status = "ok"
            try:
                p.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                status = "timeout"
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                p.wait()
            except BaseException:
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                p.wait()
                raise
            if p.returncode and status == "ok":
                status = "error"
            stdout.seek(0)
            stderr.seek(0)
            result = {
                "status": status,
                "wall_seconds": time.perf_counter() - start,
                "returncode": p.returncode,
                "stdout": stdout.read(),
                "error": stderr.read(),
                "supervisor": "linux_parent_death_guard_v1"
                if sys.platform.startswith("linux")
                else "posix_process_group",
            }
            if status == "timeout":
                result["error"] += f"\nExceeded {timeout}s; killed process group"
            if rss_file.exists() and status != "timeout":
                values = re.findall(r"^\d+$", rss_file.read_text(), re.M)
                if values:
                    result["peak_rss_mib"] = int(values[-1]) / 1024
                    result["memory_method"] = (
                        "GNU time maximum RSS of tool descendants (excludes supervisor; not process-tree sum)"
                    )
            return result


def tool_commands(root, config):
    commands = {}
    rnafold = shutil.which("RNAfold")
    local = root / "external/vienna/bin/RNAfold"
    if local.exists():
        rnafold = str(local)
    if rnafold:
        commands["ViennaRNA"] = (
            [rnafold, "--noPS", f"--temp={config['temperature_c']}"],
            None,
        )
    elif importlib.util.find_spec("RNA"):
        commands["ViennaRNA"] = (
            [
                sys.executable,
                "-m",
                "rnastable.vienna_worker",
                str(config["temperature_c"]),
            ],
            None,
        )
    for tool, directory, script in [
        ("LinearFold", "LinearFold", "linearfold"),
        ("LinearPartition", "LinearPartition", "linearpartition"),
    ]:
        path = root / "external" / directory / script
        if path.exists():
            commands[tool] = (
                [sys.executable, str(path), "-V", "-b", str(config["beam_size"])]
                + (["-p"] if tool == "LinearPartition" else []),
                path.parent,
            )
        elif shutil.which(script):
            commands[tool] = (
                [shutil.which(script), "-V", "-b", str(config["beam_size"])]
                + (["-p"] if tool == "LinearPartition" else []),
                None,
            )
    return commands


def parse_output(tool, output, length):
    # LinearPartition reports ensemble free energy, never an MFE.
    if tool == "LinearPartition":
        match = re.search(r"Free Energy[^\n]*?([-+]?\d+\.\d+)", output, re.I)
        if not match:
            raise ValueError("LinearPartition ensemble free energy missing")
        return {"ensemble_free_energy_kcal_mol": float(match.group(1))}
    match = re.search(r"^([.()]+)\s+\(\s*([-+]?\d+(?:\.\d+)?)\s*\)", output, re.M)
    if not match:
        raise ValueError("Dot-bracket structure / energy missing")
    return {
        "structure": match.group(1),
        "mfe_kcal_mol": float(match.group(2)),
        "paired_fraction": paired_fraction(match.group(1), length),
    }


def benchmark_folding(root, manifest, config, raw_dir):
    commands = tool_commands(root, config)
    rows = []
    raw_dir.mkdir(parents=True, exist_ok=True)
    from .sequences import read_fasta

    for item in manifest:
        seq = read_fasta(item["path"])[0][1]
        for tool in ("ViennaRNA", "LinearFold", "LinearPartition"):
            row = {
                "sequence_id": item["id"],
                "kind": item["kind"],
                "length": item["length"],
                "tool": tool,
                "device": "CPU",
                "status": "unavailable",
                "error": "Tool not installed or not discoverable",
            }
            if tool in commands:
                command, cwd = commands[tool]
                row["command"] = json.dumps(command)
                print(f"CPU folding: {tool} {item['id']}", flush=True)
                result = run_bounded(
                    command,
                    seq,
                    config["timeout_seconds"],
                    config["memory_limit_gib"],
                    cwd,
                )
                output = result.pop("stdout", "")
                row.update(result)
                path = raw_dir / f"{item['id']}_{tool}.txt"
                path.write_text(output + "\nSTDERR:\n" + row.get("error", ""))
                row["raw_output"] = str(path)
                if row["status"] == "ok":
                    try:
                        row.update(
                            parse_output(
                                tool, output + "\n" + row.get("error", ""), len(seq)
                            )
                        )
                    except ValueError as exc:
                        row.update(status="parse_error", error=str(exc))
            rows.append(row)
    return rows


def fold_sequence(root, sequence, config, tool="LinearFold", raw_path=None):
    """One CPU fold with the same time/memory limits as the benchmark."""
    from .sequences import validate_sequence

    validate_sequence(sequence)
    commands = tool_commands(Path(root), config)
    if tool not in commands:
        return {
            "status": "unavailable",
            "tool": tool,
            "error": "Tool not installed or not discoverable",
        }
    command, cwd = commands[tool]
    result = run_bounded(
        command, sequence, config["timeout_seconds"], config["memory_limit_gib"], cwd
    )
    output = result.pop("stdout", "")
    result.update(tool=tool, device="CPU", command=command)
    if raw_path is not None:
        raw_path = Path(raw_path)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        with raw_path.open("x") as f:
            f.write(output + "\nSTDERR:\n" + result.get("error", ""))
        result["raw_output"] = str(raw_path)
    if result["status"] == "ok":
        try:
            result.update(
                parse_output(
                    tool, output + "\n" + result.get("error", ""), len(sequence)
                )
            )
        except ValueError as exc:
            result.update(status="parse_error", error=str(exc))
    return result
