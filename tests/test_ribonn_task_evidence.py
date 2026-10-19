"""Unit tests for RiboNN per-task accuracy and overlap evidence."""
import json
import math
import zipfile
from pathlib import Path

import pytest

from rnastable.ribonn_task_evidence import (
    agreement, overlap_check, per_task_metrics, rank_tasks, read_sheet_columns,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/"configs/ribonn_task_evidence_v1_2026-10-19.json"


def test_config_is_gated_and_selects_nothing():
    config = json.loads(CONFIG.read_text())
    for flag in ("task_selected", "floors_frozen", "gate_amended",
                 "new_sequence_scoring_enabled", "expression_candidate_design_enabled",
                 "stage3_ready"):
        assert config[flag] is False
    assert any("No task is selected" in c for c in config["no_claim_permitted"])


def test_config_does_not_retain_copyrighted_sources():
    config = json.loads(CONFIG.read_text())
    assert "NOT copied into this repository" in config["sources_not_retained"]["policy"]
    for entry in config["sources"]:
        assert len(entry["sha256"]) == 64 and entry["bytes"] > 0


def test_config_records_the_held_out_assumption_and_its_failure_mode():
    assumption = json.loads(CONFIG.read_text())["method"]["held_out_assumption"]
    assert assumption["not_confirmed"]
    assert "discarded rather than adjusted" in assumption["if_violated"]


def test_agreement_is_exact_for_a_perfect_fit():
    xs = [1.0, 2.0, 3.0, 4.0]
    out = agreement(xs, xs)
    assert out["n"] == 4
    assert out["pearson"] == pytest.approx(1.0)
    assert out["r2"] == pytest.approx(1.0)


def test_agreement_separates_pearson_from_r2_under_scale_error():
    observed = [1.0, 2.0, 3.0, 4.0]
    predicted = [2.0, 4.0, 6.0, 8.0]          # perfectly correlated, wrong scale
    out = agreement(predicted, observed)
    assert out["pearson_squared"] == pytest.approx(1.0)
    assert out["r2"] < 0.0                     # coefficient of determination punishes the bias


def test_agreement_rejects_degenerate_and_short_series():
    with pytest.raises(ValueError, match="at least two"):
        agreement([1.0], [1.0])
    with pytest.raises(ValueError, match="equal-length"):
        agreement([1.0, 2.0], [1.0])
    with pytest.raises(ValueError, match="Degenerate"):
        agreement([1.0, 1.0, 1.0], [1.0, 2.0, 3.0])


def measured_predicted(n=40, noise=0.0):
    measured = {"TE_A549": {}, "TE_Lonely": {}}
    predicted = {"predicted_TE_A549": {}, "predicted_TE_Absent": {}}
    for i in range(n):
        key = f"tx{i}"
        measured["TE_A549"][key] = str(float(i))
        predicted["predicted_TE_A549"][key] = str(float(i)+noise*(i % 2))
        measured["TE_Lonely"][key] = str(float(i))
    return measured, predicted


def test_per_task_metrics_pairs_only_tasks_present_in_both():
    measured, predicted = measured_predicted()
    rows = per_task_metrics(measured, predicted, minimum_n=10)
    assert [r["task"] for r in rows] == ["A549"]
    assert rows[0]["n"] == 40
    assert rows[0]["pearson"] == pytest.approx(1.0)


def test_per_task_metrics_honours_minimum_n():
    measured, predicted = measured_predicted(n=5)
    with pytest.raises(ValueError, match="No task could be evaluated"):
        per_task_metrics(measured, predicted, minimum_n=30)


def test_per_task_metrics_skips_blank_and_nonnumeric_cells():
    measured = {"TE_X": {f"tx{i}": str(float(i)) for i in range(40)}}
    predicted = {"predicted_TE_X": {f"tx{i}": str(float(i)) for i in range(40)}}
    measured["TE_X"]["tx0"] = ""
    predicted["predicted_TE_X"]["tx1"] = "NA"
    rows = per_task_metrics(measured, predicted, minimum_n=10)
    assert rows[0]["n"] == 38


def test_per_task_metrics_rejects_an_invalid_minimum():
    with pytest.raises(ValueError, match="at least 2"):
        per_task_metrics({}, {}, minimum_n=1)


def test_rank_tasks_locates_position_and_median():
    rows = [{"task": "high", "n": 100, "pearson": 0.9, "pearson_squared": 0.81, "r2": 0.8},
            {"task": "mid", "n": 100, "pearson": 0.6, "pearson_squared": 0.36, "r2": 0.3},
            {"task": "low", "n": 100, "pearson": 0.2, "pearson_squared": 0.04, "r2": 0.1}]
    out = rank_tasks(rows, ["high", "low", "missing"])
    assert out["high"]["rank_by_pearson"] == 1 and out["high"]["above_median"] is True
    assert out["low"]["rank_by_pearson"] == 3 and out["low"]["above_median"] is False
    assert out["missing"] == {"present": False}
    assert out["high"]["of_tasks"] == 3


def test_overlap_check_reports_matches_and_distinct_symbols():
    out = overlap_check(["LUC7L", "SAMD11", "GFPT1", "", None], ["luc", "luciferase", "GFP"])
    assert out["matches"]["luc"] == ["LUC7L"]
    assert out["matches"]["luciferase"] == []
    assert out["matches"]["GFP"] == ["GFPT1"]
    assert out["distinct_symbols"] == 3
    assert "out of distribution" in out["note"]


def build_xlsx(path, sheet_name, header, rows):
    """Minimal workbook carrying only what the streaming reader consumes."""
    strings = []
    def index(value):
        if value not in strings:
            strings.append(value)
        return strings.index(value)
    body = []
    cells = "".join(
        f'<c r="{chr(65+i)}1" t="s"><v>{index(name)}</v></c>' for i, name in enumerate(header))
    body.append(f"<row r=\"1\">{cells}</row>")
    for n, row in enumerate(rows, start=2):
        parts = []
        for i, value in enumerate(row):
            ref = f"{chr(65+i)}{n}"
            if isinstance(value, str):
                parts.append(f'<c r="{ref}" t="s"><v>{index(value)}</v></c>')
            else:
                parts.append(f'<c r="{ref}"><v>{value}</v></c>')
        body.append(f"<row r=\"{n}\">{''.join(parts)}</row>")
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rns = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml",
                   f'<workbook {ns} {rns}><sheets>'
                   f'<sheet name="{sheet_name}" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/sharedStrings.xml",
                   f'<sst {ns}>' + "".join(f"<si><t>{s}</t></si>" for s in strings) + "</sst>")
        z.writestr("xl/worksheets/sheet1.xml",
                   f'<worksheet {ns}><sheetData>' + "".join(body) + "</sheetData></worksheet>")
    return path


def test_read_sheet_columns_streams_selected_columns(tmp_path):
    path = build_xlsx(tmp_path/"t.xlsx", "Human",
                      ["tx_id", "SYMBOL", "TE_A549", "tx_sequence"],
                      [["tx1", "AAA", 1.5, "ACGU"], ["tx2", "BBB", 2.5, "ACGU"]])
    columns, rows = read_sheet_columns(
        path, "Human", lambda n: n in ("tx_id", "SYMBOL", "TE_A549"))
    assert rows == 2
    assert columns["TE_A549"] == {"tx1": "1.5", "tx2": "2.5"}
    assert columns["SYMBOL"] == {"tx1": "AAA", "tx2": "BBB"}
    assert "tx_sequence" not in columns          # skipped, so sequences are never held


def test_read_sheet_columns_requires_the_key_column(tmp_path):
    path = build_xlsx(tmp_path/"n.xlsx", "Human", ["gene", "TE_A549"], [["g1", 1.0]])
    with pytest.raises(ValueError, match="no tx_id column"):
        read_sheet_columns(path, "Human", lambda n: True)


def test_read_sheet_columns_rejects_an_unknown_sheet(tmp_path):
    path = build_xlsx(tmp_path/"s.xlsx", "Human", ["tx_id"], [["tx1"]])
    with pytest.raises(ValueError, match="Sheet not found"):
        read_sheet_columns(path, "Mouse", lambda n: True)
