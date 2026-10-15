"""Coverage/provenance gates must not turn citations or scores into independence."""

import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def module(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "reference_readiness_audit", root / "scripts/audit_reference_readiness.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def policy():
    return json.loads(
        (
            Path(__file__).resolve().parents[1] / "configs/reference_readiness.json"
        ).read_text()
    )


def binding(counts, unsupported=0):
    families, records = [], []
    for index, supported in enumerate(counts):
        name = f"RF{index + 9000:05d}"
        for item in range(supported + unsupported):
            records.append(
                {
                    "id": f"{name}:{item}",
                    "family_id": name,
                    "reference_status": "ok"
                    if item < supported
                    else "unsupported_reference",
                }
            )
        families.append(
            {
                "family_id": name,
                "planned_records": supported + unsupported,
                "supported_references": supported,
            }
        )
    return {
        "records": records,
        "families": families,
        "planned_records": len(records),
        "supported_references": sum(counts),
        "sequence_bindings_complete": True,
        "known_provenance_overlap": False,
    }


def lineages(module, data):
    return {
        f["family_id"]: module.annotation_lineage(
            {"SS": ["Published; PMID:12345"], "RM": ["23456"]}
        )
        for f in data["families"]
    }


@pytest.mark.parametrize(
    "text,category,tools",
    [
        ("Published; PMID:12345", "published_source_unverified", []),
        ("Predicted; PFOLD", "prediction_declared", ["PFOLD"]),
        (
            "Published; RNAfold; PMID:12345",
            "mixed_prediction_and_source_claim",
            ["RNAfold"],
        ),
        ("NMR; curator", "experimental_claim_unverified", []),
        ("RNAalifold; curator", "prediction_declared", ["RNAalifold"]),
        ("curated manually", "unknown", []),
    ],
)
def test_citations_and_experimental_claims_never_certify_per_sequence_truth(
    module, text, category, tools
):
    result = module.annotation_lineage({"SS": [text], "RM": ["777"]})
    assert result["source_category"] == category
    assert result["declared_prediction_tools"] == tools
    assert not result["per_sequence_experiment_verified"]
    assert not result["native_control_reference_independence_certified"]
    assert result["structure_source_lines"] == [text]
    assert result["family_bibliography_pmids"] == ["777"]


def test_one_family_cannot_pass_broad_coverage_by_adding_more_homologs(module, policy):
    data = binding([50], unsupported=7)
    result = module.assess(data, lineages(module, data), policy, set())
    assert result["planned_records"] == 57 and result["unsupported_references"] == 7
    assert not result["coverage_thresholds_met"]
    assert result["readiness_failures"] == ["insufficient_supported_families"]


def test_passing_comparative_coverage_does_not_establish_experimental_independence(
    module, policy
):
    data = binding([4, 4, 4], unsupported=1)
    result = module.assess(data, lineages(module, data), policy, set())
    assert result["fresh_comparative_panel_ready"] and result["coverage_thresholds_met"]
    assert not result["independent_experimental_panel_ready"]
    assert not result["training_tool_independence_certified"]
    assert result["planned_records"] == 15 and result["supported_references"] == 12


@pytest.mark.parametrize("problem", ["sequence", "provenance", "consumed"])
def test_coverage_cannot_override_sequence_provenance_or_exposure_gate(
    module, policy, problem
):
    data = binding([4, 4, 4])
    exposed = set()
    if problem == "sequence":
        data["sequence_bindings_complete"] = False
    elif problem == "provenance":
        data["known_provenance_overlap"] = True
    else:
        exposed = {data["families"][0]["family_id"]}
    result = module.assess(data, lineages(module, data), policy, exposed)
    assert (
        result["coverage_thresholds_met"]
        and not result["fresh_comparative_panel_ready"]
    )


def test_metrics_are_not_read_or_used_for_readiness(module, policy):
    data = binding([4, 4, 4])
    expected = module.assess(data, lineages(module, data), policy, set())
    data["model_results"] = {"helix": 0.99, "ViennaRNA": -1000}
    data["records"][0]["pair_f1"] = 0
    assert module.assess(data, lineages(module, data), policy, set()) == expected


@pytest.mark.parametrize(
    "tamper", ["duplicate", "total", "family", "status", "lineage"]
)
def test_inconsistent_reference_denominators_fail_closed(module, policy, tamper):
    data = binding([4, 4, 4])
    sources = lineages(module, data)
    if tamper == "duplicate":
        data["records"][1]["id"] = data["records"][0]["id"]
    elif tamper == "total":
        data["planned_records"] += 1
    elif tamper == "family":
        data["families"][0]["supported_references"] += 1
    elif tamper == "status":
        data["records"][0]["reference_status"] = "missing"
    else:
        sources.pop(next(iter(sources)))
    with pytest.raises(ValueError):
        module.assess(data, sources, policy, set())


@pytest.mark.parametrize("value", [True, 0, -1, 3.0, "3"])
def test_thresholds_are_positive_integers_not_booleans(module, policy, value):
    policy["minimum_supported_families"] = value
    with pytest.raises(ValueError):
        module.validate_policy(policy)


@pytest.fixture
def retained_run(module, policy, tmp_path, monkeypatch):
    from rnastable.native_journal import atomic_json

    for name in (
        "evaluate_prospective_panel.py",
        "download_prospective_evidence.py",
        "prepare_prospective_family_panel.py",
    ):
        path = tmp_path / "scripts" / name
        path.parent.mkdir(exist_ok=True)
        path.write_text("# fixture source\n")
    policy_path = tmp_path / "policy.json"
    atomic_json(policy_path, policy)
    source = tmp_path / "binding"
    source.mkdir()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    data = binding([4, 4, 4], unsupported=1)
    files = {}
    for f in data["families"]:
        name = f["family_id"]
        path = evidence / (name + ".sto")
        path.write_text(
            f"# STOCKHOLM 1.0\n#=GF AC {name}\n#=GF SS Published; PMID:12345\na GCAU\n#=GC SS_cons <..>\n//\n"
        )
        files[str(path)] = module.digest(path.read_bytes())
    summary = {"run_dir": str(source), "binding": data}
    atomic_json(source / "summary.json", summary)
    atomic_json(
        source / "manifest.json",
        {"evidence_run": str(evidence), "source_sha256": files},
    )
    monkeypatch.setattr(
        module, "audit_binding", lambda path: json.loads(Path(path).read_text())
    )
    monkeypatch.setattr(module, "collect_known_exposures", lambda root: [])
    result = module.build(tmp_path, [source / "summary.json"], policy_path)
    return module, Path(result["run_dir"]), source, evidence


def test_replay_uses_saved_exposures_without_reading_live_ledger(
    retained_run, monkeypatch
):
    module, run, _, _ = retained_run

    def forbidden(*args, **kwargs):
        raise AssertionError("No live exposure access allowed during replay")

    monkeypatch.setattr(module, "collect_known_exposures", forbidden)
    result = module.audit(run / "summary.json")
    assert result["panels"][0]["fresh_comparative_panel_ready"]
    assert not result["inference_performed"] and not result["new_exposure_recorded"]
    assert not list(run.rglob("exposures"))
    assert not list(run.rglob("native_journal"))


@pytest.mark.parametrize("tamper", ["source", "policy", "exposure", "summary", "code"])
def test_replay_rejects_changed_source_plan_exposure_outcomes_and_code(
    retained_run, tamper
):
    module, run, source, evidence = retained_run
    if tamper == "source":
        target = next(evidence.glob("*.sto"))
    elif tamper == "policy":
        target = run / "policy.json"
    elif tamper == "exposure":
        target = run / "exposure.json"
    elif tamper == "code":
        target = run.parents[2] / "scripts/evaluate_prospective_panel.py"
    else:
        target = run / "summary.json"
    target.write_text(target.read_text() + "\n")
    if tamper == "summary":
        data = json.loads(target.read_text())
        data["panels"][0]["supported_references"] += 1
        target.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        module.audit(run / "summary.json")
