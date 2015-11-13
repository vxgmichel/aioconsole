"""Provide an asynchronous equivalent to the python console."""

import sys
import code
import pydoc
import codeop
import signal
import asyncio
import functools

from . import input
from . import compat
from . import execute

EXTRA_MESSAGE = """\
---
This interpreter is running in an asyncio event loop.
It allows you to wait for coroutines using the '{0}' syntax.
Try: {0} asyncio.sleep(1, result=3, loop=loop)
---""".format('await' if compat.PY35 else 'yield from')


class AsynchronousCompiler(codeop.CommandCompiler):

    def __init__(self):
        self.compiler = functools.partial(
            execute.compile_for_aexec,
            dont_imply_dedent=True)


class AsynchronousConsole(code.InteractiveConsole):

    def __init__(self, streams=None, locals=None, filename="<console>",
                 *, loop=None):
        super().__init__(locals, filename)
        self.compile = AsynchronousCompiler()
        if loop is None:
            loop = asyncio.get_event_loop()
        if streams is None:
            self.streams = input.get_standard_streams(use_stderr=True,
                                                      loop=loop)
        elif isinstance(streams, tuple):
            self.streams = asyncio.coroutine(lambda: streams)()
        else:
            self.streams = streams
        self.reader = None
        self.writer = None
        self.loop = loop
        self.locals.setdefault('asyncio', asyncio)
        self.locals.setdefault('loop', self.loop)
        self.locals.setdefault('print', self.print)
        self.locals.setdefault('help', self.help)

    @functools.wraps(print)
    def print(self, *args, **kwargs):
        kwargs.setdefault('file', self)
        print(*args, **kwargs)

    @functools.wraps(help)
    def help(self, obj):
        self.print(pydoc.render_doc(obj))

    def get_default_banner(self):
        cprt = ('Type "help", "copyright", "credits" '
                'or "license" for more information.')
        msg = "Python %s on %s\n%s\n%s"
        return msg % (sys.version, sys.platform, cprt, EXTRA_MESSAGE)

    @asyncio.coroutine
    def runsource(self, source, filename="<ainput>", symbol="single"):
        try:
            code = self.compile(source, filename, symbol)
        except (OverflowError, SyntaxError, ValueError):
            self.showsyntaxerror(filename)
            return False

        if code is None:
            return True

        yield from self.runcode(code)
        return False

    @asyncio.coroutine
    def runcode(self, code):
        try:
            yield from execute.aexec(code, self.locals, self)
        except SystemExit:
            raise
        except:
            self.showtraceback()
        yield from self.flush()

    def resetbuffer(self):
        self.buffer = []

    def handle_sigint(self, task):
        task.cancel()
        if task._fut_waiter._loop is not self.loop:
            task._wakeup(task._fut_waiter)

    def add_sigint_handler(self):
        task = asyncio.Task.current_task(loop=self.loop)
        try:
            self.loop.add_signal_handler(
                signal.SIGINT, self.handle_sigint, task)
        except NotImplementedError:
            def callback(*args):
                self.loop.call_soon_threadsafe(self.handle_sigint, task)
            signal.signal(signal.SIGINT, callback)

    def remove_sigint_handler(self):
        try:
            self.loop.remove_signal_handler(signal.SIGINT)
        except NotImplementedError:
            signal.signal(signal.SIGINT, signal.default_int_handler)

    @asyncio.coroutine
    def interact(self, banner=None, stop=True, handle_sigint=True):
        try:
            if self.streams is not None:
                self.reader, self.writer = yield from self.streams
        finally:
            self.streams = None
        try:
            if handle_sigint:
                self.add_sigint_handler()
            yield from self._interact(banner)
        except SystemExit:
            if stop:
                raise
        finally:
            if handle_sigint:
                self.remove_sigint_handler()
            if stop:
                self.loop.stop()

    @asyncio.coroutine
    def _interact(self, banner=None):
        # Get ps1 and ps2
        try:
            sys.ps1
        except AttributeError:
            sys.ps1 = ">>> "
        try:
            sys.ps2
        except AttributeError:
            sys.ps2 = "... "
        # Print banner
        if banner is None:
            banner = self.get_default_banner()
        self.write("%s\n" % str(banner))
        # Run loop
        more = 0
        while 1:
            try:
                if more:
                    prompt = sys.ps2
                else:
                    prompt = sys.ps1
                try:
                    line = yield from self.raw_input(prompt)
                except EOFError:
                    self.write("\n")
                    yield from self.flush()
                    break
                else:
                    more = yield from self.push(line)
            except asyncio.CancelledError:
                self.write("\nKeyboardInterrupt\n")
                yield from self.flush()
                self.resetbuffer()
                more = 0

    @asyncio.coroutine
    def push(self, line):
        self.buffer.append(line)
        source = "\n".join(self.buffer)
        more = yield from self.runsource(source, self.filename)
        if not more:
            self.resetbuffer()
        return more

    @asyncio.coroutine
    def raw_input(self, prompt=""):
        self.write(prompt)
        yield from self.flush()
        data = (yield from self.reader.readline())
        try:
            data = data.decode()
        except UnicodeDecodeError:
            if b'\xff\xf4\xff\xfd\x06' in data:
                raise SystemExit
            data = '\n'
        if not data.endswith('\n'):
            raise EOFError()
        return data

    def write(self, data):
        return self.writer.write(data.encode())

    @asyncio.coroutine
    def flush(self):
        self.writer.drain()


@asyncio.coroutine
def interact(banner=None, streams=None, local=None, stop=True,
             handle_sigint=True, *, loop=None):
    console = AsynchronousConsole(streams, local, loop=loop)
    yield from console.interact(banner, stop, handle_sigint)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(interact())
