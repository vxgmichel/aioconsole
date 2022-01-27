import io
import asyncio

import pytest
from aioconsole import aexec


# Helper


async def coro(x):
    await asyncio.sleep(0)
    return x


# Test data

testdata = {
    "simple": ({}, "1+1", 2, {}),
    "affect": ({}, "a=1", None, {"a": 1}),
    "modify": ({"b": 1}, "b=2", None, {"b": 2}),
    "multiple": ({}, "c=3;d=4;5", 5, {"c": 3, "d": 4}),
    "async": ({"coro": coro}, "await coro(6)", 6, {"coro": coro}),
    "multiline string": ({}, '"""\n"""', "\n", {}),
    "splitted string": ({}, '"a\\\nb"', "ab", {}),
}


# Parametrized test for aexec


@pytest.mark.parametrize(
    "local, code, expected_result, expected_local",
    list(testdata.values()),
    ids=list(testdata.keys()),
)
@pytest.mark.asyncio
async def test_aexec(event_loop, local, code, expected_result, expected_local):
    stream = io.StringIO()
    await aexec(code, local=local, stream=stream)
    if expected_result is None:
        assert stream.getvalue() == ""
    else:
        assert stream.getvalue().strip() == repr(expected_result)
    assert local.pop("_") == expected_result
    assert local == expected_local


@pytest.mark.asyncio
async def test_incomplete_code():
    with pytest.raises(SyntaxError):
        await aexec("(")


# Test return and yield handling


async def exc_from(code):
    try:
        await aexec(code)
    except Exception as e:
        return e
    else:
        return None


@pytest.mark.asyncio
async def test_return_handling():
    error = await exc_from("return None, {}")

    assert isinstance(error, SyntaxError)
    assert error.msg == "'return' outside function"


@pytest.mark.asyncio
async def test_yield_handling():
    error = await exc_from("for i in range(5): yield i")

    assert isinstance(error, SyntaxError)
    assert error.msg == "'yield' outside function"


@pytest.mark.asyncio
async def test_yield_from_handling():
    error = await exc_from("yield from range(5)")

    assert isinstance(error, SyntaxError)
    assert error.msg == "'yield' outside function"


@pytest.mark.asyncio
async def test_correct():
    assert await exc_from("def x(): return") is None
    assert await exc_from("async def x(): return") is None
    assert await exc_from("def x(): yield") is None
    assert await exc_from("async def x(): yield") is None
