"""Provide the apython script."""

import os
import sys
import runpy
import ctypes
import signal
import argparse
import subprocess

from . import events
from . import server

DESCRIPTION = """\
Run the given python file or module with a modified asyncio policy replacing
the default event loop with an interactive loop.
If no argument is given, it simply runs an asynchronous python console."""


def parse_args(args=None):
    parser = argparse.ArgumentParser(prog='apython', description=DESCRIPTION)
    parser.add_argument(
        '--serve', '-s', metavar='[HOST:] PORT',
        help='serve a console on the given interface instead')
    parser.add_argument(
        '--module', '-m', dest='module', action='store_true',
        help='run a python module')
    parser.add_argument(
        '--no-readline', dest='readline', action='store_false',
        help='Force readline disabling')
    parser.add_argument(
        'filename', metavar='FILE', nargs='?',
        help='python file or module to run')
    parser.add_argument(
        'args', metavar='ARGS', nargs=argparse.REMAINDER,
        help='extra arguments')
    namespace = parser.parse_args(args)
    if namespace.module and not namespace.filename:
        parser.error('A python module is required.')
    if namespace.serve is not None:
        namespace.serve = server.parse_server(namespace.serve, parser)
    return namespace


def run_apython(args=None):
    namespace = parse_args(args)

    try:
        import readline
        import rlcompleter
    except ImportError:
        readline, rlcompleter = None, None

    if readline and namespace.readline and not namespace.serve:
        if rlcompleter:
            readline.parse_and_bind("tab: complete")
        code = run_apython_in_subprocess(args)
        sys.exit(code)

    try:
        sys._argv = sys.argv
        sys._path = sys.path
        if namespace.module:
            sys.argv = [None] + namespace.args
            sys.path.insert(0, '')
            events.set_interactive_policy(serve=namespace.serve)
            runpy.run_module(namespace.filename,
                             run_name='__main__',
                             alter_sys=True)
        elif namespace.filename:
            sys.argv = [None] + namespace.args
            path = os.path.dirname(os.path.abspath(namespace.filename))
            sys.path.insert(0, path)
            events.set_interactive_policy(serve=namespace.serve)
            runpy.run_path(namespace.filename,
                           run_name='__main__')
        else:
            events.run_console(serve=namespace.serve)
    finally:
        sys.argv = sys._argv
        sys.path = sys._path


def run_apython_in_subprocess(args=None):
    # Get arguments
    if args is None:
        args = sys.argv[1:]

    # Create subprocess
    proc_args = [sys.executable, '-m', 'aioconsole', '--no-readline']
    process = subprocess.Popen(
        proc_args + args,
        bufsize=0,
        universal_newlines=True,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE)

    # Loop over prompts
    while process.poll() is None:
        try:
            prompt = wait_for_prompt(process.stderr, sys.stderr)
            raw = input_with_stderr_prompt(prompt) + '\n'
        except KeyboardInterrupt:
            process.send_signal(signal.SIGINT)
        except EOFError:
            process.stdin.close()
        else:
            process.stdin.write(raw)

    # Clean up
    sys.stderr.write(process.stderr.read())
    return process.returncode


def wait_for_prompt(src, dest, targets='.>', current='\n'):

    # Read exactly one byte
    def read_one():
        value = src.read(1)
        if value:
            return value
        raise EOFError

    while True:
        # Prompt detection
        if current.endswith('\n'):
            current = reference = read_one()
            if reference in targets:
                while current.endswith(reference):
                    current += read_one()
            if len(current) > 1 and current.endswith(' '):
                return current
        # Regular read
        else:
            current = read_one()
        # Write
        dest.write(current)


def input_with_stderr_prompt(prompt=''):
    api = ctypes.pythonapi
    # Get standard streams
    try:
        fin = ctypes.c_void_p.in_dll(api, 'stdin')
        ferr = ctypes.c_void_p.in_dll(api, 'stderr')
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


if __name__ == '__main__':
    run_apython()
