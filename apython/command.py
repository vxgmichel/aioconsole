"""Provide an asynchronous equivalent to the python console."""

import sys
import random
import asyncio
import argparse

from . import code


class AsynchronousCli(code.AsynchronousConsole):

    def __init__(self, commands, *, prog=None, loop=None):
        super().__init__(loop=loop)
        self.prog = prog
        self.commands = dict(commands)
        self.commands['help'] = (
            self.help_command,
            argparse.ArgumentParser(
                description='Display the help message.'))
        self.commands['list'] = (
            self.list_command,
            argparse.ArgumentParser(
                description='Display the command list.'))
        for key, (corofunc, parser) in self.commands.items():
            parser.prog = key

    def get_default_banner(self):
        prog = self.prog or sys.argv[0].split('/')[-1]
        msg = "Welcome to the CLI interface of {0}!\n".format(prog)
        msg += "Try:\n"
        msg += " * 'help' to display the help message\n"
        msg += " * 'list' to display the command list."
        return msg

    @asyncio.coroutine
    def help_command(self):
        return """\
Type 'help' to display this message.
Type 'list' to display the command list.
Type '<command> -h' to display
the help message of <command>."""

    @asyncio.coroutine
    def list_command(self):
        msg = 'List of commands:'
        for key, (corofunc, parser) in sorted(self.commands.items()):
            usage = parser.format_usage().replace('usage: ', '')[:-1]
            msg += '\n * ' + usage
        return msg

    @asyncio.coroutine
    def runsource(self, source, filename=None):
        if source.strip().endswith('\\'):
            return True
        source = source.replace('\\\n', '')
        try:
            name, *args = source.split()
        except ValueError:
            return False
        if name not in self.commands:
            self.write("Command '{0}' does not exist.\n".format(name))
            return False
        corofunc, parser = self.commands[name]
        try:
            namespace = parser.parse_args(args)
        except SystemExit:
            return False
        coro = corofunc(**vars(namespace))
        try:
            result = yield from coro
        except SystemExit:
            raise
        except:
            self.showtraceback()
        else:
            self.write(str(result) + '\n')
        return False


@asyncio.coroutine
def interact(banner=None, local=None, stop=True, *, loop=None):
    console = AsynchronousConsole(local, loop=loop)
    yield from console.interact(banner, stop)


if __name__ == "__main__":

    @asyncio.coroutine
    def dice(faces):
        for _ in range(3):
            yield from asyncio.sleep(0.33)
            print('.', end='', flush=True)
        print()
        return random.randint(1, faces)

    parser = argparse.ArgumentParser(description='Throw a dice.')
    parser.add_argument('--faces', '-f', metavar='N', type=int,
                        default=6, help='Number of faces')
    cli = AsynchronousCli({'dice': (dice, parser)})

    loop = asyncio.get_event_loop()
    loop.run_until_complete(cli.interact())
