"""Serve the python console using socket communication."""

import asyncio
import argparse

from . import code


@asyncio.coroutine
def handle_connect(reader, writer, factory, banner=None):
    streams = reader, writer
    interface = factory(streams=streams)
    yield from interface.interact(banner=banner, stop=False,
                                  handle_sigint=False)
    writer.close()


@asyncio.coroutine
def start_interactive_server(factory=code.AsynchronousConsole,
                             host='localhost', port=8000, banner=None,
                             *, loop=None):
    callback = lambda reader, writer: handle_connect(
        reader, writer, factory, banner)
    server = yield from asyncio.start_server(callback, host, port, loop=loop)
    return server


def print_server(server, name='console'):
    interface = '{}:{}'.format(*server.sockets[0].getsockname())
    print('The {} is being served on {}'.format(name, interface))


def run(host='localhost', port=8000):
    loop = asyncio.get_event_loop()
    coro = start_interactive_server(host=host, port=port)
    loop.server = loop.run_until_complete(coro)
    print_server(loop.server)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass


def parse_server(server, parser=None):
    try:
        host, port = server.split(':')
    except ValueError:
        host, port = 'localhost', server
    try:
        port = int(port)
    except (ValueError, TypeError):
        msg = "{!r} is not a valid server [HOST:]PORT".format(server)
        if not parser:
            raise ValueError(msg)
        parser.error(msg)
    return host, port


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Serve the python console.")
    parser.add_argument(
        'server',
        metavar='[HOST:]PORT',
        type=str,
        default=8000,
        help='default is localhost:8000')
    namespace = parser.parse_args(args)
    return parse_server(namespace.server, parser)
