"""Provide asynchronous equivalent to input, exec and interact.

It also includes an interactive event loop, and a command line interface.
"""

from .apython import run_apython
from .command import AsynchronousCli
from .console import AsynchronousConsole, interact
from .events import (
    InteractiveEventLoop,
    InteractiveEventLoopPolicy,
    run_console,
    set_interactive_policy,
)
from .execute import aeval, aexec
from .server import start_interactive_server
from .stream import ainput, aprint, get_standard_streams

__version__ = "0.8.3.dev0"

__all__ = [
    "AsynchronousCli",
    "AsynchronousConsole",
    "InteractiveEventLoop",
    "InteractiveEventLoopPolicy",
    "aeval",
    "aexec",
    "ainput",
    "aprint",
    "get_standard_streams",
    "interact",
    "run_apython",
    "run_console",
    "set_interactive_policy",
    "start_interactive_server",
]
