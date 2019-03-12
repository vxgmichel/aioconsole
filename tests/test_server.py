import io
import asyncio

import pytest

from aioconsole import compat
from aioconsole.server import start_console_server, print_server


@pytest.mark.asyncio
@asyncio.coroutine
def test_server(event_loop):
    server = yield from start_console_server(
        host="127.0.0.1", port=0, banner='test')
    address = server.sockets[0].getsockname()

    stream = io.StringIO()
    print_server(server, "test console", file=stream)
    expected = "The test console is being served on 127.0.0.1:{}\n"
    assert stream.getvalue() == expected.format(address[1])

    reader, writer = yield from asyncio.open_connection(*address)
    assert (yield from reader.readline()) == b'test\n'
    writer.write(b'1+1\n')
    assert (yield from reader.readline()) == b'>>> 2\n'
    writer.write_eof()
    assert (yield from reader.readline()) == b'>>> \n'
    writer.close()
    if compat.PY37:
        yield from writer.wait_closed()
    server.close()
    yield from server.wait_closed()


@pytest.mark.asyncio
@asyncio.coroutine
def test_uds_server(event_loop, tmpdir):
    path = str(tmpdir / "test.uds")
    server = yield from start_console_server(path=path, banner='test')

    stream = io.StringIO()
    print_server(server, "test console", file=stream)
    expected = "The test console is being served on {}\n"
    assert stream.getvalue() == expected.format(path)

    address = server.sockets[0].getsockname()
    reader, writer = yield from asyncio.open_unix_connection(address)
    assert (yield from reader.readline()) == b'test\n'
    writer.write(b'1+1\n')
    assert (yield from reader.readline()) == b'>>> 2\n'
    writer.write_eof()
    assert (yield from reader.readline()) == b'>>> \n'
    writer.close()
    if compat.PY37:
        yield from writer.wait_closed()
    server.close()
    yield from server.wait_closed()


@pytest.mark.asyncio
@asyncio.coroutine
def test_invalid_server(event_loop):
    with pytest.raises(ValueError):
        yield from start_console_server()
    with pytest.raises(ValueError):
        yield from start_console_server(path="uds", port=0)
