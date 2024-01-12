import argparse
import datetime
import math
import time
from pathlib import Path

import sys

sys.path.append(str(Path(__file__).parent.parent.absolute()))
print(sys.path)
from byu_pytest_utils.edit_dist import edit_dist

GAP = '~'


def format_record(block_pos, block_type, block):
    return f"{block_pos}{block_type}{''.join(block)}"


def sanitize(text):
    return text.replace('\n', '\\n').replace('\t', '\\t')


def generate_diff_records(last_content, content):
    score, last_align, cur_align = edit_dist(
        last_content, content,
        GAP=GAP, SUB=-math.inf,
    )
    # last: def first~~~~():\n
    # cur:  def ~~~~~main():\n
    #
    # 4-first
    # 4+main

    records = []
    block = []
    block_type = ''
    block_pos = 0

    pos = 0
    for la, ca in zip(last_align, cur_align):
        if la == ca:
            if block:
                records.append(format_record(block_pos, block_type, block))
                block = []
                block_type = ''
                block_pos = 0
            pos += 1
            continue

        if la == GAP:  # insertion
            if not block_type:
                block_type = '+'
                block_pos = pos
            elif block_type == '-':  # just finished a deletion
                records.append(format_record(block_pos, block_type, block))
                block = []
                block_type = '+'
                block_pos = pos
            block.append(ca)
            pos += 1

        elif ca == GAP:  # deletion
            if not block_type:
                block_type = '-'
                block_pos = pos
            elif block_type == '+':  # just finished an insertion
                records.append(format_record(block_pos, block_type, block))
                block = []
                block_type = '-'
                block_pos = pos
            block.append(la)
            # don't increment pos for deletion

    if block:
        records.append(format_record(block_pos, block_type, block))
    return records


def main(directory: Path):
    file_contents = {}
    while True:
        for file in directory.glob('*.*'):
            if file.name.endswith('.diff.txt'):  # Don't process diffs
                continue

            if file.is_dir():
                continue

            if not file.exists():  # if the file no longer exists, ignore it
                continue

            print(file.name)
            content = file.read_text()
            last_content = file_contents.get(file.name, "")

            if content != last_content:
                timestamp = datetime.datetime.now().isoformat()
                records = generate_diff_records(last_content, content)
                with open(file.parent / (file.name + '.diff.txt'), 'a') as out:
                    for record in records:
                        print(f'{file.name} {timestamp} {record}')
                        out.write(f'{timestamp} {sanitize(record)}\n')

                file_contents[file.name] = content
        time.sleep(5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', default=Path(), type=Path)
    args = parser.parse_args()
    main(args.path)
