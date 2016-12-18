import io
import asyncio

import pytest
from aioconsole import aexec
from aioconsole.compat import PY35


# Helper

@asyncio.coroutine
def coro(x):
    yield
    return x


# Test data

testdata = {
    'simple': (
        {},
        "1+1",
        2,
        {}),
    'affect': (
        {},
        "a=1",
        None,
        {'a': 1}),
    'modify': (
        {'b': 1},
        "b=2",
        None,
        {'b': 2}),
    'multiple': (
        {},
        "c=3;d=4;5",
        5,
        {'c': 3, 'd': 4}),
    'async': (
        {'coro': coro},
        "await coro(6)" if PY35 else "yield from coro(6)",
        6,
        {'coro': coro}),
}


# Parametrized test for aexec

@pytest.mark.parametrize(
    "local, code, expected_result, expected_local",
    list(testdata.values()),
    ids=list(testdata.keys()))
@pytest.mark.asyncio
def test_aexec(event_loop, local, code,
               expected_result, expected_local):
    stream = io.StringIO()
    yield from aexec(code, local=local, stream=stream)
    if expected_result is None:
        assert stream.getvalue() == ''
    else:
        assert stream.getvalue().strip() == repr(expected_result)
    assert local.pop('_') == expected_result
    assert local == expected_local
