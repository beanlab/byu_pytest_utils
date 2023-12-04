import argparse
import asyncio
import contextlib
import os
import re
import runpy
import subprocess
import subprocess as sp
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from queue import Queue, Empty
from pathlib import Path
import os

from byu_pytest_utils.edit_dist import edit_dist

_EXEC_DEFAULT_MAX_WAITTIME_BEFORE_INPUTTING = 0.1
_EXEC_DEFAULT_WARMUP_TIME = 0.5
_EXEC_DEFAULT_MAX_PROC_EXEC_TIME = 10
_EXEC_DEFAULT_MAX_OUTPUT_LEN = 2000


def _make_group_stats_decorator(group_stats):
    def decorator(func):
        # func should have empty (pass) body and no arguments
        def new_func(group_name):
            group_stat = group_stats[group_name]
            if not group_stat['passed']:
                assert group_stat['observed'] == group_stat['expected']

        new_func._group_stats = group_stats
        new_func.__name__ = func.__name__
        new_func.__module__ = func.__module__
        return new_func

    return decorator


def _ensure_absent(output_file):
    if output_file is not None:
        if isinstance(output_file, str):
            output_file = Path(output_file)
        output_file.unlink(missing_ok=True)


def dialog_exec(dialog_file, executable, *args, output_file=None,
                close_stdin_after_all_inputs_given=False,
                max_waittime_before_inputting=_EXEC_DEFAULT_MAX_WAITTIME_BEFORE_INPUTTING,
                warmup_time=_EXEC_DEFAULT_WARMUP_TIME,
                max_proc_exec_time=_EXEC_DEFAULT_MAX_PROC_EXEC_TIME,
                max_output_len=_EXEC_DEFAULT_MAX_OUTPUT_LEN, **popen_args):
    try:
        # Ensure the output file isn't leftover from a previous run
        _ensure_absent(output_file)

        if callable(executable):
            executable = executable()

        args = [arg() if callable(arg) else arg for arg in args]

        # Run the script
        group_stats = DialogChecker(dialog_file, echo_output=True) \
            .run_exec(executable, *args, output_file=output_file,
                      close_stdin_after_all_inputs_given=close_stdin_after_all_inputs_given,
                      max_waittime_before_inputting=max_waittime_before_inputting,
                      warmup_time=warmup_time,
                      max_proc_exec_time=max_proc_exec_time,
                      max_output_len=max_output_len, **popen_args)

    except Exception as ex:
        group_stats = {
            'load-tests': {
                'group_name': 'load-tests',
                'expected': '',
                'observed': traceback.format_exc(),
                'score': 0,
                'max_score': 1,
                'passed': False,
            }
        }

    return _make_group_stats_decorator(group_stats)


def dialog(dialog_file, script, *script_args, output_file=None):
    try:
        # Ensure the output file isn't leftover from a previous run
        _ensure_absent(output_file)
        if callable(script):
            script = script()
        script_args = [arg() if callable(arg) else arg for arg in script_args]

        # Run the script
        group_stats = DialogChecker(dialog_file, echo_output=True) \
            .run_script(script, *script_args, output_file=output_file)

    except Exception as ex:
        group_stats = {
            'load-tests': {
                'group_name': 'load-tests',
                'expected': '',
                'observed': traceback.format_exc(),
                'score': 0,
                'max_score': 1,
                'passed': False,
            }
        }

    return _make_group_stats_decorator(group_stats)


async def _read_stream(stream: asyncio.StreamReader, timeout: float):
    """
    Reads the stream until the end of the current content
    Stops waiting for content after `timeout` seconds
    Returns decoded content (i.e. str not bytes)
    """
    buffer = []

    while True:
        try:
            token = await asyncio.wait_for(stream.read(1), timeout)
            if not token:
                # stream.read() returns an empty byte when EOF is reached
                break
            buffer.append(token.decode())

        except asyncio.TimeoutError:
            # No bytes have been written for at least `timeout` seconds
            break

    return ''.join(buffer)


async def _run_exec_with_io(exec: list[str], inputs: list[str], read_timeout: float):
    """
    Run an executable. Provided content via STDIN. Capture STDOUT.
    :param exec: executable and arguments
    :param inputs: list of inputs to executable
                   assumes newlines have been added if they are necessary
    :param read_timeout: how long to wait after a byte is written to STDOUT before returning
    :return: STDOUT of the executable so far (includes echoed inputs)
    """
    PIPE = asyncio.subprocess.PIPE
    proc = await asyncio.create_subprocess_exec(
        *exec, stdin=PIPE, stdout=PIPE, stderr=asyncio.subprocess.STDOUT)

    output = [await _read_stream(proc.stdout, read_timeout)]
    error = ''

    for content in inputs:
        if proc.returncode is not None:
            # Process has completed
            error = 'the program exited before all inputs were provided'
            break

        output.append(content)
        proc.stdin.write(content.encode())
        await proc.stdin.drain()

        response = await _read_stream(proc.stdout, read_timeout)

        if not response:
            # i.e. nothing has been written since we provided input
            error = 'the program has been given input, but has not produced any new output'
            break

        output.append(response)

    proc.stdin.close()

    code = await proc.wait()
    if code != 0:
        error = f'the program returned a non-zero exit code: {code}'

    return ''.join(output), error


class DialogChecker:
    DEFAULT_GROUP = '.'
    DEFAULT_GROUP_NAME = 'everything-else'
    MAX_PARTIAL_CREDIT = 1
    GAP = '~'

    def __init__(self, dialog_file, echo_output):
        self.echo_output = echo_output

        with open(dialog_file) as file:
            text = file.read()
            self.inputs, no_inputs = self._extract_input(text)
            self.group_weights, self.group_names, self.group_sequence, self.expected_output = \
                self._extract_groups(no_inputs)
        self.observed_output = ""

    @staticmethod
    def _extract_input(dialogue_contents: str):
        # Find all tokens delimited by << and >> and return them
        # as a list along with the original contents with the << and >> removed
        inputs = re.findall(r'<<(.*?)>>', dialogue_contents, re.DOTALL)
        dialogue_contents = re.sub(
            r'<<(.*?)>>', r'\1', dialogue_contents, flags=re.DOTALL)
        return inputs, dialogue_contents

    @staticmethod
    def _extract_groups(dialog_contents: str):
        # blah blah [[foo;name;10]] blah blah

        group_weights = {DialogChecker.DEFAULT_GROUP: 0}
        group_names = {
            DialogChecker.DEFAULT_GROUP: DialogChecker.DEFAULT_GROUP_NAME}

        group_sequence = ''

        # Iterate through the dialog contents
        # Characters not in a group are assigned to weight group 'a'
        # Each weight group is assigned the next letter of the alphabet
        # A group starts with [[ and ends with ]]
        # The semicolon separates the group text from the weight
        # All text in a group is assigned to the same weight group
        # e.g.
        # quux [[foo;test-foo;30]] bar [[baz;test-baz;20]] quux
        # produces groups: aaaaabbbaaaacccaaaa
        # and group_weights: {'-': 40, 'b': 30, 'c': 20}

        i = 0
        while i < len(dialog_contents):
            if dialog_contents[i:i + 2] == '``':
                # Start of a group
                group_symbol = chr(ord('a') - 1 + len(group_weights))
                group_match = re.search(
                    r'``(.*?);(.+?);(\d+?)``', dialog_contents[i:], flags=re.DOTALL)
                group_text = group_match.group(1)
                group_name = group_match.group(2)
                group_names[group_symbol] = group_name
                group_weights[group_symbol] = int(group_match.group(3))
                group_sequence += group_symbol * len(group_text)
                i += group_match.end()
            else:
                # Not in a group
                group_sequence += DialogChecker.DEFAULT_GROUP
                i += 1
        total = sum(group_weights.values())
        if total > 100:
            raise Exception('Group weights must add up to 100 or less')
        group_weights[DialogChecker.DEFAULT_GROUP] = 100 - total

        # Then remove the groups from the dialog contents
        dialog_contents = re.sub(
            r'``(.*?);(.+?);(\d+?)``', r'\1', dialog_contents, flags=re.DOTALL)

        return group_weights, group_names, group_sequence, dialog_contents

    def _score_output(self, observed_output):
        _, obs, exp = edit_dist(
            observed_output,
            self.expected_output,
            GAP=DialogChecker.GAP
        )

        # insert gaps (i.e. DEFAULT_GROUP) into self.groups to match exp
        # then iterate over obs, exp, and groups
        # to compute rate of matches per group
        # (a gap in obs counts should use the prior group)
        # and return the score for each group
        # e.g. if groups is '---bbbcccc'
        # and group_weights is {'-': 50, 'b': 20, 'c': 30}
        # and exp is 'foobar~bazz'
        # and obs is 'boobarflaz~'
        # then groups should become '---bbbbcccc'

        if len(exp) - exp.count(DialogChecker.GAP) != len(self.group_sequence):
            raise Exception('Too many gaps in expected output')

        group_ids = ''
        i = 0
        g = 0
        while i < len(exp):
            if exp[i] == DialogChecker.GAP:
                group_ids += group_ids[-1] if group_ids else DialogChecker.DEFAULT_GROUP
                i += 1
            else:
                group_ids += self.group_sequence[g]
                g += 1
                i += 1
        assert len(group_ids) == len(exp)

        # Compute group scores
        group_counts = {}
        group_matches = {}
        group_obs = {}
        group_exp = {}
        for obs_c, exp_c, group_id in zip(obs, exp, group_ids):
            if obs_c == exp_c:
                group_matches[group_id] = group_matches.get(group_id, 0) + 1
            group_counts[group_id] = group_counts.get(group_id, 0) + 1
            group_obs[group_id] = group_obs.get(group_id, '') + obs_c
            group_exp[group_id] = group_exp.get(group_id, '') + exp_c

        # Fix default group obs/exp
        # Use the full output, and pad with spaces to 80 chars
        def pad(text):
            return text + ' ' * (80 - len(text))

        group_obs[DialogChecker.DEFAULT_GROUP] = pad(
            obs.replace(DialogChecker.GAP, ''))
        group_exp[DialogChecker.DEFAULT_GROUP] = pad(
            exp.replace(DialogChecker.GAP, ''))

        group_stats = {}
        for group_id, group_name in self.group_names.items():
            group_max = self.group_weights[group_id] / 100
            group_stats[group_name] = {
                'group_name': group_name,
                'expected': group_exp[group_id].replace(DialogChecker.GAP, ''),
                'observed': group_obs[group_id].replace(DialogChecker.GAP, ''),
                'score': group_matches.get(group_id, 0) / group_counts[group_id] * group_max,
                'max_score': group_max,
                'passed': group_matches.get(group_id, -1) == group_counts[group_id],
            }

        return group_stats

    def _consume_output(self, printed_text, max_output_len=None):
        self.observed_output += printed_text
        if self.echo_output:
            print(printed_text, end='')
        if max_output_len is not None and len(self.observed_output) > max_output_len:
            raise Exception('the program has printed too much text')

    @wraps(input)
    def _py_input(self, prompt):
        self._consume_output(prompt)
        if not self.inputs:
            raise Exception("input() called more times than expected")
        input_text = self.inputs.pop(0)
        self._consume_output(input_text + '\n')
        if self.echo_output:
            print(input_text)
        return input_text

    @wraps(print)
    def _py_print(self, *values, **kwargs):
        sep = kwargs.get('sep', ' ')
        end = kwargs.get('end', '\n')
        res = sep.join(str(t) for t in values) + end
        self._consume_output(res)

    def run_script(self, script_name, *args, output_file=None, module='__main__'):
        # Intercept input, print, and sys.argv
        sys.argv = [script_name, *(str(a) for a in args)]
        _globals = {
            'input': self._py_input,
            'print': self._py_print,
            'sys': sys
        }

        # Run script as __main__
        try:
            runpy.run_path(script_name, _globals, module)

            if output_file is not None:
                if os.path.exists(output_file):
                    with open(output_file) as output:
                        group_stats = self._score_output(output.read())
                else:
                    group_stats = self._score_output(
                        f"File not found: {output_file}. Did you write it?")
            else:
                group_stats = self._score_output(self.observed_output)

        except Exception as ex:
            # get stack trace as string
            exception = f"Exception: {ex}\n{traceback.format_exc()}"
            group_stats = self._score_output(exception)

        return group_stats

    def run_exec(self, executable, *args, output_file=None,
                 close_stdin_after_all_inputs_given=False,
                 max_waittime_before_inputting=_EXEC_DEFAULT_MAX_WAITTIME_BEFORE_INPUTTING,
                 warmup_time=_EXEC_DEFAULT_WARMUP_TIME,
                 max_proc_exec_time=_EXEC_DEFAULT_MAX_PROC_EXEC_TIME,
                 max_output_len=_EXEC_DEFAULT_MAX_OUTPUT_LEN, **popen_args):
        args = [executable, *(str(a) for a in args)]

        output, error = asyncio.run(_run_exec_with_io(args, [c + '\n' for c in self.inputs], read_timeout=1))
        if error:
            output += '\nError: ' + error

        try:
            if output_file is not None:
                if os.path.exists(output_file):
                    with open(output_file) as file:
                        group_stats = self._score_output(file.read())
                else:
                    group_stats = self._score_output(
                        f'File not found: {output_file}. Did you write it?')
            else:
                group_stats = self._score_output(output)

        except Exception as ex:
            exception = f'Exception: {ex}\n{traceback.format_exc()}'
            group_stats = self._score_output(exception)

        return group_stats


def record_script(dialog_file, script_name, *script_args):
    # Intercept input, print, and sys.argv
    sys.argv = [script_name, *(str(a) for a in script_args)]
    with open(dialog_file, 'w') as file:
        def _input(prompt):
            file.write(prompt)
            response = input(prompt)
            file.write(f'<<{response}>>\n')
            return response

        def _print(*args, **kwargs):
            print(*args, **kwargs)
            print(*args, **kwargs, file=file)

        _globals = {
            'input': _input,
            'print': _print,
            'sys': sys
        }

        # Run script as __main__
        result = runpy.run_path(script_name, _globals, '__main__')

    return result


def record_exec(dialog_file, executable, *args):
    args = [executable, *(str(a) for a in args)]
    with open(dialog_file, 'w') as file:
        process = sp.Popen(args, stdin=sp.PIPE,
                           stdout=sp.PIPE, stderr=sp.STDOUT)
        for line in _exec_read_stdout_with_timeout(process):
            if line is None:
                input_to_give = input()
                process.stdin.write((input_to_give + '\n').encode())
                process.stdin.flush()
                file.write(f'<<{input_to_give}>>\n')
                continue
            print(line, end='')
            file.write(line)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('dialog_file', help='Dialog file to write')
    parser.add_argument('to_run', help='Python script or executable to run')
    parser.add_argument('args', nargs='*',
                        help='Arguments (if any) to the Python script or executable')
    parser.add_argument('-e', '--exec', action='store_true',
                        help='Interpret `to_run` as an executable instead of a Python script')
    args = parser.parse_args()

    if args.exec:
        record_exec(args.dialog_file, args.to_run, *args.args)
    else:
        record_script(args.dialog_file, args.to_run, *args.args)
