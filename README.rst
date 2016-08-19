aioconsole
==========

Asynchronous console and interfaces.

This package provides:

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

The following command installs the package and the ``apython`` script.

.. code:: console

    $ python setup.py install
    $ apython -h
    usage: apython [-h] [--serve [HOST:]PORT] [-m] [FILE] ...

    Run the given python file or module with a modified asyncio policy replacing
    the default event loop with an interactive loop. If no argument is given, it
    simply runs an asynchronous python console.

    positional arguments:
      FILE                 python file or module to run
      ARGS                 extra arguments

    optional arguments:
      -h, --help           show this help message and exit
      --serve [HOST:]PORT  serve a console on the given interface instead
      -m                   run a python module


Simple usage
------------

The following example demonstrates the use of ``await`` inside the console:

.. code:: console

    $ apython
    Python 3.5.0 (default, Sep 7 2015, 14:12:03)
    [GCC 4.8.4] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    ---
    This console is running in an asyncio event loop.
    It allows you to wait for coroutines using the 'await' syntax.
    Try: await asyncio.sleep(1, result=3, loop=loop)
    ---
    >>> await asyncio.sleep(1, result=3)
    # Wait one second...
    3
    >>>


Documentation
-------------

Find more examples in the documentation_ and the `example directory`_.


Contact
-------

Vincent Michel: vxgmichel@gmail.com

.. _input: https://docs.python.org/3/library/functions.html#input
.. _exec: https://docs.python.org/3/library/functions.html#exec
.. _code.interact: https://docs.python.org/2/library/code.html#code.interact
.. _argparse: https://docs.python.org/dev/library/argparse.html
.. _stream: https://docs.python.org/3.4/library/asyncio-stream.html
.. _example directory: https://github.com/vxgmichel/aioconsole/blob/master/example
.. _documentation: http://pythonhosted.org/aioconsole
