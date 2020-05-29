"""
Read AMF spreadsheet TSV files, and produce JSON controlled vocabulary files.
CVs are also saved in pyessv format using pyessv directly.
"""
import os
import sys
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
        help="Directory to write output JSON CVs to"
    )

    # Note: default dir is not actually set in this code -- if not given
    # just use pyessv's default. Will need to update the help text if this
    # ever changes...
    parser.add_argument(
        "--pyessv-dir",
        default=None,
        dest="pyessv_root",
        help="Directory to write pyessv CVs to [default: ~/.esdoc/pyessv-archive/]"
    )

    args = parser.parse_args(sys.argv[1:])

    if not os.path.isdir(args.spreadsheets_dir):
        parser.error("No such directory '{}'".format(args.spreadsheets_dir))
    for dirname in (args.output_dir, args.pyessv_root):
        if dirname and not os.path.isdir(dirname):
            os.mkdir(dirname)

    args.spreadsheets_dir = os.path.join(args.spreadsheets_dir, 'product-definitions')
    print(args.spreadsheets_dir)
    sh = SpreadsheetHandler(args.spreadsheets_dir)
    sh.write_cvs(args.output_dir, write_pyessv=True,
                 pyessv_root=args.pyessv_root)

if __name__ == "__main__":
    main()
