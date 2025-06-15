# Reverse enginnering Nuvoton's SIO Debug protocol

Tools for reverse engineering the Nuvoton SIO (Super I/O) Debug protocol.

This protocol can be used to read POST codes written by the BIOS/UEFI to I/O port 80h (0x80) on x86 systems.
Presumably, this protocol exists to enable debugging modern systems that don't have accessible LPC ports.
For example, systems that only support TPMs that communicate over SPI instead of LPC.

**Project status**: The protocol is understood well enough to use to read POST codes.
See [Notes.md](Notes.md) for protocol documentation.


## Repository organization

- Reverse engineering notes are in [Notes.md](Notes.md).
- A protocol decoder for [sigrok][sigrok] is in [siodebuguart](siodebuguart).
- [sr-siodebuguart-to-txt.sh](sr-siodebuguart-to-txt.sh) can be used with the protocol decoder to generate a log file from a logic analyzer trace of the signal.
- [process.py](process.py) can help visualize the data in the log file at a low level.
- [monitor_io.py](monitor_io.py) will parse the data in the log file and display the I/O port accesses and POST codes recorded there.


## Getting started

1. Install the protocol decoder.
   - On Linux, to do this you can either copy or link the [siodebuguart](siodebuguart) directory into `~/.local/share/libsigrokdecode/decoders/`.
2. Run `./sr-siodebuguart-to-txt.sh cature.sr > logfile.txt` to process a srzip into a log file.
3. Run `./monitor_io.py logfile.txt` to see the I/O port accesses and POST codes.


## License

Except where stated otherwise (namely, the protocol decoder), the contents of this repository are released under the [Zero-Clause BSD (0BSD) license][license].


[sigrok]: https://sigrok.org/
[license]: LICENSE.txt
