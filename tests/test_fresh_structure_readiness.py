"""A raw graph without cWW contacts cannot fill informative-contact coverage."""

from scripts.audit_fresh_structure_readiness import assess


def test_zero_contact_graph_does_not_fill_coverage():
    names = ["RF00001", "RF00002", "RF00003", "RF00004"]
    records = [{"family_id": family, "reference_status": "ok",
                "pairs": [] if (family == names[0] and i == 0) else [[0, 3]]}
               for family in names for i in range(3)]
    reference = {"binding": {"records": records,
                              "supported_references": 12,
                              "families": [{"family_id": f, "supported_references": 3}
                                           for f in names]}}
    metadata = {f: {"rfam": {"curation": {"structure_source": "Published"}}}
                for f in names}
    result = assess(reference, metadata)
    assert result["raw_graphs_accepted"] == 12
    assert result["informative_contact_references"] == 11
    assert result["coverage_thresholds_met"] is False
    assert result["model_inference_authorized"] is False
