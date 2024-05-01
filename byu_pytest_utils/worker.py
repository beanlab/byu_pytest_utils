import os
import runpy
import sys
import traceback
from functools import wraps

def _run_script(
        script_name, *args,
        module='__main__',
        echo_output=False
):
    inputs = os.environ.get('INPUTS', None)
    if inputs:
        inputs = inputs.split('\n')

    if inputs is None:
        inputs = []

    # Intercept input, print, and sys.argv
    sys.argv = [script_name, *(str(a) for a in args)]

    output_tokens = []


    @wraps(input)
    def _py_input(prompt=''):
        output_tokens.append(prompt)
        if not inputs:
            raise Exception("input() called more times than expected")
        input_text = inputs.pop(0)
        output_tokens.append(input_text + '\n')
        if echo_output:
            print(input_text)
        return input_text


    @wraps(print)
    def _py_print(*values, **kwargs):
        sep = kwargs.get('sep', ' ')
        end = kwargs.get('end', '\n')
        res = sep.join(str(t) for t in values) + end
        output_tokens.append(res)

    _globals = {
        'input': _py_input,
        'print': _py_print,
        'sys': sys
    }

    # Run script as __main__
    try:
        runpy.run_path(script_name, _globals, module)
    except Exception as ex:
        # get stack trace as string
        stack_trace = traceback.format_exc().split('\n')
        # Find index of first line that contains the script name
        index = 0
        for i, line in enumerate(stack_trace):
            if script_name in line:
                index = i
                break
        stack_trace = "\n".join(stack_trace[index:])
        output_tokens.append(f"\nException: {ex}\n{stack_trace}")

    return ''.join(output_tokens)


if __name__ == '__main__':
    script_name = sys.argv[1]
    args = sys.argv[2:]
    print(_run_script(script_name, *args))