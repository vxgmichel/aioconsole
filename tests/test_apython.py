from unittest.mock import patch, call

import pytest

from aioconsole import apython

@pytest.fixture(params=['Darwin', 'Linux'])
def platform(request):
    return request.param

@patch('aioconsole.apython.ctypes')
@patch('aioconsole.apython.platform')
def test_input_with_stderr_prompt_darwin(m_platform, m_ctypes, platform):
    m_platform.system.return_value = platform


    if platform == 'Darwin':
        stdin = '__stdinp'
        stderr = '__stderrp'
    else:
        stdin = 'stdin'
        stderr = 'stderr'

    api = m_ctypes.pythonapi
    call_readline = api.PyOS_Readline
    result = call_readline.return_value
    result.__len__.return_value = 1

    apython.input_with_stderr_prompt()

    m_ctypes.c_void_p.in_dll.assert_has_calls([
        call(api, stdin),
        call(api, stderr),
    ])
