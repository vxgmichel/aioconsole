"""Provide an asychronous equivalent to *input*."""

import sys
import asyncio

from . import compat


def protect_standard_streams(stream):
    if stream._transport is None:
        return
    try:
        fileno = stream._transport.get_extra_info('pipe').fileno()
    except (ValueError, OSError):
        return
    if fileno < 3:
        stream._transport._pipe = None


class StandardStreamReaderProtocol(asyncio.StreamReaderProtocol):
    def connection_made(self, transport):
        if self._stream_reader._transport is not None:
            return
        super().connection_made(transport)


class StandardStreamReader(asyncio.StreamReader):

    __del__ = protect_standard_streams


class StandardStreamWriter(asyncio.StreamWriter):

    __del__ = protect_standard_streams

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
def open_stantard_pipe_connection(pipe_in, pipe_out, pipe_err, *, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()
    # Reader
    in_reader = StandardStreamReader(loop=loop)
    protocol = StandardStreamReaderProtocol(in_reader, loop=loop)
    yield from loop.connect_read_pipe(lambda: protocol, pipe_in)
    # Out writer
    out_write_connect = loop.connect_write_pipe(lambda: protocol, pipe_out)
    out_transport, _ = yield from out_write_connect
    out_writer = StandardStreamWriter(out_transport, protocol, in_reader, loop)
    # Err writer
    err_write_connect = loop.connect_write_pipe(lambda: protocol, pipe_err)
    err_transport, _ = yield from err_write_connect
    err_writer = StandardStreamWriter(err_transport, protocol, in_reader, loop)
    # Return
    return in_reader, out_writer, err_writer


@asyncio.coroutine
def create_standard_streams(stdin, stdout, stderr, *, loop=None):
    try:
        if compat.platform == 'win32':
            raise OSError
        stdin.fileno(), stdout.fileno(), stderr.fileno()
    except OSError:
        in_reader = NonFileStreamReader(stdin, loop=loop)
        out_writer = NonFileStreamWriter(stdout, loop=loop)
        err_writer = NonFileStreamWriter(stderr, loop=loop)
    else:
        future = open_stantard_pipe_connection(
            stdin, stdout, stderr, loop=loop)
        in_reader, out_writer, err_writer = yield from future
    return in_reader, out_writer, err_writer


@asyncio.coroutine
def get_standard_streams(*, cache={}, use_stderr=False, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()
    key = sys.stdin, sys.stdout, sys.stderr
    if cache.get(key) is None:
        connection = create_standard_streams(*key, loop=loop)
        cache[key] = yield from connection
    in_reader, out_writer, err_writer = cache[key]
    return in_reader, err_writer if use_stderr else out_writer


@asyncio.coroutine
def ainput(prompt='', *, streams=None, use_stderr=False, loop=None):
    """Asynchronous equivalent to *input*."""
    if loop is None:
        loop = asyncio.get_event_loop()
    # Get standard streams
    if streams is None:
        streams = yield from get_standard_streams(
            use_stderr=use_stderr, loop=loop)
    reader, writer = streams
    # Write prompt
    writer.write(prompt.encode())
    yield from writer.drain()
    # Get data
    data = yield from reader.readline()
    # Decode data
    try:
        data = data.decode()
    except UnicodeDecodeError:
        if b'\xff\xf4\xff\xfd\x06' in data:
            raise SystemExit
    # Return or raise EOF
    if not data.endswith('\n'):
        raise EOFError
    return data.rstrip('\n')
