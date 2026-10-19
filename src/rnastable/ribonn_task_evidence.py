"""Per-task accuracy and training-overlap evidence for released RiboNN tasks.

Derives per-cell-type accuracy by pairing the released measured TE table with
the released model-prediction table on transcript identity. Accuracy here is a
property of the released model on endogenous human transcripts; it says nothing
about a designed reporter construct, which is out of distribution.
"""
import math
import re
import zipfile
import xml.etree.ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
COLUMN = re.compile(r"([A-Z]+)")
MEASURED_PREFIX = "TE_"
PREDICTED_PREFIX = "predicted_TE_"


def _shared_strings(archive):
    values = []
    if "xl/sharedStrings.xml" not in archive.namelist():
        return values
    with archive.open("xl/sharedStrings.xml") as handle:
        for _, element in ET.iterparse(handle, events=("end",)):
            if element.tag == NS+"si":
                values.append("".join(t.text or "" for t in element.iter(NS+"t")))
                element.clear()
    return values


def _sheet_path(archive, sheet_name):
    workbook = archive.read("xl/workbook.xml").decode("utf-8", "replace")
    sheets = re.findall(r'<sheet name="([^"]+)"[^>]*r:id="rId(\d+)"', workbook)
    if sheet_name is not None:
        for name, rid in sheets:
            if name == sheet_name:
                candidate = f"xl/worksheets/sheet{int(rid)}.xml"
                if candidate in archive.namelist():
                    return candidate
        raise ValueError(f"Sheet not found: {sheet_name}")
    names = sorted(n for n in archive.namelist()
                   if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
    if not names:
        raise ValueError("Workbook carries no worksheet")
    return names[0]


def read_sheet_columns(path, sheet_name, keep, key_column="tx_id"):
    """Stream one sheet, returning {column: {key: value}} for kept columns.

    Streams rather than loading the workbook so the large released tables do
    not have to be held in memory with their transcript sequences.
    """
    archive = zipfile.ZipFile(path)
    shared = _shared_strings(archive)
    header, columns, rows = {}, {}, 0
    with archive.open(_sheet_path(archive, sheet_name)) as handle:
        for _, element in ET.iterparse(handle, events=("end",)):
            if element.tag != NS+"row":
                continue
            rows += 1
            cells = {}
            for cell in element.findall(NS+"c"):
                value = cell.find(NS+"v")
                if value is None or value.text is None:
                    continue
                reference = COLUMN.match(cell.get("r") or "")
                if reference is None:
                    continue
                cells[reference.group(1)] = (shared[int(value.text)]
                                             if cell.get("t") == "s" else value.text)
            if rows == 1:
                header = dict(cells)
                if key_column not in header.values():
                    raise ValueError(f"Sheet has no {key_column} column")
                columns = {name: {} for name in header.values() if keep(name)}
            else:
                key = next((v for letter, v in cells.items()
                            if header.get(letter) == key_column), None)
                if key is not None:
                    for letter, value in cells.items():
                        name = header.get(letter)
                        if name in columns:
                            columns[name][key] = value
            element.clear()
    return columns, rows-1


def agreement(predicted, observed):
    """Pearson r, its square, and the coefficient of determination."""
    n = len(predicted)
    if n < 2 or n != len(observed):
        raise ValueError("Two equal-length series of at least two points required")
    mp, mo = sum(predicted)/n, sum(observed)/n
    spo = sum((a-mp)*(b-mo) for a, b in zip(predicted, observed))
    spp = sum((a-mp)**2 for a in predicted)
    soo = sum((b-mo)**2 for b in observed)
    if spp <= 0 or soo <= 0:
        raise ValueError("Degenerate series; no variance to correlate")
    r = spo/math.sqrt(spp*soo)
    residual = sum((b-a)**2 for a, b in zip(predicted, observed))
    return {"n": n, "pearson": r, "pearson_squared": r*r, "r2": 1-residual/soo}


def per_task_metrics(measured, predicted, minimum_n=30):
    """Pair measured and predicted TE per task on transcript identity."""
    if minimum_n < 2:
        raise ValueError("minimum_n must be at least 2")
    rows = []
    for column, values in measured.items():
        if not column.startswith(MEASURED_PREFIX):
            continue
        task = column[len(MEASURED_PREFIX):]
        forecast = predicted.get(PREDICTED_PREFIX+task)
        if not forecast:
            continue
        xs, ys = [], []
        for key, observed in values.items():
            estimate = forecast.get(key)
            if estimate in (None, "") or observed in (None, ""):
                continue
            try:
                a, b = float(estimate), float(observed)
            except (TypeError, ValueError):
                continue
            if math.isfinite(a) and math.isfinite(b):
                xs.append(a)
                ys.append(b)
        if len(xs) >= minimum_n:
            rows.append({"task": task, **agreement(xs, ys)})
    if not rows:
        raise ValueError("No task could be evaluated")
    rows.sort(key=lambda row: -row["pearson"])
    return rows


def rank_tasks(rows, wanted):
    """Locate specific tasks within the per-task distribution."""
    ordered = [r["pearson"] for r in rows]
    median = sorted(ordered)[len(ordered)//2]
    index = {r["task"]: i for i, r in enumerate(rows)}
    out = {}
    for name in wanted:
        row = next((r for r in rows if r["task"] == name), None)
        if row is None:
            out[name] = {"present": False}
            continue
        out[name] = {"present": True, **row,
                     "rank_by_pearson": index[name]+1, "of_tasks": len(rows),
                     "above_median": row["pearson"] >= median}
    return out


def overlap_check(symbols, needles):
    """Gene symbols matching any needle, for a training-overlap check."""
    hits = {}
    for needle in needles:
        upper = needle.upper()
        found = sorted({s for s in symbols if s and upper in s.upper()})
        hits[needle] = found
    return {"distinct_symbols": len(set(s for s in symbols if s)),
            "matches": hits,
            "note": "Symbol matching is a screen over the released training table, not a "
                    "sequence-level search. A designed reporter absent from this table is "
                    "out of distribution, which is a separate concern from overlap."}
