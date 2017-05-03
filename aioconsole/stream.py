"""Provide an asychronous equivalent to *input*."""

import io
import sys
import asyncio

from . import compat


class StandardStreamReaderProtocol(asyncio.StreamReaderProtocol):
    def connection_made(self, transport):
        if self._stream_reader._transport is not None:
            return
        super().connection_made(transport)


class StandardStreamReader(asyncio.StreamReader):
    if compat.PY34:
        def __del__(self):
            if self._transport and self._transport.get_extra_info('pipe').fileno() < 3:
                self._transport._pipe = None


class StandardStreamWriter(asyncio.StreamWriter):
    if compat.PY34:
        def __del__(self):
            if self._transport and self._transport.get_extra_info('pipe').fileno() < 3:
                self._transport._pipe = None

    def write(self, data):
        if isinstance(data, str):
            data = data.encode()
        super().write(data)


class NonFileStreamReader:

    def __init__(self, stream, *, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self.loop = loop
        self.stream = stream
        self.eof = False

    def at_eof(self):
        return self.eof

    @asyncio.coroutine
    def readline(self):
        data = yield from self.loop.run_in_executor(None, self.stream.readline)
        if isinstance(data, str):
            data = data.encode()
        self.eof = not data
        return data

    @asyncio.coroutine
    def read(self, n=-1):
        data = yield from self.loop.run_in_executor(None, self.stream.read, n)
        if isinstance(data, str):
            data = data.encode()
        self.eof = not data
        return data

    if compat.PY35:
        @asyncio.coroutine
        def __aiter__(self):
            return self

        @asyncio.coroutine
        def __anext__(self):
            val = yield from self.readline()
            if val == b'':
                raise StopAsyncIteration
            return val


class NonFileStreamWriter:

    def __init__(self, stream, *, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self.loop = loop
        self.stream = stream

    def write(self, data):
        if isinstance(data, bytes):
            data = data.decode()
        self.stream.write(data)

    @asyncio.coroutine
    def drain(self):
        try:
            flush = self.stream.flush
        except AttributeError:
            pass
        else:
            yield from self.loop.run_in_executor(None, flush)


@asyncio.coroutine
def open_pipe_connection(pipe_in, pipe_out, *, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()
    reader = StandardStreamReader(loop=loop)
    protocol = StandardStreamReaderProtocol(reader, loop=loop)
    yield from loop.connect_read_pipe(lambda: protocol, pipe_in)
    write_connect = loop.connect_write_pipe(lambda: protocol, pipe_out)
    transport, _ = yield from write_connect
    loop.remove_reader(transport.get_extra_info('pipe').fileno())
    writer = StandardStreamWriter(transport, protocol, reader, loop)
    return reader, writer


@asyncio.coroutine
def create_standard_streams(stdin, stdout, loop):
    try:
        sys.stdin.fileno(), sys.stdout.fileno()
    except io.UnsupportedOperation:
        reader = NonFileStreamReader(stdin, loop=loop)
        writer = NonFileStreamWriter(stdout, loop=loop)
    else:
        future = open_pipe_connection(stdin, stdout, loop=loop)
        reader, writer = yield from future
    return reader, writer


@asyncio.coroutine
def get_standard_streams(*, cache={}, use_stderr=False, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()
    stdin, stdout = sys.stdin, sys.stderr if use_stderr else sys.stdout
    key = loop, stdin, stdout
    if cache.get(key) is None:
        connection = create_standard_streams(stdin, stdout, loop=loop)
        cache[key] = yield from connection
    return cache[key]


@asyncio.coroutine
def ainput(prompt=None, *, loop=None):
    """Asynchronous equivalent to *input*."""
    if loop is None:
        loop = asyncio.get_event_loop()
    if prompt is None:
        prompt = ''
    # Get streams
    reader, writer = yield from get_standard_streams(loop=loop)
    # Write prompt
    writer.write(prompt.encode())
    yield from writer.drain()
    # Get data
    data = (yield from reader.readline()).decode()
    # Return or raise EOF
    if not data.endswith('\n'):
            raise EOFError()
    return data
