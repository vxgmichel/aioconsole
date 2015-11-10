"""Command line interface for echo server."""

import fnmatch
import asyncio
import argparse
from apython import AsynchronousCli
from .echo import main


@asyncio.coroutine
def get_history(pattern=None):
    result = ''
    history = asyncio.get_event_loop().history
    if not history:
        return "No message in the history"
    if pattern:
        history = {host: history[host]
                   for host in fnmatch.filter(history, pattern)}
    if not history:
        return "No host match the given pattern"
    for host in history:
        result += 'Host {}:\n'.format(host)
        for i, message in enumerate(history[host]):
            result += '  {}. {}\n'.format(i, message)
    return result[:-1]


def schedule_cli():
    parser = argparse.ArgumentParser(description="Display the message history")
    parser.add_argument('--pattern', '-p', type=str,
                        help='pattern to filter hostnames')
    commands = {'history': (get_history, parser)}
    cli = AsynchronousCli(commands, prog='echo')
    asyncio.async(cli.interact())


if __name__ == '__main__':
    import sys
    schedule_cli()
    main(*sys.argv[1:])
