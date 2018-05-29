import io
import sys
from contextlib import contextmanager

from unittest.mock import Mock, patch, call

import pytest

from aioconsole import compat
from aioconsole import apython, rlwrap


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


def test_basic_apython_usage(capsys, use_readline):
    with patch('sys.stdin', new=io.StringIO('1+1\n')):
        with pytest.raises(SystemExit):
            apython.run_apython(['--banner=test'] + use_readline)
    out, err = capsys.readouterr()
    assert out == ''
    assert err == 'test\n>>> 2\n>>> \n'


def test_apython_with_prompt_control(capsys):
    with patch('sys.stdin', new=io.StringIO('1+1\n')):
        with pytest.raises(SystemExit):
            apython.run_apython(
                ['--banner=test', '--prompt-control=▲', '--no-readline'])
    out, err = capsys.readouterr()
    assert out == ''
    assert err == 'test\n▲>>> ▲2\n▲>>> ▲\n'


def test_apython_with_prompt_control_and_ainput(capsys):
    input_string = "{} ainput()\nhello\n".format(
        'await' if compat.PY35 else 'yield from')
    with patch('sys.stdin', new=io.StringIO(input_string)):
        with pytest.raises(SystemExit):
            apython.run_apython(
                ['--no-readline', '--banner=test', '--prompt-control=▲'])
    out, err = capsys.readouterr()
    assert out == ''
    assert err == 'test\n▲>>> ▲▲▲hello\n▲>>> ▲\n'


def test_apython_with_ainput(capsys, use_readline):
    input_string = "{} ainput()\nhello\n".format(
        'await' if compat.PY35 else 'yield from')
    with patch('sys.stdin', new=io.StringIO(input_string)):
        with pytest.raises(SystemExit):
            apython.run_apython(['--banner=test'] + use_readline)
    out, err = capsys.readouterr()
    assert out == ''
    assert err == 'test\n>>> hello\n>>> \n'


def test_apython_with_stdout_logs(capsys, use_readline):
    with patch('sys.stdin', new=io.StringIO(
            'import sys; sys.stdout.write("logging")\n')):
        with pytest.raises(SystemExit):
            apython.run_apython(['--banner=test'] + use_readline)
    out, err = capsys.readouterr()
    assert out == 'logging'
    assert err == 'test\n>>> 7\n>>> \n'
