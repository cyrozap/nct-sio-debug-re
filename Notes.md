# Notes


## Target

- Reverse engineering target is the NCT6687D on an [MSI A520M-A PRO motherboard (MS-7C96)][msi-a520m-a-pro].
- The `SIO_DEBUG` signal can be found on connector JDP1, pin 1.


## Protocol

- Single-wire serial protocol
- The line has two states, high or low.
- The stream starts with a preamble of many alternating highs and lows, with a period of about 84.375ns.
  - Looks like the clock of the chip starting up?
    Freqiency increases from about 5 MHz to 12 MHz, then the line goes idle (high).
  - Inverse happens when the chip powers down.
- It's a UART with 1 start bit (low), 1 stop bit (high), and 26 data bits, running at 1.5 Mbaud.
- Bit order on the line appears little-endian, and the 26-bit word doesn't appear byte-reversed.
- The 26 data bits may be split up into address and data.
  - If true, not sure yet what that split is exactly.
  - Could also be a bitfield of some sort.


[msi-a520m-a-pro]: https://www.msi.com/Motherboard/A520M-A-PRO
