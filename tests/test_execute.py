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


def echo(x):
    return x


async def aecho(x):
    return echo(x)


# Parametrized test with a variety of expressions
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expression, local",
    [
        # Valid Simple Expressions
        ("1 + 2", None),
        ("sum([i * i for i in range(10)])", None),
        # Invalid Expressions
        ("def foo(): return 42", None),
        ("x = 1", None),
        ("x = 1\nx + 1", None),
        ("for i in range(10): pass", None),
        ("if True: pass", None),
        ("while True: break", None),
        ("try: pass\nexcept: pass", None),
        # Expressions Involving Undefined Variables
        ("undefined_variable", None),
        ("undefined_function()", None),
        # Expressions with Deliberate Errors
        ("1/0", None),
        ("open('nonexistent_file.txt')", None),
        # Lambda and Anonymous Functions
        ("(lambda x: x * 2)(5)", None),
        # Expressions with Built-in Functions
        ("len('test')", None),
        ("min([3, 1, 4, 1, 5, 9])", None),
        ("max([x * x for x in range(10)])", None),
        # Boolean and Conditional Expressions
        ("True and False", None),
        ("not True", None),  # Boolean negation
        ("5 if True else 10", None),
        # String Manipulation
        ("'hello' + ' ' + 'world'", None),
        ("f'hello {42}'", None),
        # Complex List Comprehensions
        ("[x for x in range(5)]", None),
        ("[x * x for x in range(10) if x % 2 == 0]", None),
        # Expressions with Syntax Errors
        ("return 42", None),
        ("yield 5", None),
        # Test with await
        ("await aecho(5)", {"aecho": aecho, "echo": echo}),
        # Test invalid local
        ("...", []),
        ("...", "string_instead_of_dict"),
        ("...", 42),
        ("...", set()),
        ("...", ...),
        ("...", 1.5),
        ("...", object()),
        ("...", asyncio),
        ("...", lambda: ...),
        ("...", {"__result__": 99}),
        # Invalid expressions
        ("", None),
        (None, None),
        (0, None),
        ({}, None),
        (object(), None),
        (asyncio, None),
        (..., None),
        (lambda: ..., None),
    ],
)
async def test_aeval(expression, local):
    # Capture the result or exception of the synchronous eval
    sync_exc = None
    result = None
    try:
        if isinstance(expression, str):
            sync_expression = expression.lstrip("await a")
        else:
            sync_expression = expression

        result = eval(sync_expression, local)
    except Exception as exc:
        sync_exc = exc

    # Capture the result or exception of the asynchronous eval
    async_exc = None
    async_result = None
    try:
        async_result = await aeval(expression, local)
    except Exception as exc:
        async_exc = exc

    # Assert that the exceptions are of the same type
    assert type(sync_exc) == type(async_exc)
    # Assert that the results match
    assert result == async_result


# Test calling an async function without awaiting it
@pytest.mark.asyncio
async def test_aeval_async_func_without_await():
    expression = "asyncio.sleep(0)"
    local = {"asyncio": asyncio}
    result = await aeval(expression, local)
    assert asyncio.iscoroutine(result)
    await result


@pytest.mark.asyncio
async def test_aeval_valid_await_syntax():
    expression = "await aecho(10)"
    local = {"aecho": aecho}
    result = await aeval(expression, local)
    assert result == 10
