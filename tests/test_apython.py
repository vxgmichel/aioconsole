import io
import sys
import tempfile
from contextlib import contextmanager

from unittest.mock import Mock, patch, call

import pytest

from aioconsole import compat
from aioconsole import apython, rlwrap
from aioconsole import InteractiveEventLoop


startupfile = '''
def hehe():
    return 42

foo = 1

# Imports work
import math
r = math.cos(0)

# Exec works and is visible from the interpreter
s = 'from pprint import pprint'
exec(s)

'''

@pytest.fixture
def tempfd():
    with tempfile.NamedTemporaryFile() as tf:
        yield tf

@contextmanager
def mock_module(name):
    try:
        module = sys.modules.get(name)
        sys.modules[name] = Mock()
        yield sys.modules[name]
    finally:
        if module is None:
            del sys.modules[name]
        else:
            sys.modules[name] = module


@pytest.fixture(params=['linux', 'darwin', 'win32'])
def platform(request):
    with patch('aioconsole.compat.platform', new=request.param):
        yield request.param


@pytest.fixture
def mock_readline(platform):
    with mock_module('readline'):
        with patch('aioconsole.rlwrap.ctypes') as m_ctypes:

            if platform == 'darwin':
                stdin = '__stdinp'
                stderr = '__stderrp'
            else:
                stdin = 'stdin'
                stderr = 'stderr'

            def readline(fin, ferr, prompt):
                sys.stderr.write(prompt.decode())
                return sys.stdin.readline().encode()

            api = m_ctypes.pythonapi
            call_readline = api.PyOS_Readline
            call_readline.side_effect = readline

            if platform == 'darwin':
                with patch('aioconsole.rlwrap.fcntl', create=True):
                    yield call_readline
            else:
                yield call_readline

            if call_readline.called:
                m_ctypes.c_void_p.in_dll.assert_has_calls([
                    call(api, stdin),
                    call(api, stderr),
                ])


@pytest.fixture(params=['readline', 'no-readline'])
def use_readline(request, mock_readline, platform):
    if request.param == 'readline':
        # Readline tests hang on windows for some reason
        if sys.platform == 'win32':
            pytest.xfail()
        return [] if platform == 'win32' else ['--prompt-control=▲']
    return ['--no-readline']


def test_input_with_stderr_prompt(mock_readline):
    with patch('sys.stdin', new=io.StringIO('test\n')):
        assert rlwrap.input(use_stderr=True) == 'test'


def test_basic_apython_usage(capfd, use_readline):
    with patch('sys.stdin', new=io.StringIO('1+1\n')):
        with pytest.raises(SystemExit):
            apython.run_apython(['--banner=test'] + use_readline)
    out, err = capfd.readouterr()
    assert out == ''
    assert err == 'test\n>>> 2\n>>> \n'


def test_basic_apython_usage_with_sys_argv(capfd, use_readline):
    with patch('sys.argv', new=[
            'path.py', '--banner=test'] + use_readline):
        with patch('sys.stdin', new=io.StringIO('1+1\n')):
            with pytest.raises(SystemExit):
                apython.run_apython()
    out, err = capfd.readouterr()
    assert out == ''
    assert err == 'test\n>>> 2\n>>> \n'


def test_apython_with_prompt_control(capfd):
    with patch('sys.stdin', new=io.StringIO('1+1\n')):
        with pytest.raises(SystemExit):
            apython.run_apython(
                ['--banner=test', '--prompt-control=▲', '--no-readline'])
    out, err = capfd.readouterr()
    assert out == ''
    assert err == 'test\n▲>>> ▲2\n▲>>> ▲\n'


def test_apython_with_prompt_control_and_ainput(capfd):
    input_string = "{} ainput()\nhello\n".format(
        'await' if compat.PY35 else 'yield from')
    with patch('sys.stdin', new=io.StringIO(input_string)):
        with pytest.raises(SystemExit):
            apython.run_apython(
                ['--no-readline', '--banner=test', '--prompt-control=▲'])
    out, err = capfd.readouterr()
    assert out == ''
    assert err == "test\n▲>>> ▲▲▲'hello'\n▲>>> ▲\n"


def test_apython_with_ainput(capfd, use_readline):
    input_string = "{} ainput()\nhello\n".format(
        'await' if compat.PY35 else 'yield from')
    with patch('sys.stdin', new=io.StringIO(input_string)):
        with pytest.raises(SystemExit):
            apython.run_apython(['--banner=test'] + use_readline)
    out, err = capfd.readouterr()
    assert out == ''
    assert err == "test\n>>> 'hello'\n>>> \n"


def test_apython_with_stdout_logs(capfd, use_readline):
    with patch('sys.stdin', new=io.StringIO(
            'import sys; sys.stdout.write("logging") or 7\n')):
        with pytest.raises(SystemExit):
            apython.run_apython(['--banner=test'] + use_readline)
    out, err = capfd.readouterr()
    assert out == 'logging'
    assert err == 'test\n>>> 7\n>>> \n'


def test_apython_server(capfd, event_loop, monkeypatch):
    def run_forever(self, orig=InteractiveEventLoop.run_forever):
        if self.console_server is not None:
            self.call_later(0, self.stop)
        return orig(self)
    with patch('aioconsole.InteractiveEventLoop.run_forever', run_forever):
        with pytest.raises(SystemExit):
            apython.run_apython(['--serve=:0'])
    out, err = capfd.readouterr()
    assert out.startswith('The console is being served on')
    assert err == ''


def test_apython_non_existing_file(capfd):
    with pytest.raises(SystemExit):
        apython.run_apython(['idontexist.py'])
    out, err = capfd.readouterr()
    assert out == ''
    assert "No such file or directory: 'idontexist.py'" in err


def test_apython_non_existing_module(capfd):
    with pytest.raises(SystemExit):
        apython.run_apython(['-m', 'idontexist'])
    out, err = capfd.readouterr()
    assert out == ''
    assert "No module named idontexist" in err

def test_apython_pythonstartup(capfd, use_readline, monkeypatch, tempfd):

    monkeypatch.setenv('PYTHONSTARTUP', tempfd.name)
    tempfd.write(startupfile.encode())
    tempfd.flush()

    test_vectors = (
        ('print(foo)\n', '', '>>> 1\n'),
        ('print(hehe())\n', '', '>>> 42\n'),
        ('print(r)\n', '', '>>> 1.0\n'),
        ('pprint({1:2})\n', '{1: 2}\n', '>>> >>> \n'),
    )
    inputstr = ''.join([tv[0] for tv in test_vectors])
    outstr = ''.join([tv[1] for tv in test_vectors])
    errstr = 'test\n' + ''.join([tv[2] for tv in test_vectors])

    with patch('sys.stdin', new=io.StringIO(inputstr)):
        with pytest.raises(SystemExit):
            apython.run_apython(['--banner=test'] + use_readline)
    out, err = capfd.readouterr()
    assert out == outstr
    assert err == errstr
