"""Serve the python console using socket communication."""

import asyncio
import socket

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
                             host=None, port=None, path=None,
                             banner=None, *, loop=None):
    callback = lambda reader, writer: handle_connect(
        reader, writer, factory, banner)
    if (port is not None) == (path is not None):
        raise ValueError("Either a TCP port or a UDS path should be provided")
    if path:
        server = yield from asyncio.start_unix_server(callback, path, loop=loop)
    else:
        # Override asyncio behavior (i.e serve on all interfaces by default)
        host = host or "localhost"
        server = yield from asyncio.start_server(callback, host, port, loop=loop)
    return server


@asyncio.coroutine
def start_console_server(host=None, port=None, path=None,
                         locals=None, filename="<console>", banner=None,
                         prompt_control=None, *, loop=None):
    factory = lambda streams: code.AsynchronousConsole(
        streams, locals, filename, prompt_control=prompt_control)
    server = yield from start_interactive_server(
        factory,
        host=host,
        port=port,
        path=path,
        banner=banner,
        loop=loop)
    return server


def print_server(server, name='console'):
    interface = server.sockets[0].getsockname()
    if server.sockets[0].family != socket.AF_UNIX:
        interface = '{}:{}'.format(*interface)
    print('The {} is being served on {}'.format(name, interface))


def run(host=None, port=None, path=None):
    loop = asyncio.get_event_loop()
    coro = start_interactive_server(host=host, port=port, path=path)
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
