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


class AddrData(NamedTuple):
    addr: int
    data: int


def parse_args() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Process and reformat 26-bit hex values from a sigrok log file of a trace of the siodebuguart protocol.")
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

def parse_log(lines: Iterable[str]) -> Iterator[AddrData]:
    for line in lines:
        line = line.strip()
        if not line:
            continue

        val: int | None = parse_line(line)

        if val is None:
            continue

        data: int = val >> 18
        address: int = val & 0xFFFF  # We assume the address is 16-bit

        yield AddrData(address, data)

def main() -> int:
    args: argparse.Namespace = parse_args()

    logfile: TextIOWrapper = args.file

    long_code: int = 0
    previous_addr_data: AddrData | None = None
    for addr_data in parse_log(logfile):
        if addr_data.addr == 0x80:
            long_code &= 0xFFFFFF00
            long_code |= addr_data.data
            if previous_addr_data and previous_addr_data.addr == 0x80:
                print(f"POST code: 0x{previous_addr_data.data:02X}")
        elif addr_data.addr == 0x81:
            long_code &= 0xFFFF00FF
            long_code |= addr_data.data << 8
        elif addr_data.addr == 0x82:
            long_code &= 0xFF00FFFF
            long_code |= addr_data.data << 16
        elif addr_data.addr == 0x83:
            long_code &= 0x00FFFFFF
            long_code |= addr_data.data << 24
            print(f"POST code: 0x{long_code:08X}")
        else:
            if previous_addr_data and previous_addr_data.addr == 0x80:
                print(f"POST code: 0x{previous_addr_data.data:02X}")
            print(f"0x{addr_data.addr:04X}: 0x{addr_data.data:02X}")

        previous_addr_data = addr_data

    return 0


if __name__ == "__main__":
    # Handle broken pipe gracefully
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.stderr.close()
        sys.exit(0)
