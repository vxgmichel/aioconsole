import io
import asyncio

import pytest
from aioconsole import aexec, aeval
from aioconsole.execute import compile_for_aexec


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
async def test_aexec_exec_mode(local, code, expected_result, expected_local):
    stream = io.StringIO()
    await aexec(code, local=local, stream=stream)
    assert stream.getvalue() == ""
    assert local == expected_local


@pytest.mark.parametrize(
    "local, code, expected_result, expected_local",
    list(testdata.values()),
    ids=list(testdata.keys()),
)
@pytest.mark.asyncio
async def test_aexec_single_mode(local, code, expected_result, expected_local):
    stream = io.StringIO()
    await aexec(compile_for_aexec(code, "test", "single"), local=local, stream=stream)
    if expected_result is None:
        assert stream.getvalue() == ""
    else:
        assert stream.getvalue().strip() == repr(expected_result)
    assert local.pop("_") == expected_result
    assert local == expected_local


def test_invalid_compile_modes():
    with pytest.raises(ValueError):
        compile_for_aexec("1\n", "test", "eval")
    with pytest.raises(ValueError):
        compile_for_aexec("1\n", "test", "unknown")


@pytest.mark.asyncio
async def test_incomplete_code():
    with pytest.raises(SyntaxError):
        await aexec("(")


@pytest.mark.asyncio
async def test_missing_newline():
    # Missing newline in "exec" mode is OK
    dct = {}
    await aexec("def f():\n  return 1", dct)
    assert dct["f"]() == 1
    await aexec("def g(): return 2", dct)
    assert dct["g"]() == 2

    # Missing newline in "single" raises a SyntaxError
    with pytest.raises(SyntaxError):
        await aexec(
            compile_for_aexec(
                "def f():\n    return 1", "test", "single", dont_imply_dedent=True
            )
        )


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


# Test exception handling in aeval


@pytest.mark.asyncio
async def test_aeval_syntax_error():
    with pytest.raises(SyntaxError):
        await aeval("1+", {})


@pytest.mark.asyncio
async def test_aeval_name_error():
    with pytest.raises(NameError):
        await aeval("undefined_variable", {})


@pytest.mark.asyncio
async def test_aeval_runtime_error():
    with pytest.raises(ZeroDivisionError):
        await aeval("1/0", {})


# Test async handling


@pytest.mark.asyncio
async def test_aeval_async_function():
    result = await aeval("await coro(5)", {"coro": coro})
    assert result == 5


@pytest.mark.asyncio
async def test_aeval_coroutine_result():
    result = await aeval("coro(5)", {"coro": coro})
    assert result == 5


# Test that statements do not modify the namespace unnecessarily


@pytest.mark.asyncio
async def test_aeval_statements():
    namespace = {}
    result = await aeval("a = 1", namespace)
    assert result == 1
    assert namespace == {"a": 1}


@pytest.mark.asyncio
async def test_aeval_if_statement():
    namespace = {"a": 0}
    result = await aeval("if a == 0: a = 1", namespace)
    assert result is None  # 'if' statements don't produce a result
    assert namespace == {"a": 1}


# Test handling of special cases


@pytest.mark.asyncio
async def test_aeval_multiline_input():
    namespace = {}
    result = await aeval("x = 1\nx + 1", namespace)
    assert result == 2
    assert namespace == {"x": 1}


@pytest.mark.asyncio
async def test_aeval_function_definition():
    namespace = {}
    result = await aeval("def foo(): return 42", namespace)
    assert result is None
    assert "foo" in namespace
    assert namespace["foo"]() == 42


@pytest.mark.asyncio
async def test_aeval_async_function_definition():
    namespace = {}
    result = await aeval("async def foo(): return 42", namespace)
    assert result is None
    assert "foo" in namespace
    assert await namespace["foo"]() == 42
