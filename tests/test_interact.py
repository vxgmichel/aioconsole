import asyncio
import io
import os
import signal
import sys
from contextlib import contextmanager
from unittest.mock import Mock

import pytest
import pytest_asyncio

from aioconsole import AsynchronousConsole, interact
from aioconsole.stream import NonFileStreamReader, NonFileStreamWriter


@contextmanager
def stdcontrol(monkeypatch):
    # PS1
    monkeypatch.setattr("sys.ps1", "[Hello!]", raising=False)
    # Stdin control
    stdin_read, stdin_write = os.pipe()
    monkeypatch.setattr("sys.stdin", open(stdin_read))
    writer = NonFileStreamWriter(open(stdin_write, "w"))
    # Stdout control
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    # Stderr control
    stderr_read, stderr_write = os.pipe()
    monkeypatch.setattr("sys.stderr", open(stderr_write, "w"))
    reader = NonFileStreamReader(open(stderr_read))
    # Yield
    yield reader, writer
    # Check
    assert sys.stdout.getvalue() == ""


def feed_inputs(monkeypatch, *inputs):
    inputs = iter(inputs)

    async def raw_input(self, prompt=""):
        self.write(str(prompt))
        try:
            return next(inputs)
        except StopIteration:
            raise EOFError

    monkeypatch.setattr(AsynchronousConsole, "raw_input", raw_input)


async def assert_stream(stream, expected, loose=False):
    s = None if loose else "\n"
    for expected_line in expected.splitlines():
        line = await stream.readline()
        assert expected_line.strip(s) == line.decode().strip(s)


@pytest_asyncio.fixture(params=["unix", "not-unix"])
async def signaling(request, monkeypatch):
    if request.param == "not-unix":
        event_loop = asyncio.get_running_loop()
        m = Mock(side_effect=NotImplementedError)
        monkeypatch.setattr(event_loop, "add_signal_handler", m)
        monkeypatch.setattr(event_loop, "remove_signal_handler", m)
    yield request.param


@pytest.mark.asyncio
async def test_interact_simple(monkeypatch):
    with stdcontrol(monkeypatch) as (reader, writer):
        banner = "A BANNER"
        writer.write("1+1\n")
        await writer.drain()
        writer.stream.close()
        await interact(banner=banner, stop=False)
        await assert_stream(reader, banner)
        await assert_stream(reader, sys.ps1 + "2")
        await assert_stream(reader, sys.ps1)


@pytest.mark.asyncio
async def test_interact_traceback(monkeypatch):
    with stdcontrol(monkeypatch) as (reader, writer):
        banner = "A BANNER"
        writer.write("1/0\n")
        await writer.drain()
        writer.stream.close()
        await interact(banner=banner, stop=False)
        # Check stderr
        await assert_stream(reader, banner)
        await assert_stream(reader, sys.ps1 + "Traceback (most recent call last):")
        # Skip 3 lines
        for _ in range(4 if sys.version_info >= (3, 11) else 3):
            await reader.readline()
        # Check stderr
        await assert_stream(reader, "ZeroDivisionError: division by zero")
        await assert_stream(reader, sys.ps1)


@pytest.mark.asyncio
async def test_interact_syntax_error(monkeypatch):
    with stdcontrol(monkeypatch) as (reader, writer):
        writer.write("a b\n")
        await writer.drain()
        writer.stream.close()
        banner = "A BANNER"
        await interact(banner=banner, stop=False)
        await assert_stream(reader, banner)
        # Skip line
        await reader.readline()
        await assert_stream(reader, "    a b")
        await assert_stream(reader, "      ^", loose=True)
        await assert_stream(reader, "SyntaxError: invalid syntax")
        await assert_stream(reader, sys.ps1)


@pytest.mark.parametrize(
    "source, exc_name",
    [("1 +\n", "SyntaxError"), ("def f():\nreturn 1\n", "IndentationError")],
)
@pytest.mark.asyncio
async def test_showsyntaxerror_with_filename(monkeypatch, source, exc_name):
    for name in ("last_type", "last_value", "last_traceback"):
        monkeypatch.setattr(sys, name, None, raising=False)
    console = AsynchronousConsole(streams=(None, None))
    console.writer = io.BytesIO()
    try:
        console.compile(source, "<console>", "single")
    except SyntaxError:
        console.showsyntaxerror("<other>")
    else:
        pytest.fail("Expected a syntax error")
    output = console.writer.getvalue().decode()
    assert 'File "<other>"' in output
    assert "<console>" not in output
    assert output.splitlines()[-1].startswith(f"{exc_name}:")
    assert sys.last_type.__name__ == exc_name
    assert sys.last_value.filename == "<other>"


@pytest.mark.asyncio
async def test_interact_keyboard_interrupt(monkeypatch, signaling):
    with stdcontrol(monkeypatch) as (reader, writer):
        # Start interaction
        banner = "A BANNER"
        task = asyncio.ensure_future(interact(banner=banner, stop=False))
        # Wait for banner
        await assert_stream(reader, banner)
        # Send SIGINT
        if sys.platform == "win32":
            signal.getsignal(signal.SIGINT)(signal.SIGINT, None)
        else:
            os.kill(os.getpid(), signal.SIGINT)
        # Wait for ps1
        await assert_stream(reader, sys.ps1)
        await assert_stream(reader, "KeyboardInterrupt")
        # Close stdin
        writer.stream.close()
        # Wait for interact to finish
        await assert_stream(reader, sys.ps1)
        await task
        # Test
        assert sys.stdout.getvalue() == ""


@pytest.mark.asyncio
async def test_broken_pipe(monkeypatch, signaling):
    with stdcontrol(monkeypatch) as (reader, writer):
        # Start interaction
        banner = "A BANNER"
        task = asyncio.ensure_future(interact(banner=banner, stop=False))
        # Wait for banner
        await assert_stream(reader, banner)
        # Close stdin
        writer.stream.close()
        reader.stream.close()
        # Wait for interact to finish
        await task
        # Test
        assert sys.stdout.getvalue() == ""


@pytest.mark.asyncio
async def test_interact_non_string_prompt(monkeypatch):
    class Prompt:
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return self.value

    with stdcontrol(monkeypatch) as (reader, writer):
        monkeypatch.setattr("sys.ps1", Prompt("[PS1]"))
        monkeypatch.setattr("sys.ps2", Prompt("[PS2]"), raising=False)
        banner = "A BANNER"
        writer.write("if True:\n    print(1)\n\n")
        await writer.drain()
        writer.stream.close()
        await interact(banner=banner, stop=False)
        await assert_stream(reader, banner)
        await assert_stream(reader, "[PS1][PS2][PS2]1")
        await assert_stream(reader, "[PS1]")


@pytest.mark.asyncio
async def test_interact_multiple_indented_lines(monkeypatch):
    with stdcontrol(monkeypatch) as (reader, writer):
        banner = "A BANNER"
        writer.write("def x():\n    print(1)\n    print(2)\n\nx()\n")
        await writer.drain()
        writer.stream.close()
        await interact(banner=banner, stop=False)
        await assert_stream(reader, banner)
        await assert_stream(reader, sys.ps1 + sys.ps2 * 3 + sys.ps1 + "1\n2")


@pytest.mark.asyncio
async def test_interact_cancellation(monkeypatch):
    with stdcontrol(monkeypatch) as (reader, _writer):
        banner = "A BANNER"
        task = asyncio.ensure_future(interact(banner=banner, stop=False))
        # Wait for banner
        await assert_stream(reader, banner)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert task.cancelled


@pytest.mark.asyncio
async def test_interact_block_with_blank_lines(monkeypatch):
    with stdcontrol(monkeypatch) as (reader, _writer):
        feed_inputs(
            monkeypatch,
            "def f():\n    a = 1\n\n    b = 2\n\n    return a + b\n\nf()\nf() * 2",
        )
        await interact(banner="A BANNER", stop=False)
        await assert_stream(reader, "A BANNER")
        await assert_stream(reader, "[Hello!]3")
        await assert_stream(reader, "6")
        await assert_stream(reader, "[Hello!]")


@pytest.mark.asyncio
async def test_interact_block_with_await(monkeypatch):
    with stdcontrol(monkeypatch) as (reader, _writer):
        feed_inputs(monkeypatch, "x = await asyncio.sleep(0, 4)\n\nx + 1")
        await interact(banner="A BANNER", stop=False)
        await assert_stream(reader, "A BANNER")
        await assert_stream(reader, "[Hello!]5")


@pytest.mark.asyncio
async def test_interact_block_syntax_error(monkeypatch):
    with stdcontrol(monkeypatch) as (reader, _writer):
        feed_inputs(monkeypatch, "a = 1\n1 +* 2", "a")
        await interact(banner="A BANNER", stop=False)
        await assert_stream(reader, "A BANNER")
        await assert_stream(reader, '[Hello!]  File "<console>", line 3')
        await assert_stream(reader, "    1 +* 2")
        await assert_stream(reader, "^", loose=True)
        await assert_stream(reader, "SyntaxError: invalid syntax")
        # Nothing in the block ran
        await assert_stream(reader, "[Hello!]Traceback (most recent call last):")


@pytest.mark.asyncio
async def test_interact_incomplete_block(monkeypatch):
    with stdcontrol(monkeypatch) as (reader, _writer):
        monkeypatch.setattr("sys.ps2", "[PS2]", raising=False)
        feed_inputs(monkeypatch, "x = (1,\n2,", ")", "x")
        await interact(banner="A BANNER", stop=False)
        await assert_stream(reader, "A BANNER")
        await assert_stream(reader, "[Hello!][PS2][Hello!](1, 2)")
