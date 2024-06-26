from byu_pytest_utils import cache, dialog, dialog_exec, test_files


@cache
def python_script():
    with open('hello_world.py', 'w') as fout:
        fout.write('print("Hello World!")\n')
    return 'hello_world.py'


@dialog(test_files / 'test_cached_asset.dialog.txt', python_script)
def test_python_cached_asset():
    ...


@dialog_exec('test_files/test_cached_asset.dialog.txt', 'python3', python_script)
def test_exec_cached_asset():
    ...
