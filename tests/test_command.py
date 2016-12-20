
import io
import sys
import asyncio
import argparse

import pytest

from aioconsole import AsynchronousCli

testdata = {

    'simple_command': (
        'hello\n',
        """\
Welcome to the CLI interface of hello!
Try:
 * 'help' to display the help message
 * 'list' to display the command list.
[Hello!] Hello!
[Hello!] \n"""),

    'simple_command_with_arg': (
        'hello -n Neil\n',
        """\
Welcome to the CLI interface of hello!
Try:
 * 'help' to display the help message
 * 'list' to display the command list.
[Hello!] Hello Neil!
[Hello!] \n"""),

    'list_command': (
        'list\n',
        """\
Welcome to the CLI interface of hello!
Try:
 * 'help' to display the help message
 * 'list' to display the command list.
[Hello!] List of commands:
 * exit [-h]
 * hello [-h] [--name NAME]
 * help [-h]
 * list [-h]
[Hello!] \n"""),

    'help_command': (
        'help\n',
        """\
Welcome to the CLI interface of hello!
Try:
 * 'help' to display the help message
 * 'list' to display the command list.
[Hello!] Type 'help' to display this message.
Type 'list' to display the command list.
Type '<command> -h' to display the help message of <command>.
[Hello!] \n"""),

    'exit_command': (
        'exit\n',
        """\
Welcome to the CLI interface of hello!
Try:
 * 'help' to display the help message
 * 'list' to display the command list.
[Hello!] """),

    'wrong_command': (
        'hellooo\n',
        """\
Welcome to the CLI interface of hello!
Try:
 * 'help' to display the help message
 * 'list' to display the command list.
[Hello!] Command 'hellooo' does not exist.
[Hello!] \n"""),


}


def make_cli(streams=None):

    @asyncio.coroutine
    def say_hello(reader, writer, name=None):
        data = "Hello {}!".format(name) if name else "Hello!"
        writer.write(data.encode() + b'\n')

    parser = argparse.ArgumentParser(description="Say hello")
    parser.add_argument('--name', '-n', type=str)
    commands = {'hello': (say_hello, parser)}
    return AsynchronousCli(commands, streams, prog='hello')


@pytest.mark.parametrize(
    "input_string, expected",
    list(testdata.values()),
    ids=list(testdata.keys()))
@pytest.mark.asyncio
def test_async_cli(event_loop, input_string, expected):
    sys.ps1 = "[Hello!] "
    sys.stdin = io.StringIO(input_string)
    sys.stderr = io.StringIO()
    yield from make_cli().interact(stop=False)
    print(sys.stderr.getvalue())
    assert sys.stderr.getvalue() == expected
