"""Provide the apython script."""

import os
import sys
import ast
import runpy
import argparse

from . import events
from . import server
from . import rlwrap

DESCRIPTION = """\
Run the given python file or module with a modified asyncio policy replacing
the default event loop with an interactive loop.
If no argument is given, it simply runs an asynchronous python console."""

USAGE = """\
usage: apython [-h] [--serve [HOST:] PORT] [--no-readline]
               [--banner BANNER] [--locals LOCALS]
               [-m MODULE | FILE] ...
""".split('usage: ')[1]


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        prog='apython',
        description=DESCRIPTION,
        usage=USAGE)

    # Options

    parser.add_argument(
        '--serve', '-s', metavar='[HOST:] PORT',
        help='serve a console on the given interface instead')
    parser.add_argument(
        '--no-readline', dest='readline', action='store_false',
        help='disable readline support')
    parser.add_argument(
        '--banner', help='provide a custom banner')
    parser.add_argument(
        '--locals', type=ast.literal_eval,
        help='provide custom locals as a dictionary')

    # Hidden option

    parser.add_argument(
        '--prompt-control', metavar='PC',
        help=argparse.SUPPRESS)

    # Input

    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        '-m', dest='module',
        help='run a python module')
    group.add_argument(
        'filename', metavar='FILE', nargs='?',
        help='python file to run')

    # Extra arguments

    parser.add_argument(
        'args', metavar='ARGS', nargs=argparse.REMAINDER,
        help='extra arguments')

    namespace = parser.parse_args(args)
    if namespace.serve is not None:
        namespace.serve = server.parse_server(namespace.serve, parser)
    return namespace


def run_apython(args=None):
    namespace = parse_args(args)

    if namespace.readline and not namespace.serve and sys.platform != 'win32':

        try:
            import readline
            import rlcompleter
        except ImportError:
            readline, rlcompleter = None, None

        if readline:
            if rlcompleter:
                readline.parse_and_bind("tab: complete")
            code = run_apython_in_subprocess(args, namespace.prompt_control)
            sys.exit(code)

    try:
        sys._argv = sys.argv
        sys._path = sys.path
        if namespace.module:
            sys.argv = [None] + namespace.args
            sys.path.insert(0, '')
            events.set_interactive_policy(
                locals=namespace.locals,
                banner=namespace.banner,
                serve=namespace.serve,
                prompt_control=namespace.prompt_control)
            runpy.run_module(namespace.module,
                             run_name='__main__',
                             alter_sys=True)
        elif namespace.filename:
            sys.argv = [None] + namespace.args
            path = os.path.dirname(os.path.abspath(namespace.filename))
            sys.path.insert(0, path)
            events.set_interactive_policy(
                locals=namespace.locals,
                banner=namespace.banner,
                serve=namespace.serve,
                prompt_control=namespace.prompt_control)
            runpy.run_path(namespace.filename,
                           run_name='__main__')
        else:
            events.run_console(
                locals=namespace.locals,
                banner=namespace.banner,
                serve=namespace.serve,
                prompt_control=namespace.prompt_control)
    finally:
        sys.argv = sys._argv
        sys.path = sys._path

    sys.exit()


def run_apython_in_subprocess(args, prompt_control):
    # Get arguments
    if args is None:
        args = sys.argv[1:]
    if prompt_control is None:
        prompt_control = rlwrap.ZERO_WIDTH_SPACE

    # Check prompt control
    assert len(prompt_control) == 1

    # Create subprocess
    proc_args = [sys.executable,
                 '-m', 'aioconsole',
                 '--no-readline',
                 '--prompt-control', prompt_control]
    return rlwrap.rlwrap_process(
        proc_args + args,
        use_stderr=True,
        prompt_control=prompt_control)


if __name__ == '__main__':
    run_apython()
