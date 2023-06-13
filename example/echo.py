import sys
import asyncio
import collections


async def handle_echo(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    loop = asyncio.get_event_loop()
    data = await reader.readline()
    message = data.decode()
    addr = writer.get_extra_info("peername")
    loop.history[addr[0]].append(message.strip())
    writer.write(data)
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def run(host: str = "localhost", port: int = 8000):
    loop = asyncio.get_event_loop()
    loop.history = collections.defaultdict(list)
    loop.server = await asyncio.start_server(handle_echo, host, port)
    interface = "{}:{}".format(*loop.server.sockets[0].getsockname())
    print(f"The echo service is being served on {interface}")
    async with loop.server:
        await loop.server.serve_forever()


def main(args: list[str]):
    (server,) = args[1:]
    if ":" not in server:
        coro = run(port=int(server))
    else:
        host, port = server.split(":")
        coro = run(host, int(port))
    try:
        asyncio.run(coro)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main(sys.argv)
