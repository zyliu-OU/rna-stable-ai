"""Bounded, owned CPU subprocesses with interruption cleanup."""
import os
from pathlib import Path
import signal
import subprocess
import time
from .artifacts import write_artifact


def run_batches(tasks, command_factory, workers=2, progress=lambda *args: None):
    if workers not in (1,2):
        raise ValueError('CPU batch workers must be 1 or 2')
    active={};completed={};next_index=0;last_heartbeat=time.monotonic()
    try:
        while next_index<len(tasks) or active:
            while next_index<len(tasks) and len(active)<workers:
                index=next_index;next_index+=1;task=tasks[index]
                log=Path(task['log']);write_artifact(log,'')
                stream=log.open('a')
                try:
                    process=subprocess.Popen(command_factory(task),stdout=stream,stderr=subprocess.STDOUT,
                                             start_new_session=True)
                except OSError as error:
                    stream.write(f'{type(error).__name__}: {error}\n');stream.close()
                    completed[index]=127;progress('finished',index,127,len(completed),len(tasks))
                else:
                    active[index]=(process,stream)
                    progress('started',index,process.pid,len(completed),len(tasks))
            for index,(process,stream) in list(active.items()):
                code=process.poll()
                if code is not None:
                    stream.close();del active[index];completed[index]=code
                    progress('finished',index,code,len(completed),len(tasks))
            if time.monotonic()-last_heartbeat>=30:
                progress('heartbeat',-1,None,len(completed),len(tasks));last_heartbeat=time.monotonic()
            if active:time.sleep(.2)
    except BaseException:
        for process,stream in active.values():
            try:os.killpg(process.pid,signal.SIGINT)
            except ProcessLookupError:pass
        for process,stream in active.values():
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                process.wait()
            stream.close()
        raise
    return [completed[i] for i in range(len(tasks))]
