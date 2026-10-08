#!/usr/bin/env python3
"""Stream command output and record starts, completion, interruption and failures."""
import argparse
import datetime
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def append(path, value):
    with path.open('a') as stream:
        stream.write(json.dumps(value)+'\n')
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log-dir',type=Path,default=Path(__file__).resolve().parents[1]/'reports')
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    command=args.command
    if command and command[0]=='--':command=command[1:]
    if not command:parser.error('A command is required')
    args.log_dir.mkdir(parents=True,exist_ok=True)
    identifier=uuid.uuid4().hex
    started=utc();begin=time.monotonic()
    append(args.log_dir/'command_starts.jsonl',{'utc':started,'command':command,'command_id':identifier,
                                              'cwd':str(Path.cwd()),'logger_pid':os.getpid()})
    output=[];interrupted=False
    try:
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                 text=True,bufsize=1,start_new_session=True)
    except OSError as error:
        line=f'{type(error).__name__}: {error}\n'
        print(line,end='',file=sys.stderr,flush=True);output.append(line);code=127
    else:
        try:
            for line in process.stdout:
                output.append(line);print(line,end='',flush=True)
            code=process.wait()
        except KeyboardInterrupt:
            interrupted=True
            # Give the CLI time to clean up its separately grouped fold workers.
            try:os.killpg(process.pid,signal.SIGINT)
            except ProcessLookupError:pass
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                process.wait()
            remaining=process.stdout.read()
            if remaining:output.append(remaining);print(remaining,end='',flush=True)
            code=130
        finally:
            process.stdout.close()
    append(args.log_dir/'commands.jsonl',{'utc':utc(),'started_utc':started,'command_id':identifier,
           'command':command,'returncode':code,'output':''.join(output),
           'wall_seconds':time.monotonic()-begin,'interrupted':interrupted,'cwd':str(Path.cwd())})
    return code if code>=0 else 128-code


if __name__=='__main__':sys.exit(main())
