import json
from pathlib import Path
import selectors
import signal
import subprocess
import sys
from rnastable.cli import ROOT


def command(tmp_path,code):
    return [sys.executable,str(ROOT/'scripts/log_command.py'),'--log-dir',str(tmp_path),
            sys.executable,'-u','-c',code]


def test_streams_output_before_child_finishes_and_records_start(tmp_path):
    process=subprocess.Popen(command(tmp_path,"print('READY',flush=True); input(); print('DONE')"),
                             stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
        assert selector.select(timeout=5),'Progress should stream before command completion'
        assert process.stdout.readline()=='READY\n'
        assert process.poll() is None
        start=json.loads((tmp_path/'command_starts.jsonl').read_text())
        assert start['command'][-1].startswith("print('READY'")
        stdout,stderr=process.communicate('\n',timeout=5)
        assert process.returncode==0 and stdout=='DONE\n' and stderr==''
        end=json.loads((tmp_path/'commands.jsonl').read_text())
        assert end['command_id']==start['command_id']
        assert end['output']=='READY\nDONE\n' and end['returncode']==0
    finally:
        if process.poll() is None:process.kill();process.wait()


def test_nonzero_and_missing_command_recorded(tmp_path):
    result=subprocess.run(command(tmp_path,"import sys; print('test-only failure'); sys.exit(7)"),capture_output=True,text=True)
    assert result.returncode==7
    assert json.loads((tmp_path/'commands.jsonl').read_text())['returncode']==7
    result=subprocess.run([sys.executable,str(ROOT/'scripts/log_command.py'),'--log-dir',str(tmp_path),
                           str(tmp_path/'missing-executable')],capture_output=True,text=True)
    assert result.returncode==127
    last=json.loads((tmp_path/'commands.jsonl').read_text().splitlines()[-1])
    assert 'FileNotFoundError' in last['output'] and last['returncode']==127


def test_interrupt_is_forwarded_and_recorded(tmp_path):
    process=subprocess.Popen(command(tmp_path,"print('READY',flush=True); input()"),
                             stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
        assert selector.select(timeout=5)
        assert process.stdout.readline()=='READY\n'
        process.send_signal(signal.SIGINT)
        process.communicate(timeout=8)
        assert process.returncode==130
        end=json.loads((tmp_path/'commands.jsonl').read_text())
        assert end['interrupted'] is True and end['returncode']==130
    finally:
        if process.poll() is None:process.kill();process.wait()
