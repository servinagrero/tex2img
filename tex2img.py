#!/usr/bin/env python3

__version__ = "0.1.0"
__author__ = "Sergio Vinagrero"
__email__ = "servinagrero@gmail.com"
__license__ = "MIT"
__copyright__ = "(c) 2024, Sergio Vinagrero"

import subprocess
import shlex
import sys
from pathlib import Path
from shutil import which
import os
from string import Template
from tempfile import TemporaryDirectory
from ctypes.util import find_library
from inspect import cleandoc

_VALID_EXTS = [".pdf", ".svg", ".eps", ".jpg", ".png"]


class TeX2img:
    """Render TeX elements to images

    Different available flows are:

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

    Attributes:
        template: TeX document template.
        preamble: TeX document preamble to include packages or configuration.
        libgs: Only for Darwin systems.
    """

    DEFAULT_TEMPLATE = cleandoc(
        r"""
        \documentclass[${fontsize}pt,preview]{standalone}
        ${preamble}
        \begin{document}
        \begin{preview}
        ${body}
        \end{preview}
        \end{document}        
        """
    )

    DEFAULT_PREAMBLE = cleandoc(
        r"""
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
        """
    )

    DEFAULT_FONTSIZE = 12

    def __init__(self, template=None, preamble=None, fontsize=None):

        self.commands = {
            "latex": {
                "path": None,
                "command": "latex -interaction nonstopmode -halt-on-error {tex_file}",
            },
            "pdflatex": {"path": None, "command": "pdflatex {tex_file}"},
            "svg": {
                "path": None,
                "command": "dvisvgm --exact-bbox --no-fonts {dvi_file} -o {out_file}",
            },
            "ps": {"path": None, "command": "dvips {dvi_file} -o {out_file}"},
            "eps": {"path": None, "command": "dvips -E {dvi_file} -o {out_file}"},
            "ps2pdf": {"path": None, "command": "ps2pdf {ps_file} {out_file}"},
            "raster": {
                "path": None,
                "command": "gs -dNOPAUSE -sDEVICE=pngalpha -o {out_file} -r300 {pdf_file}",
            },
        }

        dep = self.check_deps()["latex"]
        if not dep["path"]:
            raise FileNotFoundError("latex not found in the system")

        self.template = template or TeX2img.DEFAULT_TEMPLATE
        self.preamble = preamble or TeX2img.DEFAULT_PREAMBLE
        self.fontsize = fontsize or TeX2img.DEFAULT_FONTSIZE

        self.__libgs = None
        if not hasattr(os.environ, "LIBGS") and not find_library("gs"):
            if sys.platform == "darwin":
                # Fallback to homebrew Ghostscript on macOS
                homebrew_libgs = "/usr/local/opt/ghostscript/lib/libgs.dylib"
                if Path(homebrew_libgs).exists():
                    self.__libgs = homebrew_libgs
            if not self.__libgs:
                print("Warning: libgs not found")

    def check_deps(self):
        """Check installed dependencies

        Returns:
            A dictionary containing the different tools and their path, if found in the system.
        """
        for format, options in self.commands.items():
            cmd = options["command"].split(" ")[0]
            options["path"] = which(cmd)
        return self.commands

    def prepare(self, body: str, template=None, preamble=None, fontsize=None) -> str:
        """Prepares the TeX document to be compiled

        Args:
            body: The TeX element to compile.
            template: The TeX document template.
            preamble: The TeX document preamble.
            fontsize: The TeX document fontsize.
        Returns:
            The prepared TeX document as a string
        """
        template = Template(template or self.template)
        preamble = preamble or self.preamble
        fontsize = fontsize or self.fontsize
        return template.safe_substitute(preamble=preamble, fontsize=fontsize, body=body)

    def __run_cmd(self, cmd, wd):
        ret = subprocess.run(
            shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=wd
        )
        ret.check_returncode()

    def render(self, tex: str, outfile: str, keep: bool = False, wd=None):
        """Render the TeX string to the output image

        Args:
            tex: The full TeX document as a string.
            outfile: The path to the output image.
            wd: Working directory. If not supplied, temporary directory
            bool: True to keep intermediary steps. Only makes sense when not providing a temporary directory
        """
        if wd is None:
            with TemporaryDirectory(suffix="_tex2img") as tmpdir:
                return self.render(tex, outfile, keep, tmpdir)

        # Where the user wants the file
        outpath = Path(outfile).resolve()
        format = outpath.suffix
        if format not in _VALID_EXTS:
            raise KeyError(f"Invalid file extension {format}")

        # User output filename without extension
        filename = outpath.stem

        # Absolute path to the output file without extension
        base_file = Path(wd).resolve() / filename

        commands = {name: cmd["command"] for name, cmd in self.commands.items()}

        file_props = {
            "tex_file": base_file.with_suffix(".tex"),
            "dvi_file": base_file.with_suffix(".dvi"),
            "ps_file": base_file.with_suffix(".ps"),
            "outdir": Path(outfile).parent.resolve(),
            "filename": filename,
            "out_file": None,
        }

        with open(file_props["tex_file"], "w+") as fp:
            fp.write(tex)

        self.__run_cmd(commands["latex"].format(**file_props), wd)

        if format == ".pdf":
            file_props["out_file"] = base_file.with_suffix(".ps")
            self.__run_cmd(commands["ps"].format(**file_props), wd)

            file_props["out_file"] = outpath.with_suffix(".pdf")
            self.__run_cmd(commands["ps2pdf"].format(**file_props), wd)

        elif format == ".svg":
            file_props["out_file"] = outpath.with_suffix(".svg")
            self.__run_cmd(commands["svg"].format(**file_props), wd)

        elif format == ".eps":
            file_props["out_file"] = outpath.with_suffix(".eps")
            self.__run_cmd(commands["eps"].format(**file_props), wd)

        elif format == ".png" or format == ".jpg":
            file_props["out_file"] = base_file.with_suffix(".ps")
            self.__run_cmd(commands["ps"].format(**file_props), wd)

            file_props["out_file"] = base_file.with_suffix(".pdf")
            self.__run_cmd(commands["ps2pdf"].format(**file_props), wd)

            file_props["pdf_file"] = base_file.with_suffix(".pdf")
            file_props["out_file"] = outpath.with_suffix(format)
            self.__run_cmd(commands["raster"].format(**file_props), wd)
        else:
            pass


if __name__ == "__main__":
    import argparse

    DESC = cleandoc(
        r"""
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
"""
    )

    parser = argparse.ArgumentParser(
        description=DESC, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--check-deps", help="Check installed dependencies", action="store_true"
    )
    parser.add_argument("--keep", help="Keep intermediate sources", action="store_true")
    parser.add_argument(
        "--template", help="Document template", type=argparse.FileType("r")
    )
    parser.add_argument(
        "--fontsize", help="Font size. Defaults to 12", default=12, type=int
    )
    parser.add_argument("--dir", help="Working directory")
    parser.add_argument(
        "--preamble", help="Document preamble", type=argparse.FileType("r")
    )
    parser.add_argument(
        "-i",
        "--input",
        nargs="?",
        type=argparse.FileType("r", encoding="UTF-8"),
        default=sys.stdin,
        help="Path to the input TeX file. If not provided, read from STDIN",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Path to the output file",
        metavar="outfile",
    )
    parser.add_argument(
        "body", nargs="*", help="Positional arguments or input after --"
    )

    args = vars(parser.parse_args())
    template = None
    if args["template"] and Path(args["template"]).exists():
        with open(args["template"], "r") as fp:
            template = fp.read()
    preamble = None
    if args["preamble"] and Path(args["preamble"]).exists():
        with open(args["preamble"], "r") as fp:
            template = fp.read()

    converter = TeX2img(template=template, preamble=preamble)

    if args["check_deps"]:
        for cmd, options in converter.commands.items():
            print(f'[{cmd:<8}] {options["path"] or "Not found"}')
        sys.exit(0)

    if not args["output"]:
        parser.print_help()
        sys.exit(1)

    body = " ".join(args["body"]) if args["body"] else args["input"].read().strip()

    tex = converter.prepare(
        body, template=template, preamble=preamble, fontsize=args["fontsize"]
    )
    converter.render(tex, args["output"], wd=args["dir"])
