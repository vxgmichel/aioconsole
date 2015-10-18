"""Provide an asynchronous equivalent *to exec*."""

import ast
import asyncio

CORO_NAME = '__corofn'


def full_update(dct, values):
    """Fully update a dictionary."""
    dct.clear()
    dct.update(values)


def exec_result(obj, filename="<aexec>", symbol="single"):
    """Reproduce default exec behavior (print and builtins._)"""
    code = compile('result', filename, symbol)
    exec(code, {'result': obj})


def make_coroutine(statement, filename="<aexec>", symbol="single", local={}):
    """Helper for *aexec*."""
    # Create tree
    base_code = "def {}(): return (None, locals())\n".format(CORO_NAME)
    tree = ast.parse(base_code, filename, symbol)
    # Check expression statement
    if isinstance(statement, ast.Expr):
        tree.body[0].body[0].value.elts[0] = statement.value
    else:
        tree.body[0].body.insert(0, statement)
    # Create coroutine
    coro = make_coroutine_from_tree(tree, filename, symbol, local)
    return coro, tree


def make_coroutine_from_tree(tree, filename="<aexec>", symbol="single",
                             local={}):
    """Make a coroutine from a tree structure."""
    dct = {}
    tree.body[0].args.args = [ast.arg(key, None) for key in local]
    exec(compile(tree, filename, symbol), dct)
    return asyncio.coroutine(dct[CORO_NAME])(**local)


def compile_for_aexec(source, filename="<aexec>", symbol="single", local={}):
    """Return a list of (coroutine object, abstract base tree)."""
    interactive = ast.parse(source, filename, symbol)
    return [make_coroutine(statement, filename, symbol) for
            statement in interactive.body]


@asyncio.coroutine
def aexec(source, local=None):
    """Asynchronous equivalent to *exec*.

    Support the *yield from* syntax.
    """
    if local is None:
        local = {}
    if isinstance(source, str):
        source = compile_for_aexec(source)
    for _, tree in source:
        coro = make_coroutine_from_tree(tree, local=local)
        result, new_local = yield from coro
        exec_result(result)
        full_update(local, new_local)
