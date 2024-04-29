import io
import asyncio

import pytest

from aioconsole import compat
from aioconsole.server import start_console_server, print_server


@pytest.mark.asyncio
async def test_server():
    server = await start_console_server(host="127.0.0.1", port=0, banner="test")
    address = server.sockets[0].getsockname()

    stream = io.StringIO()
    print_server(server, "test console", file=stream)
    expected = f"The test console is being served on 127.0.0.1:{address[1]}\n"
    assert stream.getvalue() == expected

    reader, writer = await asyncio.open_connection(*address)
    assert (await reader.readline()) == b"test\n"
    writer.write(b"1+1\n")
    assert (await reader.readline()) == b">>> 2\n"
    writer.write_eof()
    assert (await reader.readline()) == b">>> \n"
    writer.close()
    await writer.wait_closed()
    server.close()
    await server.wait_closed()


@pytest.mark.asyncio
async def test_uds_server(tmpdir_factory):
    path = str(tmpdir_factory.mktemp("uds") / "my_uds")

    # Not available on windows
    if compat.platform == "win32":
        with pytest.raises(ValueError):
            await start_console_server(path=path, banner="test")
        return

    server = await start_console_server(path=path, banner="test")

    stream = io.StringIO()
    print_server(server, "test console", file=stream)
    expected = f"The test console is being served on {path}\n"
    assert stream.getvalue() == expected

    address = server.sockets[0].getsockname()
    reader, writer = await asyncio.open_unix_connection(address)
    assert (await reader.readline()) == b"test\n"
    writer.write(b"1+1\n")
    assert (await reader.readline()) == b">>> 2\n"
    writer.write_eof()
    assert (await reader.readline()) == b">>> \n"
    writer.close()
    await writer.wait_closed()
    server.close()
    await server.wait_closed()


@pytest.mark.asyncio
async def test_invalid_server():
    with pytest.raises(ValueError):
        await start_console_server()
    with pytest.raises(ValueError):
        await start_console_server(path="uds", port=0)
