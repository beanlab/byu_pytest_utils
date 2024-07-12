import re

import pytest
import json
import diff_match_patch as dmp_module
from html2text import html2text

def pytest_load_initial_conftests(early_config, parser, args: list):
    """This hook sets default arguments for pytest"""
    early_config.option.htmlpath = "report.html"
    # Ensure summary is shown
    if '--no-summary' in args:
        args.remove('--no-summary')
    # early_config.option.verbosity = 2
    # early_config.option.verbose = 2
    early_config.option.r = 1
    print(f"ARGS:{args}")
    print(f"Options: {early_config.option}")
    with open("ping.txt", "w") as f:
        f.write(f"ARGS:{args}\n")
        f.write(f"Options: {early_config.option}")


def pytest_runtest_logreport(report):
    report.longrepr = None
    if report.when != "teardown":
        return




metadata = {}
test_group_stats = {}

MIN_LINES_DIFF = 3


def index_of_any(words, text: str):
    for word in words:
        if word in text:
            return text.index(word)
    return None


def clean_html_chars(html):
    return (html.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\\n", "<br>"))


def split_on_error(all_text, error_words):
    index_of_error = index_of_any(error_words, all_text)
    return all_text[:index_of_error], all_text[index_of_error:]


def diff_prettyHtml(diffs):
    """Convert a diff array into a pretty HTML report.

    Args:
      diffs: Array of diff tuples.

    Returns:
      HTML representation.
    """
    dmp = dmp_module.diff_match_patch()
    html = []
    diffs = [(op, clean_html_chars(data)) for op, data in diffs if op != dmp.DIFF_DELETE]
    for op, text in diffs:
        if op == dmp.DIFF_INSERT:
            html.append(f'<span style="background:#e6ffe6;">{text}</span>')
        elif op == dmp.DIFF_EQUAL:
            html.append(f'<span>{text}</span>')
    return "".join(html)


def pytest_html_results_table_html(report, data: list[str]):
    text = "".join(data)
    # Find the assertion expressions
    pattern = r"assert (?:&#x27;|&quot;)(.*)(?:&#x27;|&quot;) == (?:&#x27;|&quot;)(.*)(?:&#x27;|&quot;)(?![\s\S]*assert)[\s\S]*AssertionError"

    if "assert" in text and (match := re.search(pattern, text, flags=re.MULTILINE)):
        # Delete all strings from data, then add new html
        data.clear()
        observed = html2text(match.group(1))
        expected = html2text(match.group(2))

        error_words = ["Traceback", "Exception: ", "Error: "]
        error_html = ""
        if any(error_word in observed for error_word in error_words):
            observed, error_text = split_on_error(observed, error_words)
            error_html = f'<span class="error">{error_text}</span>'

        right_html = diff_texts_as_html(expected, observed)
        left_html = diff_texts_as_html(observed, expected)
        new_html = (f'<div style="max-width: 45%; float: left; margin: 2%;">'
                    f'<h1> Old </h1>'
                    f'{left_html}'
                    f'</div>'
                    f'<div style="max-width: 45%; float: left; margin: 2%;">'
                    f'<h1> New </h1>'
                    f'{right_html}'
                    f'{error_html}'
                    f'</div>')
        data.append(new_html)


def diff_texts_as_html(old, new):
    dmp = dmp_module.diff_match_patch()
    dmp.Diff_EditCost = 2
    diff = dmp.diff_main(old, new)
    dmp.diff_cleanupEfficiency(diff)
    return diff_prettyHtml(diff)


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
