
import io
import os
import sys
import signal
import asyncio
from contextlib import contextmanager

import pytest
from aioconsole import compat
from aioconsole import interact
from aioconsole.stream import NonFileStreamReader, NonFileStreamWriter


@contextmanager
def stdcontrol(event_loop, monkeypatch):
    with monkeypatch.context() as m:
        # PS1
        m.setattr('sys.ps1', "[Hello!]")
        # Stdin control
        stdin_read, stdin_write = os.pipe()
        m.setattr('sys.stdin', open(stdin_read))
        writer = NonFileStreamWriter(open(stdin_write, 'w'), loop=event_loop)
        # Stdout control
        m.setattr(sys, 'stdout', io.StringIO())
        # Stderr control
        stderr_read, stderr_write = os.pipe()
        m.setattr('sys.stderr', open(stderr_write, 'w'))
        reader = NonFileStreamReader(open(stderr_read), loop=event_loop)
        # Yield
        yield reader, writer
        # Check
        assert sys.stdout.getvalue() == ''


@asyncio.coroutine
def assert_stream(stream, expected):
    for line in expected.splitlines():
        assert line == (yield from stream.readline()).decode().strip('\n')


@pytest.mark.asyncio
def test_interact_simple(event_loop, monkeypatch):
    with stdcontrol(event_loop, monkeypatch) as (reader, writer):
        banner = "A BANNER"
        writer.write('1+1\n')
        writer.stream.close()
        yield from interact(banner=banner, stop=False)
        yield from assert_stream(reader, banner)
        yield from assert_stream(reader, sys.ps1 + '2')
        yield from assert_stream(reader, sys.ps1)


@pytest.mark.asyncio
def test_interact_traceback(event_loop, monkeypatch):
    with stdcontrol(event_loop, monkeypatch) as (reader, writer):
        banner = "A BANNER"
        writer.write('1/0\n')
        writer.stream.close()
        yield from interact(banner=banner, stop=False)
        # Check stderr
        yield from assert_stream(reader, banner)
        yield from assert_stream(
            reader, sys.ps1 + 'Traceback (most recent call last):')
        # Skip 3 (or 5) lines
        for _ in range(3 if compat.PY35 else 5):
            yield from reader.readline()
        # Check stderr
        yield from assert_stream(reader, "ZeroDivisionError: division by zero")
        yield from assert_stream(reader, sys.ps1)


@pytest.mark.asyncio
def test_interact_syntax_error(event_loop, monkeypatch):
    with stdcontrol(event_loop, monkeypatch) as (reader, writer):
        writer.write('a b\n')
        writer.stream.close()
        banner = "A BANNER"
        yield from interact(banner=banner, stop=False)
        yield from assert_stream(reader, banner)
        # Skip line
        yield from reader.readline()
        yield from assert_stream(reader, '    a b')
        yield from assert_stream(reader, '      ^')
        yield from assert_stream(reader, 'SyntaxError: invalid syntax')
        yield from assert_stream(reader, sys.ps1)


@pytest.mark.asyncio
def test_interact_keyboard_interrupt(event_loop, monkeypatch):
    with stdcontrol(event_loop, monkeypatch) as (reader, writer):
        # Start interaction
        banner = "A BANNER"
        task = asyncio.ensure_future(interact(banner=banner, stop=False))
        # Wait for banner
        yield from assert_stream(reader, banner)
        # Send SIGINT
        os.kill(os.getpid(), signal.SIGINT)
        # Wait for ps1
        yield from assert_stream(reader, sys.ps1)
        yield from assert_stream(reader, "KeyboardInterrupt")
        # Close stdin
        writer.stream.close()
        # Wait for interact to finish
        yield from assert_stream(reader, sys.ps1)
        yield from task
        # Test
        assert sys.stdout.getvalue() == ''
