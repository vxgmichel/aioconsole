
import io
import sys

import pytest
from aioconsole import interact


@pytest.mark.asyncio
def test_interact_simple(event_loop):
    sys.ps1 = "[Hello!]"
    sys.stdin = io.StringIO('1+1\n')
    sys.stderr = io.StringIO()
    banner = "A BANNER"
    expected = '\n'.join((banner, sys.ps1 + '2', sys.ps1)) + '\n'
    yield from interact(banner=banner, stop=False)
    assert sys.stderr.getvalue() == expected


@pytest.mark.asyncio
def test_interact_traceback(event_loop):
    sys.ps1 = "[Hello!] "
    sys.stdin = io.StringIO('1/0\n')
    sys.stderr = io.StringIO()
    banner = "A BANNER"
    expected = '\n'.join((banner, sys.ps1 + '2', sys.ps1)) + '\n'
    yield from interact(banner=banner, stop=False)
    lines = sys.stderr.getvalue().splitlines()
    assert lines[0] == banner
    assert lines[1] == sys.ps1 + "Traceback (most recent call last):"
    assert lines[5] == "ZeroDivisionError: division by zero"
    assert lines[6] == sys.ps1
