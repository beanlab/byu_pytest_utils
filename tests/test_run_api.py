from byu_pytest_utils import run_exec, max_score, test_files


def test_run_exec():
    stats = run_exec("python3", "script_for_dialog_passes.py", 'woot', 7,
                     expected_stdio=test_files / "test_dialog_should_pass.txt")
    assert 'stdout' in stats
    assert stats['stdout']['passed']


def test_run_exec_with_failed_test():
    stats = run_exec(
        "python3", "script_for_dialog_fails.py", 'woot', 7, 'foobar',
        expected_stdio=test_files / "test_dialog_should_pass.txt"
    )
    assert 'stdout' in stats
    assert not stats['stdout']['passed']


'''

@run_exec(
    "python3", "script_for_dialog_passes.py", 'woot',
    expected_stdio=test_files / "test_dialog_expects_more_input.txt",
)
@max_score(10)
def test_dialog_expects_more_input_should_fail():
    """
    args, seven, and eight should pass,
    but nine and everything-else should not
    """


@max_score(10)
@run_exec(
    "python3", "script_for_dialog_passes.py", 'woot',
    expected_stdio=test_files / "test_dialog_expects_less_input.txt",
)
def test_dialog_expects_less_input_should_fail():
    """
    seven should pass, but everything-else should fail
    There should be an error: "Input called more times than expected"
    """


@max_score(10)
@run_exec(
    "python3", "script_that_writes_to_file.py",
    test_files / "basic_text_input_file.txt",
    "basic_text_output.observed.txt",
    expected_files=[
        (test_files / "basic_text_output.expected.txt", "basic_text_output.observed.txt")
    ]
)
def test_dialog_output_file():
    """
    Should pass cleanly
    """


@max_score(10)
@run_exec(
    "python3", "script_that_writes_to_file.py",
    test_files / "basic_text_input_file.txt",
    "basic_text_output.observed.txt",
    expected_files=[
        (test_files / "basic_text_output.dialog.expected.txt", "basic_text_output.observed.txt")
    ]
)
def test_dialog_output_file_groups():
    """
    Should match with partial-credit groups
    """
'''
