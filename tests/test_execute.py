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
    "expression",
    [
        # Valid Simple Expressions
        "1 + 2",
        "sum([i * i for i in range(10)])",
        # Invalid Expressions
        "def foo(): return 42",
        "x = 1",
        "x = 1\nx + 1",
        "for i in range(10): pass",
        "if True: pass",
        "while True: break",
        "try: pass\nexcept: pass",
        # Expressions Involving Undefined Variables
        "undefined_variable",
        "undefined_function()",
        # Expressions with Deliberate Errors
        "1/0",
        "open('nonexistent_file.txt')",
        # Lambda and Anonymous Functions
        "(lambda x: x * 2)(5)",
        # Expressions with Built-in Functions
        "len('test')",
        "min([3, 1, 4, 1, 5, 9])",
        "max([x * x for x in range(10)])",
        # Boolean and Conditional Expressions
        "True and False",
        "not True",  # Boolean negation
        "5 if True else 10",
        # String Manipulation
        "'hello' + ' ' + 'world'",
        "f'hello {42}'",
        # Complex List Comprehensions
        "[x for x in range(5)]",
        "[x * x for x in range(10) if x % 2 == 0]",
        # Expressions with Syntax Errors
        "return 42",
        "yield 5",
    ],
)
async def test_aeval(expression):
    # Set up a namespace that has all the needed functions
    namespace = {"aecho": aecho, "echo": echo}

    # Capture the result or exception of the synchronous eval
    sync_exc = None
    result = None
    try:
        sync_expression = expression.lstrip("await a")
        result = eval(sync_expression, namespace)
    except Exception as exc:
        sync_exc = exc

    # Capture the result or exception of the asynchronous eval
    async_exc = None
    async_result = None
    try:
        async_result = await aeval(expression, namespace)
    except Exception as exc:
        async_exc = exc

    # Assert that the exceptions are of the same type
    assert type(sync_exc) == type(async_exc)
    # Assert that the results match
    assert result == async_result
