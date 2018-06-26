"""Provide a readline wrapper to control a subprocess."""

import sys
import ctypes
import signal
import builtins
import threading
import subprocess

from . import compat

ZERO_WIDTH_SPACE = '\u200b'


def rlwrap_process(args=None, use_stderr=False,
                   prompt_control=ZERO_WIDTH_SPACE):
    # Get args
    if args is None:
        args = sys.argv[1:]
    # Start process
    process = subprocess.Popen(
        args,
        bufsize=0,
        universal_newlines=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    # Readline wrapping
    return _rlwrap(process, use_stderr, prompt_control)


def _rlwrap(process, use_stderr=False,
            prompt_control=ZERO_WIDTH_SPACE):
    # Bind unused stream
    source = process.stdout if use_stderr else process.stderr
    dest = sys.stdout if use_stderr else sys.stderr
    pipe_thread = threading.Thread(target=bind, args=(source, dest))
    pipe_thread.start()

    # Get source and destination
    source = process.stderr if use_stderr else process.stdout
    dest = sys.stderr if use_stderr else sys.stdout

    # Check prompt control
    assert len(prompt_control) == 1

    # Loop over prompts
    while process.poll() is None:
        try:
            prompt = wait_for_prompt(
                source, dest, prompt_control)
            raw = input(prompt, use_stderr=use_stderr) + '\n'
        except KeyboardInterrupt:
            process.send_signal(signal.SIGINT)
        except EOFError:
            process.stdin.close()
        else:
            process.stdin.write(raw)

    # Clean up
    dest.write(source.read())
    pipe_thread.join()
    return process.returncode


def bind(src, dest, value=True, buffersize=1):
    while value:
        value = src.read(buffersize)
        dest.write(value)
        dest.flush()


def wait_for_prompt(src, dest, prompt_control, buffersize=1):

    def read():
        value = src.read(buffersize)
        if value:
            return value
        raise EOFError

    def write(arg):
        if arg:
            dest.write(arg)
            dest.flush()

    # Wait for first prompt control
    while True:
        current = read()
        if prompt_control in current:
            break
        write(current)

    preprompt, current = current.split(prompt_control, 1)
    write(preprompt)

    # Wait for second prompt control
    while prompt_control not in current:
        current += read()

    prompt, postprompt = current.split(prompt_control, 1)
    write(postprompt)

    return prompt


def input(prompt='', use_stderr=False):
    # Use readline if possible
    try:
        import readline
    except ImportError:
        return builtins.input(prompt)
    # Use stdout
    if not use_stderr:
        return builtins.input(prompt)
    api = ctypes.pythonapi
    # Cross-platform compatibility
    if compat.platform == 'darwin':
        stdin = '__stdinp'
        stderr = '__stderrp'
    else:
        stdin = 'stdin'
        stderr = 'stderr'
    # Get standard streams
    try:
        fin = ctypes.c_void_p.in_dll(api, stdin)
        ferr = ctypes.c_void_p.in_dll(api, stderr)
    # Cygwin fallback
    except ValueError:
        return builtins.input(prompt)
    # Call readline
    call_readline = api.PyOS_Readline
    call_readline.restype = ctypes.c_char_p
    result = call_readline(fin, ferr, prompt.encode())
    # Decode result
    if len(result) == 0:
        raise EOFError
    return result.decode().rstrip('\n')
