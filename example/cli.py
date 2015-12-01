"""Command line interface for echo server."""

import fnmatch
import asyncio
import argparse
import apython
from . import echo


@asyncio.coroutine
def get_history(reader, writer, pattern=None):
    history = asyncio.get_event_loop().history
    if not history:
        return "No message in the history"
    if pattern:
        history = {host: history[host]
                   for host in fnmatch.filter(history, pattern)}
    if not history:
        return "No host match the given pattern"
    for host in history:
        writer.write('Host {}:\n'.format(host).encode())
        for i, message in enumerate(history[host]):
            writer.write('  {}. {}\n'.format(i, message).encode())


def make_cli(streams=None):
    parser = argparse.ArgumentParser(description="Display the message history")
    parser.add_argument('--pattern', '-p', type=str,
                        help='pattern to filter hostnames')
    commands = {'history': (get_history, parser)}
    return apython.AsynchronousCli(commands, streams, prog='echo')


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Run the echo server and a command line interface.")
    parser.add_argument(
        '--port',
        '-p',
        type=int,
        default=8000,
        help='port for the echo server, default is 8000')
    parser.add_argument(
        '--serve-cli',
        metavar='PORT',
        type=int,
        help='serve the command line interface on the given port '
        'instead of using the standard streams')
    namespace = parser.parse_args(args)
    return namespace.port, namespace.serve_cli


def main(args=None):
    port, serve_cli = parse_args(args)
    if not serve_cli:
        asyncio.async(make_cli().interact())
    else:
        coro = apython.start_interactive_server(make_cli, '', serve_cli)
        asyncio.get_event_loop().run_until_complete(coro)
        msg = 'A command line interface is being served on port {} ...'
        print(msg.format(serve_cli))
    return echo.main(port)

if __name__ == '__main__':
    main()
