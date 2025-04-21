import sys
import argparse
from inspect import cleandoc
from pathlib import Path

from tex2img import TeX2img, DEFAULT_FONTSIZE

_DESC = cleandoc(
    r"""
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
"""
)


class ParseKwargs(argparse.Action):
    """Parses arguments as --args key=value to a dictionary

    Modified from https://sumit-ghosh.com/posts/parsing-dictionary-key-value-pairs-kwargs-argparse-python/
    """

    def __call__(self, parser, namespace, values, option_string=None):
        if not getattr(namespace, self.dest, False):
            setattr(namespace, self.dest, dict())
        key, value = values.split("=", 1)
        getattr(namespace, self.dest)[key] = value


def main():
    parser = argparse.ArgumentParser(
        description=_DESC, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "-v",
        "--verbose",
        help="print the executed commands",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--check-deps", help="check installed dependencies", action="store_true"
    )
    parser.add_argument(
        "--optimize-svg",
        help="optimize the SVG using scour",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--template-file",
        help="filepath for the document template",
        type=Path,
    )
    parser.add_argument(
        "--preamble-file",
        help="filepath for the document preamble",
        type=Path,
    )
    parser.add_argument(
        "--fontsize",
        help=f"font size. Defaults to {DEFAULT_FONTSIZE}",
        default=DEFAULT_FONTSIZE,
        type=int,
    )
    parser.add_argument(
        "-i",
        "--input-file",
        type=argparse.FileType("r", encoding="UTF-8"),
        help="path to the input TeX file.",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        help="path to the output file including extension",
    )
    parser.add_argument("body", nargs="?", help="string containing the TeX")
    parser.add_argument(
        "--param",
        dest="params",
        metavar="param='value'",
        help="template parameters",
        action=ParseKwargs,
    )
    parser.add_argument(
        "--arguments",
        action=ParseKwargs,
        dest="arguments",
        metavar="command='arguments'",
        help="command arguments",
    )

    args = vars(parser.parse_args())

    template = None
    if args["template_file"] and Path(args["template_file"]).exists():
        with open(args["template_file"], "r") as fp:
            template = fp.read()
    preamble = None
    if args["preamble_file"] and Path(args["preamble_file"]).exists():
        with open(args["preamble_file"], "r") as fp:
            template = fp.read()

    converter = TeX2img(template, preamble, args["fontsize"], args["params"])

    if args.get("arguments", False):
        for name, cmd_args in args["arguments"].items():
            if not converter.commands.get(name, False):
                converter.logger.info(f"Command {name} not found. Ignoring")
            else:
                converter.commands[name].args = cmd_args

    if args["check_deps"]:
        for name, cmd in converter.commands.items():
            print(f"[{name}] {cmd.path()}")
            print(f"{cmd.cmd} {cmd.args}\n")
        sys.exit(0)

    if args.get("input_file", False):
        body = args["input_file"].read().strip()
    else:
        body = args["body"]

    if not body:
        parser.print_usage()
        sys.exit(0)

    try:
        converter.render(
            converter.prepare(body),
            output_file=args["output_file"],
            verbose=args["verbose"],
            optimize_svg=args["optimize_svg"],
        )
    except Exception as exc:
        converter.logger.error(exc)
