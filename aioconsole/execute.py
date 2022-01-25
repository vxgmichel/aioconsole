"""Provide an asynchronous equivalent *to exec*."""

import ast
import codeop
from re import findall

CORO_NAME = "__corofn"
CORO_DEF = f"async def {CORO_NAME}(): "
CORO_CODE = CORO_DEF + "return (None, locals())\n"


def make_arg(key, annotation=None):
    """Make an ast function argument."""
    arg = ast.arg(key, annotation)
    arg.lineno, arg.col_offset = 0, 0
    return arg


def full_update(dct, values):
    """Fully update a dictionary."""
    dct.clear()
    dct.update(values)


def exec_result(obj, local, stream):
    """Reproduce default exec behavior (print and builtins._)"""
    local["_"] = obj
    if obj is not None:
        print(repr(obj), file=stream)


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


def make_coroutine_from_tree(tree, filename="<aexec>", symbol="single", local={}):
    """Make a coroutine from a tree structure."""
    dct = {}
    tree.body[0].args.args = list(map(make_arg, local))
    exec(compile(tree, filename, symbol), dct)
    return dct[CORO_NAME](**local)


def compile_for_aexec(
    source, filename="<aexec>", mode="single", dont_imply_dedent=False, local={}
):
    """Return a list of (coroutine object, abstract base tree)."""
    flags = ast.PyCF_ONLY_AST
    if dont_imply_dedent:
        flags |= codeop.PyCF_DONT_IMPLY_DEDENT

    # Avoid a syntax error by wrapping code with `async def`
    indented = ''
    unclosed = ''
    for line in source.split("\n"):
        # Disabling indentation inside multiline strings
        indented += (' ' * 4 if not unclosed and line else '') + line + '\n'
        for q in findall('"""' '|' "'''", line):
            if not unclosed:
                unclosed = q
            elif unclosed == q:
                unclosed = ''
    coroutine = CORO_DEF + "\n" + indented
    interactive = compile(coroutine, filename, mode, flags).body[0]

    return [make_tree(statement, filename, mode) for statement in interactive.body]


async def aexec(source, local=None, stream=None):
    """Asynchronous equivalent to *exec*.

    Support the *await* syntax.
    """
    if local is None:
        local = {}
    if isinstance(source, str):
        source = compile_for_aexec(source)
    for tree in source:
        coro = make_coroutine_from_tree(tree, local=local)
        result, new_local = await coro
        exec_result(result, new_local, stream)
        full_update(local, new_local)
