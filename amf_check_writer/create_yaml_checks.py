"""
Read AMF spreadsheet TSV files and produce YAML checks that can be used with
IOOS compliance-checker via the cc-yaml plugin and compliance-check-lib
"""
import sys
import os
import argparse

from amf_check_writer.spreadsheet_handler import SpreadsheetHandler
from amf_check_writer.config import ALL_VERSIONS, CURRENT_VERSION


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "-s", "--source-dir", required=True,
        help="Source directory, as downloaded and produced by "
             "`download-from-drive` script."
    )

    parser.add_argument(
        "-v", "--version", required=True, choices=ALL_VERSIONS,
        help=f"Version of the spreadsheets to use (e.g. '{CURRENT_VERSION}')."
    )

    args = parser.parse_args(sys.argv[1:])

    if not os.path.isdir(args.source_dir):
        parser.error(f"No such directory '{args.source_dir}'")

    version_dir = os.path.join(args.source_dir, args.version)
    sh = SpreadsheetHandler(version_dir)

    checks_dir = os.path.join(version_dir, "checks")
    if not os.path.isdir(checks_dir): 
        os.makedirs(checks_dir)

    sh.write_yaml(checks_dir)


if __name__ == "__main__":
    main()
