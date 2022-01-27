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


@pytest.mark.asyncio
async def test_return_handling():
    with pytest.raises(SyntaxError) as context:
        await aexec("return None, {}")

    assert context.value.msg == "'return' outside function"


@pytest.mark.asyncio
async def test_yield_handling():
    with pytest.raises(SyntaxError) as context:
        await aexec("for i in range(5): yield i")

    assert context.value.msg == "'yield' outside function"


@pytest.mark.asyncio
async def test_yield_from_handling():
    with pytest.raises(SyntaxError) as context:
        await aexec("yield from range(5)")

    assert context.value.msg == "'yield' outside function"


@pytest.mark.asyncio
async def test_correct():
    await aexec("def x(): return")
    await aexec("async def x(): return")
    await aexec("def x(): yield")
    await aexec("async def x(): yield")
