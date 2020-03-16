"""Provide an asynchronous equivalent to the python console."""

import sys
import code
import pydoc
import codeop
import signal
import asyncio
import functools
import traceback

from . import stream
from . import compat
from . import execute

EXTRA_MESSAGE = """\
---
This console is running in an asyncio event loop.
It allows you to wait for coroutines using the '{0}' syntax.
Try: {0} asyncio.sleep(1, result=3)
---""".format('await' if compat.PY35 else 'yield from')


current_task = (
    asyncio.current_task if compat.PY37 else asyncio.Task.current_task)


class AsynchronousCompiler(codeop.CommandCompiler):

    def __init__(self):
        self.compiler = functools.partial(
            execute.compile_for_aexec,
            dont_imply_dedent=True)


class AsynchronousConsole(code.InteractiveConsole):

    def __init__(self, streams=None, locals=None, filename="<console>",
                 prompt_control=None, *, loop=None):
        super().__init__(locals, filename)
        # Process arguments
        if loop is None:
            loop = asyncio.get_event_loop()
        if streams is None:
            streams = stream.get_standard_streams(use_stderr=True, loop=loop)
        elif isinstance(streams, tuple):
            streams = asyncio.coroutine(lambda x=streams: x)()
        # Attributes
        self.streams = streams
        self.loop = loop
        self.reader = None
        self.writer = None
        self.prompt_control = prompt_control
        self.compile = AsynchronousCompiler()
        # Populate locals
        self.locals.setdefault('asyncio', asyncio)
        self.locals.setdefault('loop', self.loop)
        self.locals.setdefault('print', self.print)
        self.locals.setdefault('help', self.help)
        self.locals.setdefault('ainput', self.ainput)

    @functools.wraps(print)
    def print(self, *args, **kwargs):
        kwargs.setdefault('file', self)
        print(*args, **kwargs)

    @functools.wraps(help)
    def help(self, obj):
        self.print(pydoc.render_doc(obj))

    @functools.wraps(stream.ainput)
    @asyncio.coroutine
    def ainput(self, prompt='', *, streams=None, use_stderr=False, loop=None):
        # Get the console streams by default
        if streams is None and use_stderr is False:
            streams = self.reader, self.writer
        # Wrap the prompt with prompt control characters
        if self.prompt_control and self.prompt_control not in prompt:
            prompt = self.prompt_control + prompt + self.prompt_control
        # Run ainput
        return (yield from stream.ainput(
            prompt, streams=streams, use_stderr=use_stderr, loop=loop))

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
        except BaseException:
            self.showtraceback()
        yield from self.flush()

    def resetbuffer(self):
        self.buffer = []

    def handle_sigint(self, task):
        task.cancel()
        if task._fut_waiter._loop is not self.loop:
            task._wakeup(task._fut_waiter)

    def add_sigint_handler(self):
        task = current_task(loop=self.loop)
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
        # Get the streams
        try:
            if self.streams is not None:
                self.reader, self.writer = yield from self.streams
        finally:
            self.streams = None
        # Interact
        try:
            if handle_sigint:
                self.add_sigint_handler()
            yield from self._interact(banner)
        # Exit
        except SystemExit:
            if stop:
                raise
        # Clean-up
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
    def raw_input(self, prompt=''):
        return (yield from self.ainput(prompt))

    def write(self, data):
        return self.writer.write(data.encode())

    @asyncio.coroutine
    def flush(self):
        try:
            yield from self.writer.drain()
        except ConnectionResetError:
            pass

    # Re-implement showtraceback and showsyntaxerror
    # to ignore sys.excepthook (set by ubuntu apport for instance)

    def showtraceback(self):
        sys.last_type, sys.last_value, last_tb = ei = sys.exc_info()
        sys.last_traceback = last_tb
        try:
            lines = traceback.format_exception(ei[0], ei[1], last_tb.tb_next)
            self.write(''.join(lines))
        finally:
            last_tb = ei = None

    def showsyntaxerror(self, filename=None):
        type, value, tb = sys.exc_info()
        sys.last_type = type
        sys.last_value = value
        sys.last_traceback = tb
        if filename and type is SyntaxError:
            # Work hard to stuff the correct filename in the exception
            try:
                msg, (dummy_filename, lineno, offset, line) = value.args
            except ValueError:
                # Not the format we expect; leave it alone
                pass
            else:
                # Stuff in the right filename
                value = SyntaxError(msg, (filename, lineno, offset, line))
                sys.last_value = value
        lines = traceback.format_exception_only(type, value)
        self.write(''.join(lines))


@asyncio.coroutine
def interact(banner=None, streams=None, locals=None,
             prompt_control=None, stop=True,
             handle_sigint=True, *, loop=None):
    console = AsynchronousConsole(
        streams,
        locals=locals,
        prompt_control=prompt_control,
        loop=loop)
    yield from console.interact(banner, stop, handle_sigint)
