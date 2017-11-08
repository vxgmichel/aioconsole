aioconsole
==========

.. image:: https://readthedocs.org/projects/aioconsole/badge/?version=latest
   :target: http://aioconsole.readthedocs.io/
   :alt:

.. image:: https://travis-ci.org/vxgmichel/aioconsole.svg?branch=master
   :target: https://travis-ci.org/vxgmichel/aioconsole
   :alt:

.. image:: https://img.shields.io/pypi/v/aioconsole.svg
   :target: https://pypi.python.org/pypi/aioconsole
   :alt:

.. image:: https://img.shields.io/pypi/pyversions/aioconsole.svg
   :target: https://pypi.python.org/pypi/aioconsole
   :alt:

Asynchronous console and interfaces for asyncio

aioconsole_ provides:

* asynchronous equivalents to `input`_, `exec`_ and `code.interact`_
* an interactive loop running the asynchronous python console
* a way to customize and run command line interface using `argparse`_
* `stream`_ support to serve interfaces instead of using standard streams
* the ``apython`` script to access asyncio code at runtime without modifying the sources


Requirements
------------

*  python >= 3.4


Installation
------------

aioconsole_ is available on PyPI_ and GitHub_.
Both of the following commands install the ``aioconsole`` package
and the ``apython`` script.

.. sourcecode:: console

    $ pip3 install aioconsole   # from PyPI
    $ python3 setup.py install  # or from the sources
    $ apython -h
    usage: apython [-h] [--serve [HOST:]PORT] [-m] [FILE] ...


Asynchronous console
--------------------

The `example directory`_ includes a `slightly modified version`_ of the
`echo server from the asyncio documentation`_. It runs an echo server on
a given port and save the received messages in ``loop.history``.

It runs fine and doesn't use any ``aioconsole`` function:

.. sourcecode:: console

    $ python3 -m example.echo 8888
    The echo service is being served on 127.0.0.1:8888

In order to access the program while it’s running, simply replace
``python3`` with ``apython`` and redirect ``stdout`` so the console is
not polluted by ``print`` statements (``apython`` uses ``stderr``):

.. sourcecode:: console

    $ apython -m example.echo 8888 > echo.log
    Python 3.5.0 (default, Sep 7 2015, 14:12:03)
    [GCC 4.8.4] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    ---
    This console is running in an asyncio event loop.
    It allows you to wait for coroutines using the 'await' syntax.
    Try: await asyncio.sleep(1, result=3, loop=loop)
    ---
    >>>

This looks like the standard python console, with an extra message. It
suggests using the ``await`` syntax (``yield from`` for python 3.4):

.. sourcecode:: python3

    >>> await asyncio.sleep(1, result=3, loop=loop)
    # Wait one second...
    3
    >>>

The ``locals`` contain a reference to the event loop:

.. sourcecode:: python3

    >>> dir()
    ['__doc__', '__name__', 'asyncio', 'loop']
    >>> loop
    <InteractiveEventLoop running=True closed=False debug=False>
    >>>

So we can access the ``history`` of received messages:

.. sourcecode:: python3

    >>> loop.history
    defaultdict(<class 'list'>, {})
    >>> sum(loop.history.values(), [])
    []

Let’s send a message to the server using a netcat_ client:

.. sourcecode:: console

    $ nc localhost 8888
    Hello!
    Hello!

The echo server behaves correctly. It is now possible to retrieve the
message:

.. sourcecode:: python3

    >>> sum(loop.history.values(), [])
    ['Hello!']

The console also supports ``Ctrl-C`` and ``Ctrl-D`` signals:

.. sourcecode:: python3

    >>> ^C
    KeyboardInterrupt
    >>> # Ctrl-D
    $

All this is implemented by setting ``InteractiveEventLoop`` as default
event loop. It simply is a selector loop that schedules
``aioconsole.interact()`` coroutine when it’s created.


Serving the console
-------------------

Moreover, ``aioconsole.interact()`` supports `stream objects`_ so it can be
used along with `asyncio.start\_server`_ to serve the python console.
The ``aioconsole.start_interactive_server`` coroutine does exactly that. A
backdoor can be introduced by simply adding the following line in the
program:

.. sourcecode:: python3

    server = await aioconsole.start_interactive_server(
        host='localhost', port=8000)

This is actually very similar to the `eventlet.backdoor module`_. It is
also possible to use the ``--serve`` option so it is not necessary to
modify the code:

.. sourcecode:: console

    $ apython --serve :8889 -m example.echo 8888
    The console is being served on 0.0.0.0:8889
    The echo service is being served on 127.0.0.1:8888

Then connect using netcat_ and optionally, rlwrap_:

.. sourcecode:: console

    $ rlwrap nc localhost 8889
    Python 3.5.0 (default, Sep 7 2015, 14:12:03)
    [GCC 4.8.4] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    ---
    This console is running in an asyncio event loop.
    It allows you to wait for coroutines using the 'await' syntax.
    Try: await asyncio.sleep(1, result=3, loop=loop)
    ---
    >>>

Great! Anyone can now forkbomb your machine:

.. sourcecode:: python3

    >>> import os
    >>> os.system(':(){ :|:& };:')


Command line interfaces
-----------------------

The package also provides an ``AsychronousCli`` object. It is
initialized with a dictionary of commands and can be scheduled with the
coroutine ``async_cli.interact()``. A dedicated command line interface
to the echo server is defined in `example/cli.py`_. In this case, the
command dictonary is defined as:

.. sourcecode:: python3

    commands = {'history': (get_history, parser)}

where ``get_history`` is a coroutine and ``parser`` an `ArgumentParser`_
from the `argparse`_ module. The arguments of the parser will be passed
as keywords arguments to the coroutine.

Let’s run the command line interface:

.. sourcecode:: console

    $ python3 -m example.cli 8888 > cli.log
    Welcome to the CLI interface of echo!
    Try:
    * 'help' to display the help message
    * 'list' to display the command list.
    >>>

The ``help`` and ``list`` commands are generated automatically:

.. sourcecode:: console

    >>> help
    Type 'help' to display this message.
    Type 'list' to display the command list.
    Type '<command> -h' to display the help message of <command>.
    >>> list
    List of commands:
     * help [-h]
     * history [-h] [--pattern PATTERN]
     * list [-h]
    >>>

The ``history`` command defined earlier can be found in the list. Note
that it has an ``help`` option and a ``pattern`` argument:

.. sourcecode:: console

    >>> history -h
    usage: history [-h] [--pattern PATTERN]

    Display the message history

    optional arguments:
      -h, --help            show this help message and exit
      --pattern PATTERN, -p PATTERN
                            pattern to filter hostnames

Example usage of the ``history`` command:

.. sourcecode:: console

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


Serving interfaces
------------------

Just like ``asyncio.interact()``, ``AsynchronousCli`` can be initialized
with any pair of `streams`_. It can be used along with
`asyncio.start\_server`_ to serve the command line interface. The
previous `example`_ provides this functionality through the
``--serve-cli`` option:

.. sourcecode:: console

    $ python3 -m example.cli 8888 --serve-cli 8889
    The command line interface is being served on 127.0.0.1:8889
    The echo service is being served on 127.0.0.1:8888

It’s now possible to access the interface using netcat_:

.. sourcecode:: console

    $ rlwrap nc localhost 8889
    Welcome to the CLI interface of echo!
    Try:
     * 'help' to display the help message
     * 'list' to display the command list.
    >>>

It is also possible to combine the example with the ``apython`` script
to add an extra access for debugging:

.. sourcecode:: console

    $ apython --serve 8887 -m example.cli 8888 --serve-cli 8889
    The console is being served on 127.0.0.1:8887
    The command line interface is being served on 127.0.0.1:8889
    The echo service is being served on 127.0.0.1:8888


Contact
-------

Vincent Michel: vxgmichel@gmail.com

.. _aioconsole: https://pypi.python.org/pypi/aioconsole
.. _GitHub: https://github.com/vxgmichel/aioconsole
.. _input: https://docs.python.org/3/library/functions.html#input
.. _exec: https://docs.python.org/3/library/functions.html#exec
.. _code.interact: https://docs.python.org/2/library/code.html#code.interact
.. _argparse: https://docs.python.org/dev/library/argparse.html
.. _stream: https://docs.python.org/3.4/library/asyncio-stream.html
.. _example directory: https://github.com/vxgmichel/aioconsole/blob/master/example
.. _example/echo.py: https://github.com/vxgmichel/aioconsole/blob/master/example/echo.py
.. _echo server from the asyncio documentation: https://docs.python.org/3/library/asyncio-stream.html#tcp-echo-server-using-streams
.. _asyncio.start\_server: https://docs.python.org/3.4/library/asyncio-stream.html#asyncio.start_server
.. _eventlet.backdoor module: http://eventlet.net/doc/modules/backdoor.html#backdoor-python-interactive-interpreter-within-a-running-process
.. _example/cli.py: https://github.com/vxgmichel/aioconsole/blob/master/example/cli.py
.. _ArgumentParser: https://docs.python.org/dev/library/argparse.html#argparse.ArgumentParser

.. _streams: stream_
.. _stream objects: stream_
.. _slightly modified version: `example/echo.py`_
.. _example: `example/cli.py`_
.. _PyPI: aioconsole_
.. _netcat: https://linux.die.net/man/1/nc
.. _rlwrap: https://linux.die.net/man/1/rlwrap
