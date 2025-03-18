# TeX2img

Render TeX elements to images (SVG, EPS, PDF, JPG and PNG)

Based on the [original work](https://github.com/tuxu/latex2svg) by Timo Wagner and [other improvements](https://github.com/Moonbase59/latex2svg).


## CLI utility

```
$ ./tex2img.py --help
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
[svg     ] /usr/bin/dvisvgm
[ps      ] /usr/bin/dvips
[eps     ] /usr/bin/dvips
[ps2pdf  ] /usr/bin/ps2pdf
[raster  ] /usr/bin/gs
```

To convert a TeX expression to an image, provide the output path with the `-o` flag, including the desired extension and the input. The input can be provided through STDIN. The flag `-E` is provided to echo to avoid escaping the backlashes.

```
$ echo -E '$\alpha = 2$' | ./tex2img.py -o ./test.svg
```

The input can also be provided directly after `--`.

```
$ ./tex2img.py -o ./test.jpg -- '$\\alpha = 2$'
```

The input can be read from a by by using the `-i` flag.

```
$ ./tex2img.py -o ./test.jpg -i input.tex
```

The TeX document is built first by injecting user input into a `template` with a `preamble`. Both the template and the preamble can be provided from a file by using the respective flags.

```
$ ./tex2img.py -o ./test.jpg -i input.tex --fontsize 14 --preamble preamble.txt --template template.txt
```

The template and the preamble are formatted using the `Template` Python module, so variables should be enclosed as `${variable}`. The default template and preamble are the following:

```text
\documentclass[${fontsize}pt,preview]{standalone}
${preamble}
\begin{document}
\begin{preview}
${body}
\end{preview}
\end{document}
```

```text
\usepackage[utf8]{inputenc}
\usepackage{float}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{siunitx}
\usepackage{xcolor}
\usepackage{comment}
\usepackage[boxed,algoruled,vlined,linesnumbered]{algorithm2e}
\usepackage{amsmath,amsthm,amssymb,amsfonts,amstext,newtxtext}
\usepackage{color,soul}
\usepackage{tikz}
```

## License

This project is licensed under the MIT license. See [LICENSE.md](LICENSE.md) for details.

© 2025 Sergio Vinagrero
