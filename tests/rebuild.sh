pip uninstall byu_pytest_utils -y
poetry build
pip install ../dist/byu_pytest_utils-0.7.13-py3-none-any.whl
pytest --html=report.html -vv
