#!/usr/bin/env python3
"""Execute commands, recording arguments, output and exit status."""
import datetime,json,subprocess,sys
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'reports/commands.jsonl'
command=sys.argv[1:]
r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
with p.open('a') as f:
 f.write(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':command,'returncode':r.returncode,'output':r.stdout})+'\n')
print(r.stdout,end='');sys.exit(r.returncode)
