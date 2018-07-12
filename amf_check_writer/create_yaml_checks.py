"""
Read AMF spreadsheet TSV files and produce YAML checks that can be used with
IOOS compliance-checker via the cc-yaml plugin and compliance-check-lib
"""
import sys
import os
import argparse

from amf_check_writer.spreadsheet_handler import SpreadsheetHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "spreadsheets_dir",
        help="Directory containing spreadsheet data, as produced by "
             "download_from_drive.py"
    )
    parser.add_argument(
        "output_dir",
        help="Directory to write output YAML files to"
    )
    args = parser.parse_args(sys.argv[1:])

    if not os.path.isdir(args.spreadsheets_dir):
        parser.error("No such directory '{}'".format(args.spreadsheets_dir))
    if not os.path.isdir(args.output_dir):
        os.mkdir(args.output_dir)

    sh = SpreadsheetHandler(args.spreadsheets_dir)
    sh.write_yaml(args.output_dir)

if __name__ == "__main__":
    main()
