"""Acquire the pinned research model archive and inventory every extracted file.

The original weight license is preserved next to the archive and extraction.
No pickle is loaded or upstream program executed by this acquisition script.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT/"results/ribonn_weight_inventory_runs/20261019T041243.650769Z/summary.json"
SOURCE = ROOT/"results/four_component_source_runs/20261019T040820.389955Z/ribonn"


def main():
    info = json.loads(INVENTORY.read_text())
    entry = next(x for x in info["files"] if x["key"] == "weights.zip")
    if entry["size"] != 207395960 or entry["checksum"] != "md5:dd088ee2feffcda6ce26124a471a140f":
        raise ValueError("Pinned archive inventory changed")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = ROOT/"results/ribonn_weight_acquisition_runs"/stamp
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(SOURCE/"MODEL WEIGHTS LICENSE.txt",output/"MODEL WEIGHTS LICENSE.txt")
    partial = output/"weights.zip.partial"
    request = Request(entry["links"]["self"],headers={"User-Agent":"RNA-StableAI-fixed-input-replay/1.0"})
    md5,sha = hashlib.md5(),hashlib.sha256()
    count = 0
    with urlopen(request,timeout=60) as response, partial.open("xb") as f:
        while True:
            block = response.read(1024*1024)
            if not block: break
            count += len(block)
            if count > entry["size"]: raise ValueError("Archive exceeds pinned length")
            f.write(block); md5.update(block); sha.update(block)
    if count != entry["size"] or md5.hexdigest() != entry["checksum"].split(":")[1]:
        raise ValueError("Archive length/checksum mismatch; retained .partial for audit")
    archive = output/"weights.zip"; partial.rename(archive)
    files = []
    extracted = output/"extracted"; extracted.mkdir()
    with zipfile.ZipFile(archive) as z:
        if sum(x.file_size for x in z.infolist()) > 2_000_000_000:
            raise ValueError("Unexpected uncompressed archive size")
        for member in z.infolist():
            path = PurePosixPath(member.filename)
            mode = member.external_attr >> 16
            if path.is_absolute() or ".." in path.parts or stat.S_ISLNK(mode):
                raise ValueError("Unsafe archive member")
            if member.is_dir(): continue
            target = extracted/Path(*path.parts)
            if not target.resolve().is_relative_to(extracted.resolve()):
                raise ValueError("Archive member leaves output directory")
            target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(member) as inp,target.open("xb") as out:
                shutil.copyfileobj(inp,out)
            data = target.read_bytes()
            files.append({"path":str(target.relative_to(ROOT)),"archive_path":member.filename,
                          "bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
    summary = {"schema_version":1,"created_utc":stamp,"source_url":entry["links"]["self"],
        "archive_path":str(archive.relative_to(ROOT)),"bytes":count,"md5":md5.hexdigest(),
        "sha256":sha.hexdigest(),"license_path":str((output/"MODEL WEIGHTS LICENSE.txt").relative_to(ROOT)),
        "license_sha256":hashlib.sha256((output/"MODEL WEIGHTS LICENSE.txt").read_bytes()).hexdigest(),
        "purpose":"fixed-input pretrained research inference only; no training or candidate design",
        "files":files}
    (output/"manifest.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(output/"manifest.json",flush=True)
    print(json.dumps({"bytes":count,"sha256":sha.hexdigest(),"files":len(files)},indent=2))


if __name__ == "__main__": main()
