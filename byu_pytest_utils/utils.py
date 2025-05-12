import importlib
import json
import os.path
import runpy
from functools import wraps
from pathlib import Path
import inspect
from typing import Union
from dataclasses import dataclass

from byu_pytest_utils.html.html_renderer import HTMLRenderer

import pytest
import sys


@dataclass
class TestInfo:
    name: str
    points: float
    result: dict


def run_python_script(script, *args, module='__main__'):
    """
    Run the python script with arguments

    If the script expects STDIN, use the dialog framework instead

    :param script: Python script to run
    :param args: Arguments to the python script
    :param module: Defaults to '__main__'
    :return: Namespace as a result of running the script
    """
    if not os.path.exists(script):
        pytest.fail(f'The file {script} does not exist. Did you submit it?')

    def _input(*args):
        raise Exception("input function not supported for this test")

    sys.argv = [script, *(str(a) for a in args)]
    _globals = {
        'sys': sys,
        'input': _input
    }
    return runpy.run_path(script, _globals, module)


def get_results(test_results):
    return {
        'tests': [
            {
                'name': test_data['name'],
                'expected': group_result.get('expected', ''),
                'observed': group_result.get('observed', ''),
                'score': round(group_result['score'] * test_data['points'], 3),
                'max_score': round(group_result['max_score'] * test_data['points'], 3),
                'passed': group_result['passed'],
            }
            for binary_name, binary_results in test_results.items()
            for test_data in binary_results
            for group_name, group_result in test_data['result'].items()
        ]
    }


def get_gradescope_results(tests_info, html_report):
    """
    Get the gradescope results from the test_info and html_report

    :param tests_info: Dictionary of test information
    :param html_report: HTML-rendered output from comparison
    :return: Dictionary in Gradescope-compatible format
    """

    _, test_results = next(iter(tests_info.items()))

    return {
        'tests': [
            {
                'name': test_result['name'],
                'output': report,
                'score': round(test_result['points'], 3),
                'max_score': round(test_result['points'], 3),
                'visibility': 'visible',
            }
            for test_result, report in zip(test_results, html_report)
        ]
    }


def run_tests(tests_info, test_dir, headless=False):
    """
    Run the tests and return the results

    :param tests_info: TestInfo object
    :param test_dir: Directory where the tests are located
    :param headless: Whether to run the tests in headless mode
    :return: Results of the tests
    """
    results = get_results(tests_info)

    renderer = HTMLRenderer()
    render_info = renderer.parse_info(results)

    renderer.render(
        test_file_dir=test_dir,
        comparison_info=render_info,
        headless=headless
    )

    if headless:
        html_results = renderer.get_comparison_results()
        gradescope_output = get_gradescope_results(tests_info, html_results)

        with open('results.json', 'w') as f:
            json.dump(gradescope_output, f, indent=2)


def ensure_missing(file: Union[Path, str]):
    """
    Use the decorator to ensure the provided file is always missing
    when the test starts
    """
    if isinstance(file, str):
        file = Path(file)
    def decorator(func):
        @wraps(func)
        def new_func(*args, **kwargs):
            file.unlink(missing_ok=True)
            return func(*args, **kwargs)

        return new_func

    return decorator


def with_import(module_name=None, function_name=None):
    # Create a decorator
    def decorator(test_function):
        # Import function_name from module_name, then run function
        # with function_name passed in as first arg
        nonlocal function_name
        nonlocal module_name
        params = inspect.signature(test_function).parameters
        first_param = next((pname for pname, _ in params.items()))
        function_name = function_name or first_param
        module_name = module_name or function_name

        @wraps(test_function)
        def new_test_function(*args, **kwargs):
            try:
                module = importlib.import_module(module_name)
                func = getattr(module, function_name)
                return test_function(func, *args, **kwargs)

            except ModuleNotFoundError as err:
                pytest.fail(
                    f'{type(err).__name__}: {err}\n'
                    f'Unable to load {module_name}.py. '
                    f'Was {module_name}.py submitted?'
                )
            except ImportError as err:
                pytest.fail(
                    f'{type(err).__name__}: {err}\n'
                    f'Unable to load {module_name}.py. '
                    f'Are there errors in the file?'
                )
            except KeyError as err:
                pytest.fail(
                    f'{type(err).__name__}: {err}\n'
                    f'Unable to load {function_name} from {module_name}.py. '
                    f'Is {function_name} defined?'
                )

        # Modify signature to look like test_function but without
        # anything filled by with_import
        sig = inspect.signature(test_function)
        sig._parameters = dict(sig.parameters)
        del sig._parameters[first_param]
        new_test_function.__signature__ = sig

        return new_test_function

    if callable(module_name):
        # The decorator was used without arguments,
        # so this call is the decorator
        func = module_name
        module_name = None
        return decorator(func)
    else:
        return decorator
