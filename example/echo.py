import asyncio
import collections


async def handle_echo(reader, writer):
    loop = asyncio.get_event_loop()
    data = await reader.read(100)
    message = data.decode()
    addr = writer.get_extra_info('peername')
    loop.history[addr[0]].append(message.strip())
    writer.write(data)
    await writer.drain()
    writer.close()


def run(host='localhost', port=8000):
    loop = asyncio.get_event_loop()
    loop.history = collections.defaultdict(list)
    coro = asyncio.start_server(handle_echo, host, port, loop=loop)
    loop.server = loop.run_until_complete(coro)
    interface = '{}:{}'.format(*loop.server.sockets[0].getsockname())
    print('The echo service is being served on {}'.format(interface))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass


def main(args):
    server, = args[1:]
    if ':' not in server:
        return run(port=int(server))
    host, port = server.split(':')
    return run(host, int(port))


if __name__ == '__main__':
    import sys
    main(sys.argv)
