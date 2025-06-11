# Reverse enginnering Nuvoton's SIO Debug protocol

Tools for reverse engineering the Nuvoton SIO (Super I/O) Debug protocol.


## Repository organization

- Reverse engineering notes are in [Notes.md](Notes.md).
- A protocol decoder for [sigrok][sigrok] is in [siodebuguart](siodebuguart).
- [sr-siodebuguart-to-txt.sh](sr-siodebuguart-to-txt.sh) can be used with the protocol decoder to generate a log file from a logic analyzer trace of the signal.
- [process.py](process.py) can help visualize the data in the log file.


## Getting started

1. Install the protocol decoder.
   - On Linux, to do this you can either copy or link the [siodebuguart](siodebuguart) directory into `~/.local/share/libsigrokdecode/decoders/`.
2. Run `./sr-siodebuguart-to-txt.sh cature.sr > logfile.txt` to process a srzip into a log file.
3. Run `./process.py logfile.txt` to process the log file.
   - Run `./process.py --help` to see the available processing options.


## License

Except where stated otherwise (namely, the protocol decoder), the contents of this repository are released under the [Zero-Clause BSD (0BSD) license][license].


[sigrok]: https://sigrok.org/
[license]: LICENSE.txt
