# TeX2img

Render TeX elements to images (SVG, EPS, PDF, JPG and PNG)

Based on the [original work](https://github.com/tuxu/latex2svg) by Timo Wagner and [other improvements](https://github.com/Moonbase59/latex2svg).


## CLI utility

```
$ ./tex2img.py --help
usage: tex2img.py [-h] [--check-deps] [--keep] [--template TEMPLATE]
                  [--fontsize FONTSIZE] [--dir DIR] [--preamble PREAMBLE]
                  [-i [INPUT]] [-o outfile]
                  [body ...]

Render TeX code from a file or stdin as a document.

The different available flows are the following:

[0] TeX -------> PDF
        pdflatex
[1] TeX ----> DVI ----> PS -----> PDF
        latex     dvips    ps2pdf
[2] TeX ----> DVI ----> EPS
        latex     dvips
[3] TeX -------> PDF ----> SVG
        pdflatex     dvips
[4] TeX -------> PDF ----> JPG/PNG
        pdflatex      gs

positional arguments:
  body                  Positional arguments or input after --

options:
  -h, --help            show this help message and exit
  --check-deps          Check installed dependencies
  --keep                Keep intermediate sources
  --template TEMPLATE   Document template
  --fontsize FONTSIZE   Font size. Defaults to 12
  --dir DIR             Working directory
  --preamble PREAMBLE   Document preamble
  -i, --input [INPUT]   Path to the input TeX file. If not provided, read from STDIN
  -o, --output outfile  Path to the output file
```

## Usage

Installed dependencies can be checked by using `--check-deps`

```
$ ./tex2img.py --check-deps
[latex   ] /usr/bin/latex
[pdflatex] /usr/bin/pdflatex
[dvisvgm ] /usr/bin/dvisvgm
[dvips   ] /usr/bin/dvips
[ps2pdf  ] /usr/bin/ps2pdf
[gs      ] /usr/bin/gs
```

## License

This project is licensed under the MIT license. See [LICENSE.md](LICENSE.md) for details.

© 2025 Sergio Vinagrero
