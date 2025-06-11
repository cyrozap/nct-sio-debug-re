#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD

# Copyright (C) 2025 by Forest Crossman <cyrozap@gmail.com>
#
# Permission to use, copy, modify, and/or distribute this software for
# any purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
# WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE
# AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL
# DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR
# PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
# TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.


import argparse
import re
import sys
from io import TextIOWrapper
from typing import Iterable, Iterator, NamedTuple


class BitRange(NamedTuple):
    start: int
    end: int


def parse_args() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Process and reformat 26-bit hex values from a sigrok log file of a trace of the siodebuguart protocol.")
    parser.add_argument("-a", "--arrange",
                        default="25-0",
                        help="Specify bit ranges to arrange the output (e.g. 25-24,23-0).")
    parser.add_argument("-b", "--binary",
                        action="store_true",
                        help="Format output parts as binary instead of hex.")
    parser.add_argument("-r", "--reverse",
                        action="store_true",
                        help="Bit-reverse the 26-bit value before processing.")
    parser.add_argument("file",
                        nargs="?",
                        type=argparse.FileType("r"),
                        default=sys.stdin,
                        help="Input file (default is stdin).")

    return parser.parse_args()

def parse_line(line: str) -> int | None:
    match: re.Match | None = re.match(r"siodebuguart-\d+: ([0-9A-Fa-f]+)", line)
    if not match:
        return None

    hex_str: str = match.group(1).strip()

    val: int = int(hex_str, 16)
    val &= (1 << 26) - 1  # Ensure 26 bits

    return val

def reverse_bits(val: int) -> int:
    val &= (1 << 26) - 1  # Ensure 26 bits masked
    return int(format(val, "026b")[::-1], 2)

def parse_arrange(arrange: str) -> list[BitRange]:
    ranges: list[BitRange] = []
    for part in arrange.split(","):
        bits: list[str] = part.split("-")
        if len(bits) == 1:
            start_str: str = bits[0]
            end_str: str = start_str
        else:
            start_str, end_str = bits
        start: int = int(start_str)
        end: int = int(end_str)
        if start < end:
            start, end = end, start
        ranges.append(BitRange(start, end))

    return ranges

def format_part(val: int, start: int, end: int, binary: bool) -> str:
    bits: int = start - end + 1
    mask: int = (1 << bits) - 1
    extracted: int = (val >> end) & mask

    if binary:
        return f"{extracted:0{bits}b}"

    else:
        hex_digits: int = (bits + 3) // 4  # ceiling division

        return f"{extracted:0{hex_digits}X}"

def parse_log(lines: Iterable[str], arrange: str, binary: bool, reverse: bool) -> Iterator[str]:
    for line in lines:
        line = line.strip()
        if not line:
            continue

        val: int | None = parse_line(line)

        if val is None:
            continue

        if reverse:
            val = reverse_bits(val)

        ranges: list[BitRange] = parse_arrange(arrange)
        output_parts: list[str] = []
        for bit_range in ranges:
            part_str: str = format_part(val, bit_range.start, bit_range.end, binary)
            output_parts.append(part_str)

        yield " ".join(output_parts)

def main() -> int:
    args: argparse.Namespace = parse_args()

    logfile: TextIOWrapper = args.file

    for line in parse_log(logfile, args.arrange, args.binary, args.reverse):
        print(line)

    return 0


if __name__ == "__main__":
    # Handle broken pipe gracefully
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.stderr.close()
        sys.exit(0)
