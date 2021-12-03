"""
Read AMF spreadsheet TSV files, and produce JSON controlled vocabulary files.
CVs are also saved in pyessv format using pyessv directly.
"""
import os
import sys
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

    cvs_dir = os.path.join(version_dir, "AMF_CVs")
    pyessv_dir = os.path.join(version_dir, "amf-pyessv-vocabs")

    for dr in (cvs_dir, pyessv_dir):
        if not os.path.isdir(dr):
            os.makedirs(dr)

    sh.write_cvs(cvs_dir, write_pyessv=True,
                 pyessv_root=pyessv_dir)



if __name__ == "__main__":
    main()
