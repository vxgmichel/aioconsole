import asyncio
from . import code


@asyncio.coroutine
def handle_connect(reader, writer):
    streams = reader, writer
    yield from code.interact(streams=streams, stop=False, handle_sigint=False)
    writer.close()


def main(port=8000):
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(handle_connect, '', port)
    loop.server = loop.run_until_complete(coro)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])
