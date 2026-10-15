"""Preserve earlier reports and create unique, auditable run directories."""
import csv
import datetime
import hashlib
import json
from pathlib import Path
import shutil


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')


def sha256(sequence):
    return hashlib.sha256(sequence.encode()).hexdigest()


def write_artifact(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.parent/'archive'/timestamp()/path.name
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
    path.write_text(content)


def publish(root, name, summary, rows, fields, report):
    root = Path(root)
    write_artifact(root/'results'/f'{name}_summary.json', json.dumps(summary, indent=2, allow_nan=False)+'\n')
    import io
    text = io.StringIO(newline='')
    writer = csv.DictWriter(text, fieldnames=fields, extrasaction='ignore')
    writer.writeheader(); writer.writerows(rows)
    write_artifact(root/'results'/f'{name}.csv', text.getvalue())
    write_artifact(root/'reports'/f'{name}_report.md', report)
