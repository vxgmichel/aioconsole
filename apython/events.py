"""Provide an interactive event loop class."""

import asyncio

from . import code
from . import compat


class InteractiveEventLoop(asyncio.SelectorEventLoop):
    """Event loop running a python console."""

    def __init__(self, selector=None, local=None, banner=None, stop=True):
        super().__init__(selector=selector)
        coro = code.interact(local=local, banner=banner, stop=stop, loop=self)
        self.console = asyncio.async(coro, loop=self)

    def close(self):
        if not self.is_running():
            asyncio.Future.cancel(self.console)
        super().close()

    if compat.PY34:
        def __del__(self):
            if self.console.done():
                self.console.exception()
            try:
                super().__del__()
            except AttributeError:
                pass


class InteractiveEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    """Policy to use the interactive event loop by default."""
    _loop_factory = InteractiveEventLoop


def set_interactive_policy():
    """Use an interactive event loop by default."""
    asyncio.set_event_loop_policy(InteractiveEventLoopPolicy())


def run_console(selector=None):
    """Run the interactive event loop."""
    loop = InteractiveEventLoop(selector=selector)
    asyncio.set_event_loop(loop)
    loop.run_forever()


if __name__ == '__main__':
    run_console()
