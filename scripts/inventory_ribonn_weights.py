"""Record upstream weight archive metadata without downloading any weights."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    url = "https://zenodo.org/api/records/17258709"
    request = Request(url, headers={"User-Agent": "RNA-StableAI-source-audit/1.0"})
    with urlopen(request, timeout=45) as response:
        raw = response.read(10_000_001)
    if len(raw) > 10_000_000:
        raise ValueError("Unexpected metadata response size")
    obj = json.loads(raw)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = ROOT/"results/ribonn_weight_inventory_runs"/stamp
    output.mkdir(parents=True, exist_ok=False)
    (output/"zenodo_record.json").write_bytes(raw)
    summary = {"record_id": obj["id"], "source_url": url,
               "metadata_sha256": hashlib.sha256(raw).hexdigest(), "files": [
                   {k:entry.get(k) for k in ("key", "size", "checksum", "links")}
                   for entry in obj["files"]],
               "weights_downloaded": False,
               "weight_license_source": "Pinned RiboNN MODEL WEIGHTS LICENSE.txt; academic/noncommercial restrictions"}
    (output/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(output/"summary.json")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
