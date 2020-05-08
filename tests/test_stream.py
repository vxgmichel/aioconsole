import os
import io
import gc
import sys
import pytest
import asyncio
from unittest.mock import Mock

from aioconsole import compat
from aioconsole.stream import create_standard_streams, ainput, aprint
from aioconsole.stream import is_pipe_transport_compatible


@pytest.mark.skipif(
    sys.platform == 'win32',
    reason='Not supported on windows')
@pytest.mark.asyncio
@asyncio.coroutine
def test_create_standard_stream_with_pipe():
    r, w = os.pipe()
    stdin = open(r)
    stdout = open(w, 'w')
    stderr = open(w, 'w')

    assert is_pipe_transport_compatible(stdin)
    assert is_pipe_transport_compatible(stdout)
    assert is_pipe_transport_compatible(stderr)

    reader, writer1, writer2 = yield from create_standard_streams(
        stdin, stdout, stderr)

    writer1.write('a\n')
    yield from writer1.drain()
    data = yield from reader.readline()
    assert data == b'a\n'

    writer2.write('b\n')
    yield from writer2.drain()
    data = yield from reader.readline()
    assert data == b'b\n'

    reader._transport = None
    stdout.fileno = Mock(return_value=0)
    get_extra_info = Mock(side_effect=OSError)
    writer2._transport.get_extra_info = get_extra_info
    del reader, writer1, writer2
    gc.collect()  # Force garbage collection - necessary for pypy
    get_extra_info.assert_called_once_with('pipe')
    stdout.fileno.assert_called_once_with()


@pytest.mark.asyncio
@asyncio.coroutine
def test_create_standard_stream_with_non_pipe():
    stdin = io.StringIO('a\nb\nc\nd\n')
    stdout = io.StringIO()
    stderr = io.StringIO()
    reader, writer1, writer2 = yield from create_standard_streams(
        stdin, stdout, stderr)

    writer1.write('a\n')
    yield from writer1.drain()
    data = yield from reader.readline()
    assert data == b'a\n'
    assert stdout.getvalue() == 'a\n'

    writer2.write('b\n')
    yield from writer2.drain()
    data = yield from reader.readline()
    assert data == b'b\n'
    assert stderr.getvalue() == 'b\n'

    writer2.stream = Mock(spec={})
    yield from writer2.drain()

    data = yield from reader.read(2)
    assert data == b'c\n'

    assert reader.at_eof() is False

    if compat.PY35:
        assert (yield from reader.__aiter__()) == reader
        assert (yield from reader.__anext__()) == b'd\n'
        with pytest.raises(StopAsyncIteration):
            yield from reader.__anext__()
    else:
        assert (yield from reader.read()) == b'd\n'
        assert (yield from reader.read()) == b''

    assert reader.at_eof() is True


@pytest.mark.asyncio
def test_ainput_with_standard_stream(monkeypatch):
    string = 'a\nb\n'
    monkeypatch.setattr('sys.stdin', io.StringIO(string))
    monkeypatch.setattr('sys.stdout', io.StringIO())
    monkeypatch.setattr('sys.stderr', io.StringIO())

    assert (yield from ainput()) == 'a'
    assert (yield from ainput('>>> ')) == 'b'
    assert sys.stdout.getvalue() == '>>> '
    assert sys.stderr.getvalue() == ''


@pytest.mark.asyncio
def test_aprint_with_standard_stream(monkeypatch):
    string = ''
    monkeypatch.setattr('sys.stdin', io.StringIO())
    monkeypatch.setattr('sys.stdout', io.StringIO(string))
    monkeypatch.setattr('sys.stderr', io.StringIO())
    yield from aprint('ab', 'cd')
    assert sys.stdout.getvalue() == 'ab cd\n'
    yield from aprint('a' * 1024 * 64)
    assert sys.stdout.getvalue() == 'ab cd\n' + 'a' * 1024 * 64 + '\n'
    assert sys.stderr.getvalue() == ''


@pytest.mark.asyncio
def test_read_from_closed_pipe():
    stdin_r, stdin_w = os.pipe()
    stdout_r, stdout_w = os.pipe()
    stderr_r, stderr_w = os.pipe()

    stdin = open(stdin_w, 'wb')
    stdin.write(b'hello\n')
    stdin.close()

    reader, writer1, writer2 = yield from create_standard_streams(
        open(stdin_r, 'rb'), open(stdout_w, 'wb'), open(stderr_w, 'rb'))

    result = yield from ainput('>>> ', streams=(reader, writer1))
    assert result == 'hello'

    os.close(stdout_w)
    os.close(stderr_w)

    assert open(stdout_r).read() == '>>> '
    assert open(stderr_r).read() == ''


@pytest.mark.skipif(
    sys.platform == 'win32',
    reason='Not supported on windows')
@pytest.mark.asyncio
@asyncio.coroutine
def test_standard_stream_pipe_buffering():
    r, w = os.pipe()
    stdin = open(r)
    stdout = open(w, 'w')
    stderr = open(w, 'w')

    assert is_pipe_transport_compatible(stdin)
    assert is_pipe_transport_compatible(stdout)
    assert is_pipe_transport_compatible(stderr)

    reader, writer1, writer2 = yield from create_standard_streams(
        stdin, stdout, stderr)

    blob_size = 4 * 1024 * 1024  # 4 MB
    writer1.write("a\n" + "b" * blob_size + "\n")
    task = asyncio.ensure_future(writer1.drain())
    data = yield from reader.readline()
    assert data == b'a\n'

    # Check back pressure
    yield from asyncio.sleep(0.1)
    assert not task.done()
    assert len(reader._buffer) < blob_size

    data = yield from reader.readline()
    assert data == b"b" * blob_size + b"\n"
    yield from task
