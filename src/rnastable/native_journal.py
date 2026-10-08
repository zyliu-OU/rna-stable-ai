"""Atomic, bound native-fold cache; interrupted requests remain unknown and are not retried."""

import contextlib
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import re
import uuid
from .reference import digest
from .scoring import paired_fraction
from .sequences import validate_sequence


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x") as file:
            json.dump(data, file, indent=2, allow_nan=False)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()


@contextlib.contextmanager
def exclusive_driver(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as file:
        try:
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another driver is active for this journal") from exc
        try:
            yield
        finally:
            fcntl.flock(file, fcntl.LOCK_UN)


class NativeJournal:
    def __init__(self, directory, binding_sha256):
        if not isinstance(binding_sha256, str) or not re.fullmatch(
            "[0-9a-f]{64}", binding_sha256
        ):
            raise ValueError("Invalid journal binding digest")
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.binding = binding_sha256
        self.cache_hits = 0
        self.callbacks_invoked = 0

    def path(self, key):
        if not isinstance(key, str) or not re.fullmatch(
            "[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", key
        ):
            raise ValueError("Invalid journal request key")
        return self.directory / (key + ".json")

    def check_directory_binding(self, create=False):
        marker = self.directory / ".binding"
        if marker.exists():
            try:
                data = json.loads(marker.read_text())
            except (ValueError, OSError) as exc:
                raise ValueError("Invalid journal directory binding") from exc
            if (
                not isinstance(data, dict)
                or type(data.get("schema_version")) is not int
                or data != {"schema_version": 1, "binding_sha256": self.binding}
            ):
                raise ValueError("Journal directory binding changed")
        elif create:
            # Adopt an older ledger only when every existing entry has this binding.
            for path in self.directory.glob("*.json"):
                self.read(path.stem)
            atomic_json(marker, {"schema_version": 1, "binding_sha256": self.binding})

    def read(self, key):
        self.check_directory_binding()
        try:
            envelope = json.loads(self.path(key).read_text())
            payload = envelope["payload"]
            valid = (
                type(envelope["schema_version"]) is int
                and envelope["schema_version"] == 1
                and digest(canonical(payload)) == envelope["payload_sha256"]
                and payload["binding_sha256"] == self.binding
                and payload["key"] == key
                and payload["state"] in ("started", "complete", "interrupted")
                and isinstance(payload["parameters"], dict)
                and isinstance(payload["sequence_sha256"], str)
                and re.fullmatch("[0-9a-f]{64}", payload["sequence_sha256"])
            )
            if not valid:
                raise ValueError("Journal payload/binding changed")
            if payload["state"] != "started":
                result = payload["result"]
                self.validate_result(result)
                if payload["state"] == "interrupted" and (
                    result.get("interrupted") is not True
                    or result["status"] != "error"
                    or "wall_seconds" in result
                    or "mfe_kcal_mol" in result
                ):
                    raise ValueError("Invalid interrupted native result")
            return payload
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid journal payload schema") from exc

    @staticmethod
    def validate_result(result, length=None):
        if not isinstance(result, dict) or result.get("status") not in (
            "ok",
            "timeout",
            "error",
            "parse_error",
            "unavailable",
        ):
            raise ValueError("Invalid native result status")
        canonical(result)
        for name in ("wall_seconds", "peak_rss_mib"):
            if name in result and (
                type(result[name]) not in (int, float)
                or not math.isfinite(result[name])
                or result[name] < 0
            ):
                raise ValueError("Native cost must be finite and nonnegative")
        if result["status"] == "ok":
            energy = result.get("mfe_kcal_mol")
            if type(energy) not in (int, float) or not math.isfinite(energy):
                raise ValueError("Native energy must be finite")
            structure = result.get("structure")
            if not isinstance(structure, str):
                raise ValueError("Native structure missing")
            paired_fraction(structure, len(structure) if length is None else length)

    def write(self, key, payload):
        atomic_json(
            self.path(key),
            {
                "schema_version": 1,
                "payload": payload,
                "payload_sha256": digest(canonical(payload)),
            },
        )

    @staticmethod
    def unknown_result(parameters):
        result = {
            "status": "error",
            "error": "Interrupted native request; outcome and cost unknown. Not retried.",
            "interrupted": True,
        }
        for key in ("tool", "command", "device"):
            if key in parameters:
                result[key] = parameters[key]
        path = parameters.get("raw_output")
        if path and Path(path).is_file():
            result.update(raw_output=path, raw_sha256=digest(Path(path).read_bytes()))
        return result

    def run(self, key, sequence, parameters, callback):
        validate_sequence(sequence)
        path = self.path(key)
        if not isinstance(parameters, dict):
            raise ValueError("Native request parameters must be an object")
        parameters = json.loads(canonical(parameters))
        identity = {
            "binding_sha256": self.binding,
            "key": key,
            "sequence_sha256": digest(sequence.encode()),
            "parameters": parameters,
        }
        with exclusive_driver(self.directory / ".lock"):
            self.check_directory_binding(create=True)
            if path.exists():
                payload = self.read(key)
                if any(payload[k] != v for k, v in identity.items()):
                    raise ValueError("Journal sequence or request parameters changed")
                if payload["state"] == "started":
                    payload.update(
                        state="interrupted",
                        result=self.unknown_result(parameters),
                        recovered_at=datetime.now(timezone.utc).isoformat(),
                    )
                    self.write(key, payload)
                self.validate_result(payload["result"], len(sequence))
                self.cache_hits += 1
                return json.loads(canonical(payload["result"]))
            raw = parameters.get("raw_output")
            if raw and Path(raw).exists():
                raise ValueError(
                    "Native raw output exists without a journal request; refusing duplicate work"
                )
            payload = {
                **identity,
                "state": "started",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "driver_pid": os.getpid(),
            }
            self.write(key, payload)
            self.callbacks_invoked += 1
            try:
                result = callback()
                self.validate_result(result, len(sequence))
                payload.update(
                    state="complete",
                    result=result,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )
                self.write(key, payload)
                return json.loads(canonical(result))
            except BaseException:
                payload.update(
                    state="interrupted",
                    result=self.unknown_result(parameters),
                    interrupted_at=datetime.now(timezone.utc).isoformat(),
                )
                self.write(key, payload)
                raise
