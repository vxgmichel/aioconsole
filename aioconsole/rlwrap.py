"""Provide a readline wrapper to control a subprocess."""

import sys
import ctypes
import signal
import builtins
import subprocess

ZERO_WIDTH_SPACE = '\u200b'


def rlwrap_process(args=None, use_stderr=False,
                   prompt_control=ZERO_WIDTH_SPACE):
    # Get args
    if args is None:
        args = sys.argv[1:]
    # Piping
    kwargs = {'stderr' if use_stderr else 'stdout': subprocess.PIPE}
    # Start process
    process = subprocess.Popen(
        args,
        bufsize=0,
        universal_newlines=True,
        stdin=subprocess.PIPE,
        **kwargs)
    # Readline wrapping
    return _rlwrap(process, use_stderr, prompt_control)


def _rlwrap(process, use_stderr=False,
            prompt_control=ZERO_WIDTH_SPACE):
    # Get destination
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
    return process.returncode


def wait_for_prompt(src, dest, prompt_control, current='\n'):

    # Read exactly one byte
    def read_one():
        value = src.read(1)
        if value:
            return value
        raise EOFError

    while True:
        # Prompt detection
        if current.endswith('\n'):
            current = read_one()
            if current.startswith(prompt_control):
                current += read_one()
                while current[-1] not in (prompt_control, '\n'):
                    current += read_one()
                if current.endswith(prompt_control):
                    return current[1:-1]
        # Regular read
        else:
            current = read_one()
        # Write and flush
        dest.write(current)
        dest.flush()


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
    if sys.platform == 'darwin':
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
        return input(prompt)
    # Call readline
    call_readline = api.PyOS_Readline
    call_readline.restype = ctypes.c_char_p
    result = call_readline(fin, ferr, prompt.encode())
    # Decode result
    if len(result) == 0:
        raise EOFError
    return result.decode().rstrip('\n')
