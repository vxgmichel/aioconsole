import asyncio
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
    yield from asyncio.start_server(callback, host, port, loop=loop)


def main(port=8000):
    loop = asyncio.get_event_loop()
    coro = start_interactive_server(code.AsynchronousConsole, '', port)
    loop.server = loop.run_until_complete(coro)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])
