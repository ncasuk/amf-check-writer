"""
Read variable/dimension attribute specifications from.tsv files, and produce
JSON controlled vocabulary files
"""
import os
import sys
import argparse

from amf_check_writer.cv_handlers import BatchCvGenerator


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "spreadsheets_dir",
        help="Directory containing spreadsheet data, as produced by "
             "download_from_drive.py"
    )
    parser.add_argument(
        "output_dir",
        help="Directory to write output CVs to"
    )
    args = parser.parse_args(sys.argv[1:])

    if not os.path.isdir(args.spreadsheets_dir):
        parser.error("No such directory '{}'".format(args.spreadsheets_dir))
    if not os.path.isdir(args.output_dir):
        os.mkdir(args.output_dir)

    BatchCvGenerator.write_cvs(args.spreadsheets_dir, args.output_dir)


if __name__ == "__main__":
    main()
