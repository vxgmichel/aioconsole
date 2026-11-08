import gc
import io
import sys
import warnings

import pytest

from aioconsole import InteractiveEventLoop


@pytest.fixture
def unraisables(monkeypatch):
    """Collect exceptions ignored in `__del__` methods."""
    result = []
    monkeypatch.setattr(sys, "unraisablehook", result.append)
    return result


@pytest.mark.filterwarnings("ignore:coroutine .* was never awaited:RuntimeWarning")
def test_close_cancels_pending_console_task(unraisables):
    loop = InteractiveEventLoop()
    task = loop.console_task
    loop.close()
    assert task.cancelled()
    # The loop never ran, so it is collected (and `__del__` called) here
    del loop, task
    gc.collect()
    assert unraisables == []


@pytest.mark.parametrize("finalize", ["close", "__del__"])
def test_console_task_exception_is_retrieved(monkeypatch, finalize):
    # The console reads EOF right away and exits with SystemExit
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    loop = InteractiveEventLoop(banner="")
    with pytest.raises(SystemExit):
        loop.run_forever()
    task = loop.console_task
    assert task.done() and not task.cancelled()
    assert task._log_traceback  # Would log "exception was never retrieved"
    # The standard streams cache keeps the loop alive, call `__del__` directly
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ResourceWarning)
        getattr(loop, finalize)()
    assert loop.is_closed()
    assert not task._log_traceback
