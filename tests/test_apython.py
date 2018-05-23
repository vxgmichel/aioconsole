import io

from unittest.mock import patch, call

import pytest

from aioconsole import apython, rlwrap


@pytest.fixture(params=['darwin', 'linux'])
def platform(request):
    return request.param


@patch('aioconsole.rlwrap.ctypes')
@patch('aioconsole.rlwrap.sys')
def test_input_with_stderr_prompt_darwin(m_sys, m_ctypes, platform):
    m_sys.platform = platform

    if platform == 'darwin':
        stdin = '__stdinp'
        stderr = '__stderrp'
    else:
        stdin = 'stdin'
        stderr = 'stderr'

    api = m_ctypes.pythonapi
    call_readline = api.PyOS_Readline
    result = call_readline.return_value
    result.__len__.return_value = 1

    rlwrap.input(use_stderr=True)

    m_ctypes.c_void_p.in_dll.assert_has_calls([
        call(api, stdin),
        call(api, stderr),
    ])


def test_basic_apython_usage(capsys):
    with patch('sys.stdin', new=io.StringIO('1+1\n')):
        apython.run_apython(['--no-readline', '--banner=test'])
    out, err = capsys.readouterr()
    assert out == ''
    assert err == 'test\n>>> 2\n>>> \n'


def test_apython_with_prompt_control(capsys):
    with patch('sys.stdin', new=io.StringIO('1+1\n')):
        apython.run_apython(
            ['--no-readline', '--banner=test', '--prompt-control=▲'])
    out, err = capsys.readouterr()
    assert out == ''
    assert err == 'test\n▲>>> ▲2\n▲>>> ▲\n'


def test_apython_with_ainput(capsys):
    with patch('sys.stdin', new=io.StringIO('await ainput()\nhello\n')):
        apython.run_apython(
            ['--no-readline', '--banner=test', '--prompt-control=▲'])
    out, err = capsys.readouterr()
    assert out == ''
    assert err == 'test\n▲>>> ▲▲▲hello\n▲>>> ▲\n'
