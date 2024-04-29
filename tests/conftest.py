import pytest
import asyncio


def import_uvloop():
    try:
        import uvloop
    except ImportError:
        return None
    else:
        return uvloop


@pytest.fixture(
    params=(
        "default",
        "uvloop",
    ),
)
def event_loop_policy(request):
    if request.param == "default":
        return asyncio.DefaultEventLoopPolicy()
    elif request.param == "uvloop":
        uvloop = import_uvloop()
        if uvloop is None:
            pytest.skip("uvloop is not installed")
        return uvloop.EventLoopPolicy()
    return request.param


@pytest.fixture
def is_uvloop(event_loop_policy):
    uvloop = import_uvloop()
    if uvloop is None:
        return False
    return isinstance(event_loop_policy, uvloop.EventLoopPolicy)
