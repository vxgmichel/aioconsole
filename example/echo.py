import asyncio
import collections


@asyncio.coroutine
def handle_echo(reader, writer):
    loop = asyncio.get_event_loop()
    data = yield from reader.read(100)
    message = data.decode()
    addr = writer.get_extra_info('peername')
    loop.history[addr[0]].append(message.strip())
    writer.write(data)
    yield from writer.drain()
    writer.close()


def main():
    loop = asyncio.get_event_loop()
    loop.history = collections.defaultdict(list)
    coro = asyncio.start_server(handle_echo, '0.0.0.0', 8888, loop=loop)
    loop.server = loop.run_until_complete(coro)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
