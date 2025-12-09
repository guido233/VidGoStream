# coding:utf-8
# author: https://github.com/myrfy001

import sys
import collections


class SubtitleBlock:
    __slots__ = ("idx_line", "time_line", "text_lines")


spliter = ">>"


def read_subtitle(fi):
    lines = []
    for line in fi:
        line = line.strip()
        if not line:
            continue

        lb = SubtitleBlock()
        lines.append(lb)
        lb.idx_line = line
        line = fi.readline().strip()
        lb.time_line = line
        lb.text_lines = []

        while True:
            line = fi.readline().strip()
            if not line:
                break
            lb.text_lines.append(line)
    return lines


def write_subtitle(fo, lines):
    for cur_line_blk in lines:
        fo.write(f'{cur_line_blk.idx_line}\n')
        fo.write(f'{cur_line_blk.time_line}\n')
        for line in cur_line_blk.text_lines:
            if line:
                fo.write(f'{line}\n')
        fo.write(f'\n')


def dedup(lines):
    for block_idx, cur_line_blk in enumerate(lines):
        for line_idx, line_in_cur_block in enumerate(cur_line_blk.text_lines):
            span = 1
            for delta in range(1, 4):
                if (block_idx + delta < len(lines) and
                        line_in_cur_block in lines[block_idx+delta].text_lines):
                    span += 1
                    lines[block_idx+delta].text_lines.remove(line_in_cur_block)

            cur_line_blk.text_lines[line_idx] = (
                f'{span}{spliter}{line_in_cur_block}')

    for block_idx, cur_line_blk in enumerate(lines):
        if not cur_line_blk.text_lines:
            cur_line_blk.text_lines.append(f'0{spliter}')

    return lines


def dup(lines):
    lines.reverse()
    for block_idx, cur_line_blk in enumerate(lines):
        cur_line_blk.text_lines.reverse()
        for line_idx, line_in_current_block in enumerate(cur_line_blk.text_lines):
            tmp = line_in_current_block.split(spliter, 1)
            if len(tmp) != 2:
                continue
            span = int(tmp[0].strip())
            line_txt = tmp[1].strip()
            cur_line_blk.text_lines[line_idx] = line_txt
            for delta in range(1, span):
                lines[block_idx-delta].text_lines.insert(0, line_txt)
        cur_line_blk.text_lines.reverse()
    lines.reverse()
    return lines


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python dup_convert.py <dup|dedup> <input_file> <output_file>")
        return

    src = sys.argv[2]
    dst = sys.argv[3]
    fi = open(src, 'r')
    fo = open(dst, 'w')

    lines = read_subtitle(fi)
    lines = (dedup if sys.argv[1] == "dedup" else dup)(lines)
    write_subtitle(fo, lines)


if __name__ == '__main__':
    main()
