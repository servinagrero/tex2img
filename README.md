# TeX2img

Render TeX elements to images (SVG, EPS, PDF, JPG and PNG)

Heavily based on the [original work](https://github.com/tuxu/latex2svg) by Timo Wagner and [other improvements](https://github.com/Moonbase59/latex2svg).

## CLI utility

```
$ ./tex2img.py --help
usage: tex2img.py [-h] [--check-deps] [-v] [--template TEMPLATE] [--preamble PREAMBLE] [--fontsize FONTSIZE] [-i [INPUT]] [-o outfile] [--param key=value] [body ...]

Render TeX code from a file or stdin as a document.

The different available flows are the following:

[0] TeX ----> DVI ----> PS -----> PDF
        latex     dvips    ps2pdf
[1] TeX ----> DVI ----> EPS
        latex     dvips
[2] TeX ----> DVI ----> SVG
        latex     dvips
[3] TeX ----> DVI ----> JPG/PNG
        latex      gs

positional arguments:
  body                  Input string provided after --

options:
  -h, --help            show this help message and exit
  --check-deps          Check installed dependencies
  -v, --verbose         Print the executed commands
  --template TEMPLATE   Filepath for the document template
  --preamble PREAMBLE   Filepath for the document preamble
  --fontsize FONTSIZE   Font size. Defaults to 12
  -i, --input [INPUT]   Path to the input TeX file. If not provided, read from STDIN
  -o, --output outfile  Path to the output file including extension
  --param key=value     Additional template parameters. Can be used multiple times
```

## Usage

Installed dependencies can be checked by using `--check-deps`

```
$ ./tex2img.py --check-deps
latex
  Path: /usr/bin/latex
  Command: latex -interaction nonstopmode -halt-on-error {tex_file}
svg
  Path: /usr/bin/dvisvgm
  Command: dvisvgm --exact-bbox --no-fonts {dvi_file} -o {out_file}
ps
  Path: /usr/bin/dvips
  Command: dvips {dvi_file} -o {out_file}
eps
  Path: /usr/bin/dvips
  Command: dvips -E {dvi_file} -o {out_file}
ps2pdf
  Path: /usr/bin/ps2pdf
  Command: ps2pdf {ps_file} {out_file}
raster
  Path: /usr/bin/gs
  Command: gs -dNOPAUSE -sDEVICE=pngalpha -o {out_file} -r300 {pdf_file}
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

Extra parameters to the templates can be provided by using the `--param` argument. It can be used multiple times

```
$ ./tex2img.py -o ./test.pdf -i input.tex --param foo='bar' --param response=42
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
