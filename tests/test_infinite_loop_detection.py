import pytest
from byu_pytest_utils.dialog import _run_exec_with_io
from byu_pytest_utils import this_folder


@pytest.mark.asyncio
async def test_infinite_loop_detection():
    stdout, error = await _run_exec_with_io(
        ['python', str(this_folder / 'script_for_infinite_loop.py')],
        [],
        read_timeout=1,
        finish_timeout=3
    )
    assert stdout == 'bar\n'
    assert 'The program failed to finish in the expected amount of time; do you have an infinite loop?\n' in error
