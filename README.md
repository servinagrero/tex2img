# TeX2img

Render TeX elements to images (PS, EPS, PDF, SVG, JPG, PNG and TIFF) plus it allows SVGs to be optimized through [scour](https://github.com/scour-project/scour)

Heavily based on the [original work](https://github.com/tuxu/latex2svg) by Timo Wagner and [other improvements](https://github.com/Moonbase59/latex2svg).

## Installation

The utility can be installed with pip or any other system that uses `pyproject.toml`

```shell
$ pip install --user .
```

## CLI utility

```shell
$ tex2img --help
usage: tex2img [-h] [-v] [--check-deps] [--optimize-svg] [--template-file TEMPLATE_FILE] [--preamble-file PREAMBLE_FILE] [--fontsize FONTSIZE] [-i INPUT_FILE]
               [-o OUTPUT_FILE] [--param param='value'] [--arguments command='arguments']
               [body]

Render TeX code from a file or stdin as a document.

The different available flows are the following:

[0] TeX ----> DVI
        latex
[1] TeX ----> DVI ----> PS
        latex     dvips
[2] TeX ----> DVI ----> EPS
        latex     dvips
[3] TeX ----> DVI ----> PS -----> PDF
        latex     dvips    ps2pdf
[4] TeX ----> DVI ----> SVG --?--> SVG
        latex     dvips     scour
[5] TeX ----> DVI -> JPG/PNG/TIFF
        latex     gs

positional arguments:
  body                  string containing the TeX

options:
  -h, --help            show this help message and exit
  -v, --verbose         print the executed commands
  --check-deps          check installed dependencies
  --optimize-svg        optimize the SVG using scour
  --template-file TEMPLATE_FILE
                        filepath for the document template
  --preamble-file PREAMBLE_FILE
                        filepath for the document preamble
  --fontsize FONTSIZE   font size. Defaults to 12
  -i, --input-file INPUT_FILE
                        path to the input TeX file.
  -o, --output-file OUTPUT_FILE
                        path to the output file including extension
  --param param='value'
                        template parameters
  --arguments command='arguments'
                        command arguments
```

## Usage

Installed dependencies can be checked by using `--check-deps`. This will print the command `[command]` next to the corresponding binary if found in the system or "Not found" otherwise. Bellow each command is the full command with the arguments that will be used to convert the input text to the desired output.

When trying to convert to a format not supported, a warning will be printed and the process aborted.

```shell
$ tex2img --check-deps
[dvi] /usr/bin/latex
latex -interaction nonstopmode -halt-on-error {tex_file}

[ps] /usr/bin/dvips
dvips {dvi_file} -o {out_file}

[eps] /usr/bin/dvips
dvips -E {dvi_file} -o {out_file}

[pdf] /usr/bin/ps2pdf
ps2pdf {ps_file} {out_file}

[svg] /usr/bin/dvisvgm
dvisvgm --exact-bbox --no-fonts {dvi_file} -o {out_file}

[png] /usr/bin/gs
gs -dNOPAUSE -sDEVICE=pngalpha -r600 -o {out_file} {pdf_file}

[jpg] /usr/bin/gs
gs -dNOPAUSE -sDEVICE=jpeg -dJPEGQ=95 -r600 -o {out_file} {pdf_file}

[tiff] /usr/bin/gs
gs -dNOPAUSE -sDEVICE=tiffg4 -r600 -o {out_file} {pdf_file}

[optimize] /usr/bin/scour
scour --shorten-ids --shorten-ids-prefix="{prefix}" --no-line-breaks --remove-metadata --enable-comment-stripping --strip-xml-prolog -i {svg_file} -o {out_file}
```

To convert a TeX expression to an image, provide the output path with the `-o` flag, including the desired extension and the input. The input is provided as the last argument.

```shell
$ tex2img -o ./test.svg '$\alpha = 2$'
```

The input can also be provided from a file

```shell
$ tex2img -o ./test.jpg --input-file input.tex
```

Extra parameters to the templates can be provided by using the `--param` argument. It can be used multiple times

```shell
$ tex2img -o ./test.pdf -i input.tex --param foo='bar' --param response=42
```

The command arguments can be modified by using the `--arguments` flag. This can also be provided multiple times to change multiple commands

```shell
$ tex2img -v -o test.png --arguments png='-dNOPAUSE -sDEVICE=pngalpha -r1200 -o {out_file} {pdf_file}' -i input.tex
```

Verbose output can be activated by using the `--verbose` flag

```shell
$ tex2img -v -o test.png '$\alpha = \beta = 2$'
15:01:47 :: INFO :: Wrote latex to /tmp/tmp2ys85a0q_tex2img/test.tex
15:01:47 :: INFO :: Converted latex to /tmp/tmp2ys85a0q_tex2img/test.dvi
15:01:47 :: INFO :: Converted dvi to /tmp/tmp2ys85a0q_tex2img/test.ps
15:01:47 :: INFO :: Converted ps to /tmp/tmp2ys85a0q_tex2img/test.pdf
15:01:48 :: INFO :: Converted pdf to /path/to/test.png
```

The TeX document is built first by injecting user input into a `template` with a `preamble` configuration. The template and the preamble are formatted using the `Template` Python module, so variables should be enclosed as `${variable}`. Both the template and the preamble can be provided from a file by using the `--template-file` and `--preamble-file` flags respectively.

The default template and preamble are the following:

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

## Using it from Python

This utility can also be used from inside python. You can take a look at the cli.py file in this repository to see how or with the following example

```python
from tex2img import DEFAULT_TEMPLATE, DEFAULT_PREAMBLE, DEFAULT_FONTSIZE
from tex2img import TeX2img

template = None or DEFAULT_TEMPLATE
preamble = None or DEFAULT_PREAMBLE
fontsize = None or DEFAULT_FONTSIZE
params = {}

converter = TeX2img(template, preamble, fontsize, params)
body = r"$\alpha = 2$"
latex_str = converter.prepare(body)

# The valid extensions are defined in tex2img.VALID_SUFFIXES
output = "/path/to/file.png"
try:
    converter.render(
        latex_str, output_file=output, verbose=False,optimize_svg=False
    )
except Exception as e:
    print(e)
```

## License

This project is licensed under the MIT license. See [LICENSE.md](LICENSE.md) for details.

© 2025 Sergio Vinagrero
