#!/usr/bin/env python3

__version__ = "0.1.0"
__author__ = "Sergio Vinagrero"
__email__ = "servinagrero@gmail.com"
__license__ = "MIT"
__copyright__ = "(c) 2024, Sergio Vinagrero"

import subprocess
import shlex
import sys
import logging
from pathlib import Path
from shutil import which
import os
from string import Template
from tempfile import TemporaryDirectory
from ctypes.util import find_library
from inspect import cleandoc


class TeX2img:
    """Render TeX elements to images

    Different available flows are:

    [0] TeX ----> DVI ----> PS -----> PDF
            latex     dvips    ps2pdf
    [1] TeX ----> DVI ----> EPS
            latex     dvips
    [2] TeX ----> DVI ----> SVG
            latex     dvips
    [3] TeX ----> DVI ----> JPG/PNG
            latex      gs

    Attributes:
        template: TeX document template. Defaults to `TeX2img.DEFAULT_TEMPLATE`
        preamble: TeX document preamble to include packages or configuration. Defaults to `TeX2img.DEFAULT_PREAMBLE`
        fontsize: Document fontsize. Defaults to `TeX2img.DEFAULT_FONTSIZE`
        template_params: Additional template variables.
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

    def __init__(
        self, template=None, preamble=None, fontsize=None, template_params=None
    ):
        self.commands = {
            "latex": {
                "path": None,
                "command": "latex -interaction nonstopmode -halt-on-error {tex_file}",
            },
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

        self.check_deps()
        if not self.commands["latex"]:
            raise FileNotFoundError("latex not found in the system")

        self.template = template or TeX2img.DEFAULT_TEMPLATE
        self.preamble = preamble or TeX2img.DEFAULT_PREAMBLE
        self.fontsize = fontsize or TeX2img.DEFAULT_FONTSIZE

        self.template_params = template_params or {}

        self._logger = logging.Logger("TeX2img", level=logging.INFO)
        self._logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)

        self.__libgs = None
        if not hasattr(os.environ, "LIBGS") and not find_library("gs"):
            if sys.platform == "darwin":
                # Fallback to homebrew Ghostscript on macOS
                homebrew_libgs = "/usr/local/opt/ghostscript/lib/libgs.dylib"
                if Path(homebrew_libgs).exists():
                    self.__libgs = homebrew_libgs
            if not self.__libgs:
                self._logger.info("libgs not found")

    @staticmethod
    def is_valid_ext(ext: str) -> bool:
        """Check if the extension is supported
        Args:
            ext: The extension including the .
        Returns:
            True if the extension is supported
        """
        VALID_EXTS = [".dvi", ".pdf", ".ps", ".eps", ".svg", ".jpg", ".png"]
        return ext.lower() in VALID_EXTS

    def check_deps(self):
        """Check installed dependencies.

        For the commands in `self.commands` find the binary in the system using `shutil.which`.
        The binary is extracted as the first word in the command string.
        """
        for format, options in self.commands.items():
            cmd = options["command"].split(" ")[0]
            options["path"] = which(cmd)

    def prepare(self, body: str, template=None, preamble=None, **kwargs) -> str:
        """Prepares the TeX document to be compiled

        Args:
            body: The TeX element to compile.
            template: The TeX document template. Defaults to `self.template`
            preamble: The TeX document preamble. Defaults to `self.preamble`
            kwargs: Extra template parameters.

        Returns:
            The prepared TeX document as a string
        """
        template = Template(template or self.template)
        params = self.template_params.copy()
        params.update(
            {
                "preamble": preamble or self.preamble,
                "fontsize": kwargs.get("fontsize", self.fontsize),
                "body": body,
            }
        )
        params.update(kwargs)
        return template.safe_substitute(**params)

    def __run_cmd(self, cmd: str, wd):
        """Wrapper to run a system command

        On darwin systems, it loads LIBGS on the environment

        Args:
            cmd: The command string to execute. Its escaped with `shlex.split`
            wd: The working directory for the command.

        Raises:
            RuntimeError if the command failed
        """
        env = os.environ.copy()
        if self.__libgs:
            env["LIBGS"] = self.__libgs
        try:
            ret = subprocess.run(
                shlex.split(cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=wd,
                env=env,
            )
            ret.check_returncode()
        except subprocess.CalledProcessError as e:
            msg = f"Command '{cmd}' failed with exit code {e.returncode}"
            self._logger.error(msg)
            self._logger.error(e.stderr.decode("utf-8"))
            raise RuntimeError(msg)

    def render(self, tex: str, outfile: str, wd=None, verbose: bool = False):
        """Render the TeX string to the output image

        The following template variables are available:
            - tex_file: Absolute path to the prepared latex document
            - dvi_file: Absolute path to the resulting dvi file
            - ps_file: Absolute path to the resulting ps file
            - outdir: Absolute path to the directory of the user output file
            - filename: Name of the user output file without extension
            - out_file: Absolute path to the output file of the command

        Args:
            tex: The full TeX document as a string.
            outfile: The path to the output image.
            verbose: If True, print the commands after being executed
            wd: Working directory. If not supplied, temporary directory

        Raises:
            ValueError: If the output extension is not supported.
        """
        if wd is None:
            with TemporaryDirectory(suffix="_tex2img") as tmpdir:
                return self.render(tex, outfile, tmpdir, verbose)

        if verbose:
            self._logger.setLevel(logging.INFO)
        else:
            self._logger.setLevel(logging.WARNING)

        # Where the user wants the file
        outpath = Path(outfile).resolve()
        format = outpath.suffix
        if not TeX2img.is_valid_ext(format):
            raise ValueError(f"Invalid file extension {format}")

        # User output filename without extension
        filename = outpath.stem

        # Absolute path to the output file without extension
        base_file = Path(wd).resolve() / filename

        commands = {name: cmd["command"] for name, cmd in self.commands.items()}

        # Props available in the command templates
        props = {
            "tex_file": base_file.with_suffix(".tex"),
            "dvi_file": base_file.with_suffix(".dvi"),
            "ps_file": base_file.with_suffix(".ps"),
            "outdir": Path(outfile).parent.resolve(),
            "filename": filename,
            "out_file": None,
        }

        with open(props["tex_file"], "w+") as fp:
            fp.write(tex)
        self._logger.info(f"Wrote latex to {props['tex_file']}")

        self.__run_cmd(commands["latex"].format(**props), wd)
        self._logger.info(f"Converted tex to {props['dvi_file']}")

        if format == ".pdf":
            props["out_file"] = base_file.with_suffix(".ps")
            self.__run_cmd(commands["ps"].format(**props), wd)
            self._logger.info(f"Converted dvi to {props['ps_file']}")

            props["out_file"] = outpath.with_suffix(".pdf")
            self.__run_cmd(commands["ps2pdf"].format(**props), wd)
            self._logger.info(f"Converted ps to {props['out_file']}")
            return

        if format == ".svg":
            props["out_file"] = outpath.with_suffix(".svg")
            self.__run_cmd(commands["svg"].format(**props), wd)
            self._logger.info(f"Converted dvi to {props['out_file']}")
            return

        if format == ".eps":
            props["out_file"] = outpath.with_suffix(".eps")
            self.__run_cmd(commands["eps"].format(**props), wd)
            self._logger.info(f"Converted dvi to {props['out_file']}")
            return

        if format == ".png" or format == ".jpg":
            props["out_file"] = base_file.with_suffix(".ps")
            self.__run_cmd(commands["ps"].format(**props), wd)
            self._logger.info(f"Converted dvi to {props['out_file']}")

            props["out_file"] = base_file.with_suffix(".pdf")
            self.__run_cmd(commands["ps2pdf"].format(**props), wd)
            self._logger.info(f"Converted ps to {props['out_file']}")

            props["pdf_file"] = base_file.with_suffix(".pdf")
            props["out_file"] = outpath.with_suffix(format)
            self.__run_cmd(commands["raster"].format(**props), wd)
            self._logger.info(f"Converted pdf to {props['out_file']}")
            return


if __name__ == "__main__":
    import argparse

    DESC = cleandoc(
        r"""
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
"""
    )

    parser = argparse.ArgumentParser(
        description=DESC, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--check-deps", help="Check installed dependencies", action="store_true"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Print the executed commands",
        action="store_const",
        const=logging.INFO,
        default=logging.WARNING,
    )
    parser.add_argument(
        "--template",
        help="Filepath for the document template",
        type=argparse.FileType("r"),
    )
    parser.add_argument(
        "--preamble",
        help="Filepath for the document preamble",
        type=argparse.FileType("r"),
    )
    parser.add_argument(
        "--fontsize", help="Font size. Defaults to 12", default=12, type=int
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
        help="Path to the output file including extension",
        metavar="outfile",
    )
    parser.add_argument("body", nargs="*", help="Input string provided after --")
    parser.add_argument(
        "--param",
        action="append",
        dest="params",
        metavar="key=value",
        help="Additional template parameters. Can be used multiple times",
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

    params = {}
    if args["params"]:
        params = dict([p.split("=") for p in args["params"]])

    try:
        converter = TeX2img(
            template, preamble, fontsize=args["fontsize"], template_params=params
        )
    except FileExistsError:
        print(
            "latex binary is not found in the system. Please install it first to continue"
        )
        sys.exit(1)

    if args["check_deps"]:
        for name, options in converter.commands.items():
            path = options["path"] or "Not found"
            print(f"{name:<8}")
            print(f'  Path: {path}\n  Command: {options["command"]}')
        sys.exit(0)

    if not args["output"]:
        parser.print_help()
        sys.exit(1)

    body = " ".join(args["body"]) if args["body"] else args["input"].read().strip()

    tex = converter.prepare(body)

    try:
        converter.render(tex, args["output"], verbose=args["verbose"])
    except Exception as exc:
        converter._logger.error(exc)
