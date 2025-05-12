from byu_pytest_utils import run_script, test_files, this_folder

# New imports
from byu_pytest_utils.utils import run_tests

tests = {
    'run_tests': [
        {
            'name': 'mad_libs_short',
            'points': 5,
            'result': run_script(
                'mad_libs.py',
                expected_stdio=test_files / 'mad-libs-short.dialog.txt',
            )
        },
        {
            'name': 'mad_libs',
            'points': 5,
            'result': run_script(
                'mad_libs.py',
                expected_stdio=test_files / 'mad-libs.dialog.txt',
            )
        },
        {
            'name': 'pizza_time_1',
            'points': 2.5,
            'result': run_script(
                'pizza_time.py',
                expected_stdio=test_files / 'pizza-time.dialog.txt',
            )
        },
        {
            'name': 'pizza_time_2',
            'points': 2.5,
            'result': run_script(
                'pizza_time.py',
                expected_stdio=test_files / 'pizza-time-2.dialog.txt',
            )
        },
    ]
}

if __name__ == '__main__':
    run_tests(tests_info=tests, test_dir=this_folder)
