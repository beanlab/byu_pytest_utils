from .diff_tracker import generate_diff_records


def test_generate_records():
    old = 'def main():\n    pass'
    new = 'def foobar():\n    pass'
    records = generate_diff_records(old, new)
    assert len(records) == 2
    assert records[0] == '4-main'
    assert records[1] == '4+foobar'
