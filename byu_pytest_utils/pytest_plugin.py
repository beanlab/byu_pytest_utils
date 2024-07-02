import re

import pytest
import json
import diff_match_patch as dmp_module
import pytest_html
from bs4 import BeautifulSoup
from pytest_html.hooks import pytest_html_results_table_html
from html2text import html2text

metadata = {}
test_group_stats = {}

MIN_LINES_DIFF = 3

import pytest_html


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    extras = getattr(report, "extras", [])
    if report.when == "call":
        # always add url to report
        extras.append(pytest_html.extras.url("http://www.example.com/"))
        xfail = hasattr(report, "wasxfail")
        if (report.skipped and xfail) or (report.failed and not xfail):
            # only add additional html on failure
            extras.append(pytest_html.extras.html("<div>Additional HTML</div>"))
        report.extras = extras


#
# def pytest_html_results_table_row(report, cells):
#     print(f"\nreport:\n{report}\n\n\n cells {cells}\n\n")
#     if report.failed:
#         del cells[:]


def diff_prettyHtml(diffs):
    """Convert a diff array into a pretty HTML report.

    Args:
      diffs: Array of diff tuples.

    Returns:
      HTML representation.
    """
    dmp = dmp_module.diff_match_patch()
    html = []
    for op, data in diffs:
        text = (
            data.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )

        if op == dmp.DIFF_INSERT:
            html.append('<span style="background:#e6ffe6;">%s</span>' % text)
        elif op == dmp.DIFF_DELETE:
            pass
            # html.append('<del style="background:#ffe6e6;">%s</del>' % text)
        elif op == dmp.DIFF_EQUAL:
            html.append("<span>%s</span>" % text)
    return "".join(html)


def pytest_html_results_table_html(report, data: list[str]):
    # xfail = hasattr(report, "wasxfail")
    # (report.skipped and xfail) or (report.failed and not xfail):
    # if report.failed or xfail:

    text = "".join(data)
    print(f"{'Z' * 77} \n [[[{text}]]] \n\n")
    # Find the assertion expressions
    pattern = r"assert (?:&#x27;|&quot;)(.*)(?:&#x27;|&quot;) == (?:&#x27;|&quot;)(.*)(?:&#x27;|&quot;)(?![\s\S]*assert)[\s\S]*AssertionError"

    if "assert" in text and (match := re.search(pattern, text, flags=re.MULTILINE)):
        data.clear()
        left = html2text(match.group(1))
        right = html2text(match.group(2))
        dmp = dmp_module.diff_match_patch()
        right_diff = dmp.diff_main(right, left)
        right_html = diff_prettyHtml(right_diff)
        left_diff = dmp.diff_main(left, right)
        left_html = diff_prettyHtml(left_diff)
        new_html = (f'<div style="max-width: 45%; float: left; margin: 2%;">'
                    f'<h1> Old </h1>'
                    f'{left_html}'
                    f'</div>'
                    f'<div style="max-width: 45%; float: left; margin: 2%;">'
                    f'<h1> New </h1>'
                    f'{right_html}'
                    f'</div>')
        data.append(new_html)
        print("Data" * 7 + f"{data}")


def html_to_ansi(html):
    # ANSI escape code mapping
    html_to_ansi = {
        "#ffe6e6": "\033[41m",  # Red background
        "#e6ffe6": "\033[42m",  # Green background
        "reset": "\033[0m"  # Reset
    }

    # Parse HTML
    soup = BeautifulSoup(html, "html.parser")

    # Function to convert HTML to ANSI text
    def html_to_ansi_text(soup):
        ansi_text = ""
        for elem in soup.descendants:
            if elem.name == "span":
                ansi_text += elem.get_text()
            elif elem.name == "del":
                color_code = html_to_ansi.get(elem.get("style")[12:19], "")
                ansi_text += f"{color_code}{elem.get_text()}{html_to_ansi['reset']}"
            elif elem.name == "ins":
                color_code = html_to_ansi.get(elem.get("style")[12:19], "")
                ansi_text += f"{color_code}{elem.get_text()}{html_to_ansi['reset']}"
            elif elem.name == "br":
                ansi_text += "\n"
            elif elem.name == "para":
                ansi_text += "¶"
        return ansi_text

    # Convert HTML to ANSI text
    ansi_output = html_to_ansi_text(soup)
    return ansi_output


# def pytest_assertrepr_compare(config, op, left, right):
#     if op == '==' \
#             and isinstance(left, str) and len(left_lines := left.splitlines()) > MIN_LINES_DIFF \
#             and isinstance(right, str) and len(right_lines := right.splitlines()) > MIN_LINES_DIFF:
#         # Use custom side-by-side assertion diff
#         # How wide?
#         left_width = max((len(line) for line in left_lines))
#         right_width = max((len(line) for line in right_lines))
#         left_view_lines = [f"{line:<{left_width}}" for line in left_lines]
#         right_view_lines = [f"{line:<{right_width}}" for line in right_lines]
#
#         # Pad with empty lines
#         while len(left_view_lines) < len(right_view_lines):
#             left_view_lines.append(' ' * left_width)
#         while len(right_view_lines) < len(left_view_lines):
#             right_view_lines.append(' ' * right_width)
#
#         # Join lines side by side
#         diff_view = [
#             'Observed (left) == Expected (right)',
#             *(l + ' | ' + r for l, r in zip(left_view_lines, right_view_lines))
#         ]
#         return diff_view


def pytest_generate_tests(metafunc):
    if hasattr(metafunc.function, '_group_stats'):
        group_stats = metafunc.function._group_stats

        for group_name, stats in group_stats.items():
            stats['max_score'] *= getattr(metafunc.function, 'max_score', 0)
            stats['score'] *= getattr(metafunc.function, 'max_score', 0)
            test_name = f'{metafunc.function.__module__}.py::{metafunc.function.__name__}[{group_name}]'
            test_group_stats[test_name] = stats

        metafunc.parametrize('group_name', group_stats.keys())
    else:
        test_name = f'{metafunc.function.__module__}.py::{metafunc.function.__name__}'
        test_group_stats[test_name] = {
            'max_score': getattr(metafunc.function, 'max_score', 0)
        }


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item):
    x = yield
    if item._obj not in metadata:
        metadata[item._obj] = {}
    metadata[item._obj]['max_score'] = getattr(item._obj, 'max_score', 0)
    metadata[item._obj]['visibility'] = getattr(
        item._obj, 'visibility', 'visible')
    x._result.metadata_key = item._obj


@pytest.hookimpl(hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem):
    # Deprecated function - remove with CheckIO stuff
    outcome = yield
    excinfo = outcome.excinfo
    if excinfo is not None \
            and excinfo[0] is AssertionError \
            and hasattr(excinfo[1], '_partial_credit'):
        metadata[pyfuncitem._obj]['partial_credit'] = excinfo[1]._partial_credit


def pytest_terminal_summary(terminalreporter, exitstatus):
    json_results = {'tests': []}

    all_tests = []
    if 'passed' in terminalreporter.stats:
        all_tests = all_tests + terminalreporter.stats['passed']
    if 'failed' in terminalreporter.stats:
        all_tests = all_tests + terminalreporter.stats['failed']

    for s in all_tests:
        output = s.capstdout + '\n' + s.capstderr
        # The group stats key is the name of the test (eg test_lab08.py::test_get_and_set)
        # However s.nodeid includes the full relative path to test (causing Key Error)
        # The following line takes that rel path from s.nodeid and extracts just filename
        group_stats_key = s.nodeid.split('/')[-1]
        group_stats = test_group_stats[group_stats_key]

        max_score = group_stats['max_score']
        score = group_stats.get('score', max_score if s.passed else 0)

        output += s.longreprtext

        json_results["tests"].append(
            {
                'score': round(score, 4),
                'max_score': round(max_score, 4),
                'name': group_stats_key,
                'output': output,
                'visibility': 'visible',
            }
        )

    with open('results.json', 'w') as results:
        results.write(json.dumps(json_results, indent=4))
