apython
=======

An asynchronous python console.

It provides asynchronous equivalents to [input], [exec][ and [code.interact].

It also includes an interactive event loop and an asynchronous command line interface.

[input]: https://docs.python.org/3/library/functions.html#input
[exec]: https://docs.python.org/3/library/functions.html#exec
[code.interact]: https://docs.python.org/2/library/code.html#code.interact


Requirements
------------

- python >= 3.4


Installation
------------

    This will install the package and the `apython` script.

    $ python setup.py install
    $ apython -h
    usage: apython [-h] [-m] [FILE] [ARG [ARG ...]]


Asynchronous console example
----------------------------

The [example directory] includes a [slightly modified version] of the [echo server from the asyncio documentation].
It runs an echo server on port 8888 but doesn't print anything and save the received message in `loop.history` instead.

It runs fine without any `apython` related stuff:

    $ python3 -m example.echo

In order to access the program while it's running, simply use `apython` instead:

    $ apython -m example.echo
    Python 3.5.0 (default, Sep 16 2015, 13:06:03)
    [GCC 4.8.4] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    ---
    This interpreter is running in an asyncio event loop.
    It allows you to wait for coroutines using the 'await' syntax.
    Try: await asyncio.sleep(1, result=3, loop=loop)
    ---
    >>>

This looks like the standard python console, with an extra message. It suggests using the `await` syntax (`yield from` for python 3.4):

    >>> await asyncio.sleep(1, result=3, loop=loop)
    # Wait one second...
    3
    >>>

The `locals` contains a reference to the event loop:

    >>> dir()
    ['__doc__', '__name__', 'asyncio', 'loop']
    >>> loop
    <InteractiveEventLoop running=True closed=False debug=False>
    >>>

So we can access the `history` of received messages:

    >>> loop.history
    defaultdict(<class 'list'>, {})
    >>> sum(loop.history.values(), [])
    []

Let's send a message to the server using a `telnet` client:

    $ telnet localhost 8888
    Trying 127.0.0.1...
    Connected to localhost.
    Escape character is '^]'.
    Hello!
    Hello!
    Connection closed by foreign host.

The echo server behaves correctly. It is now possible to retreive the message:

    >>> sum(loop.history.values(), [])
    ['Hello!']

The console also supports `Ctrl-C` and `Ctrl-D` signals:

    >>> ^C
    KeyboardInterrupt
    >>> # Ctrl-D
    $

[example directory]: example
[slightly modified version]: example/echo.py
[echo server from the asyncio documentation]: https://docs.python.org/3/library/asyncio-stream.html#tcp-echo-server-using-streams


Asynchronous CLI example
------------------------

The package also provides an `AsychronousCli` object. It is initialized with a dictionary of commands and can be scheduled with the coroutine `async_cli.interact()`.
A dedicated command line interface to the echo server is defined in [example/cli.py] In this case, the command dictonary is defined as:

    commands = {'history': (get_history, parser)}

where `get_history` is a coroutine and `parser` an [ArgumentParser]from the [argparse] module.
The arguments of the parser will be passed as keywords arguments to the coroutine.

Let's run the command line interface:

    $ python3 example.cli
    Welcome to the CLI interface of echo!
    Try:
    * 'help' to display the help message
    * 'list' to display the command list.
    >>>

The `help` and `list` commands are generated automatically:

    >>> help
    Type 'help' to display this message.
    Type 'list' to display the command list.
    Type '<command> -h' to display
    the help message of <command>.
    >>> list
    List of commands:
     * help [-h]
     * history [-h] [--pattern PATTERN]
     * list [-h]
    >>>

The `history` command defined earlier can be found in the list. Note that it has an `help` option and a `pattern` argument:

    >>> history -h
    usage: history [-h] [--pattern PATTERN]

    Display the message history

    optional arguments:
      -h, --help            show this help message and exit
      --pattern PATTERN, -p PATTERN
                            pattern to filter hostnames

An example:

    >>> history
    No message in the history
    >>> # A few messages later
    >>> history
    Host 127.0.0.1:
      0. Hello!
      1. Bye!
    Host 192.168.0.3
      0. Sup!
    >>> history -p 127.*
    Host 127.0.0.1:
      0. Hello!
      1. Bye!

[example.cli]: example.cli
[ArgumentParser]: https://docs.python.org/dev/library/argparse.html#argparse.ArgumentParser
[argparse]: https://docs.python.org/dev/library/argparse.html


Contact
-------

Vincent Michel: vxgmichel@gmail.com
