
import sys
import runpy
import argparse

from . import events


def parse_args(args):
    parser = argparse.ArgumentParser(prog='apython', description='''\
Asynchronous python interpreter.
Run the given python file or module with the default event loop policy changed
to use an interactive event loop. If no argument is given, it runs an
asynchronous python console.''')
    parser.add_argument('-m', dest='module', action='store_true',
                        help='run a python module')
    parser.add_argument('filename', metavar='FILE', nargs='?',
                        help='python file or module to run')
    parser.add_argument('arg', metavar='ARG', nargs='*',
                        help='extra arguments')
    namespace = parser.parse_args(args)
    if namespace.module and not namespace.filename:
        parser.error('A python module is required.')
    return namespace


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    namespace = parse_args(args)

    try:
        sys._argv = sys.argv
        if namespace.module:
            sys.argv = args[1:]
            events.set_interactive_policy()
            runpy.run_module(namespace.filename,
                             run_name='__main__',
                             alter_sys=True)
        elif namespace.filename:
            sys.argv = args
            events.set_interactive_policy()
            runpy.run_path(namespace.filename,
                           run_name='__main__')
        else:
            events.run_console()
    finally:
        sys.argv = sys._argv


if __name__ == '__main__':
    main()
