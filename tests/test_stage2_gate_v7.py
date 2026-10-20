"""Tests for gate v7, the purge of the retired model and of out-of-scope data.

A gate that records a deletion is the one most likely to be read later as
evidence that the deleted thing never mattered. These tests pin the opposite:
that v6 is retained unedited, that the requirement basis is carried forward
untouched, that what the purge destroyed is stated as plainly as what it
preserved, that the reversed length-scope policy is acknowledged rather than
quietly dropped, and that the recorded counts match the manifests that were
written before anything was removed.
"""
import glob
import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
V6 = ROOT / "configs/stage2_to_stage3_gate_v6_2026-10-20.json"
V7 = ROOT / "configs/stage2_to_stage3_gate_v7_2026-10-20.json"
MANIFESTS = sorted(glob.glob(str(ROOT / "results/model_purge_runs/*/manifest.json")))


@pytest.fixture(scope="module")
def v7():
    return json.loads(V7.read_text())


@pytest.fixture(scope="module")
def v6():
    return json.loads(V6.read_text())


@pytest.fixture(scope="module")
def manifests():
    return [json.loads(Path(p).read_text()) for p in MANIFESTS]


def test_v6_is_retained_unedited_at_its_recorded_hash(v7):
    assert hashlib.sha256(V6.read_bytes()).hexdigest() == v7["supersedes"]["sha256"]


def test_the_requirement_basis_is_carried_forward_untouched(v6, v7):
    assert v7["requirements_before_stage3"] == v6["requirements_before_stage3"]
    assert v7["requirements_satisfied"] == v6["requirements_satisfied"] == 6
    basis = v7["requirements_satisfied_basis_unchanged_from_v5"]
    assert basis["1"] == "accepted_as_documented_limitation"
    assert basis["3"] == "accepted_as_documented_limitation"
    assert "re-opens no requirement" in basis["note"]
    assert "accepted limitations rather than evidence" in basis["note"]


def test_the_switches_are_unchanged_from_v6(v6, v7):
    for key, value in v7["switches_unchanged_from_v6"].items():
        if key in v6:
            previous = v6[key]
        elif key in v6.get("switches_opened_here", {}):
            previous = v6["switches_opened_here"][key]["now"]
        else:
            previous = v6["switches_still_closed"][key]
        assert previous == value, key


def test_the_purge_states_what_it_destroyed_before_what_it_preserved(v7):
    purge = v7["learned_model_purge"]
    destroyed = " ".join(purge["what_this_destroyed"])
    assert "ability to regenerate" in destroyed
    assert "validate_native_controls_stage2.py" in destroyed
    assert "expand_band_native_controls.py" in destroyed
    assert "not recoverable from git history" in destroyed
    assert "609 tests" in destroyed
    assert list(purge).index("what_this_destroyed") < list(purge).index("what_this_preserved")


def test_the_purge_records_that_the_artifacts_survive_their_generators(v7):
    destroyed = " ".join(v7["learned_model_purge"]["what_this_destroyed"])
    assert "ARTIFACTS remain and are unchanged" in destroyed
    text = " ".join(v7["what_must_not_be_claimed"])
    assert "Their artifacts remain; their generators do not" in text


def test_the_retirement_is_not_rewritten_as_unjustified(v7):
    assert "evidence-based" in v7["learned_model_purge"]["what_must_not_be_claimed"]
    preserved = " ".join(v7["learned_model_purge"]["what_this_preserved"])
    assert "0.2965 against 0.4381" in preserved
    assert "0.3255 against 0.6261" in preserved


def test_the_length_scope_policy_reversal_is_acknowledged(v7):
    reverses = v7["length_scope_removal"]["reverses"]
    assert reverses["document"] == "docs/LENGTH_SCOPE.md"
    assert "preserved" in reverses["what_it_said"]
    assert "reversed by this gate" in reverses["status"]
    assert "left contradicting the tree" in reverses["status"]


def test_the_length_scope_document_carries_the_reversal(v7):
    text = (ROOT / v7["length_scope_removal"]["reverses"]["document"]).read_text()
    assert "REMOVED on 2026-10-20" in text
    assert "That policy\nis reversed" in text or "That policy is reversed" in text
    assert "model_purge_runs" in text
    assert "work above 3,000 nt was never done" in text


def test_editing_frozen_artifacts_is_called_out_rather_than_hidden(v7):
    why = v7["length_scope_removal"]["why_some_artifacts_were_stripped_rather_than_removed"]
    assert "only place in the purge where frozen artifacts were edited" in why
    assert "pre-removal hash was recorded" in why
    assert "convention is not to edit them" in why


def test_no_file_under_results_still_carries_an_out_of_scope_sequence():
    """The removal's own claim, re-checked rather than trusted."""
    pattern = re.compile(r'"sequence"\s*:\s*"[ACGUTacgut]{3000,}"')
    offenders = []
    for path in (ROOT / "results").rglob("*.json"):
        if not path.is_file() or path.stat().st_size > 20_000_000:
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        if pattern.search(text):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_requirement_5_was_reissued_on_the_in_scope_cohort(v7):
    reissue = v7["requirement_5_reissue"]
    superseded = json.loads((ROOT / reissue["superseded_run"]).read_text())
    reissued = json.loads((ROOT / reissue["reissued_run"]).read_text())
    assert superseded["cohort"]["records"] == 11
    assert reissued["cohort"]["records"] == 6
    assert reissued["replay"]["checked"] == 12
    assert reissued["replay"]["reproduced_exactly"] == 12
    assert reissued["constraint_decoder"]["passed"] is True
    assert reissued["refusal_control"]["passed"] is True
    assert "Correct for the cohort it covered" in reissue["superseded_detail"]


def test_the_reissued_run_has_no_out_of_band_rows(v7):
    reissued = json.loads((ROOT / v7["requirement_5_reissue"]["reissued_run"]).read_text())
    for method in reissued["methods"]:
        bands = reissued["resources"][method]["unconstrained_by_band"]
        assert "out_of_band" not in bands


def test_the_generator_survived_by_losing_a_dependency_not_by_keeping_a_module(v7):
    status = v7["requirement_5_reissue"]["generator_status"]
    assert "inlining the six-element set" in status
    assert "removes a dependency rather than preserving a model module" in status
    script = (ROOT / "scripts/verify_native_path_requirement5.py").read_text()
    assert "pair_model" not in script
    assert 'CANONICAL = {"AU", "UA", "GC", "CG", "GU", "UG"}' in script


def test_the_purged_modules_are_actually_gone(v7):
    for stem in ("pair_model", "structure_model", "context_training", "pair_set_training",
                 "checkpoint_prior", "sampled_pair_supervision"):
        assert not (ROOT / "src/rnastable" / f"{stem}.py").exists(), stem


def test_the_current_pipeline_modules_survived():
    for stem in ("folding", "scoring", "pareto", "multi_objective_bo", "discrete_bo",
                 "synonymous_window", "transcript_assembly", "component_integration",
                 "strand_reference", "ribonn_integration", "score_records"):
        assert (ROOT / "src/rnastable" / f"{stem}.py").exists(), stem


def test_a_manifest_was_written_for_every_pass(v7, manifests):
    assert manifests, "the purge must leave an audit trail"
    for manifest in manifests:
        assert manifest["applied"] is True
        assert manifest["authorized_by"]
        assert manifest["groups"]
        assert manifest["maximum_length_nt"] == 3000
        text = " ".join(manifest["what_this_destroys"])
        assert "not recoverable from git history" in text


def test_the_recorded_counts_match_the_manifests(v7, manifests):
    """A gate that paraphrases its own audit trail is where drift starts."""
    counts = {}
    total = 0
    for manifest in manifests:
        total += manifest["total_bytes"]
        for name, group in manifest["groups"].items():
            counts[name] = counts.get(name, 0) + group["count"]
    removed = v7["learned_model_purge"]["what_was_removed"]
    assert removed["source_modules"] == counts.get("model_modules", 0)
    assert removed["run_directories"] == counts.get("model_runs", 0)
    assert removed["configs"] == counts.get("model_configs", 0)
    assert removed["driver_scripts"] == (counts.get("model_scripts", 0)
                                         + counts.get("broken_scripts", 0))
    assert v7["learned_model_purge"]["total_bytes_removed_all_passes"] == total
    long_removed = v7["length_scope_removal"]["what_was_removed"]
    assert long_removed["synthetic_inputs"] == counts.get("long_data", 0)
    assert long_removed["run_directories_removed_by_content"] == counts.get(
        "longcontent_runs", 0)


def test_the_purge_refuses_to_touch_the_current_pipeline():
    """The guard that makes the closure safe to compute automatically."""
    script = (ROOT / "scripts/purge_retired_model_and_long_data.py").read_text()
    assert "CURRENT_PIPELINE_MODULES" in script
    assert "Refusing to proceed" in script
    assert "wrote its manifest BEFORE removing anything" in script or \
        "before removing anything" in script


def test_what_must_not_be_claimed_covers_the_predictable_misreadings(v7):
    text = " ".join(v7["what_must_not_be_claimed"])
    assert "changed any measurement. It changed none" in text
    assert "never obtained" in text
    assert "smaller test suite means a sounder project" in text
