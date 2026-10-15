"""Bound, resumable native requests for the pooled proposal experiment."""

import json
import sys
from pathlib import Path
from .folding import fold_sequence, tool_commands
from .native_journal import NativeJournal, canonical
from .reference import digest


def native_runtime(root, config):
    commands = tool_commands(Path(root), config)
    files = {}
    for tool, (command, cwd) in commands.items():
        for argument in command:
            path = Path(argument)
            if path.is_file():
                files[str(path)] = digest(path.read_bytes())
        if cwd and (Path(cwd) / "bin").is_dir():
            for path in sorted((Path(cwd) / "bin").iterdir()):
                if path.is_file():
                    files[str(path)] = digest(path.read_bytes())
    if sys.platform.startswith("linux"):
        guard = Path(__file__).with_name("process_guard.py")
        files[str(guard)] = digest(guard.read_bytes())
    if (
        "ViennaRNA" in commands
        and "rnastable.vienna_worker" in commands["ViennaRNA"][0]
    ):
        import RNA
        import RNA._RNA

        path = Path(RNA._RNA.__file__)
        files[str(path)] = digest(path.read_bytes())
    return {
        "commands": {
            tool: {"command": command, "cwd": str(cwd) if cwd else None}
            for tool, (command, cwd) in commands.items()
        },
        "file_sha256": files,
    }


class PooledNativeRunner:
    def __init__(self, root, run, config, manifest, callback=None):
        self.root = Path(root)
        self.run = Path(run)
        self.config = json.loads(canonical(config))
        if manifest["config"] != config or manifest["run_dir"] != str(self.run):
            raise ValueError("Native plan/config binding differs")
        for name, expected in manifest["snapshot_sha256"].items():
            if digest((self.run / name).read_bytes()) != expected:
                raise ValueError("Native source snapshot binding differs")
        if (
            digest(Path(manifest["checkpoint"]).read_bytes())
            != manifest["checkpoint_sha256"]
        ):
            raise ValueError("Native checkpoint binding differs")
        for name, expected in manifest["code_sha256"].items():
            if digest(Path(name).read_bytes()) != expected:
                raise ValueError("Native source code binding differs")
        if manifest["native_runtime"] != native_runtime(self.root, config):
            raise ValueError("Native runtime binding differs")
        self.binding = digest(canonical(manifest))
        self.journal = NativeJournal(self.run / "native_journal", self.binding)
        self.callback = callback or fold_sequence

    def parameters(self, policy, phase, step):
        if policy not in ("random_pool", "compatibility_only", "checkpoint_prior"):
            raise ValueError("Unknown native policy")
        if phase not in (
            "baseline",
            "proposal",
            "validation_input",
            "validation_finalist",
        ):
            raise ValueError("Unknown native phase")
        if (
            type(step) is not int
            or (phase == "proposal" and not 1 <= step <= self.config["steps"])
            or (phase != "proposal" and step != 0)
        ):
            raise ValueError("Invalid native request step")
        tool = "LinearFold" if phase in ("baseline", "proposal") else "ViennaRNA"
        folding = dict(self.config)
        if tool == "ViennaRNA":
            folding["timeout_seconds"] = self.config["finalist_timeout_seconds"]
        command, cwd = tool_commands(self.root, folding).get(tool, (None, None))
        parameters = {
            "tool": tool,
            "device": "CPU",
            "command": command,
            "cwd": str(cwd) if cwd else None,
            "config": folding,
            "raw_output": str(self.run / policy / f"{phase}_{step:04d}_{tool}.txt"),
        }
        return parameters

    def run_request(self, policy, sequence, phase, step):
        parameters = self.parameters(policy, phase, step)

        def native():
            result = self.callback(
                self.root,
                sequence,
                parameters["config"],
                parameters["tool"],
                Path(parameters["raw_output"]),
            )
            if "raw_output" in result:
                result["raw_sha256"] = digest(Path(result["raw_output"]).read_bytes())
            return result

        result = self.journal.run(
            f"{policy}_{phase}_{step:04d}", sequence, parameters, native
        )
        if (
            "raw_output" in result
            and digest(Path(result["raw_output"]).read_bytes()) != result["raw_sha256"]
        ):
            raise ValueError("Native cached raw output changed")
        return result

    def accounting(self):
        payloads = [
            self.journal.read(path.stem)
            for path in sorted(self.journal.directory.glob("*.json"))
        ]
        return {
            "unique_requests": len(payloads),
            "completed_requests": sum(p["state"] == "complete" for p in payloads),
            "unknown_requests": sum(p["state"] != "complete" for p in payloads),
            "known_native_wall_seconds": sum(
                p.get("result", {}).get("wall_seconds", 0) for p in payloads
            ),
            "current_invocation_callbacks": self.journal.callbacks_invoked,
            "current_invocation_cache_hits": self.journal.cache_hits,
            "total_cost_known": all(p["state"] == "complete" for p in payloads),
        }
