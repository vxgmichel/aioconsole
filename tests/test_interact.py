
import io
import os
import sys
import signal
import asyncio
from unittest.mock import Mock
from contextlib import contextmanager

import pytest
from aioconsole import compat
from aioconsole import interact
from aioconsole.stream import NonFileStreamReader, NonFileStreamWriter


@contextmanager
def stdcontrol(event_loop, monkeypatch):
    # PS1
    monkeypatch.setattr('sys.ps1', "[Hello!]", raising=False)
    # Stdin control
    stdin_read, stdin_write = os.pipe()
    monkeypatch.setattr('sys.stdin', open(stdin_read))
    writer = NonFileStreamWriter(open(stdin_write, 'w'), loop=event_loop)
    # Stdout control
    monkeypatch.setattr(sys, 'stdout', io.StringIO())
    # Stderr control
    stderr_read, stderr_write = os.pipe()
    monkeypatch.setattr('sys.stderr', open(stderr_write, 'w'))
    reader = NonFileStreamReader(open(stderr_read), loop=event_loop)
    # Yield
    yield reader, writer
    # Check
    assert sys.stdout.getvalue() == ''


@asyncio.coroutine
def assert_stream(stream, expected, loose=False):
    s = None if loose else "\n"
    for line in expected.splitlines():
        assert line.strip(s) == (yield from stream.readline()).decode().strip(s)


@pytest.fixture(params=['unix', 'not-unix'])
def signaling(request, monkeypatch, event_loop):
    if request.param == 'not-unix':
        m = Mock(side_effect=NotImplementedError)
        monkeypatch.setattr(event_loop, 'add_signal_handler', m)
        monkeypatch.setattr(event_loop, 'remove_signal_handler', m)
    yield request.param


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
        yield from assert_stream(reader, '      ^', loose=True)
        yield from assert_stream(reader, 'SyntaxError: invalid syntax')
        yield from assert_stream(reader, sys.ps1)


@pytest.mark.asyncio
def test_interact_keyboard_interrupt(event_loop, monkeypatch, signaling):
    with stdcontrol(event_loop, monkeypatch) as (reader, writer):
        # Start interaction
        banner = "A BANNER"
        task = asyncio.ensure_future(interact(banner=banner, stop=False))
        # Wait for banner
        yield from assert_stream(reader, banner)
        # Send SIGINT
        if sys.platform == 'win32':
            signal.getsignal(signal.SIGINT)(signal.SIGINT, None)
        else:
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
