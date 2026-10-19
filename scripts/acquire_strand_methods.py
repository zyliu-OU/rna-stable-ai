"""Archive the open-access article's XML as provenance for extraction audit."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13264031/fullTextXML"
    request = Request(url, headers={"User-Agent": "RNA-StableAI-reference-reproduction/1.0"})
    with urlopen(request, timeout=45) as response:
        data = response.read(10_000_001)
    if len(data) > 10_000_000 or b"<article" not in data:
        raise ValueError("Unexpected article XML response")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out = ROOT/"results/strand_methods_source_runs"/stamp
    out.mkdir(parents=True, exist_ok=False)
    (out/"article.xml").write_bytes(data)
    (out/"manifest.json").write_text(json.dumps({"source_url":url,
        "article":"PMC13264031", "sha256":hashlib.sha256(data).hexdigest(),
        "bytes":len(data),"acquired_utc":stamp},indent=2)+"\n")
    print(out/"manifest.json")


if __name__ == "__main__":
    main()
