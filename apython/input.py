"""Provide an asychronous equivalent to *input*."""

import io
import sys
import asyncio

from . import compat


@asyncio.coroutine
def ainput(prompt=None, *, loop=None):
    """Asynchronous equivalent to *input*."""
    if loop is None:
        loop = asyncio.get_event_loop()
    if prompt is None:
        prompt = ''
    try:
        sys.stdin.fileno()
    except io.UnsupportedOperation:
        future = loop.run_in_executor(None, input, prompt)
    else:
        future = StdinPipe.read(loop=loop)
        print(prompt, end='', flush=True)
    return (yield from future)


class SafeStreamReaderProtocol(asyncio.StreamReaderProtocol):
    def connection_made(self, transport):
        if self._stream_reader._transport is not None:
            return
        super().connection_made(transport)


class SafeStreamReader(asyncio.StreamReader):
    if compat.PY34:
        def __del__(self):
            if self._transport and self._transport._fileno < 3:
                self._transport._pipe = None


class SafeStreamWriter(asyncio.StreamWriter):
    if compat.PY34:
        def __del__(self):
            if self._transport and self._transport._fileno < 3:
                self._transport._pipe = None

    def write(self, data):
        if isinstance(data, str):
            data = data.encode()
        super().write(data)


@asyncio.coroutine
def open_pipe_connection(pipe_in, pipe_out, *, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()
    reader = SafeStreamReader(loop=loop)
    protocol = SafeStreamReaderProtocol(reader, loop=loop)
    yield from loop.connect_read_pipe(lambda: protocol, pipe_in)
    write_connect = loop.connect_write_pipe(lambda: protocol, pipe_out)
    transport, _ = yield from write_connect
    loop.remove_reader(transport._fileno)
    writer = SafeStreamWriter(transport, protocol, reader, loop)
    return reader, writer


@asyncio.coroutine
def get_standard_streams(*, cache={}, use_stderr=False, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()
    if cache.get(loop) is None:
        out = sys.stderr if use_stderr else sys.stdout
        connection = open_pipe_connection(sys.stdin, out, loop=loop)
        cache[loop] = yield from connection
    return cache[loop]


@asyncio.coroutine
def ainput(prompt=None, *, loop=None):
    """Asynchronous equivalent to *input*."""
    if loop is None:
        loop = asyncio.get_event_loop()
    if prompt is None:
        prompt = ''
    try:
        sys.stdin.fileno()
    except io.UnsupportedOperation:
        future = loop.run_in_executor(None, input, prompt)
    else:
        reader, writer = yield from get_standard_streams(loop=loop)
        future = reader.readline()
        writer.write(prompt.encode())
        yield from writer.drain()
    data = (yield from future).decode()
    if not data.endswith('\n'):
            raise EOFError()
    return data


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(ainput(">>> "))
    print(repr(result))
    result = loop.run_until_complete(ainput(">>> "))
    print(repr(result))
    loop.close()
