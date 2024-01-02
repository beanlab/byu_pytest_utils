import logging
import subprocess as sp
from pathlib import Path


def compile_cpp(*input_files, flags=['-Wall', '-std=c++17'], output_exec=None, compiler='g++'):
    input_files = [str(file.absolute()) if isinstance(file, Path) else file for file in input_files]

    if output_exec is None:
        output_exec = next(Path(arg).stem for arg in input_files if arg.endswith(".cpp"))

    command = ' '.join(
        [compiler, *flags, '-o', output_exec, *input_files])
    print(command)

    proc = sp.run(command, stdout=sp.PIPE,
                  stderr=sp.STDOUT, shell=True, text=True)

    if proc.returncode != 0:
        raise Exception(f'"{command}" failed:\n{proc.stdout}')

    if proc.stdout:
        logging.warning(f'"{command}" gave output:\n{proc.stdout}')

    return str(Path(output_exec).absolute())


def diff_outputs(left: str, right: str):
    left_lines = left.splitlines()
    right_lines = right.splitlines()
    left_width = max((len(line) for line in left_lines)) if left_lines else 1
    right_width = max((len(line)
                      for line in right_lines)) if right_lines else 1
    left_view_lines = [f"{line:<{left_width}}" for line in left_lines]
    right_view_lines = [f"{line:<{right_width}}" for line in right_lines]

    # Pad with empty lines
    while len(left_view_lines) < len(right_view_lines):
        left_view_lines.append(' ' * left_width)
    while len(right_view_lines) < len(left_view_lines):
        right_view_lines.append(' ' * right_width)

    # Join lines side by side
    diff_view = [
        'Observed (left) == Expected (right)',
        *(l + ' | ' + r for l, r in zip(left_view_lines, right_view_lines))
    ]
    return '\n'.join(diff_view)


def format_results_for_gradescope(test_results):
    return {
        'tests': [
            {
                'name': '.'.join([binary_name, test_data['name'], group_name]),
                'output': diff_outputs(group_result.get('observed', ''), group_result.get('expected', '')),
                'score': round(group_result['score'] * test_data['points'], 3),
                'max_score': round(group_result['max_score'] * test_data['points'], 3),
                'visibility': 'visible',
            }
            for binary_name, binary_results in test_results.items()
            for test_data in binary_results
            for group_name, group_result in test_data['result'].items()
        ]
    }

