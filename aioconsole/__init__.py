"""Provide asynchronous equivalent to input, exec and interact.

It also includes an interactive event loop, and a command line interface.
"""

from .execute import aexec
from .console import AsynchronousConsole, interact
from .stream import ainput, aprint, afancy_print, get_standard_streams
from .events import InteractiveEventLoop, InteractiveEventLoopPolicy
from .events import set_interactive_policy, run_console
from .command import AsynchronousCli
from .server import start_interactive_server
from .apython import run_apython

__all__ = [
    "aexec",
    "ainput",
    "aprint",
    "afancy_print",
    "AsynchronousConsole",
    "interact",
    "InteractiveEventLoop",
    "InteractiveEventLoopPolicy",
    "set_interactive_policy",
    "run_console",
    "AsynchronousCli",
    "start_interactive_server",
    "get_standard_streams",
    "run_apython",
]
