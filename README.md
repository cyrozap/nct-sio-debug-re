# Reverse enginnering Nuvoton's serial Port 80h protocol

This repository contains a description of the serial protocol used to transmit I/O port 80h (0x80) data, sometimes referred to as "POST codes", from a host PC to a debugging device.
This repository also contains some tools to aid in decoding this protocol.

**Project status**: The protocol is understood well enough to use to read POST codes.
See [Protocol description](#protocol-description) for protocol documentation.


## Introduction

This protocol can be used to read POST codes written by the BIOS/UEFI to x86 I/O port 80h (0x80), which can help in troubleshooting system startup issues.

The serial Port 80h procotol is used on some newer motherboards for AMD and Intel CPUs.
Specifically, motherboards that use Nuvoton Super I/O ("SIO") chips and don't have an LPC port exposed.
Presumably, this protocol exists to enable debugging modern systems that don't have accessible LPC ports.
LPC has been slowly phased out in recent years, so while it used to be common to see LPC used on TPM headers, now that TPMs are more frequently using SPI instead, those ports are no longer accessible to the user.

I assume this protocol was created by Nuvoton as I've only seen it used on motherboards with Nuvoton Super I/O chips.
If you come across a counterexample, feel free to let me know by opening an issue or sending me an email.


## Repository organization

- Reverse engineering notes are in [Notes.md](Notes.md).
- A protocol decoder for [sigrok][sigrok] is in [siodebuguart](siodebuguart).
- [sr-siodebuguart-to-txt.sh](sr-siodebuguart-to-txt.sh) can be used with the protocol decoder to generate a log file from a logic analyzer trace of the signal.
- [process.py](process.py) can help visualize the data in the log file at a low level.
- [monitor_io.py](monitor_io.py) will parse the data in the log file and display the I/O port accesses and POST codes recorded there.


## Getting started

1. Install the protocol decoder.
   - On Linux, to do this you can either copy or link the [siodebuguart](siodebuguart) directory into `~/.local/share/libsigrokdecode/decoders/`.
2. Use a logic analyzer supported by sigrok or Pulseview to capture the serial Port 80h pin output at 6 MHz or higher (preferably 9 MHz or higher), then save the capture to an srzip file.
3. Run `./sr-siodebuguart-to-txt.sh cature.sr > logfile.txt` to process a srzip into a log file.
4. Run `./monitor_io.py logfile.txt` to see the I/O port accesses and POST codes.


## Ports and pinouts

On motherboards, the serial Port 80h signal can be found on connectors with names and configurations that vary by manufacturer:

- ASRock: `UART1` (1×4 pin header)
  - Pin 1: Unknown
  - Pin 2: Unknown
  - Pin 3: `NC` (key, empty)
  - Pin 4: Unknown
- ASUS: `COM_DEBUG` (2×3 pin header)
  - Pin 1: `O_COMDBG_P80` (serial Port 80h)
  - Pin 2: `GND`
  - Pin 3: `NC` (key, empty)
  - Pin 4: `GND`
  - Pin 5: `3V`
  - Pin 6: `O_COM1_TXD1` (UART TX, Super I/O)
- MSI: `JDP1` (2×2 pin header)
  - Pin 1: `SIO_DEBUG` (serial Port 80h)
  - Pin 2: `5V`
  - Pin 3: `GND`
  - Pin 4: `NC` (key, empty)


## Protocol description

The physical layer is just a UART, but running at 1.5 Mbaud and with 26 data bits, no parity bits, and one (or more) stop bits ("1500000 26N1", for short). As with most other common UART protocols, the data bits are transmitted from least-significant bit to most-significant bit.

The data bits are broken up as follows:

- Bits `[25:18]`: I/O port data.
- Bits `[17:16]`: Unknown, always zero.
- Bits `[15:8]`: Assumed to be the high byte of the I/O port address, always zero.
- Bits `[7:0]`: The low byte of the I/O port address. The value is in the range of 0x80-0x83, inclusive.

While traditionally POST codes have only had eight bits, newer POST codes can have 32 bits.
These longer post codes are written one byte at a time to ports 0x80-0x83 (inclusive) in little-endian byte order.

When a byte isn't updated from one long POST code to the next, the sequence of writes for that code may omit writing that byte, unless it is the most-significant byte.
For example, if POST code `0xB000A955` is written, followed by four writes of `0xB000A914`, that is represented by the following table of writes:

| Sequence | Port   | Value  |
| -------- | ------ | ------ |
| 0        | `0x80` | `0x55` |
| 1        | `0x81` | `0xA9` |
| 2        | `0x82` | `0x00` |
| 3        | `0x83` | `0xB0` |
| 4        | `0x80` | `0x14` |
| 5        | `0x83` | `0xB0` |
| 6        | `0x83` | `0xB0` |
| 7        | `0x83` | `0xB0` |
| 8        | `0x83` | `0xB0` |


## References

- ["ASUS COM\_DEBUG port 80" (Video)](https://www.youtube.com/watch?v=Gnm_tuARqVI)
- ["Motherboard Analyzer Post Code Debugger Overview" (Video)](https://www.youtube.com/watch?v=S-IEp8jTgs4)
- ["My TL631 Pro Motherboard Diagnostic and Debug Card Notes"](https://quantumwarp.com/kb/articles/75-general/996-my-tl631-pro-motherboard-diagnostic-and-debug-card-notes)
- ["PHD 6000 Connector on Asus MB, what I found"](https://linustechtips.com/topic/1373425-phd-6000-connector-on-asus-mb-what-i-fond/)
  - Note that while the `PHD6000` connector mentioned in this thread has the same shape as the `COM_DEBUG` connector, `PHD6000` has a completely different set of signals and signal arrangement, and is _not_ compatible with `COM_DEBUG`.


## License

Except where stated otherwise (namely, the protocol decoder), the contents of this repository are released under the [Zero-Clause BSD (0BSD) license][license].


[sigrok]: https://sigrok.org/
[license]: LICENSE.txt
