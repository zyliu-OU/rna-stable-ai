"""Linux native-process supervisor that kills its isolated group when the driver dies."""
import ctypes
import os
import signal
import subprocess
import sys


def kill_owned_group(signum=None,frame=None):
    if os.getpgrp()!=os.getpid():raise RuntimeError('Refusing to terminate an unowned process group')
    os.killpg(os.getpid(),signal.SIGKILL)


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    if len(args)<3 or args[1]!='--':raise ValueError('Expected parent PID and native command')
    expected_parent=int(args[0]);command=args[2:]
    if expected_parent<1 or os.getpgrp()!=os.getpid():raise ValueError('Native supervisor requires an isolated process group and valid parent')
    signal.signal(signal.SIGTERM,kill_owned_group)
    libc=ctypes.CDLL(None,use_errno=True);prctl=libc.prctl
    prctl.argtypes=[ctypes.c_int,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong];prctl.restype=ctypes.c_int
    if prctl(1,signal.SIGTERM,0,0,0)!=0:raise OSError(ctypes.get_errno(),'Cannot establish native parent-death protection')
    # Covers a parent dying before prctl was established. No native command starts.
    if os.getppid()!=expected_parent:kill_owned_group()
    process=subprocess.Popen(command)
    try:code=process.wait()
    except BaseException:kill_owned_group();raise
    return code if code>=0 else 128-code


if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError,RuntimeError) as exc:sys.stderr.write(f'Native supervisor rejected: {exc}\n');sys.exit(125)
