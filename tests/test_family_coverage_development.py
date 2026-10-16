"""Coverage-led development selection records the earlier annotation failure."""

import importlib.util
from pathlib import Path

from rnastable.prospective_binding import parse_stockholm


def test_coverage_filter_is_explicit_and_preserves_excluded_decisions(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "coverage_development_test",
        root / "scripts/derive_coverage_development_dataset.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    alignment = parse_stockholm(
        b"# STOCKHOLM 1.0\n#=GF AC RF00022\na --ACGU\nb ACGUGG\n"
        b"#=GC SS_cons <<..>>\n//\n", "RF00022"
    )
    policy = {"minimum_length": 1, "maximum_length": 100,
              "sequence_similarity_threshold": 0.8,
              "train_candidate_cap_per_family": 12}
    selected, decisions = module.coverage_selection(alignment, [], policy)
    assert [r["id"] for r in selected] == ["RF00022:b"]
    assert decisions[0]["reason"] == "incomplete_consensus_coverage"
    assert decisions[0]["missing_paired_columns"] == 2
    assert decisions[1]["reason"] == "selected_after_declared_coverage_filter"
