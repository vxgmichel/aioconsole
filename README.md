apython
=======

Asynchronous console and interfaces.

This package provides:
 - asynchronous equivalents to [input], [exec] and [code.interact]
 - an interactive loop running the asynchronous python console
 - a way to customize and run command line interface using [argparse]
 - [stream] support to serve interfaces instead of using standard streams
 - the `apython` script to access asyncio code at runtime without modifying
   the sources

[input]: https://docs.python.org/3/library/functions.html#input
[exec]: https://docs.python.org/3/library/functions.html#exec
[code.interact]: https://docs.python.org/2/library/code.html#code.interact
[stream]: https://docs.python.org/3.4/library/asyncio-stream.html


Requirements
------------

 - python >= 3.4


Installation
------------

This will install the package and the `apython` script.

```bash
$ python setup.py install
$ apython -h
usage: apython [-h] [-m] [FILE] ...
```

Asynchronous console
--------------------

The [example directory] includes a [slightly modified version] of the
[echo server from the asyncio documentation]. It runs an echo server on a
given port but doesn't print anything and save the received messages in
`loop.history` instead.

It runs fine without any `apython` related stuff:

```bash
$ python3 -m example.echo 8888
```

In order to access the program while it's running, simply replace `python3`
with `apython`:

```bash
$ apython -m example.echo 8888
Python 3.5.0 (default, Sep 7 2015, 14:12:03)
[GCC 4.8.4] on linux
Type "help", "copyright", "credits" or "license" for more information.
---
This interpreter is running in an asyncio event loop.
It allows you to wait for coroutines using the 'await' syntax.
Try: await asyncio.sleep(1, result=3, loop=loop)
---
>>>
```

This looks like the standard python console, with an extra message. It
suggests using the `await` syntax (`yield from` for python 3.4):

```python
>>> await asyncio.sleep(1, result=3, loop=loop)
# Wait one second...
3
>>>
```

The `locals` contains a reference to the event loop:

```python
>>> dir()
['__doc__', '__name__', 'asyncio', 'loop']
>>> loop
<InteractiveEventLoop running=True closed=False debug=False>
>>>
```

So we can access the `history` of received messages:

```python
>>> loop.history
defaultdict(<class 'list'>, {})
>>> sum(loop.history.values(), [])
[]
```

Let's send a message to the server using a `netcat` client:

```bash
$ nc localhost 8888
Trying 127.0.0.1...
Connected to localhost.
Escape character is '^]'.
Hello!
Hello!
Connection closed by foreign host.
```

The echo server behaves correctly. It is now possible to retrieve the message:

```python
>>> sum(loop.history.values(), [])
['Hello!']
```

The console also supports `Ctrl-C` and `Ctrl-D` signals:

```python
>>> ^C
KeyboardInterrupt
>>> # Ctrl-D
$
```

All this is implemented by setting `InteractiveEventLoop` as default event
loop. It simply is a selector loop that schedules `apython.interact()`
coroutine when it's created. `apython.interact()` supports any [stream object]
so it can be used along with [asyncio.start_server] to serve the python
console.  The [apython.server] module does exactly that:

```bash
$ python3 -m apython.server 8888
The python console is being served on port 8888 ...
```

Then connect using `netcat`:

```bash
$ nc localhost 8888
Python 3.5.0 (default, Sep 7 2015, 14:12:03)
[GCC 4.8.4] on linux
Type "help", "copyright", "credits" or "license" for more information.
---
This interpreter is running in an asyncio event loop.
It allows you to wait for coroutines using the 'await' syntax.
Try: await asyncio.sleep(1, result=3, loop=loop)
---
>>>
```

Great! Anyone can now forkbomb your machine:

```python
>>> import os
>>> os.system(':(){ :|:& };:')
```

Note that it's still possible to combine the previous example with the
`apython` script to access the server locally while it outrageously
compromises your computer safety:

```bash
$ apython -m apython.server 8888
Python 3.5.0 (default, Sep 7 2015, 14:12:03)
[GCC 4.8.4] on linux
Type "help", "copyright", "credits" or "license" for more information.
[...]
```

[example directory]: example
[slightly modified version]: example/echo.py
[echo server from the asyncio documentation]: https://docs.python.org/3/library/asyncio-stream.html#tcp-echo-server-using-streams
[stream object]: https://docs.python.org/3.4/library/asyncio-stream.html
[asyncio.start_server]: https://docs.python.org/3.4/library/asyncio-stream.html#asyncio.start_server
[apython.server]: apython/server.py


Command line interfaces
-----------------------

The package also provides an `AsychronousCli` object. It is initialized with a
dictionary of commands and can be scheduled with the coroutine
`async_cli.interact()`.  A dedicated command line interface to the echo server
is defined in [example/cli.py] In this case, the command dictonary is defined
as:

```python
commands = {'history': (get_history, parser)}
```

where `get_history` is a coroutine and `parser` an [ArgumentParser] from the
[argparse] module.  The arguments of the parser will be passed as keywords
arguments to the coroutine.

Let's run the command line interface:

```bash
$ python3 -m example.cli --port 8888
Welcome to the CLI interface of echo!
Try:
* 'help' to display the help message
* 'list' to display the command list.
>>>
```

The `help` and `list` commands are generated automatically:

```none
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
```

The `history` command defined earlier can be found in the list. Note that it
has an `help` option and a `pattern` argument:

```none
>>> history -h
usage: history [-h] [--pattern PATTERN]

Display the message history

optional arguments:
  -h, --help            show this help message and exit
  --pattern PATTERN, -p PATTERN
                        pattern to filter hostnames
```

Example usage of the `history` command:

```none
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
```

Just like `asyncio.interact()`, `AsynchronousCli` can be initialized with any
pair of [streams]. It can be used along with [asyncio.start_server] to serve
the command line interface. [example/cli.py] provides this functionality
through the `--serve-cli` option:

```bash
$ python3 -m example.cli --port 8888 --serve-cli 8889
A command line interface is being served on port 8889 ...
```

It's now possible to access the interface using `netcat`:

```bash
$ nc localhost 8889
Welcome to the CLI interface of echo!
Try:
 * 'help' to display the help message
 * 'list' to display the command list.
>>>
```

Again, it is fine to run the example with `apython` instead:

```bash
$ apython -m example.cli --port 8888 --serve-cli 8889
Python 3.5.0 (default, Sep 7 2015, 14:12:03)
[GCC 4.8.4] on linux
Type "help", "copyright", "credits" or "license" for more information.
[...]
```

Hence, the example above combines:
- an asynchronous python console running locally
- an echo server running on port 8888
- an dedicated interface running on port 8889


[example/cli.py]: example/cli.py
[ArgumentParser]: https://docs.python.org/dev/library/argparse.html#argparse.ArgumentParser
[argparse]: https://docs.python.org/dev/library/argparse.html
[streams]: https://docs.python.org/3.4/library/asyncio-stream.html
[asyncio.start_server]: https://docs.python.org/3.4/library/asyncio-stream.html#asyncio.start_server


Contact
-------

Vincent Michel: vxgmichel@gmail.com
