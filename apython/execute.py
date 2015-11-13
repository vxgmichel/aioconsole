"""Provide an asynchronous equivalent *to exec*."""

import sys
import ast
import codeop
import asyncio

from . import compat

CORO_NAME = '__corofn'
CORO_DEF = 'def {}(): '.format(CORO_NAME)
if compat.PY35:
    CORO_DEF = 'async ' + CORO_DEF
CORO_CODE = CORO_DEF + 'return (None, locals())\n'


def full_update(dct, values):
    """Fully update a dictionary."""
    dct.clear()
    dct.update(values)


def exec_result(obj, local, stream):
    """Reproduce default exec behavior (print and builtins._)"""
    local['_'] = obj
    if obj is not None:
        print(obj, file=stream)


def make_tree(statement, filename="<aexec>", symbol="single", local={}):
    """Helper for *aexec*."""
    # Create tree
    tree = ast.parse(CORO_CODE, filename, symbol)
    # Check expression statement
    if isinstance(statement, ast.Expr):
        tree.body[0].body[0].value.elts[0] = statement.value
    else:
        tree.body[0].body.insert(0, statement)
    # Check and return coroutine
    exec(compile(tree, filename, symbol))
    return tree


def make_coroutine_from_tree(tree, filename="<aexec>", symbol="single",
                             local={}):
    """Make a coroutine from a tree structure."""
    dct = {}
    tree.body[0].args.args = [ast.arg(key, None) for key in local]
    exec(compile(tree, filename, symbol), dct)
    return asyncio.coroutine(dct[CORO_NAME])(**local)


def compile_for_aexec(source, filename="<aexec>", mode="single",
                      dont_imply_dedent=False, local={}):
    """Return a list of (coroutine object, abstract base tree)."""
    flags = ast.PyCF_ONLY_AST
    if dont_imply_dedent:
        flags |= codeop.PyCF_DONT_IMPLY_DEDENT
    if compat.PY35:
        # Avoid a syntax error by wrapping code with `async def`
        indented = '\n'.join(line and ' ' * 4 + line
                             for line in source.split('\n'))
        coroutine = CORO_DEF + '\n' + indented + '\n'
        interactive = compile(coroutine, filename, mode, flags).body[0]
        # Check EOF errors
        try:
            compile(source, filename, mode, flags)
        except SyntaxError as exc:
            if exc.msg == 'unexpected EOF while parsing':
                raise
    else:
        interactive = compile(source, filename, mode, flags)
    return [make_tree(statement, filename, mode) for
            statement in interactive.body]


@asyncio.coroutine
def aexec(source, local=None, stream=None):
    """Asynchronous equivalent to *exec*.

    Support the *yield from* syntax.
    """
    if local is None:
        local = {}
    if isinstance(source, str):
        source = compile_for_aexec(source)
    for tree in source:
        coro = make_coroutine_from_tree(tree, local=local)
        result, new_local = yield from coro
        exec_result(result, new_local, stream)
        full_update(local, new_local)
