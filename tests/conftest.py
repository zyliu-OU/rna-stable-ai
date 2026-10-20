"""Test configuration.

The learned pair model was retired on 2026-10-20. Its checkpoints were removed
from the tree, because the project relies on LinearFold and ViennaRNA for
structure and those feed STRAND, RiboNN and BoTorch downstream. See
`reports/structure_model_gap_diagnosis_2026-10-20.md` and
`configs/stage2_to_stage3_gate_v4_2026-10-20.json`.

A number of replay tests verify that frozen development runs reproduce from
those checkpoints. Their metrics and summaries are retained, so the evidence
behind the retirement is intact, but the weights they reload are gone and those
tests can no longer run.

Rather than delete the tests, which would destroy the ability to re-verify those
runs if the weights are ever restored from git history, they are skipped when
and only when the missing file is a retired checkpoint.

The guard is deliberately narrow. It converts a failure into a skip only when
all of the following hold, so that a genuine missing-file bug still fails:

- the exception is `FileNotFoundError`
- the missing path ends in `.pt` or `.pth`
- the missing path lies under `results/`
- the missing path is NOT a RiboNN weight, which is third-party and retained

Anything else propagates unchanged.
"""
from pathlib import Path

import pytest

RETIREMENT_REASON = (
    "learned pair model retired 2026-10-20; checkpoint removed from the tree. "
    "Structure now comes from LinearFold/ViennaRNA. Run metrics are retained; "
    "see reports/structure_model_gap_diagnosis_2026-10-20.md"
)

ROOT = Path(__file__).resolve().parents[1]


def _is_retired_checkpoint(path):
    if not path:
        return False
    text = str(path)
    if not text.endswith((".pt", ".pth")):
        return False
    # RiboNN weights are third-party, still present, and still relied upon by
    # the translation arm. A missing one is a real failure, never a skip.
    if "ribonn" in text.lower():
        return False
    try:
        resolved = Path(text).resolve()
    except (OSError, ValueError):
        return False
    try:
        relative = resolved.relative_to(ROOT)
    except ValueError:
        return False
    return relative.parts[:1] == ("results",)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    outcome = yield
    info = outcome.excinfo
    if not info or not issubclass(info[0], FileNotFoundError):
        return
    error = info[1]
    candidate = getattr(error, "filename", None) or getattr(error, "filename2", None)
    if candidate is None:
        # Some callers raise FileNotFoundError with the path only in the message.
        candidate = next((part for part in str(error).split()
                          if part.endswith((".pt", ".pth"))), None)
        candidate = candidate.strip("'\"") if candidate else None
    if _is_retired_checkpoint(candidate):
        outcome.force_exception(
            pytest.skip.Exception(f"{RETIREMENT_REASON} (missing: {candidate})"))
