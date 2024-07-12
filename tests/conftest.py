import pytest
@pytest.hookimpl(tryfirst=True)
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    # Suppress or modify terminal output here
    terminalreporter._tw.write("Custom summary output\n")
    # Optionally, you can still call the original summary
    # terminalreporter.summary_stats()

@pytest.hookimpl(tryfirst=True)
def pytest_report_teststatus(report, config):
    # Suppress the verbose output for each test
    return (report.outcome, '', '')

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logreport(report):
    # Suppress individual test reports
    report.longrepr = ''
    report.sections = []