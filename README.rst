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
    
.. sourcecode:: console

    $ apython
    Python 3.5.0 (default, Sep 7 2015, 14:12:03)
    [GCC 4.8.4] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    ---
    This console is running in an asyncio event loop.
    It allows you to wait for coroutines using the 'await' syntax.
    Try: await asyncio.sleep(1, result=3, loop=loop)
    ---
    
.. sourcecode:: python3

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

.. _aioconsole: https://pypi.python.org/pypi/aioconsole
.. _GitHub: https://github.com/vxgmichel/aioconsole
.. _input: https://docs.python.org/3/library/functions.html#input
.. _exec: https://docs.python.org/3/library/functions.html#exec
.. _code.interact: https://docs.python.org/2/library/code.html#code.interact
.. _argparse: https://docs.python.org/dev/library/argparse.html
.. _stream: https://docs.python.org/3.4/library/asyncio-stream.html
.. _example directory: https://github.com/vxgmichel/aioconsole/blob/master/example
.. _documentation: http://aioconsole.readthedocs.io/
.. _PyPI: aioconsole_
