##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2011-2014 Uwe Hermann <uwe@hermann-uwe.de>
## Copyright (C) 2025 Forest Crossman <cyrozap@gmail.com>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
##

import sigrokdecode as srd
from common.srdhelper import bitpack
from math import floor, ceil

'''
OUTPUT_PYTHON format:

Packet:
[<ptype>, <rxtx>, <pdata>]

This is the list of <ptype>s and their respective <pdata> values:
 - 'STARTBIT': The data is the (integer) value of the start bit (0/1).
 - 'DATA': This is always a tuple containing two items:
   - 1st item: the (integer) value of the UART data. Valid values
     range from 0 to 511 (as the data can be up to 9 bits in size).
   - 2nd item: the list of individual data bits and their ss/es numbers.
 - 'PARITYBIT': The data is the (integer) value of the parity bit (0/1).
 - 'STOPBIT': The data is the (integer) value of the stop bit (0 or 1).
 - 'INVALID STARTBIT': The data is the (integer) value of the start bit (0/1).
 - 'INVALID STOPBIT': The data is the (integer) value of the stop bit (0/1).
 - 'PARITY ERROR': The data is a tuple with two entries. The first one is
   the expected parity value, the second is the actual parity value.
 - 'BREAK': The data is always 0.
 - 'FRAME': The data is always a tuple containing two items: The (integer)
   value of the UART data, and a boolean which reflects the validity of the
   UART frame.
 - 'IDLE': The data is always 0.

The <rxtx> field is 0 for RX packets, 1 for TX packets.
'''

# Used for differentiating between the two data directions.
RX = 0
TX = 1

# Given a parity type to check (odd, even, zero, one), the value of the
# parity bit, the value of the data, and the length of the data (5-9 bits,
# usually 8 bits) return True if the parity is correct, False otherwise.
# 'none' is _not_ allowed as value for 'parity_type'.
def parity_ok(parity_type, parity_bit, data, data_bits):

    if parity_type == 'ignore':
        return True

    # Handle easy cases first (parity bit is always 1 or 0).
    if parity_type == 'zero':
        return parity_bit == 0
    elif parity_type == 'one':
        return parity_bit == 1

    # Count number of 1 (high) bits in the data (and the parity bit itself!).
    ones = bin(data).count('1') + parity_bit

    # Check for odd/even parity.
    if parity_type == 'odd':
        return (ones % 2) == 1
    elif parity_type == 'even':
        return (ones % 2) == 0

class SamplerateError(Exception):
    pass

class ChannelError(Exception):
    pass

class Decoder(srd.Decoder):
    api_version = 3
    id = 'siodebuguart'
    name = 'SIO UART'
    longname = 'Serial I/O UART'
    desc = 'Nuvoton\'s special 26-bit UART.'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = ['siodebuguart']
    tags = ['Embedded/industrial']
    optional_channels = (
        # Allow specifying only one of the signals, e.g. if only one data
        # direction exists (or is relevant).
        {'id': 'rx', 'name': 'RX', 'desc': 'UART receive line'},
        {'id': 'tx', 'name': 'TX', 'desc': 'UART transmit line'},
    )
    options = (
        {'id': 'baudrate', 'desc': 'Baud rate', 'default': 1_500_000},
        {'id': 'bit_order', 'desc': 'Bit order', 'default': 'lsb-first',
            'values': ('lsb-first', 'msb-first')},
        {'id': 'invert_rx', 'desc': 'Invert RX', 'default': 'no',
            'values': ('yes', 'no')},
        {'id': 'invert_tx', 'desc': 'Invert TX', 'default': 'no',
            'values': ('yes', 'no')},
        {'id': 'rx_packet_delim', 'desc': 'RX packet delimiter (decimal)',
            'default': -1},
        {'id': 'tx_packet_delim', 'desc': 'TX packet delimiter (decimal)',
            'default': -1},
        {'id': 'rx_packet_len', 'desc': 'RX packet length', 'default': -1},
        {'id': 'tx_packet_len', 'desc': 'TX packet length', 'default': -1},
    )
    annotations = (
        ('rx-data', 'RX data'),
        ('tx-data', 'TX data'),
        ('rx-start', 'RX start bits'),
        ('tx-start', 'TX start bits'),
        ('rx-parity-ok', 'RX parity OK bits'),
        ('tx-parity-ok', 'TX parity OK bits'),
        ('rx-parity-err', 'RX parity error bits'),
        ('tx-parity-err', 'TX parity error bits'),
        ('rx-stop', 'RX stop bits'),
        ('tx-stop', 'TX stop bits'),
        ('rx-warnings', 'RX warnings'),
        ('tx-warnings', 'TX warnings'),
        ('rx-data-bits', 'RX data bits'),
        ('tx-data-bits', 'TX data bits'),
        ('rx-break', 'RX break'),
        ('tx-break', 'TX break'),
        ('rx-packet', 'RX packet'),
        ('tx-packet', 'TX packet'),
    )
    annotation_rows = (
        ('rx-data-bits', 'RX bits', (12,)),
        ('rx-data', 'RX', (0, 2, 4, 6, 8)),
        ('rx-warnings', 'RX warnings', (10,)),
        ('rx-break', 'RX break', (14,)),
        ('rx-packets', 'RX packets', (16,)),
        ('tx-data-bits', 'TX bits', (13,)),
        ('tx-data', 'TX', (1, 3, 5, 7, 9)),
        ('tx-warnings', 'TX warnings', (11,)),
        ('tx-break', 'TX break', (15,)),
        ('tx-packets', 'TX packets', (17,)),
    )
    binary = (
        ('rx', 'RX dump'),
        ('tx', 'TX dump'),
        ('rxtx', 'RX/TX dump'),
    )
    idle_state = ['WAIT FOR START BIT', 'WAIT FOR START BIT']

    def putx(self, rxtx, data):
        s, halfbit = self.startsample[rxtx], self.bit_width / 2.0
        self.put(s - floor(halfbit), self.samplenum + ceil(halfbit), self.out_ann, data)

    def putx_packet(self, rxtx, data):
        s, halfbit = self.ss_packet[rxtx], self.bit_width / 2.0
        self.put(s - floor(halfbit), self.samplenum + ceil(halfbit), self.out_ann, data)

    def putpx(self, rxtx, data):
        s, halfbit = self.startsample[rxtx], self.bit_width / 2.0
        self.put(s - floor(halfbit), self.samplenum + ceil(halfbit), self.out_python, data)

    def putg(self, data):
        s, halfbit = self.samplenum, self.bit_width / 2.0
        self.put(s - floor(halfbit), s + ceil(halfbit), self.out_ann, data)

    def putp(self, data):
        s, halfbit = self.samplenum, self.bit_width / 2.0
        self.put(s - floor(halfbit), s + ceil(halfbit), self.out_python, data)

    def putgse(self, ss, es, data):
        self.put(ss, es, self.out_ann, data)

    def putpse(self, ss, es, data):
        self.put(ss, es, self.out_python, data)

    def putbin(self, rxtx, data):
        s, halfbit = self.startsample[rxtx], self.bit_width / 2.0
        self.put(s - floor(halfbit), self.samplenum + ceil(halfbit), self.out_binary, data)

    def __init__(self):
        self.reset()

    def reset(self):
        self.samplerate = None
        self.frame_start = [-1, -1]
        self.frame_valid = [None, None]
        self.startbit = [-1, -1]
        self.cur_data_bit = [0, 0]
        self.datavalue = [0, 0]
        self.paritybit = [-1, -1]
        self.stopbit1 = [-1, -1]
        self.startsample = [-1, -1]
        self.state = ['WAIT FOR START BIT', 'WAIT FOR START BIT']
        self.databits = [[], []]
        self.break_start = [None, None]
        self.packet_cache = [[], []]
        self.ss_packet, self.es_packet = [None, None], [None, None]
        self.idle_start = [None, None]

    def start(self):
        self.out_python = self.register(srd.OUTPUT_PYTHON)
        self.out_binary = self.register(srd.OUTPUT_BINARY)
        self.out_ann = self.register(srd.OUTPUT_ANN)
        self.bw = (26 + 7) // 8

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value
            # The width of one UART bit in number of samples.
            self.bit_width = float(self.samplerate) / float(self.options['baudrate'])

    def get_sample_point(self, rxtx, bitnum):
        # Determine absolute sample number of a bit slot's sample point.
        # bitpos is the samplenumber which is in the middle of the
        # specified UART bit (0 = start bit, 1..x = data, x+1 = parity bit
        # (if used) or the first stop bit, and so on).
        # The samples within bit are 0, 1, ..., (bit_width - 1), therefore
        # index of the middle sample within bit window is (bit_width - 1) / 2.
        bitpos = self.frame_start[rxtx] + (self.bit_width - 1) / 2.0
        bitpos += bitnum * self.bit_width
        return bitpos

    def wait_for_start_bit(self, rxtx, signal):
        # Save the sample number where the start bit begins.
        self.frame_start[rxtx] = self.samplenum
        self.frame_valid[rxtx] = True

        self.state[rxtx] = 'GET START BIT'

    def get_start_bit(self, rxtx, signal):
        self.startbit[rxtx] = signal

        # The startbit must be 0. If not, we report an error and wait
        # for the next start bit (assuming this one was spurious).
        if self.startbit[rxtx] != 0:
            self.putp(['INVALID STARTBIT', rxtx, self.startbit[rxtx]])
            self.putg([rxtx + 10, ['Frame error', 'Frame err', 'FE']])
            self.frame_valid[rxtx] = False
            es = self.samplenum + ceil(self.bit_width / 2.0)
            self.putpse(self.frame_start[rxtx], es, ['FRAME', rxtx,
                (self.datavalue[rxtx], self.frame_valid[rxtx])])
            self.state[rxtx] = 'WAIT FOR START BIT'
            return

        self.cur_data_bit[rxtx] = 0
        self.datavalue[rxtx] = 0
        self.startsample[rxtx] = -1

        self.putp(['STARTBIT', rxtx, self.startbit[rxtx]])
        self.putg([rxtx + 2, ['Start bit', 'Start', 'S']])

        self.state[rxtx] = 'GET DATA BITS'

    def handle_packet(self, rxtx):
        d = 'rx' if (rxtx == RX) else 'tx'
        delim = self.options[d + '_packet_delim']
        plen = self.options[d + '_packet_len']
        if delim == -1 and plen == -1:
            return

        # Cache data values until we see the delimiter and/or the specified
        # packet length has been reached (whichever happens first).
        if len(self.packet_cache[rxtx]) == 0:
            self.ss_packet[rxtx] = self.startsample[rxtx]
        self.packet_cache[rxtx].append(self.datavalue[rxtx])
        if self.datavalue[rxtx] == delim or len(self.packet_cache[rxtx]) == plen:
            self.es_packet[rxtx] = self.samplenum
            s = ''
            for b in self.packet_cache[rxtx]:
                s += self.format_value(b)
                if 'hex' != 'ascii':
                    s += ' '
            if 'hex' != 'ascii' and s[-1] == ' ':
                s = s[:-1] # Drop trailing space.
            self.putx_packet(rxtx, [16 + rxtx, [s]])
            self.packet_cache[rxtx] = []

    def get_data_bits(self, rxtx, signal):
        # Save the sample number of the middle of the first data bit.
        if self.startsample[rxtx] == -1:
            self.startsample[rxtx] = self.samplenum

        self.putg([rxtx + 12, ['%d' % signal]])

        # Store individual data bits and their start/end samplenumbers.
        s, halfbit = self.samplenum, int(self.bit_width / 2)
        self.databits[rxtx].append([signal, s - halfbit, s + halfbit])

        # Return here, unless we already received all data bits.
        self.cur_data_bit[rxtx] += 1
        if self.cur_data_bit[rxtx] < 26:
            return

        # Convert accumulated data bits to a data value.
        bits = [b[0] for b in self.databits[rxtx]]
        if self.options['bit_order'] == 'msb-first':
            bits.reverse()
        self.datavalue[rxtx] = bitpack(bits)
        self.putpx(rxtx, ['DATA', rxtx,
            (self.datavalue[rxtx], self.databits[rxtx])])

        b = self.datavalue[rxtx]
        formatted = self.format_value(b)
        if formatted is not None:
            self.putx(rxtx, [rxtx, [formatted]])

        bdata = b.to_bytes(self.bw, byteorder='big')
        self.putbin(rxtx, [rxtx, bdata])
        self.putbin(rxtx, [2, bdata])

        self.handle_packet(rxtx)

        self.databits[rxtx] = []

        # Advance to either reception of the parity bit, or reception of
        # the STOP bits if parity is not applicable.
        self.state[rxtx] = 'GET PARITY BIT'
        if 'none' == 'none':
            self.state[rxtx] = 'GET STOP BITS'

    def format_value(self, v):
        digits = (26 + 4 - 1) // 4
        fmtchar = "X"
        fmt = "{{:0{:d}{:s}}}".format(digits, fmtchar)
        return fmt.format(v)

    def get_parity_bit(self, rxtx, signal):
        self.paritybit[rxtx] = signal

        if parity_ok('none', self.paritybit[rxtx],
                     self.datavalue[rxtx], 26):
            self.putp(['PARITYBIT', rxtx, self.paritybit[rxtx]])
            self.putg([rxtx + 4, ['Parity bit', 'Parity', 'P']])
        else:
            # TODO: Return expected/actual parity values.
            self.putp(['PARITY ERROR', rxtx, (0, 1)]) # FIXME: Dummy tuple...
            self.putg([rxtx + 6, ['Parity error', 'Parity err', 'PE']])
            self.frame_valid[rxtx] = False

        self.state[rxtx] = 'GET STOP BITS'

    # TODO: Currently only supports 1 stop bit.
    def get_stop_bits(self, rxtx, signal):
        self.stopbit1[rxtx] = signal

        # Stop bits must be 1. If not, we report an error.
        if self.stopbit1[rxtx] != 1:
            self.putp(['INVALID STOPBIT', rxtx, self.stopbit1[rxtx]])
            self.putg([rxtx + 10, ['Frame error', 'Frame err', 'FE']])
            self.frame_valid[rxtx] = False

        self.putp(['STOPBIT', rxtx, self.stopbit1[rxtx]])
        self.putg([rxtx + 4, ['Stop bit', 'Stop', 'T']])

        # Pass the complete UART frame to upper layers.
        es = self.samplenum + ceil(self.bit_width / 2.0)
        self.putpse(self.frame_start[rxtx], es, ['FRAME', rxtx,
            (self.datavalue[rxtx], self.frame_valid[rxtx])])

        self.state[rxtx] = 'WAIT FOR START BIT'
        self.idle_start[rxtx] = self.frame_start[rxtx] + self.frame_len_sample_count

    def handle_break(self, rxtx):
        self.putpse(self.frame_start[rxtx], self.samplenum,
                ['BREAK', rxtx, 0])
        self.putgse(self.frame_start[rxtx], self.samplenum,
                [rxtx + 14, ['Break condition', 'Break', 'Brk', 'B']])
        self.state[rxtx] = 'WAIT FOR START BIT'

    def get_wait_cond(self, rxtx, inv):
        # Return condititions that are suitable for Decoder.wait(). Those
        # conditions either match the falling edge of the START bit, or
        # the sample point of the next bit time.
        state = self.state[rxtx]
        if state == 'WAIT FOR START BIT':
            return {rxtx: 'r' if inv else 'f'}
        if state == 'GET START BIT':
            bitnum = 0
        elif state == 'GET DATA BITS':
            bitnum = 1 + self.cur_data_bit[rxtx]
        elif state == 'GET PARITY BIT':
            bitnum = 1 + 26
        elif state == 'GET STOP BITS':
            bitnum = 1 + 26
            bitnum += 0 if 'none' == 'none' else 1
        want_num = ceil(self.get_sample_point(rxtx, bitnum))
        return {'skip': want_num - self.samplenum}

    def get_idle_cond(self, rxtx, inv):
        # Return a condition that corresponds to the (expected) end of
        # the next frame, assuming that it will be an "idle frame"
        # (constant high input level for the frame's length).
        if self.idle_start[rxtx] is None:
            return None
        end_of_frame = self.idle_start[rxtx] + self.frame_len_sample_count
        if end_of_frame < self.samplenum:
            return None
        return {'skip': end_of_frame - self.samplenum}

    def inspect_sample(self, rxtx, signal, inv):
        # Inspect a sample returned by .wait() for the specified UART line.
        if inv:
            signal = not signal

        state = self.state[rxtx]
        if state == 'WAIT FOR START BIT':
            self.wait_for_start_bit(rxtx, signal)
        elif state == 'GET START BIT':
            self.get_start_bit(rxtx, signal)
        elif state == 'GET DATA BITS':
            self.get_data_bits(rxtx, signal)
        elif state == 'GET PARITY BIT':
            self.get_parity_bit(rxtx, signal)
        elif state == 'GET STOP BITS':
            self.get_stop_bits(rxtx, signal)

    def inspect_edge(self, rxtx, signal, inv):
        # Inspect edges, independently from traffic, to detect break conditions.
        if inv:
            signal = not signal
        if not signal:
            # Signal went low. Start another interval.
            self.break_start[rxtx] = self.samplenum
            return
        # Signal went high. Was there an extended period with low signal?
        if self.break_start[rxtx] is None:
            return
        diff = self.samplenum - self.break_start[rxtx]
        if diff >= self.break_min_sample_count:
            self.handle_break(rxtx)
        self.break_start[rxtx] = None

    def inspect_idle(self, rxtx, signal, inv):
        # Check each edge and each period of stable input (either level).
        # Can derive the "idle frame period has passed" condition.
        if inv:
            signal = not signal
        if not signal:
            # Low input, cease inspection.
            self.idle_start[rxtx] = None
            return
        # High input, either just reached, or still stable.
        if self.idle_start[rxtx] is None:
            self.idle_start[rxtx] = self.samplenum
        diff = self.samplenum - self.idle_start[rxtx]
        if diff < self.frame_len_sample_count:
            return
        ss, es = self.idle_start[rxtx], self.samplenum
        self.putpse(ss, es, ['IDLE', rxtx, 0])
        self.idle_start[rxtx] = self.samplenum

    def decode(self):
        if not self.samplerate:
            raise SamplerateError('Cannot decode without samplerate.')

        has_pin = [self.has_channel(ch) for ch in (RX, TX)]
        if not True in has_pin:
            raise ChannelError('Need at least one of TX or RX pins.')

        opt = self.options
        inv = [opt['invert_rx'] == 'yes', opt['invert_tx'] == 'yes']
        cond_data_idx = [None] * len(has_pin)

        # Determine the number of samples for a complete frame's time span.
        # A period of low signal (at least) that long is a break condition.
        frame_samples = 1 # START
        frame_samples += 26
        frame_samples += 0 if 'none' == 'none' else 1
        frame_samples += 1
        frame_samples *= self.bit_width
        self.frame_len_sample_count = ceil(frame_samples)
        self.break_min_sample_count = self.frame_len_sample_count
        cond_edge_idx = [None] * len(has_pin)
        cond_idle_idx = [None] * len(has_pin)

        while True:
            conds = []
            if has_pin[RX]:
                cond_data_idx[RX] = len(conds)
                conds.append(self.get_wait_cond(RX, inv[RX]))
                cond_edge_idx[RX] = len(conds)
                conds.append({RX: 'e'})
                cond_idle_idx[RX] = None
                idle_cond = self.get_idle_cond(RX, inv[RX])
                if idle_cond:
                    cond_idle_idx[RX] = len(conds)
                    conds.append(idle_cond)
            if has_pin[TX]:
                cond_data_idx[TX] = len(conds)
                conds.append(self.get_wait_cond(TX, inv[TX]))
                cond_edge_idx[TX] = len(conds)
                conds.append({TX: 'e'})
                cond_idle_idx[TX] = None
                idle_cond = self.get_idle_cond(TX, inv[TX])
                if idle_cond:
                    cond_idle_idx[TX] = len(conds)
                    conds.append(idle_cond)
            (rx, tx) = self.wait(conds)
            if cond_data_idx[RX] is not None and self.matched[cond_data_idx[RX]]:
                self.inspect_sample(RX, rx, inv[RX])
            if cond_edge_idx[RX] is not None and self.matched[cond_edge_idx[RX]]:
                self.inspect_edge(RX, rx, inv[RX])
                self.inspect_idle(RX, rx, inv[RX])
            if cond_idle_idx[RX] is not None and self.matched[cond_idle_idx[RX]]:
                self.inspect_idle(RX, rx, inv[RX])
            if cond_data_idx[TX] is not None and self.matched[cond_data_idx[TX]]:
                self.inspect_sample(TX, tx, inv[TX])
            if cond_edge_idx[TX] is not None and self.matched[cond_edge_idx[TX]]:
                self.inspect_edge(TX, tx, inv[TX])
                self.inspect_idle(TX, tx, inv[TX])
            if cond_idle_idx[TX] is not None and self.matched[cond_idle_idx[TX]]:
                self.inspect_idle(TX, tx, inv[TX])
