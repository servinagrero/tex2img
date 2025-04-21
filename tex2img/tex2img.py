#!/usr/bin/env python3

import subprocess
import shlex
import sys
import logging
import random
import string
from pathlib import Path
from shutil import which
import os
from string import Template
from tempfile import TemporaryDirectory
from ctypes.util import find_library
from inspect import cleandoc
from typing import Optional, Dict, List

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
VALID_SUFFIXES = [".ps", ".eps", ".pdf", ".svg", ".jpg", ".png", ".tiff"]


class CMD:
    """Wrapper around a shell command

    Attributes:
        cmd: Command to execute.
        args: Arguments for the command.
    """

    def __init__(self, cmd: str, args: str):
        self.cmd: str = cmd
        self.args: str = args

    def path(self) -> str:
        "Returns the path of the command or 'Not found' if the binary is not found in the system"
        return which(self.cmd) or "Not found"

    def is_available(self) -> bool:
        "Returns true if the command is available in the system"
        return bool(which(self.cmd))

    def prepare(self, props: Optional[Dict] = None) -> List[str]:
        """Prepares the command and arguments to be executed

        Args:
            props: Optional dictionary containing the parameters to format the command arguments.

        Returns:
            The full command as returned by shlex.split
        """
        args = self.args.format(**props) if props else self.args
        return shlex.split(f"{self.cmd} {args}")


class TeX2img:
    """Render TeX elements to images

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

    Attributes:
        template: TeX document template. Defaults to `DEFAULT_TEMPLATE`
        preamble: TeX document preamble to include packages or configuration. Defaults to `DEFAULT_PREAMBLE`
        fontsize: Document fontsize. Defaults to `DEFAULT_FONTSIZE`
        commands: Dictionary of command to convert the TeX document to the different formats.
        params: Additional template variables.
        logger: Logger that writes to stdout.
        libgs: Only for Darwin-based systems.
    """

    def __init__(
        self,
        template: Optional[str] = None,
        preamble: Optional[str] = None,
        fontsize: Optional[int] = None,
        params: Optional[Dict] = None,
    ):
        self.commands = {
            # TODO: Allow also using pdflatex, xelatex or lualatex
            "dvi": CMD("latex", "-interaction nonstopmode -halt-on-error {tex_file}"),
            "ps": CMD("dvips", "{dvi_file} -o {out_file}"),
            "eps": CMD("dvips", "-E {dvi_file} -o {out_file}"),
            "pdf": CMD("ps2pdf", "{ps_file} {out_file}"),
            "svg": CMD("dvisvgm", "--exact-bbox --no-fonts {dvi_file} -o {out_file}"),
            "png": CMD(
                "gs", "-dNOPAUSE -sDEVICE=pngalpha -r600 -o {out_file} {pdf_file}"
            ),
            "jpg": CMD(
                "gs",
                "-dNOPAUSE -sDEVICE=jpeg -dJPEGQ=95 -r600 -o {out_file} {pdf_file}",
            ),
            "tiff": CMD(
                "gs", "-dNOPAUSE -sDEVICE=tiffg4 -r600 -o {out_file} {pdf_file}"
            ),
            "optimize": CMD(
                "scour",
                '--shorten-ids --shorten-ids-prefix="{prefix}" --no-line-breaks --remove-metadata --enable-comment-stripping --strip-xml-prolog -i {svg_file} -o {out_file}',
            ),
        }

        self.template = template or DEFAULT_TEMPLATE
        self.preamble = preamble or DEFAULT_PREAMBLE
        self.fontsize = fontsize or DEFAULT_FONTSIZE
        self.params = params or {}

        self.logger = logging.Logger("TeX2img", level=logging.ERROR)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s :: %(levelname)s :: %(message)s", datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.__libgs: Optional[str] = None
        if not hasattr(os.environ, "LIBGS") and not find_library("gs"):
            if sys.platform == "darwin":
                # Fallback to homebrew Ghostscript on macOS
                homebrew_libgs = "/usr/local/opt/ghostscript/lib/libgs.dylib"
                if Path(homebrew_libgs).exists():
                    self.__libgs = homebrew_libgs
            if not self.__libgs:
                self.logger.info("libgs not found")

    @staticmethod
    def is_valid_suffix(suffix: str) -> bool:
        """Check if the suffix is in VALID_SUFFIXES
        Args:
            suffix: The file suffix
        Returns:
            True if the extension is supported
        """
        return suffix in VALID_SUFFIXES

    def check_deps(self) -> Dict[str, bool]:
        """Check installed dependencies.

        Returns:
            A dictionary containing the command name and True if the command is avaliable and False otherwise
        """
        return {name: cmd.is_available() for name, cmd in self.commands.items()}

    def prepare(
        self,
        body: str,
        template: Optional[str] = None,
        preamble: Optional[str] = None,
        fontsize: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Prepares the TeX document to be compiled

        The arguments are updated first with self.params and then with kwargs

        Args:
            body: The TeX element to compile.
            template: The TeX document template. Defaults to `self.template`
            preamble: The TeX document preamble. Defaults to `self.preamble`
            fontsize: The TeX document fontsize. Defaults to `self.fontsize`
            kwargs: Extra template parameters.

        Returns:
            The prepared TeX document as a string
        """
        tmpl = Template(template or self.template)
        params = {
            "preamble": preamble or self.preamble,
            "fontsize": fontsize or self.fontsize,
            "body": body,
        }
        params.update(self.params)
        params.update(kwargs)
        return tmpl.safe_substitute(**params)

    def __run_cmd(self, cmd_name: str, props: Dict, tmpdir: str):
        """Wrapper to run a system command

        On darwin systems, it loads LIBGS on the environment

        Args:
            cmd_name: The name of the command in self.commands
            props: The props to format the command with
            tmpdir: The working directory for the command

        Raises:
            RuntimeError if the command failed
        """
        env = os.environ.copy()
        if self.__libgs:
            env["LIBGS"] = self.__libgs

        cmd = self.commands[cmd_name].prepare(props)
        try:
            ret = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=tmpdir,
                env=env,
            )
            ret.check_returncode()
        except subprocess.CalledProcessError as e:
            msg = f"Command '{cmd}' failed with exit code {e.returncode}"
            self.logger.error(msg)
            self.logger.error(e.stderr.decode("utf-8"))
            raise RuntimeError(msg)

    def render(
        self,
        tex: str,
        output_file: str,
        verbose: bool = False,
        optimize_svg: bool = False,
    ):
        """Render the TeX string to the desired output file

        If a dependency is not found, logs an error message and returns

        The following template variables are available by default:
            - outdir: Absolute path to the directory of the user output file
            - filename: Name of the user output file without extension
            - out_file: Absolute path to the user output file
            - tex_file: Absolute path to the temporary latex document
            - dvi_file: Absolute path to the temporary dvi file
            - ps_file:  Absolute path to the temporary ps file
            - eps_file: Absolute path to the temporary eps file
            - svg_file: Absolute path to the temporary svg file
            - pdf_file: Absolute path to the temporary pdf file

        Args:
            tex: The full TeX document as a string.
            output_file: The path to the output file.
            verbose: If True, print the commands after being executed
            optimize_svg: If True, optimize the final svg

        Raises:
            RuntimeError: If the command executed with errors.
        """
        with TemporaryDirectory(suffix="_tex2img") as tmpdir:
            self.__render(tex, output_file, tmpdir, verbose, optimize_svg)

    def __render(
        self,
        tex: str,
        output_file: str,
        tmpdir: str,
        verbose: bool = False,
        optimize_svg: bool = False,
    ):
        if verbose:
            self.logger.setLevel(logging.INFO)

        # Where the user wants the file
        out_file = Path(output_file).resolve()
        suffix = out_file.suffix
        extension = suffix[1:]

        # User output filename without extension
        filename = out_file.stem
        # Absolute path to the temporary file without extension
        base_file = Path(tmpdir).resolve() / filename

        if not TeX2img.is_valid_suffix(suffix):
            raise ValueError(f"Invalid file extension {suffix}")

        if (
            not self.commands[extension].is_available()
            or not self.commands["dvi"].is_available()
        ):
            self.logger.error(
                f"command {self.commands[extension].cmd} not found in the system. please install it first to continue"
            )
            return

        # Props available in the command templates
        props = {
            "outdir": Path(out_file).parent.resolve(),
            "filename": filename,
            "out_file": None,
            "tex_file": base_file.with_suffix(".tex"),
            "dvi_file": base_file.with_suffix(".dvi"),
        }
        for _suffix in VALID_SUFFIXES:
            props[f"{_suffix[1:]}_file"] = base_file.with_suffix(_suffix)

        with open(props["tex_file"], "w+") as fp:
            fp.write(tex)
        self.logger.info(f"Wrote latex to {props['tex_file']}")

        self.__run_cmd("dvi", props, tmpdir)
        self.logger.info(f"Converted latex to {props['dvi_file']}")

        if suffix == ".ps":
            props["out_file"] = out_file.with_suffix(".ps")
            self.__run_cmd("ps", props, tmpdir)
            self.logger.info(f"Converted dvi to {props['out_file']}")
            return

        if suffix == ".eps":
            props["out_file"] = out_file.with_suffix(".eps")
            self.__run_cmd("eps", props, tmpdir)
            self.logger.info(f"Converted dvi to {props['out_file']}")
            return

        if suffix == ".pdf":
            props["out_file"] = base_file.with_suffix(".ps")
            self.__run_cmd("ps", props, tmpdir)
            self.logger.info(f"Converted dvi to {props['ps_file']}")

            props["out_file"] = out_file.with_suffix(".pdf")
            self.__run_cmd("pdf", props, tmpdir)
            self.logger.info(f"Converted ps to {props['out_file']}")
            return

        if suffix == ".svg":
            if optimize_svg and not self.commands["optimize"].is_available():
                self.logger.error("cannot optimize svg if scour is not found")

            elif optimize_svg and self.commands["optimize"].is_available():
                props["prefix"] = "".join(random.sample(string.ascii_letters, 5)) + "_"

                props["out_file"] = base_file.with_suffix(".svg")
                self.__run_cmd("svg", props, tmpdir)
                self.logger.info(f"Converted dvi to {props['out_file']}")

                props["svg_file"] = props["out_file"]
                props["out_file"] = out_file.with_suffix(".svg")
                self.__run_cmd("optimize", props, tmpdir)
                self.logger.info(
                    f"Optimized svg {props['svg_file']} to {props['out_file']}"
                )
                return
            else:
                props["out_file"] = out_file.with_suffix(".svg")
                self.__run_cmd("svg", props, tmpdir)
                self.logger.info(f"Converted dvi to {props['out_file']}")
                return

        if suffix in [".png", ".jpg", ".tiff"]:
            props["out_file"] = base_file.with_suffix(".ps")
            self.__run_cmd("ps", props, tmpdir)
            self.logger.info(f"Converted dvi to {props['out_file']}")

            props["out_file"] = base_file.with_suffix(".pdf")
            self.__run_cmd("pdf", props, tmpdir)
            self.logger.info(f"Converted ps to {props['out_file']}")

            props["pdf_file"] = base_file.with_suffix(".pdf")
            props["out_file"] = out_file.with_suffix(suffix)
            self.__run_cmd(extension, props, tmpdir)
            self.logger.info(f"Converted pdf to {props['out_file']}")
            return
