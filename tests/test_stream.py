import os
import io
import gc
import sys
import pytest
import asyncio
from unittest.mock import Mock

from aioconsole.stream import create_standard_streams, ainput, aprint
from aioconsole.stream import is_pipe_transport_compatible


@pytest.mark.skipif(sys.platform == "win32", reason="Not supported on windows")
@pytest.mark.asyncio
async def test_create_standard_stream_with_pipe():
    r1, w1 = os.pipe()
    r2, w2 = os.pipe()
    stdin = open(r1)
    stdout = open(w1, "w")
    stderr = open(w2, "w")

    assert is_pipe_transport_compatible(stdin)
    assert is_pipe_transport_compatible(stdout)
    assert is_pipe_transport_compatible(stderr)

    reader, writer1, writer2 = await create_standard_streams(stdin, stdout, stderr)

    writer1.write("a\n")
    await writer1.drain()
    data = await reader.readline()
    assert data == b"a\n"

    writer2.write("b\n")
    await writer2.drain()
    assert os.read(r2, 2) == b"b\n"

    reader._transport = None
    stdout.fileno = Mock(return_value=0)
    get_extra_info = Mock(side_effect=OSError)
    writer2._transport.get_extra_info = get_extra_info
    del reader, writer1, writer2
    gc.collect()  # Force garbage collection - necessary for pypy
    get_extra_info.assert_called_once_with("pipe")
    stdout.fileno.assert_called_once_with()


@pytest.mark.asyncio
async def test_create_standard_stream_with_non_pipe(monkeypatch):
    stdin = io.StringIO("a\nb\nc\nd\n")
    stdout = io.StringIO()
    stderr = io.StringIO()
    reader, writer1, writer2 = await create_standard_streams(stdin, stdout, stderr)

    writer1.write("a\n")
    await writer1.drain()
    data = await reader.readline()
    assert data == b"a\n"
    assert stdout.getvalue() == "a\n"

    writer2.write("b\n")
    await writer2.drain()
    data = await reader.readline()
    assert data == b"b\n"
    assert stderr.getvalue() == "b\n"

    # Multiple writes
    writer2.write("c\n")
    writer2.write("d\n")
    await asyncio.sleep(0.1)
    writer2.write("e\n")
    writer2.close()
    assert writer2.is_closing()
    await writer2.wait_closed()
    assert stderr.getvalue() == "b\nc\nd\ne\n"
    with pytest.raises(RuntimeError):
        writer2.write("f\n")

    data = await reader.read(2)
    assert data == b"c\n"

    assert reader.at_eof() is False

    async for data in reader:
        assert data == b"d\n"

    assert reader.at_eof() is True

    # Check exception handling in the daemon thread

    class KeyboardInterruptLike(BaseException):
        pass

    def raise_keyboard_interrupt(*args):
        raise KeyboardInterruptLike

    def raise_os_error(*args):
        raise OSError

    monkeypatch.setattr(stdin, "readline", raise_os_error)
    with pytest.raises(OSError):
        data = await reader.readline()

    monkeypatch.setattr(stdin, "read", raise_keyboard_interrupt)
    with pytest.raises(KeyboardInterruptLike):
        data = await reader.read()


def mock_stdio(monkeypatch, input_text=""):
    monkeypatch.setattr("sys.stdin", io.StringIO(input_text))
    monkeypatch.setattr("sys.stdout", io.StringIO())
    monkeypatch.setattr("sys.stderr", io.StringIO())


@pytest.mark.asyncio
async def test_ainput_with_standard_stream(monkeypatch):
    mock_stdio(monkeypatch, "a\nb\n")
    assert (await ainput()) == "a"
    assert (await ainput(">>> ")) == "b"
    assert sys.stdout.getvalue() == ">>> "
    assert sys.stderr.getvalue() == ""


@pytest.mark.asyncio
async def test_aprint_with_standard_stream(monkeypatch):
    mock_stdio(monkeypatch)
    await aprint("ab", "cd")
    assert sys.stdout.getvalue() == "ab cd\n"
    await aprint("a" * 1024 * 64)
    assert sys.stdout.getvalue() == "ab cd\n" + "a" * 1024 * 64 + "\n"
    assert sys.stderr.getvalue() == ""


@pytest.mark.parametrize("flush", [False, True])
@pytest.mark.asyncio
async def test_aprint_flush_argument(monkeypatch, flush):
    mock_stdio(monkeypatch)
    await aprint("a", flush=flush)
    if not flush:
        # Might or might not be there yet, depending on internal logic
        assert sys.stdout.getvalue() in ("", "a\n")
        await aprint("", end="", flush=True)
    assert sys.stdout.getvalue() == "a\n"


@pytest.mark.asyncio
async def test_read_from_closed_pipe():
    stdin_r, stdin_w = os.pipe()
    stdout_r, stdout_w = os.pipe()
    stderr_r, stderr_w = os.pipe()

    stdin = open(stdin_w, "wb")
    stdin.write(b"hello\n")
    stdin.close()

    f_stdin = open(stdin_r, "r")
    f_stdout = open(stdout_w, "w")
    f_stderr = open(stderr_w, "r")

    reader, writer1, writer2 = await create_standard_streams(
        f_stdin, f_stdout, f_stderr
    )

    result = await ainput(">>> ", streams=(reader, writer1))
    assert result == "hello"

    writer1.close()
    await writer1.wait_closed()
    f_stdout.close()

    writer2.close()
    await writer2.wait_closed()
    f_stderr.close()

    assert open(stdout_r).read() == ">>> "
    assert open(stderr_r).read() == ""


@pytest.mark.skipif(sys.platform == "win32", reason="Not supported on windows")
@pytest.mark.asyncio
async def test_standard_stream_pipe_buffering():
    r1, w1 = os.pipe()
    r2, w2 = os.pipe()
    stdin = open(r1)
    stdout = open(w1, "w")
    stderr = open(w2, "w")

    assert is_pipe_transport_compatible(stdin)
    assert is_pipe_transport_compatible(stdout)
    assert is_pipe_transport_compatible(stderr)

    reader, writer1, writer2 = await create_standard_streams(stdin, stdout, stderr)

    blob_size = 4 * 1024 * 1024  # 4 MB
    writer1.write("a\n" + "b" * blob_size + "\n")
    task = asyncio.ensure_future(writer1.drain())
    data = await reader.readline()
    assert data == b"a\n"

    # Check back pressure
    await asyncio.sleep(0.1)
    assert not task.done()
    assert len(reader._buffer) < blob_size

    data = await reader.readline()
    assert data == b"b" * blob_size + b"\n"
    await task
