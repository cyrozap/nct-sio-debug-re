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
- Bit order on the line is little-endian.
- The 26 data bits are split up into address and data.
  - Bits 7-0 are definitely the low byte of the I/O port address when the value is in the range of 0x80-0x83, inclusive.
  - Bits 25-18 are definitely I/O port data when the I/O port address is in the range of 0x80-0x83, inclusive.
  - Bits 15-8 may be the high byte of the I/O port address, but I don't have a way to confirm this since I've only seen these bits set to zero.
  - Bits 17-16 are completely unknown, since I've only ever seen them set to zero.
- This protocol is used for reading Port 80h (0x80) POST codes, as written by the CPU.
  - Traditionally, POST codes were only 8-bit, but newer ones can be 32-bit.
  - For 32-bit POST codes, the upper three bytes of the 32-bit DWORD are written to I/O ports 0x81, 0x82, and 0x83.


[msi-a520m-a-pro]: https://www.msi.com/Motherboard/A520M-A-PRO
