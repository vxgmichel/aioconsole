import asyncio

import pytest

from aioconsole import compat
from aioconsole.server import start_console_server


@pytest.mark.asyncio
@asyncio.coroutine
def test_server(event_loop):
    server = yield from start_console_server(
        host="127.0.0.1", port=0, banner='test')
    address = server.sockets[0].getsockname()
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
