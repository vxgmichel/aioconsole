
import os
import sys
import runpy
import argparse

from . import events
from . import server


def parse_args(args):
    parser = argparse.ArgumentParser(prog='apython', description='''\
Run the given python file or module with a modified asyncio policy replacing
the default event loop with an interactive loop.
If no argument is given, it simply runs an asynchronous python console.
''')
    parser.add_argument('--serve', '-s', metavar='[HOST:]PORT',
                        help='serve a console on the given interface instead')
    parser.add_argument('--module', '-m', dest='module', action='store_true',
                        help='run a python module')
    parser.add_argument('filename', metavar='FILE', nargs='?',
                        help='python file or module to run')
    parser.add_argument('args', metavar='ARGS', nargs=argparse.REMAINDER,
                        help='extra arguments')
    namespace = parser.parse_args(args)
    if namespace.module and not namespace.filename:
        parser.error('A python module is required.')
    if namespace.serve is not None:
        namespace.serve = server.parse_server(namespace.serve, parser)
    return namespace


def run_apython(args=None):
    if args is None:
        args = sys.argv[1:]
    namespace = parse_args(args)

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
