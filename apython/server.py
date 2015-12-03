"""Serve the python console using socket communication."""

import asyncio
import argparse
from . import code


@asyncio.coroutine
def handle_connect(reader, writer, factory):
    streams = reader, writer
    cli = factory(streams=streams)
    yield from cli.interact(stop=False, handle_sigint=False)
    writer.close()


@asyncio.coroutine
def start_interactive_server(factory, host='', port=8000, *, loop=None):
    callback = lambda reader, writer: handle_connect(reader, writer, factory)
    server = yield from asyncio.start_server(callback, host, port, loop=loop)
    return server


def run(port=8000):
    loop = asyncio.get_event_loop()
    coro = start_interactive_server(code.AsynchronousConsole, '', port)
    loop.server = loop.run_until_complete(coro)
    print('The python console is being served on port {} ...'.format(port))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Serve the python console.")
    parser.add_argument(
        'port',
        metavar='PORT',
        type=int,
        default=8000,
        help='default port is 8000')
    namespace = parser.parse_args(args)
    return namespace.port


def main(args=None):
    run(parse_args(args))

if __name__ == '__main__':
    main()
