"""Provide an asychronous equivalent to *input*."""

import io
import sys
import asyncio

from . import compat


class InputPipeProtocol(asyncio.BaseProtocol):
    """Protocol for the standard input pipe."""

    def __init__(self, *, loop=None):
        super().__init__()
        self._loop = loop
        self.reset_waiter()

    def reset_waiter(self, future=None):
        if future and not future.cancelled():
            future.exception()
        self.waiter = asyncio.Future(loop=self._loop)
        self.waiter.add_done_callback(self.reset_waiter)

    def data_received(self, data):
        self.waiter.set_result(data.decode().strip('\n'))

    def eof_received(self):
        self.waiter.set_exception(EOFError("EOF when reading a line"))


class StdinPipe:
    """Provide a *read* coroutine at class level to read from stdin."""
    instances = {}

    @classmethod
    def get_instance(cls, loop):
        """Get the instance corresponding to the given loop."""
        if cls.instances.get(loop) is None:
            cls.instances[loop] = cls(loop)
        return cls.instances[loop]

    @classmethod
    def read(cls, *, loop=None):
        """Read from the stdin pipe."""
        if loop is None:
            loop = asyncio.get_event_loop()
        instance = cls.get_instance(loop)
        return (yield from instance._read())

    def __init__(self, loop):
        """Initialize."""
        self.loop = loop
        self.transport = None
        self.protocol = None

    @asyncio.coroutine
    def _read(self):
        """Read from the stdin pipe."""
        if self.transport is None:
            protocol = lambda: InputPipeProtocol(loop=self.loop)
            coro = self.loop.connect_read_pipe(protocol, sys.stdin)
            self.transport, self.protocol = yield from coro
        return (yield from self.protocol.waiter)

    if compat.PY34:
        def __del__(self):
            """Make sure the transports don't close the pipe."""
            for instance in self.instances.values():
                if instance.transport:
                    instance.transport._pipe = None


@asyncio.coroutine
def ainput(prompt=None, *, loop=None):
    """Asynchronous equivalent to *input*."""
    if loop is None:
        loop = asyncio.get_event_loop()
    if prompt is None:
        prompt = ''
    try:
        sys.stdin.fileno()
    except io.UnsupportedOperation:
        future = loop.run_in_executor(None, input, prompt)
    else:
        future = StdinPipe.read(loop=loop)
        print(prompt, end='', flush=True)
    return (yield from future)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(ainput(">>> "))
    print(repr(result))
    result = loop.run_until_complete(ainput(">>> "))
    print(repr(result))
    loop.close()
