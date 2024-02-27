"""
Read AMF spreadsheet TSV files, and produce JSON controlled vocabulary files.
CVs are also saved in pyessv format using pyessv directly.
"""
import os
import sys
import argparse

from amf_check_writer.spreadsheet_handler import SpreadsheetHandler
from amf_check_writer.config import ALL_VERSIONS, CURRENT_VERSION, ALL_VOCABS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-s", "--source-dir", required=True,
        help="Source directory, as downloaded and produced by "
             "`download-from-drive` script."
    )

    parser.add_argument(
        "-v", "--version", choices=ALL_VERSIONS,
        help=f"Version of the spreadsheets to use (e.g. '{CURRENT_VERSION}')."
    )

    parser.add_argument(
        "-c",
        "--vocab",
        choices = ALL_VOCABS,
        help = "Specific vocabulary to download",
        default = None,
    )

    args = parser.parse_args(sys.argv[1:])

    if (not args.version and not args.vocab) or (args.version and args.vocab):
        msg = "One and only one of -v/--version and -c/--vocab must be specified"
        parser.error(msg)

    if not os.path.isdir(args.source_dir):
        parser.error(f"No such directory '{args.source_dir}'")

    if args.version:
        version_dir = os.path.join(args.source_dir, args.version)
    else:
        version_dir = os.path.join(args.source_dir, f"vocabs/{args.vocab}")
    sh = SpreadsheetHandler(version_dir, "version" if args.version else args.vocab)

    cvs_dir = os.path.join(version_dir, "AMF_CVs")

    if not os.path.isdir(cvs_dir):
        os.makedirs(cvs_dir)

    sh.write_cvs(cvs_dir, write_pyessv=False)



if __name__ == "__main__":
    main()
